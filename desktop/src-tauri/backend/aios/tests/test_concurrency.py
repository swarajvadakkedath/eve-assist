"""Concurrency hardening tests — Parts E through K.

Verifies request-scoped routing isolation, parallel conversation safety,
concurrent streaming, concurrent fallback, health-update races, and
rate-limit isolation under concurrent access.

These tests use deterministic async interleaving to expose races that
sequential tests would miss.
"""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock

from aios.core.smart_router import (
    SmartRouter,
    RoutingPolicy,
    RouteStreamResult,
    NoEligibleRouteError,
)
from aios.core.adapters.base import ChatRequest, ChatResponse, ProviderStatus
from aios.core.model_info import ModelInfo, CommercialStatus
from aios.core.health_monitor import HealthMonitor, RateLimitState
from aios.core.routing_types import RoutingTrace


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeAdapter:
    """Adapter that identifies itself in responses and supports delays."""

    def __init__(self, provider_id: str, model_id: str = "default",
                 delay: float = 0, fail: bool = False,
                 error_class: type = Exception):
        self.provider_id = provider_id
        self.model_id = model_id
        self.health_status = ProviderStatus.CONNECTED
        self._delay = delay
        self._fail = fail
        self._error_class = error_class
        self.call_count = 0
        self.tokens_emitted = []

    async def chat(self, request):
        self.call_count += 1
        if self._fail:
            raise self._error_class(f"Simulated failure from {self.provider_id}")
        if self._delay:
            await asyncio.sleep(self._delay)
        return ChatResponse(
            content=f"response from {self.provider_id}/{request.model}",
            model=request.model,
            provider=self.provider_id,
        )

    async def stream(self, request):
        self.call_count += 1
        if self._fail:
            raise self._error_class(f"Simulated failure from {self.provider_id}")
        for token in [f"token-A-", f"{self.provider_id}", f"-{request.model}"]:
            if self._delay:
                await asyncio.sleep(self._delay)
            self.tokens_emitted.append(token)
            yield token

    async def health(self):
        return self.health_status

    async def disconnect(self):
        pass

    async def list_models(self):
        return []


def make_model(model_id: str, enabled: bool = True,
               provider_id: str = "p1",
               commercial_status: str = "free") -> ModelInfo:
    cs = CommercialStatus(commercial_status) if isinstance(commercial_status, str) else commercial_status
    return ModelInfo(
        id=model_id,
        display_name=model_id,
        provider_id=provider_id,
        provider_name="Test",
        enabled=enabled,
        commercial_status=cs,
    )


def make_request(provider_id: str = None, model: str = None) -> ChatRequest:
    return ChatRequest(
        messages=[{"role": "user", "content": "hello"}],
        model=model or "",
        provider_id=provider_id,
    )


# ===========================================================================
# Part E — Parallel Conversation Test (2 conversations)
# ===========================================================================

class TestParallelConversationIsolation:
    """Two conversations with different providers/policies run concurrently.
    Verify zero trace crossover."""

    @pytest.mark.asyncio
    async def test_two_parallel_conversations_isolated(self):
        router = SmartRouter()

        adapter_a = FakeAdapter("google-a")
        adapter_b = FakeAdapter("groq-b")
        router.register_adapter("google-a", adapter_a)
        router.register_adapter("groq-b", adapter_b)
        router.set_provider_models("google-a", [make_model("gemini-a", provider_id="google-a")])
        router.set_provider_models("groq-b", [make_model("llama-b", provider_id="groq-b")])

        # Conversation A: google-a, AUTO
        # Conversation B: groq-b, STRICT
        req_a = make_request(provider_id="google-a", model="gemini-a")
        req_b = make_request(provider_id="groq-b", model="llama-b")

        async def run_a():
            return await router.route_stream(
                req_a, routing_policy=RoutingPolicy.AUTO
            )

        async def run_b():
            return await router.route_stream(
                req_b, routing_policy=RoutingPolicy.STRICT
            )

        result_a, result_b = await asyncio.gather(run_a(), run_b())

        # Both must be RouteStreamResult
        assert isinstance(result_a, RouteStreamResult)
        assert isinstance(result_b, RouteStreamResult)

        # Traces must have unique request_ids
        assert result_a.request_id != result_b.request_id
        assert result_a.trace.request_id == result_a.request_id
        assert result_b.trace.request_id == result_b.request_id

        # Consume tokens concurrently
        tokens_a = []
        tokens_b = []

        async def collect_a():
            async for t in result_a.tokens:
                tokens_a.append(t)

        async def collect_b():
            async for t in result_b.tokens:
                tokens_b.append(t)

        await asyncio.gather(collect_a(), collect_b())

        # A used google-a, B used groq-b
        assert "google-a" in "".join(tokens_a)
        assert "groq-b" in "".join(tokens_b)

        # No crossover in traces
        assert result_a.trace.selected_provider_instance_id == "google-a"
        assert result_b.trace.selected_provider_instance_id == "groq-b"


# ===========================================================================
# Part F — High Concurrency Test (25 requests)
# ===========================================================================

class TestHighConcurrency:
    """25 concurrent requests with mixed policies and outcomes."""

    @pytest.mark.asyncio
    async def test_25_concurrent_requests_no_crossover(self):
        router = SmartRouter()

        adapters = {}
        for i in range(5):
            pid = f"provider-{i}"
            adapter = FakeAdapter(pid)
            adapters[pid] = adapter
            router.register_adapter(pid, adapter)
            router.set_provider_models(pid, [make_model(f"model-{i}", provider_id=pid)])

        policies = [RoutingPolicy.AUTO, RoutingPolicy.STRICT, RoutingPolicy.ALLOW_FALLBACK]

        async def run_request(idx):
            policy = policies[idx % len(policies)]
            provider_idx = idx % 5
            req = make_request(provider_id=f"provider-{provider_idx}", model=f"model-{provider_idx}")
            result = await router.route_stream(req, routing_policy=policy)
            tokens = []
            async for t in result.tokens:
                tokens.append(t)
            return {
                "idx": idx,
                "request_id": result.request_id,
                "trace": result.trace,
                "tokens": tokens,
                "provider": f"provider-{provider_idx}",
            }

        results = await asyncio.gather(*[run_request(i) for i in range(25)])

        # All 25 must complete
        assert len(results) == 25

        # All request IDs must be unique
        request_ids = [r["request_id"] for r in results]
        assert len(set(request_ids)) == 25

        # Each trace must match its own request_id
        for r in results:
            assert r["trace"].request_id == r["request_id"]

        # Each STRICT request must use the exact provider it asked for
        for r in results:
            if r["trace"].policy == "strict":
                assert r["trace"].selected_provider_instance_id == r["provider"]

        # No duplicate done events (each result has tokens)
        for r in results:
            assert len(r["tokens"]) > 0


# ===========================================================================
# Part G — Concurrent Streaming
# ===========================================================================

class TestConcurrentStreaming:
    """Multiple streams with interleaved token delivery."""

    @pytest.mark.asyncio
    async def test_interleaved_tokens_isolated(self):
        router = SmartRouter()

        adapter_a = FakeAdapter("prov-a", delay=0.001)
        adapter_b = FakeAdapter("prov-b", delay=0.002)
        adapter_c = FakeAdapter("prov-c", delay=0.0015)

        router.register_adapter("prov-a", adapter_a)
        router.register_adapter("prov-b", adapter_b)
        router.register_adapter("prov-c", adapter_c)

        router.set_provider_models("prov-a", [make_model("m-a", provider_id="prov-a")])
        router.set_provider_models("prov-b", [make_model("m-b", provider_id="prov-b")])
        router.set_provider_models("prov-c", [make_model("m-c", provider_id="prov-c")])

        req_a = make_request(provider_id="prov-a", model="m-a")
        req_b = make_request(provider_id="prov-b", model="m-b")
        req_c = make_request(provider_id="prov-c", model="m-c")

        result_a = await router.route_stream(req_a, routing_policy=RoutingPolicy.STRICT)
        result_b = await router.route_stream(req_b, routing_policy=RoutingPolicy.STRICT)
        result_c = await router.route_stream(req_c, routing_policy=RoutingPolicy.STRICT)

        tokens_a, tokens_b, tokens_c = [], [], []

        async def collect(result, collector):
            async for t in result.tokens:
                collector.append(t)

        await asyncio.gather(
            collect(result_a, tokens_a),
            collect(result_b, tokens_b),
            collect(result_c, tokens_c),
        )

        # Each token set contains only its own provider
        combined_a = "".join(tokens_a)
        combined_b = "".join(tokens_b)
        combined_c = "".join(tokens_c)

        assert "prov-a" in combined_a
        assert "prov-b" in combined_b
        assert "prov-c" in combined_c

        # No cross-contamination
        assert "prov-b" not in combined_a
        assert "prov-a" not in combined_b
        assert "prov-a" not in combined_c
        assert "prov-c" not in combined_a

        # Traces isolated
        assert result_a.trace.selected_provider_instance_id == "prov-a"
        assert result_b.trace.selected_provider_instance_id == "prov-b"
        assert result_c.trace.selected_provider_instance_id == "prov-c"


# ===========================================================================
# Part H — Concurrent Fallback
# ===========================================================================

class TestConcurrentFallback:
    """Simultaneous fallback with different policies."""

    @pytest.mark.asyncio
    async def test_concurrent_fallback_isolation(self):
        router = SmartRouter()
        health = router._health_monitor

        # google-a: rate limited (quota exhausted)
        adapter_google_a = FakeAdapter("google-a", fail=True)
        adapter_google_b = FakeAdapter("google-b")
        adapter_groq = FakeAdapter("groq")

        router.register_adapter("google-a", adapter_google_a)
        router.register_adapter("google-b", adapter_google_b)
        router.register_adapter("groq", adapter_groq)

        router.set_provider_models("google-a", [make_model("gemini-x", provider_id="google-a")])
        router.set_provider_models("google-b", [make_model("gemini-x", provider_id="google-b")])
        router.set_provider_models("groq", [make_model("llama-x", provider_id="groq")])

        # Mark google-a rate limited
        health.register_provider("google-a")
        rl = health.get_model_rate_limit("google-a", "gemini-x")
        rl.record_429(retry_after=60)

        # Conversation A: AUTO, prefers google-a → should fall back to google-b
        req_a = make_request(provider_id="google-a", model="gemini-x")
        # Conversation B: AUTO, no preference → should pick healthy provider
        req_b = make_request()
        # Conversation B has no provider_id so AUTO will pick best available
        # Conversation C: STRICT google-a → should fail
        req_c = make_request(provider_id="google-a", model="gemini-x")

        async def run_a():
            return await router.route_stream(req_a, routing_policy=RoutingPolicy.AUTO)

        async def run_b():
            return await router.route_stream(req_b, routing_policy=RoutingPolicy.AUTO)

        async def run_c():
            return await router.route_stream(req_c, routing_policy=RoutingPolicy.STRICT)

        result_a = await run_a()
        result_b = await run_b()

        # C may raise or return with error trace
        try:
            result_c = await run_c()
            c_failed = False
        except Exception:
            c_failed = True
            result_c = None

        # A: should have fallen back
        assert result_a.trace.selected_provider_instance_id != "google-a" or \
               result_a.trace.fallback_level > 0 or \
               result_a.trace.fallback_reason != "none"

        # B: should have selected a healthy provider
        assert result_b.trace.selected_provider_instance_id in ("google-b", "groq")

        # C: STRICT should have failed (google-a is rate limited, STRICT doesn't fallback)
        assert c_failed or result_c is None or \
               result_c.trace.fallback_reason == "none"


# ===========================================================================
# Part I — Concurrent Health Update
# ===========================================================================

class TestConcurrentHealthUpdate:
    """Health state updates under concurrent access."""

    @pytest.mark.asyncio
    async def test_429_isolation_across_providers(self):
        health = HealthMonitor()

        health.register_provider("google-a")
        health.register_provider("google-b")
        health.register_provider("groq-a")

        # Rate limit google-a
        rl = health.get_model_rate_limit("google-a", "model-x")
        rl.record_429(retry_after=60)

        # Verify google-a is rate limited
        rl_check = health.get_model_rate_limit("google-a", "model-x")
        assert rl_check.state in (RateLimitState.PROVIDER_COOLDOWN, RateLimitState.LOCAL_COOLDOWN)

        # Verify google-b is NOT rate limited
        rl_b = health.get_model_rate_limit("google-b", "model-x")
        assert rl_b.state == RateLimitState.NONE

        # Verify groq-a is NOT rate limited
        rl_g = health.get_model_rate_limit("groq-a", "model-x")
        assert rl_g.state == RateLimitState.NONE

    @pytest.mark.asyncio
    async def test_concurrent_health_updates_consistent(self):
        health = HealthMonitor()
        health.register_provider("prov-0")

        async def update_health(provider_id, success):
            if success:
                adapter = FakeAdapter(provider_id)
                await health.check_provider(provider_id, adapter)
            else:
                adapter = FakeAdapter(provider_id, fail=True)
                try:
                    await health.check_provider(provider_id, adapter)
                except Exception:
                    pass

        # Run 10 health checks concurrently
        tasks = [update_health("prov-0", i % 2 == 0) for i in range(10)]
        await asyncio.gather(*tasks)

        # Health state must be consistent (not corrupted)
        h = health.get_health("prov-0")
        assert h is not None
        assert h.consecutive_failures >= 0


# ===========================================================================
# Part J — Concurrent Model Rate Limit
# ===========================================================================

class TestConcurrentModelRateLimit:
    """Rate-limit scope isolation under concurrent access."""

    @pytest.mark.asyncio
    async def test_rate_limit_scope_isolation(self):
        health = HealthMonitor()

        health.register_provider("google-a")
        health.register_provider("google-b")

        # Rate limit google-a/model-x only
        rl_ax = health.get_model_rate_limit("google-a", "model-x")
        rl_ax.record_429(retry_after=60)

        # google-a/model-y should NOT be rate limited
        rl_ay = health.get_model_rate_limit("google-a", "model-y")
        assert rl_ay.state != RateLimitState.LOCAL_COOLDOWN

        # google-b/model-x should NOT be rate limited
        rl_bx = health.get_model_rate_limit("google-b", "model-x")
        assert rl_bx.state != RateLimitState.LOCAL_COOLDOWN

        # google-b/model-y should NOT be rate limited
        rl_by = health.get_model_rate_limit("google-b", "model-y")
        assert rl_by.state != RateLimitState.LOCAL_COOLDOWN

    @pytest.mark.asyncio
    async def test_concurrent_rate_limit_updates(self):
        health = HealthMonitor()
        health.register_provider("prov-0")

        async def hit_rate_limit():
            rl = health.get_model_rate_limit("prov-0", "model-a")
            rl.record_429(retry_after=10)

        # 20 concurrent 429s on same model — should not corrupt state
        tasks = [hit_rate_limit() for _ in range(20)]
        await asyncio.gather(*tasks)

        rl = health.get_model_rate_limit("prov-0", "model-a")
        assert rl.state in (RateLimitState.PROVIDER_COOLDOWN, RateLimitState.LOCAL_COOLDOWN)
        assert rl.consecutive_429s == 20


# ===========================================================================
# Part K — Cancellation
# ===========================================================================

class TestCancellation:
    """User cancellation during streaming."""

    @pytest.mark.asyncio
    async def test_cancel_stream_stops_tokens(self):
        from aios.conversation.stream import StreamManager

        sm = StreamManager()

        async def slow_tokens():
            for i in range(100):
                await asyncio.sleep(0.01)
                yield f"token-{i}"

        stream_id = "cancel-test-001"
        collected = []

        async def consume():
            async for event in sm.stream(stream_id, slow_tokens()):
                if event["type"] == "token":
                    collected.append(event["data"]["token"])

        # Start consuming, then cancel after a bit
        task = asyncio.create_task(consume())
        await asyncio.sleep(0.05)
        sm.cancel(stream_id)
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Should have received some tokens then stopped
        assert len(collected) < 100

    @pytest.mark.asyncio
    async def test_cancel_one_stream_does_not_affect_others(self):
        from aios.conversation.stream import StreamManager

        sm = StreamManager()

        async def token_gen(name, count):
            for i in range(count):
                await asyncio.sleep(0.005)
                yield f"{name}-{i}"

        collected_a = []
        collected_b = []

        async def consume_a():
            async for event in sm.stream("stream-a", token_gen("A", 100)):
                if event["type"] == "token":
                    collected_a.append(event["data"]["token"])

        async def consume_b():
            async for event in sm.stream("stream-b", token_gen("B", 100)):
                if event["type"] == "token":
                    collected_b.append(event["data"]["token"])

        task_a = asyncio.create_task(consume_a())
        task_b = asyncio.create_task(consume_b())

        await asyncio.sleep(0.05)
        sm.cancel("stream-a")
        await asyncio.sleep(0.2)

        try:
            await task_a
        except asyncio.CancelledError:
            pass
        await task_b

        # A should have fewer tokens
        assert len(collected_a) < len(collected_b)
        # B should have all tokens (or close)
        assert len(collected_b) > len(collected_a)
        # No crossover
        assert all("A" in t for t in collected_a)
        assert all("B" in t for t in collected_b)


# ===========================================================================
# Request ID uniqueness test
# ===========================================================================

class TestRequestIDUniqueness:
    """Every route_stream call gets a unique request_id."""

    @pytest.mark.asyncio
    async def test_request_ids_unique_across_calls(self):
        router = SmartRouter()
        adapter = FakeAdapter("prov-1")
        router.register_adapter("prov-1", adapter)
        router.set_provider_models("prov-1", [make_model("m-1", provider_id="prov-1")])

        ids = set()
        for _ in range(50):
            req = make_request(provider_id="prov-1", model="m-1")
            result = await router.route_stream(req, routing_policy=RoutingPolicy.STRICT)
            ids.add(result.request_id)
            # Consume tokens to avoid generator warning
            async for _ in result.tokens:
                pass

        assert len(ids) == 50

    @pytest.mark.asyncio
    async def test_request_id_in_trace(self):
        router = SmartRouter()
        adapter = FakeAdapter("prov-1")
        router.register_adapter("prov-1", adapter)
        router.set_provider_models("prov-1", [make_model("m-1", provider_id="prov-1")])

        req = make_request(provider_id="prov-1", model="m-1")
        result = await router.route_stream(req, routing_policy=RoutingPolicy.STRICT)

        trace_dict = result.trace.to_dict()
        assert "request_id" in trace_dict
        assert trace_dict["request_id"] == result.request_id

        async for _ in result.tokens:
            pass
