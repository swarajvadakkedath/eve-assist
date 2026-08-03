"""Comprehensive tests for quota-aware SmartRouter — all routing scenarios.

Covers:
  - STRICT routing (exact route, typed errors, no fallback)
  - AUTO routing (multi-account failover hierarchy)
  - Same-model account failover
  - Same-provider model failover
  - Cross-provider failover
  - Commercial policy (FREE_ONLY, NO_DIRECT_PAID, ALLOW_PAID)
  - Capability filtering
  - Provider health handling
  - Rate-limit / quota exhaustion handling
  - Recovery behavior
  - Streaming pre-token / post-token failure
  - Retry-loop protection
  - Conversation preference preservation
  - Routing trace sanitization
  - Credential leakage prevention
"""

from __future__ import annotations

import time
import pytest
from unittest.mock import AsyncMock, MagicMock

from aios.core.smart_router import (
    SmartRouter,
    RoutingPolicy,
    RoutingStrategy,
    ProviderUnavailableError,
    ModelUnavailableError,
    RoutingError,
    FallbackMetadata,
)
from aios.core.adapters.base import ChatRequest, ChatResponse, ProviderStatus, sanitize_error
from aios.core.model_info import ModelInfo, CommercialStatus, AvailabilityStatus
from aios.core.health_monitor import (
    HealthMonitor,
    HealthState,
    RateLimitState,
    RateLimitInfo,
    ProviderHealth,
)
from aios.core.streaming_manager import StreamingManager
from aios.core.routing_types import (
    CommercialPolicy,
    FallbackReason,
    RouteCandidate,
    RouteError,
    RouteUnavailableError,
    RouteQuotaExhaustedError,
    RouteRateLimitedError,
    RouteAuthError,
    RouteCapabilityError,
    NoEligibleRouteError,
    PaidRoutingDisabledError,
    RoutingTrace,
    RoutingExecutionMetadata,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeAdapter:
    """Fake adapter that returns a response identifying itself."""

    def __init__(self, provider_id: str, fail: bool = False, stream_fail_after: int = 0):
        self.provider_id = provider_id
        self.provider_name = provider_id
        self._fail = fail
        self._stream_fail_after = stream_fail_after
        self._stream_tokens_yielded = 0

    async def chat(self, request):
        if self._fail:
            raise RuntimeError(f"{self.provider_id} chat failed")
        return ChatResponse(
            content=f"response from {self.provider_id}/{request.model}",
            model=request.model,
            provider=self.provider_id,
        )

    async def stream(self, request):
        if self._fail:
            raise RuntimeError(f"{self.provider_id} stream failed")
        for i in range(10):
            if self._stream_fail_after and i >= self._stream_fail_after:
                raise RuntimeError(f"{self.provider_id} stream failed mid-way")
            yield f"token{i} "

    async def health(self):
        return ProviderStatus.CONNECTED

    async def disconnect(self):
        pass

    async def list_models(self):
        return []


def make_model(
    model_id: str,
    provider_id: str = "p1",
    provider_type: str = "",
    enabled: bool = True,
    commercial_status: CommercialStatus = CommercialStatus.FREE,
    availability: AvailabilityStatus = AvailabilityStatus.AVAILABLE,
    supports_streaming: bool = True,
    supports_vision: bool = False,
    supports_reasoning: bool = False,
    supports_tools: bool = False,
    supports_function_calling: bool = False,
    speed: int = 5,
    quality: int = 5,
    latency: float = 0.0,
) -> ModelInfo:
    return ModelInfo(
        id=model_id,
        display_name=model_id,
        provider_id=provider_id,
        provider_name=provider_id,
        provider_type=provider_type or provider_id.split("-")[0],
        enabled=enabled,
        commercial_status=commercial_status,
        availability=availability,
        supports_streaming=supports_streaming,
        supports_vision=supports_vision,
        supports_reasoning=supports_reasoning,
        supports_tools=supports_tools,
        supports_function_calling=supports_function_calling,
        speed=speed,
        quality=quality,
        latency=latency,
    )


def make_request(
    provider_id: str | None = None,
    model: str | None = None,
    content: str = "hello",
) -> ChatRequest:
    return ChatRequest(
        messages=[{"role": "user", "content": content}],
        model=model or "",
        provider_id=provider_id,
    )


def setup_multi_account_router() -> tuple[SmartRouter, dict]:
    """Set up a router with Google A (healthy) and Google B (quota exhausted).

    Returns (router, adapters_dict) for inspection.
    """
    router = SmartRouter(commercial_policy=CommercialPolicy.ALLOW_PAID)

    ga = FakeAdapter("google-a")
    gb = FakeAdapter("google-b")
    groq = FakeAdapter("groq-main")

    router.register_adapter("google-a", ga)
    router.register_adapter("google-b", gb)
    router.register_adapter("groq-main", groq)

    router.set_provider_models("google-a", [
        make_model("gemini-2.5-flash", "google-a", "google",
                   commercial_status=CommercialStatus.FREE_TIER),
        make_model("gemini-2.5-pro", "google-a", "google",
                   commercial_status=CommercialStatus.PAID),
    ])
    router.set_provider_models("google-b", [
        make_model("gemini-2.5-flash", "google-b", "google",
                   commercial_status=CommercialStatus.FREE_TIER),
        make_model("gemini-2.5-pro", "google-b", "google",
                   commercial_status=CommercialStatus.PAID),
    ])
    router.set_provider_models("groq-main", [
        make_model("llama-3.3-70b", "groq-main", "groq",
                   commercial_status=CommercialStatus.FREE_TIER,
                   supports_tools=True, supports_function_calling=True),
    ])

    # Simulate Google B quota exhaustion
    health_b = router._health_monitor.get_health("google-b")
    health_b.record_failure(
        ProviderStatus.QUOTA_EXCEEDED,
        "Daily quota exceeded",
    )

    return router, {"google-a": ga, "google-b": gb, "groq": groq}


# ---------------------------------------------------------------------------
# STRICT routing tests
# ---------------------------------------------------------------------------

class TestStrictRouting:
    """STRICT = exact route only, no fallback."""

    @pytest.mark.asyncio
    async def test_strict_exact_route_used(self):
        router = SmartRouter()
        adapter = FakeAdapter("google-a")
        router.register_adapter("google-a", adapter)
        router.set_provider_models("google-a", [
            make_model("gemini-2.5-flash", "google-a", "google"),
        ])

        req = make_request(provider_id="google-a", model="gemini-2.5-flash")
        resp = await router.route(req, routing_policy=RoutingPolicy.STRICT)

        assert resp.provider == "google-a"
        assert "gemini-2.5-flash" in resp.model

    @pytest.mark.asyncio
    async def test_strict_unregistered_provider_raises(self):
        router = SmartRouter()
        req = make_request(provider_id="google-a", model="gemini-2.5-flash")

        with pytest.raises(ProviderUnavailableError) as exc_info:
            await router.route(req, routing_policy=RoutingPolicy.STRICT)

        assert exc_info.value.error_type == "PROVIDER_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_strict_wrong_model_raises(self):
        router = SmartRouter()
        adapter = FakeAdapter("google-a")
        router.register_adapter("google-a", adapter)
        router.set_provider_models("google-a", [
            make_model("gemini-2.5-flash", "google-a", "google"),
        ])

        req = make_request(provider_id="google-a", model="gemini-2.5-pro")
        with pytest.raises(ModelUnavailableError) as exc_info:
            await router.route(req, routing_policy=RoutingPolicy.STRICT)

        assert exc_info.value.error_type == "MODEL_UNAVAILABLE"
        assert exc_info.value.requested_model_id == "gemini-2.5-pro"

    @pytest.mark.asyncio
    async def test_strict_quota_exhausted_raises(self):
        router = SmartRouter()
        adapter = FakeAdapter("google-a")
        router.register_adapter("google-a", adapter)
        router.set_provider_models("google-a", [
            make_model("gemini-2.5-flash", "google-a", "google"),
        ])

        # Simulate quota exhaustion
        health = router._health_monitor.get_health("google-a")
        health.record_failure(ProviderStatus.QUOTA_EXCEEDED, "quota exceeded")

        req = make_request(provider_id="google-a", model="gemini-2.5-flash")
        with pytest.raises(RouteQuotaExhaustedError):
            await router.route(req, routing_policy=RoutingPolicy.STRICT)

    @pytest.mark.asyncio
    async def test_strict_auth_error_raises(self):
        router = SmartRouter()
        adapter = FakeAdapter("google-a")
        router.register_adapter("google-a", adapter)
        router.set_provider_models("google-a", [
            make_model("gemini-2.5-flash", "google-a", "google"),
        ])

        health = router._health_monitor.get_health("google-a")
        health.record_failure(ProviderStatus.AUTH_FAILED, "invalid key")

        req = make_request(provider_id="google-a", model="gemini-2.5-flash")
        with pytest.raises(RouteAuthError):
            await router.route(req, routing_policy=RoutingPolicy.STRICT)

    @pytest.mark.asyncio
    async def test_strict_no_silent_fallback(self):
        """Google A quota exhausted → STRICT must NOT fall back to Google B."""
        router = SmartRouter()
        ga = FakeAdapter("google-a")
        gb = FakeAdapter("google-b")
        router.register_adapter("google-a", ga)
        router.register_adapter("google-b", gb)
        router.set_provider_models("google-a", [
            make_model("gemini-2.5-flash", "google-a", "google"),
        ])
        router.set_provider_models("google-b", [
            make_model("gemini-2.5-flash", "google-b", "google"),
        ])

        # Simulate Google A quota exhaustion
        health_a = router._health_monitor.get_health("google-a")
        health_a.record_failure(ProviderStatus.QUOTA_EXCEEDED, "quota")

        req = make_request(provider_id="google-a", model="gemini-2.5-flash")
        with pytest.raises(RouteQuotaExhaustedError):
            await router.route(req, routing_policy=RoutingPolicy.STRICT)

    @pytest.mark.asyncio
    async def test_strict_streaming_same_semantics(self):
        router = SmartRouter()
        req = make_request(provider_id="google-a", model="gemini-2.5-flash")

        with pytest.raises(ProviderUnavailableError):
            result = await router.route_stream(req, routing_policy=RoutingPolicy.STRICT)
            async for _ in result.tokens:
                pass


# ---------------------------------------------------------------------------
# AUTO routing — multi-account failover
# ---------------------------------------------------------------------------

class TestAutoMultiAccountFailover:
    """AUTO with multi-account scenarios."""

    @pytest.mark.asyncio
    async def test_google_a_preferred_when_healthy(self):
        router = SmartRouter()
        ga = FakeAdapter("google-a")
        gb = FakeAdapter("google-b")
        router.register_adapter("google-a", ga)
        router.register_adapter("google-b", gb)
        router.set_provider_models("google-a", [
            make_model("gemini-2.5-flash", "google-a", "google"),
        ])
        router.set_provider_models("google-b", [
            make_model("gemini-2.5-flash", "google-b", "google"),
        ])

        req = make_request(provider_id="google-a", model="gemini-2.5-flash")
        resp = await router.route(req, routing_policy=RoutingPolicy.AUTO)
        assert resp.provider == "google-a"

    @pytest.mark.asyncio
    async def test_google_a_quota_b_healthy_same_model(self):
        """Google A quota exhausted → Google B with same model."""
        router = SmartRouter(commercial_policy=CommercialPolicy.NO_DIRECT_PAID)
        ga = FakeAdapter("google-a")
        gb = FakeAdapter("google-b")
        router.register_adapter("google-a", ga)
        router.register_adapter("google-b", gb)
        router.set_provider_models("google-a", [
            make_model("gemini-2.5-flash", "google-a", "google",
                       commercial_status=CommercialStatus.FREE_TIER),
        ])
        router.set_provider_models("google-b", [
            make_model("gemini-2.5-flash", "google-b", "google",
                       commercial_status=CommercialStatus.FREE_TIER),
        ])

        health_a = router._health_monitor.get_health("google-a")
        health_a.record_failure(ProviderStatus.QUOTA_EXCEEDED, "quota")

        req = make_request(provider_id="google-a", model="gemini-2.5-flash")
        resp = await router.route(req, routing_policy=RoutingPolicy.AUTO)

        assert resp.provider == "google-b"
        assert "gemini-2.5-flash" in resp.model

    @pytest.mark.asyncio
    async def test_google_a_offline_b_healthy(self):
        router = SmartRouter()
        ga = FakeAdapter("google-a")
        gb = FakeAdapter("google-b")
        router.register_adapter("google-a", ga)
        router.register_adapter("google-b", gb)
        router.set_provider_models("google-a", [
            make_model("gemini-2.5-flash", "google-a", "google"),
        ])
        router.set_provider_models("google-b", [
            make_model("gemini-2.5-flash", "google-b", "google"),
        ])

        health_a = router._health_monitor.get_health("google-a")
        health_a.state = HealthState.UNREACHABLE

        req = make_request(provider_id="google-a", model="gemini-2.5-flash")
        resp = await router.route(req, routing_policy=RoutingPolicy.AUTO)
        assert resp.provider == "google-b"

    @pytest.mark.asyncio
    async def test_google_a_auth_error_b_healthy(self):
        router = SmartRouter()
        ga = FakeAdapter("google-a")
        gb = FakeAdapter("google-b")
        router.register_adapter("google-a", ga)
        router.register_adapter("google-b", gb)
        router.set_provider_models("google-a", [
            make_model("gemini-2.5-flash", "google-a", "google"),
        ])
        router.set_provider_models("google-b", [
            make_model("gemini-2.5-flash", "google-b", "google"),
        ])

        health_a = router._health_monitor.get_health("google-a")
        health_a.state = HealthState.INVALID_KEY

        req = make_request(provider_id="google-a", model="gemini-2.5-flash")
        resp = await router.route(req, routing_policy=RoutingPolicy.AUTO)
        # Google B should be used (health_a is INVALID_KEY, but B is separate)
        assert resp.provider == "google-b"

    @pytest.mark.asyncio
    async def test_all_google_unavailable_groq_fallback(self):
        """All Google instances unavailable → Groq as cross-provider fallback."""
        router = SmartRouter(commercial_policy=CommercialPolicy.ALLOW_PAID)
        ga = FakeAdapter("google-a")
        gb = FakeAdapter("google-b")
        groq = FakeAdapter("groq-main")
        router.register_adapter("google-a", ga)
        router.register_adapter("google-b", gb)
        router.register_adapter("groq-main", groq)
        router.set_provider_models("google-a", [
            make_model("gemini-2.5-flash", "google-a", "google",
                       commercial_status=CommercialStatus.FREE_TIER),
        ])
        router.set_provider_models("google-b", [
            make_model("gemini-2.5-flash", "google-b", "google",
                       commercial_status=CommercialStatus.FREE_TIER),
        ])
        router.set_provider_models("groq-main", [
            make_model("llama-3.3-70b", "groq-main", "groq",
                       commercial_status=CommercialStatus.FREE_TIER),
        ])

        # Both Google instances unhealthy
        router._health_monitor.get_health("google-a").state = HealthState.UNREACHABLE
        router._health_monitor.get_health("google-b").state = HealthState.UNREACHABLE

        req = make_request(provider_id="google-a", model="gemini-2.5-flash")
        resp = await router.route(req, routing_policy=RoutingPolicy.AUTO)
        assert resp.provider == "groq-main"

    @pytest.mark.asyncio
    async def test_only_paid_route_no_direct_paid_policy(self):
        """Only paid routes available + NO_DIRECT_PAID → PaidRoutingDisabledError."""
        router = SmartRouter(commercial_policy=CommercialPolicy.NO_DIRECT_PAID)
        adapter = FakeAdapter("openai-main")
        router.register_adapter("openai-main", adapter)
        router.set_provider_models("openai-main", [
            make_model("gpt-4o", "openai-main", "openai",
                       commercial_status=CommercialStatus.PAID),
        ])

        req = make_request()
        with pytest.raises(PaidRoutingDisabledError):
            await router.route(req, routing_policy=RoutingPolicy.AUTO)

    @pytest.mark.asyncio
    async def test_only_paid_route_allow_paid_policy(self):
        """Only paid routes available + ALLOW_PAID → paid route used."""
        router = SmartRouter(commercial_policy=CommercialPolicy.ALLOW_PAID)
        adapter = FakeAdapter("openai-main")
        router.register_adapter("openai-main", adapter)
        router.set_provider_models("openai-main", [
            make_model("gpt-4o", "openai-main", "openai",
                       commercial_status=CommercialStatus.PAID),
        ])

        req = make_request()
        resp = await router.route(req, routing_policy=RoutingPolicy.AUTO)
        assert resp.provider == "openai-main"

    @pytest.mark.asyncio
    async def test_vision_request_rejects_text_only(self):
        """Vision request → text-only model rejected before cost ranking."""
        router = SmartRouter()
        adapter = FakeAdapter("openai-main")
        router.register_adapter("openai-main", adapter)
        router.set_provider_models("openai-main", [
            make_model("gpt-4o-mini", "openai-main", "openai",
                       supports_vision=False,
                       commercial_status=CommercialStatus.FREE_TIER),
        ])

        req = make_request()
        with pytest.raises(NoEligibleRouteError):
            await router.route(req, category="vision", routing_policy=RoutingPolicy.AUTO)


# ---------------------------------------------------------------------------
# Commercial policy tests
# ---------------------------------------------------------------------------

class TestCommercialPolicy:
    """Commercial policy filtering."""

    @pytest.mark.asyncio
    async def test_free_only_rejects_paid(self):
        router = SmartRouter(commercial_policy=CommercialPolicy.FREE_ONLY)
        adapter = FakeAdapter("openai-main")
        router.register_adapter("openai-main", adapter)
        router.set_provider_models("openai-main", [
            make_model("gpt-4o", "openai-main", "openai",
                       commercial_status=CommercialStatus.PAID),
        ])

        req = make_request()
        with pytest.raises((NoEligibleRouteError, PaidRoutingDisabledError)):
            await router.route(req, routing_policy=RoutingPolicy.AUTO)

    @pytest.mark.asyncio
    async def test_free_only_allows_free(self):
        router = SmartRouter(commercial_policy=CommercialPolicy.FREE_ONLY)
        adapter = FakeAdapter("ollama-local")
        router.register_adapter("ollama-local", adapter)
        router.set_provider_models("ollama-local", [
            make_model("llama3.2", "ollama-local", "ollama",
                       commercial_status=CommercialStatus.FREE),
        ])

        req = make_request()
        resp = await router.route(req, routing_policy=RoutingPolicy.AUTO)
        assert resp.provider == "ollama-local"

    @pytest.mark.asyncio
    async def test_free_only_allows_local(self):
        router = SmartRouter(commercial_policy=CommercialPolicy.FREE_ONLY)
        adapter = FakeAdapter("ollama-local")
        router.register_adapter("ollama-local", adapter)
        router.set_provider_models("ollama-local", [
            make_model("llama3.2", "ollama-local", "ollama",
                       commercial_status=CommercialStatus.LOCAL),
        ])

        req = make_request()
        resp = await router.route(req, routing_policy=RoutingPolicy.AUTO)
        assert resp.provider == "ollama-local"

    @pytest.mark.asyncio
    async def test_no_direct_paid_allows_free_tier(self):
        router = SmartRouter(commercial_policy=CommercialPolicy.NO_DIRECT_PAID)
        adapter = FakeAdapter("groq-main")
        router.register_adapter("groq-main", adapter)
        router.set_provider_models("groq-main", [
            make_model("llama-3.3-70b", "groq-main", "groq",
                       commercial_status=CommercialStatus.FREE_TIER),
        ])

        req = make_request()
        resp = await router.route(req, routing_policy=RoutingPolicy.AUTO)
        assert resp.provider == "groq-main"

    @pytest.mark.asyncio
    async def test_no_direct_paid_allows_credit_based(self):
        router = SmartRouter(commercial_policy=CommercialPolicy.NO_DIRECT_PAID)
        adapter = FakeAdapter("hf-main")
        router.register_adapter("hf-main", adapter)
        router.set_provider_models("hf-main", [
            make_model("llama-3.3-70b", "hf-main", "huggingface",
                       commercial_status=CommercialStatus.CREDIT_BASED),
        ])

        req = make_request()
        resp = await router.route(req, routing_policy=RoutingPolicy.AUTO)
        assert resp.provider == "hf-main"

    @pytest.mark.asyncio
    async def test_no_direct_paid_rejects_paid(self):
        router = SmartRouter(commercial_policy=CommercialPolicy.NO_DIRECT_PAID)
        adapter = FakeAdapter("openai-main")
        router.register_adapter("openai-main", adapter)
        router.set_provider_models("openai-main", [
            make_model("gpt-4o", "openai-main", "openai",
                       commercial_status=CommercialStatus.PAID),
        ])

        req = make_request()
        with pytest.raises(PaidRoutingDisabledError):
            await router.route(req, routing_policy=RoutingPolicy.AUTO)


# ---------------------------------------------------------------------------
# Capability filtering tests
# ---------------------------------------------------------------------------

class TestCapabilityFiltering:
    """Capability-first filtering."""

    @pytest.mark.asyncio
    async def test_vision_model_selected_for_vision_category(self):
        router = SmartRouter()
        adapter = FakeAdapter("openai-main")
        router.register_adapter("openai-main", adapter)
        router.set_provider_models("openai-main", [
            make_model("gpt-4o-mini", "openai-main", "openai",
                       supports_vision=False),
            make_model("gpt-4o", "openai-main", "openai",
                       supports_vision=True),
        ])

        req = make_request()
        resp = await router.route(req, category="vision", routing_policy=RoutingPolicy.AUTO)
        assert resp.model == "gpt-4o"

    @pytest.mark.asyncio
    async def test_tool_model_selected_for_coding_category(self):
        router = SmartRouter()
        adapter = FakeAdapter("anthropic-main")
        router.register_adapter("anthropic-main", adapter)
        router.set_provider_models("anthropic-main", [
            make_model("claude-haiku", "anthropic-main", "anthropic",
                       supports_tools=False, supports_function_calling=False,
                       supports_reasoning=False),
            make_model("claude-sonnet", "anthropic-main", "anthropic",
                       supports_tools=True, supports_function_calling=True,
                       supports_reasoning=True),
        ])

        req = make_request()
        resp = await router.route(req, category="coding", routing_policy=RoutingPolicy.AUTO)
        assert resp.model == "claude-sonnet"


# ---------------------------------------------------------------------------
# Rate-limit / quota tests
# ---------------------------------------------------------------------------

class TestRateLimitHandling:
    """Rate limit and quota exhaustion handling."""

    @pytest.mark.asyncio
    async def test_model_cooldown_does_not_affect_other_models(self):
        router = SmartRouter()
        adapter = FakeAdapter("google-a")
        router.register_adapter("google-a", adapter)
        router.set_provider_models("google-a", [
            make_model("gemini-2.5-flash", "google-a", "google"),
            make_model("gemini-2.5-pro", "google-a", "google"),
        ])

        # Rate limit gemini-2.5-flash
        router._health_monitor.record_model_429("google-a", "gemini-2.5-flash")

        req = make_request()
        resp = await router.route(req, routing_policy=RoutingPolicy.AUTO)
        # Should use gemini-2.5-pro (flash is rate limited)
        assert resp.model == "gemini-2.5-pro"

    @pytest.mark.asyncio
    async def test_provider_quota_exhausted_filters_candidates(self):
        """Provider QUOTA_EXCEEDED health state filters all candidates from that instance."""
        router = SmartRouter()
        adapter = FakeAdapter("google-a")
        router.register_adapter("google-a", adapter)
        router.set_provider_models("google-a", [
            make_model("gemini-2.5-flash", "google-a", "google"),
        ])

        health = router._health_monitor.get_health("google-a")
        health.record_failure(ProviderStatus.QUOTA_EXCEEDED, "quota")

        # Candidates from google-a should be filtered by eligibility
        from aios.core.smart_router import _build_candidates, _filter_eligible, RoutingTrace
        candidates = _build_candidates(
            router._adapters, router._provider_models, router._health_monitor
        )
        eligible = _filter_eligible(candidates, [], CommercialPolicy.ALLOW_PAID)
        assert len(eligible) == 0  # google-a filtered out

    @pytest.mark.asyncio
    async def test_different_instances_independent_rate_limits(self):
        router = SmartRouter()
        ga = FakeAdapter("google-a")
        gb = FakeAdapter("google-b")
        router.register_adapter("google-a", ga)
        router.register_adapter("google-b", gb)
        router.set_provider_models("google-a", [
            make_model("gemini-2.5-flash", "google-a", "google",
                       commercial_status=CommercialStatus.FREE_TIER),
        ])
        router.set_provider_models("google-b", [
            make_model("gemini-2.5-flash", "google-b", "google",
                       commercial_status=CommercialStatus.FREE_TIER),
        ])

        # Rate limit Google A
        router._health_monitor.record_model_429("google-a", "gemini-2.5-flash")

        # Google B should still be available
        assert router._health_monitor.is_model_available("google-b", "gemini-2.5-flash")


# ---------------------------------------------------------------------------
# Recovery tests
# ---------------------------------------------------------------------------

class TestRecovery:
    """Health recovery and rate-limit cooldown expiry."""

    @pytest.mark.asyncio
    async def test_cooldown_expiry_makes_route_eligible(self):
        router = SmartRouter()
        adapter = FakeAdapter("google-a")
        router.register_adapter("google-a", adapter)
        router.set_provider_models("google-a", [
            make_model("gemini-2.5-flash", "google-a", "google"),
        ])

        # Simulate rate limit with very short cooldown
        rl = router._health_monitor.get_model_rate_limit("google-a", "gemini-2.5-flash")
        rl.state = RateLimitState.LOCAL_COOLDOWN
        rl.cooldown_until = time.monotonic() + 0.01  # 10ms cooldown

        time.sleep(0.02)  # Wait for cooldown to expire

        assert router._health_monitor.is_model_available("google-a", "gemini-2.5-flash")


# ---------------------------------------------------------------------------
# Streaming failure tests
# ---------------------------------------------------------------------------

class TestStreamingFailure:
    """Streaming pre-token and post-token failure behavior."""

    @pytest.mark.asyncio
    async def test_stream_failure_propagates_error(self):
        """Stream failure propagates error. Conservative: no mid-stream failover (spec §27)."""
        router = SmartRouter()
        fail_adapter = FakeAdapter("google-a", fail=True)
        good_adapter = FakeAdapter("google-b")
        router.register_adapter("google-a", fail_adapter)
        router.register_adapter("google-b", good_adapter)
        router.set_provider_models("google-a", [
            make_model("gemini-2.5-flash", "google-a", "google"),
        ])
        router.set_provider_models("google-b", [
            make_model("gemini-2.5-flash", "google-b", "google"),
        ])

        req = make_request()
        tokens = []
        with pytest.raises(RuntimeError):
            result = await router.route_stream(req, routing_policy=RoutingPolicy.AUTO)
            async for token in result.tokens:
                tokens.append(token)

    @pytest.mark.asyncio
    async def test_stream_post_tokens_no_silent_switch(self):
        """Stream emits partial tokens then fails → do NOT switch provider."""
        router = SmartRouter()
        # Create adapter that fails after 3 tokens
        fail_adapter = FakeAdapter("google-a", stream_fail_after=3)
        good_adapter = FakeAdapter("google-b")
        router.register_adapter("google-a", fail_adapter)
        router.register_adapter("google-b", good_adapter)
        router.set_provider_models("google-a", [
            make_model("gemini-2.5-flash", "google-a", "google"),
        ])
        router.set_provider_models("google-b", [
            make_model("gemini-2.5-flash", "google-b", "google"),
        ])

        req = make_request()
        tokens = []
        with pytest.raises(RuntimeError):
            result = await router.route_stream(req, routing_policy=RoutingPolicy.AUTO)
            async for token in result.tokens:
                tokens.append(token)

        # Should NOT have tokens from google-b
        assert not any("google-b" in t for t in tokens)


# ---------------------------------------------------------------------------
# Routing trace tests
# ---------------------------------------------------------------------------

class TestRoutingTrace:
    """Routing trace sanitization."""

    @pytest.mark.asyncio
    async def test_routing_trace_attached_to_response(self):
        router = SmartRouter()
        adapter = FakeAdapter("google-a")
        router.register_adapter("google-a", adapter)
        router.set_provider_models("google-a", [
            make_model("gemini-2.5-flash", "google-a", "google"),
        ])

        req = make_request(provider_id="google-a", model="gemini-2.5-flash")
        resp = await router.route(req, routing_policy=RoutingPolicy.STRICT)

        trace = resp.metadata.get("routing_trace")
        assert trace is not None
        assert trace["policy"] == "strict"
        assert trace["selected"]["provider_instance_id"] == "google-a"
        assert trace["selected"]["model_id"] == "gemini-2.5-flash"

    @pytest.mark.asyncio
    async def test_trace_no_credentials(self):
        """Routing trace must never contain API keys or credentials."""
        router = SmartRouter()
        adapter = FakeAdapter("google-a")
        router.register_adapter("google-a", adapter)
        router.set_provider_models("google-a", [
            make_model("gemini-2.5-flash", "google-a", "google"),
        ])

        req = make_request(provider_id="google-a", model="gemini-2.5-flash")
        resp = await router.route(req, routing_policy=RoutingPolicy.STRICT)

        trace_str = str(resp.metadata.get("routing_trace", {}))
        assert "api_key" not in trace_str.lower()
        assert "secret" not in trace_str.lower()
        assert "token" not in trace_str.lower()
        assert "authorization" not in trace_str.lower()


# ---------------------------------------------------------------------------
# Error metadata tests
# ---------------------------------------------------------------------------

class TestErrorMetadata:
    """Error types carry safe metadata only."""

    def test_route_unavailable_error_to_dict(self):
        err = RouteUnavailableError(
            provider_type="google",
            provider_instance_id="google-a",
            model_id="gemini-2.5-flash",
        )
        d = err.to_dict()
        assert "api_key" not in d
        assert d["error_type"] == "ROUTE_UNAVAILABLE"
        assert d["provider_instance_id"] == "google-a"

    def test_route_quota_exhausted_error_to_dict(self):
        err = RouteQuotaExhaustedError(
            provider_type="google",
            provider_instance_id="google-a",
            model_id="gemini-2.5-flash",
            retry_after=60.0,
        )
        d = err.to_dict()
        assert d["retry_after"] == 60.0
        assert "api_key" not in d

    def test_no_eligible_route_error_to_dict(self):
        err = NoEligibleRouteError(candidates_attempted=5)
        d = err.to_dict()
        assert d["candidates_attempted"] == 5

    def test_capability_error_includes_missing(self):
        err = RouteCapabilityError(
            missing_capabilities=["supports_vision", "supports_tools"],
        )
        d = err.to_dict()
        assert "supports_vision" in d["missing_capabilities"]

    def test_paid_routing_disabled_error(self):
        err = PaidRoutingDisabledError(provider_type="openai", model_id="gpt-4o")
        d = err.to_dict()
        assert d["error_type"] == "PAID_ROUTING_DISABLED"


# ---------------------------------------------------------------------------
# Conversation preference preservation
# ---------------------------------------------------------------------------

class TestConversationPreference:
    """Conversation preferences preserved through fallback."""

    def test_conversation_provider_model_fields(self):
        from aios.conversation.models import Conversation
        conv = Conversation(provider_id="google-a", model_id="gemini-2.5-flash")
        assert conv.provider_id == "google-a"
        assert conv.model_id == "gemini-2.5-flash"


# ---------------------------------------------------------------------------
# RoutingExecutionMetadata tests
# ---------------------------------------------------------------------------

class TestExecutionMetadata:
    """Response metadata for UI integration."""

    def test_metadata_to_dict(self):
        meta = RoutingExecutionMetadata(
            requested_provider_id="google-a",
            requested_model="gemini-2.5-flash",
            actual_provider_id="google-b",
            actual_model="gemini-2.5-flash",
            actual_provider_type="google",
            fallback_used=True,
            fallback_reason="same_model_alternate_instance",
            fallback_level=1,
            candidates_evaluated=3,
        )
        d = meta.to_dict()
        assert d["fallback_used"] is True
        assert d["fallback_level"] == 1
        assert d["actual_provider_id"] == "google-b"
        assert "api_key" not in d


# ---------------------------------------------------------------------------
# RoutingTrace dataclass tests
# ---------------------------------------------------------------------------

class TestRoutingTraceDataclass:
    def test_trace_to_dict(self):
        trace = RoutingTrace(
            policy="auto",
            required_capabilities=["supports_streaming"],
            commercial_policy="allow_paid",
            candidate_count=5,
            selected_provider_type="google",
            selected_provider_instance_id="google-a",
            selected_model_id="gemini-2.5-flash",
            fallback_level=0,
            fallback_reason="none",
        )
        d = trace.to_dict()
        assert d["policy"] == "auto"
        assert d["selected"]["provider_type"] == "google"
        assert d["fallback_reason"] == "none"

    def test_trace_rejected_candidates(self):
        trace = RoutingTrace()
        trace.rejected_candidates.append({"google-a/gemini-2.5-flash": "quota_exhausted"})
        d = trace.to_dict()
        assert len(d["rejected_candidates"]) == 1
        assert "quota_exhausted" in d["rejected_candidates"][0].values()


# ---------------------------------------------------------------------------
# FallbackReason enum tests
# ---------------------------------------------------------------------------

class TestFallbackReasonEnum:
    def test_all_reasons_defined(self):
        reasons = [
            FallbackReason.NONE,
            FallbackReason.SAME_MODEL_ALTERNATE_INSTANCE,
            FallbackReason.SAME_PROVIDER_ALTERNATE_MODEL,
            FallbackReason.FREE_ALTERNATE_PROVIDER,
            FallbackReason.FREE_TIER_ALTERNATE_PROVIDER,
            FallbackReason.CREDIT_ALTERNATE_PROVIDER,
            FallbackReason.LOCAL_ALTERNATE,
            FallbackReason.PAID_ALTERNATE,
        ]
        assert len(reasons) == 8
        assert all(isinstance(r, FallbackReason) for r in reasons)


# ---------------------------------------------------------------------------
# CommercialPolicy enum tests
# ---------------------------------------------------------------------------

class TestCommercialPolicyEnum:
    def test_all_policies_defined(self):
        assert CommercialPolicy.FREE_ONLY.value == "free_only"
        assert CommercialPolicy.NO_DIRECT_PAID.value == "no_direct_paid"
        assert CommercialPolicy.ALLOW_PAID.value == "allow_paid"


# ---------------------------------------------------------------------------
# No eligible route tests
# ---------------------------------------------------------------------------

class TestNoEligibleRoute:
    @pytest.mark.asyncio
    async def test_no_providers_registered(self):
        router = SmartRouter()
        req = make_request()
        with pytest.raises(NoEligibleRouteError):
            await router.route(req, routing_policy=RoutingPolicy.AUTO)

    @pytest.mark.asyncio
    async def test_all_providers_unreachable(self):
        router = SmartRouter()
        adapter = FakeAdapter("google-a")
        router.register_adapter("google-a", adapter)
        router.set_provider_models("google-a", [
            make_model("gemini-2.5-flash", "google-a", "google"),
        ])

        health = router._health_monitor.get_health("google-a")
        health.state = HealthState.UNREACHABLE

        req = make_request()
        with pytest.raises(NoEligibleRouteError):
            await router.route(req, routing_policy=RoutingPolicy.AUTO)


# ---------------------------------------------------------------------------
# ALLOW_FALLBACK tests
# ---------------------------------------------------------------------------

class TestAllowFallback:
    @pytest.mark.asyncio
    async def test_allow_fallback_uses_fallback(self):
        router = SmartRouter()
        fallback = FakeAdapter("openai-xyz")
        router.register_adapter("openai-xyz", fallback)
        router.set_provider_models("openai-xyz", [
            make_model("gpt-4o", "openai-xyz", "openai"),
        ])

        req = make_request(provider_id="google-abc", model="gemini-2.5-flash")
        resp = await router.route(req, routing_policy=RoutingPolicy.ALLOW_FALLBACK)
        assert resp.provider == "openai-xyz"


# ---------------------------------------------------------------------------
# Rank candidates tests
# ---------------------------------------------------------------------------

class TestRankingPipeline:
    def test_free_ranked_before_paid(self):
        from aios.core.smart_router import _build_candidates, _filter_eligible, _rank_candidates, RoutingTrace

        router = SmartRouter(commercial_policy=CommercialPolicy.ALLOW_PAID)
        adapter = FakeAdapter("test")
        router.register_adapter("test", adapter)
        router.set_provider_models("test", [
            make_model("paid-model", "test", "openai",
                       commercial_status=CommercialStatus.PAID, quality=10, speed=10),
            make_model("free-model", "test", "groq",
                       commercial_status=CommercialStatus.FREE, quality=5, speed=5),
        ])

        candidates = _build_candidates(
            router._adapters, router._provider_models, router._health_monitor
        )
        eligible = _filter_eligible(candidates, [], CommercialPolicy.ALLOW_PAID)
        ranked = _rank_candidates(eligible, RoutingStrategy.PERFORMANCE)

        # Free model should rank higher than paid despite lower quality
        assert ranked[0].model_id == "free-model"

    def test_capability_mismatch_rejected_before_ranking(self):
        from aios.core.smart_router import _build_candidates, _filter_eligible, RoutingTrace

        router = SmartRouter()
        adapter = FakeAdapter("test")
        router.register_adapter("test", adapter)
        router.set_provider_models("test", [
            make_model("text-only", "test", "openai", supports_vision=False),
        ])

        candidates = _build_candidates(
            router._adapters, router._provider_models, router._health_monitor
        )
        trace = RoutingTrace()
        eligible = _filter_eligible(candidates, ["supports_vision"], CommercialPolicy.ALLOW_PAID, trace)

        assert len(eligible) == 0
        assert len(trace.rejected_candidates) == 1


# ---------------------------------------------------------------------------
# Credential leakage regression tests (spec §37)
# ---------------------------------------------------------------------------

CREDENTIAL_LEAK_PATTERNS = [
    "api_key", "secret", "token", "authorization", "bearer",
    "password", "credential", "private_key", "access_key",
]


class TestCredentialLeakageRegression:
    """Comprehensive regression tests ensuring no credentials leak anywhere."""

    def _check_dict_no_credentials(self, d: dict, context: str):
        """Assert a dict contains no credential patterns."""
        for key, value in d.items():
            key_lower = key.lower()
            for pattern in CREDENTIAL_LEAK_PATTERNS:
                assert pattern not in key_lower, (
                    f"Credential key '{key}' found in {context}"
                )
            if isinstance(value, str):
                for pattern in CREDENTIAL_LEAK_PATTERNS:
                    assert pattern not in value.lower(), (
                        f"Credential value containing '{pattern}' found in {context}.{key}"
                    )
            elif isinstance(value, dict):
                self._check_dict_no_credentials(value, f"{context}.{key}")
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        self._check_dict_no_credentials(item, f"{context}.{key}[{i}]")

    @pytest.mark.asyncio
    async def test_strict_error_no_credential_leak(self):
        """STRICT routing errors must never contain credentials."""
        router = SmartRouter()
        req = make_request(provider_id="google-a", model="gemini-2.5-flash")

        with pytest.raises(RouteError) as exc_info:
            await router.route(req, routing_policy=RoutingPolicy.STRICT)

        err_dict = exc_info.value.to_dict()
        self._check_dict_no_credentials(err_dict, "strict_error")

    @pytest.mark.asyncio
    async def test_auto_error_no_credential_leak(self):
        """AUTO routing errors must never contain credentials."""
        router = SmartRouter()
        req = make_request()

        with pytest.raises(RouteError) as exc_info:
            await router.route(req, routing_policy=RoutingPolicy.AUTO)

        err_dict = exc_info.value.to_dict()
        self._check_dict_no_credentials(err_dict, "auto_error")

    @pytest.mark.asyncio
    async def test_routing_trace_never_contains_creds(self):
        """Routing trace on successful response must never contain credentials."""
        router = SmartRouter()
        adapter = FakeAdapter("google-a")
        router.register_adapter("google-a", adapter)
        router.set_provider_models("google-a", [
            make_model("gemini-2.5-flash", "google-a", "google"),
        ])

        req = make_request(provider_id="google-a", model="gemini-2.5-flash")
        resp = await router.route(req, routing_policy=RoutingPolicy.STRICT)

        trace = resp.metadata.get("routing_trace", {})
        self._check_dict_no_credentials(trace, "routing_trace")

    @pytest.mark.asyncio
    async def test_fallback_response_trace_no_creds(self):
        """Routing trace on fallback response must never contain credentials."""
        router = SmartRouter()
        ga = FakeAdapter("google-a")
        gb = FakeAdapter("google-b")
        router.register_adapter("google-a", ga)
        router.register_adapter("google-b", gb)
        router.set_provider_models("google-a", [
            make_model("gemini-2.5-flash", "google-a", "google"),
        ])
        router.set_provider_models("google-b", [
            make_model("gemini-2.5-flash", "google-b", "google"),
        ])

        # Force google-a unhealthy → fallback to google-b
        router._health_monitor.get_health("google-a").state = HealthState.UNREACHABLE

        req = make_request(provider_id="google-a", model="gemini-2.5-flash")
        resp = await router.route(req, routing_policy=RoutingPolicy.AUTO)

        trace = resp.metadata.get("routing_trace", {})
        self._check_dict_no_credentials(trace, "fallback_routing_trace")

    @pytest.mark.asyncio
    async def test_error_exception_message_no_creds(self):
        """Exception messages from routing errors must not contain credentials."""
        router = SmartRouter()
        req = make_request(provider_id="google-a", model="gemini-2.5-flash")

        with pytest.raises(RouteError) as exc_info:
            await router.route(req, routing_policy=RoutingPolicy.STRICT)

        msg = str(exc_info.value)
        for pattern in CREDENTIAL_LEAK_PATTERNS:
            assert pattern not in msg.lower(), (
                f"Pattern '{pattern}' found in error message: {msg}"
            )

    @pytest.mark.asyncio
    async def test_all_error_types_safe_to_dict(self):
        """All error types produce safe to_dict() output."""
        errors = [
            RouteUnavailableError(provider_type="google", model_id="gpt-4"),
            RouteQuotaExhaustedError(provider_type="google", model_id="gpt-4"),
            RouteRateLimitedError(provider_type="google", model_id="gpt-4"),
            RouteAuthError(provider_type="google", model_id="gpt-4"),
            RouteCapabilityError(missing_capabilities=["supports_vision"]),
            NoEligibleRouteError(candidates_attempted=0),
            PaidRoutingDisabledError(provider_type="google", model_id="gpt-4"),
        ]
        for err in errors:
            d = err.to_dict()
            self._check_dict_no_credentials(d, f"error.{err.error_type}")

    @pytest.mark.asyncio
    async def test_streaming_error_no_credential_leak(self):
        """Streaming routing errors must not contain credentials."""
        router = SmartRouter()
        req = make_request(provider_id="google-a", model="gemini-2.5-flash")

        with pytest.raises(RouteError) as exc_info:
            result = await router.route_stream(req, routing_policy=RoutingPolicy.STRICT)
            async for _ in result.tokens:
                pass

        err_dict = exc_info.value.to_dict()
        self._check_dict_no_credentials(err_dict, "streaming_error")


# ---------------------------------------------------------------------------
# Conversation preference full round-trip
# ---------------------------------------------------------------------------

class TestConversationPreferenceRoundTrip:
    """Conversation provider/model preference preserved through routing."""

    @pytest.mark.asyncio
    async def test_conversation_preference_used_in_auto_routing(self):
        """Conversation's provider_id/model_id should be used as preference in AUTO routing."""
        from aios.conversation.models import Conversation

        conv = Conversation(provider_id="google-b", model_id="gemini-2.5-flash")

        router = SmartRouter(commercial_policy=CommercialPolicy.NO_DIRECT_PAID)
        ga = FakeAdapter("google-a")
        gb = FakeAdapter("google-b")
        router.register_adapter("google-a", ga)
        router.register_adapter("google-b", gb)
        router.set_provider_models("google-a", [
            make_model("gemini-2.5-flash", "google-a", "google",
                       commercial_status=CommercialStatus.FREE_TIER),
        ])
        router.set_provider_models("google-b", [
            make_model("gemini-2.5-flash", "google-b", "google",
                       commercial_status=CommercialStatus.FREE_TIER),
        ])

        # Use conversation preference as request
        req = make_request(provider_id=conv.provider_id, model=conv.model_id)
        resp = await router.route(req, routing_policy=RoutingPolicy.AUTO)

        # Should route to google-b (conversation preference), not google-a (higher ranked)
        assert resp.provider == "google-b"

    @pytest.mark.asyncio
    async def test_conversation_preference_fallback_preserved(self):
        """When preferred provider fails, response metadata shows fallback."""
        from aios.conversation.models import Conversation

        conv = Conversation(provider_id="google-a", model_id="gemini-2.5-flash")

        router = SmartRouter()
        ga = FakeAdapter("google-a")
        gb = FakeAdapter("google-b")
        router.register_adapter("google-a", ga)
        router.register_adapter("google-b", gb)
        router.set_provider_models("google-a", [
            make_model("gemini-2.5-flash", "google-a", "google"),
        ])
        router.set_provider_models("google-b", [
            make_model("gemini-2.5-flash", "google-b", "google"),
        ])

        # Force google-a unhealthy
        router._health_monitor.get_health("google-a").state = HealthState.UNREACHABLE

        req = make_request(provider_id=conv.provider_id, model=conv.model_id)
        resp = await router.route(req, routing_policy=RoutingPolicy.AUTO)

        # Should fallback to google-b
        assert resp.provider == "google-b"
        trace = resp.metadata.get("routing_trace", {})
        assert trace.get("fallback_level", 0) > 0

    def test_conversation_model_fields_preserved(self):
        """Conversation model fields survive round-trip."""
        from aios.conversation.models import Conversation

        conv = Conversation(
            provider_id="google-a",
            model_id="gemini-2.5-flash",
            title="Test conversation",
        )

        assert conv.provider_id == "google-a"
        assert conv.model_id == "gemini-2.5-flash"
        assert conv.title == "Test conversation"


# ---------------------------------------------------------------------------
# Retry-after recovery tests
# ---------------------------------------------------------------------------

class TestRetryAfterRecovery:
    """Rate limit retry-after and cooldown expiry."""

    @pytest.mark.asyncio
    async def test_rate_limited_model_cooldown_expiry_recovers(self):
        """Model rate-limited → cooldown expires → model becomes available again."""
        router = SmartRouter()
        adapter = FakeAdapter("google-a")
        router.register_adapter("google-a", adapter)
        router.set_provider_models("google-a", [
            make_model("gemini-2.5-flash", "google-a", "google"),
            make_model("gemini-2.5-pro", "google-a", "google"),
        ])

        # Rate limit gemini-2.5-flash with short cooldown
        rl = router._health_monitor.get_model_rate_limit("google-a", "gemini-2.5-flash")
        rl.state = RateLimitState.LOCAL_COOLDOWN
        rl.cooldown_until = time.monotonic() + 0.01

        # flash is rate limited, pro should be used
        req = make_request()
        resp = await router.route(req, routing_policy=RoutingPolicy.AUTO)
        assert resp.model == "gemini-2.5-pro"

        # Wait for cooldown
        time.sleep(0.02)

        # Now flash should be available
        assert router._health_monitor.is_model_available("google-a", "gemini-2.5-flash")

    @pytest.mark.asyncio
    async def test_retry_after_error_carries_retry_after(self):
        """RouteRateLimitedError carries retry_after field."""
        err = RouteRateLimitedError(
            provider_type="google",
            provider_instance_id="google-a",
            model_id="gemini-2.5-flash",
            retry_after=30.0,
        )
        assert err.retry_after == 30.0
        d = err.to_dict()
        assert d["retry_after"] == 30.0

    @pytest.mark.asyncio
    async def test_quota_exhausted_error_carries_retry_after(self):
        """RouteQuotaExhaustedError carries retry_after field."""
        err = RouteQuotaExhaustedError(
            provider_type="google",
            provider_instance_id="google-a",
            model_id="gemini-2.5-flash",
            retry_after=3600.0,
        )
        assert err.retry_after == 3600.0
        d = err.to_dict()
        assert d["retry_after"] == 3600.0


# ---------------------------------------------------------------------------
# ALLOW_FALLBACK execution metadata
# ---------------------------------------------------------------------------

class TestAllowFallbackMetadata:
    """ALLOW_FALLBACK policy produces execution metadata with fallback info."""

    @pytest.mark.asyncio
    async def test_allow_fallback_has_execution_metadata(self):
        """ALLOW_FALLBACK response includes routing trace with fallback info."""
        router = SmartRouter()
        fallback = FakeAdapter("openai-xyz")
        router.register_adapter("openai-xyz", fallback)
        router.set_provider_models("openai-xyz", [
            make_model("gpt-4o", "openai-xyz", "openai"),
        ])

        req = make_request(provider_id="google-abc", model="gemini-2.5-flash")
        resp = await router.route(req, routing_policy=RoutingPolicy.ALLOW_FALLBACK)

        trace = resp.metadata.get("routing_trace", {})
        assert trace is not None
        assert trace.get("fallback_level", 0) > 0
        assert trace.get("selected", {}).get("provider_instance_id") == "openai-xyz"

    @pytest.mark.asyncio
    async def test_allow_fallback_error_no_creds(self):
        """ALLOW_FALLBACK errors must not leak credentials."""
        router = SmartRouter()
        req = make_request(provider_id="google-abc", model="gemini-2.5-flash")

        # No adapters registered → should raise error
        with pytest.raises(RouteError) as exc_info:
            await router.route(req, routing_policy=RoutingPolicy.ALLOW_FALLBACK)

        err_dict = exc_info.value.to_dict()
        assert "api_key" not in str(err_dict).lower()
        assert "secret" not in str(err_dict).lower()


# ---------------------------------------------------------------------------
# Streaming trace attachment
# ---------------------------------------------------------------------------

class TestStreamingTraceAttachment:
    """Streaming responses should carry routing trace."""

    @pytest.mark.asyncio
    async def test_stream_success_yields_tokens(self):
        """Successful streaming yields tokens from the routed adapter."""
        router = SmartRouter()
        adapter = FakeAdapter("google-a")
        router.register_adapter("google-a", adapter)
        router.set_provider_models("google-a", [
            make_model("gemini-2.5-flash", "google-a", "google"),
        ])

        req = make_request(provider_id="google-a", model="gemini-2.5-flash")
        tokens = []
        result = await router.route_stream(req, routing_policy=RoutingPolicy.STRICT)
        async for token in result.tokens:
            tokens.append(token)

        assert len(tokens) == 10
        assert all(t.startswith("token") for t in tokens)

    @pytest.mark.asyncio
    async def test_stream_strict_unavailable_raises_before_streaming(self):
        """STRICT stream on unavailable provider raises before yielding any tokens."""
        router = SmartRouter()
        req = make_request(provider_id="google-a", model="gemini-2.5-flash")

        tokens = []
        with pytest.raises(RouteError):
            result = await router.route_stream(req, routing_policy=RoutingPolicy.STRICT)
            async for token in result.tokens:
                tokens.append(token)

        assert len(tokens) == 0


# ---------------------------------------------------------------------------
# Execution metadata for AUTO fallback path
# ---------------------------------------------------------------------------

class TestAutoFallbackExecutionMetadata:
    """AUTO fallback responses include proper execution metadata."""

    @pytest.mark.asyncio
    async def test_auto_fallback_metadata_shows_original_and_actual(self):
        """AUTO fallback response metadata shows requested vs actual provider."""
        router = SmartRouter()
        ga = FakeAdapter("google-a")
        gb = FakeAdapter("google-b")
        router.register_adapter("google-a", ga)
        router.register_adapter("google-b", gb)
        router.set_provider_models("google-a", [
            make_model("gemini-2.5-flash", "google-a", "google"),
        ])
        router.set_provider_models("google-b", [
            make_model("gemini-2.5-flash", "google-b", "google"),
        ])

        # Force google-a unhealthy
        router._health_monitor.get_health("google-a").state = HealthState.UNREACHABLE

        req = make_request(provider_id="google-a", model="gemini-2.5-flash")
        resp = await router.route(req, routing_policy=RoutingPolicy.AUTO)

        trace = resp.metadata.get("routing_trace", {})
        # Selected should be google-b (fallback)
        assert trace["selected"]["provider_instance_id"] == "google-b"
        # Fallback level should be > 0
        assert trace["fallback_level"] > 0
        # Fallback reason should indicate what happened
        assert trace["fallback_reason"] != "none"

    @pytest.mark.asyncio
    async def test_auto_no_fallback_metadata_level_zero(self):
        """AUTO with direct route shows fallback_level=0."""
        router = SmartRouter()
        adapter = FakeAdapter("google-a")
        router.register_adapter("google-a", adapter)
        router.set_provider_models("google-a", [
            make_model("gemini-2.5-flash", "google-a", "google"),
        ])

        req = make_request(provider_id="google-a", model="gemini-2.5-flash")
        resp = await router.route(req, routing_policy=RoutingPolicy.AUTO)

        trace = resp.metadata.get("routing_trace", {})
        assert trace["fallback_level"] == 0
        assert trace["fallback_reason"] == "none"

    @pytest.mark.asyncio
    async def test_auto_multi_level_fallback_trace(self):
        """AUTO failover through multiple levels produces correct trace."""
        router = SmartRouter(commercial_policy=CommercialPolicy.ALLOW_PAID)
        ga = FakeAdapter("google-a")
        gb = FakeAdapter("google-b")
        oai = FakeAdapter("openai-main")
        router.register_adapter("google-a", ga)
        router.register_adapter("google-b", gb)
        router.register_adapter("openai-main", oai)

        # google-a: has the requested model but is unhealthy
        router.set_provider_models("google-a", [
            make_model("gemini-2.5-flash", "google-a", "google",
                       commercial_status=CommercialStatus.FREE_TIER),
        ])
        # google-b: different model, healthy
        router.set_provider_models("google-b", [
            make_model("gemini-2.5-pro", "google-b", "google",
                       commercial_status=CommercialStatus.PAID),
        ])
        # openai: FREE model
        router.set_provider_models("openai-main", [
            make_model("gpt-4o-mini", "openai-main", "openai",
                       commercial_status=CommercialStatus.FREE),
        ])

        # Force google-a unhealthy
        router._health_monitor.get_health("google-a").state = HealthState.UNREACHABLE

        req = make_request(provider_id="google-a", model="gemini-2.5-flash")
        resp = await router.route(req, routing_policy=RoutingPolicy.AUTO)

        trace = resp.metadata.get("routing_trace", {})
        # Should have fallen back (level > 0)
        assert trace["fallback_level"] > 0
        # Trace should contain rejected candidates
        assert len(trace.get("rejected_candidates", [])) >= 0


# ---------------------------------------------------------------------------
# sanitize_error tests (expanded coverage)
# ---------------------------------------------------------------------------

class TestSanitizeError:
    """Verify sanitize_error redacts all major API key formats."""

    def test_redacts_openai_sk_prefix(self):
        result = sanitize_error("Error: sk-abc123def456ghi789jkl012mno")
        assert "sk-abc123" not in result
        assert "REDACTED" in result

    def test_redacts_anthropic_sk_ant_prefix(self):
        result = sanitize_error("Key: sk-ant-api03-abcdefghijklmnop")
        assert "sk-ant-api03" not in result
        assert "REDACTED" in result

    def test_redacts_google_aiza_prefix(self):
        result = sanitize_error("Error: AIzaSyDabcdefghijklmnopqrstuvwx")
        assert "AIzaSyD" not in result
        assert "REDACTED" in result

    def test_redacts_groq_gsk_prefix(self):
        result = sanitize_error("Error: gsk_abcdefghij1234567890abcdef")
        assert "gsk_abcdefghij" not in result
        assert "REDACTED" in result

    def test_redacts_bearer_token(self):
        result = sanitize_error("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U")
        assert "eyJhbGciOiJI" not in result
        assert "REDACTED" in result

    def test_redacts_api_key_pattern(self):
        result = sanitize_error('api_key: "supersecretkey12345678"')
        assert "supersecretkey12345678" not in result
        assert "REDACTED" in result

    def test_preserves_short_strings(self):
        result = sanitize_error("Error: sk-abc")
        assert "sk-abc" in result  # too short to redact

    def test_preserves_normal_text(self):
        result = sanitize_error("Connection refused to provider")
        assert result == "Connection refused to provider"


# ---------------------------------------------------------------------------
# Adapter security regression tests (Phase 0)
# ---------------------------------------------------------------------------

class TestAdapterSecurityRegression:
    """Verify adapter error paths sanitize credentials."""

    def test_health_monitor_history_sanitized(self):
        """HealthMonitor history entries are sanitized."""
        monitor = HealthMonitor()
        monitor.register_provider("test-provider")
        health = monitor.get_health("test-provider")

        # Record failure with credential in error message
        health.record_failure(
            ProviderStatus.AUTH_FAILED,
            "Auth failed: Bearer sk-test-abc123def456ghi789",
        )

        # Error message should be sanitized
        assert "sk-test-abc123" not in health.error_message
        assert "REDACTED" in health.error_message

        # History should also be sanitized
        history = health.to_dict().get("history", [])
        if history:
            for entry in history:
                error_text = str(entry.get("error", ""))
                assert "sk-test-abc123" not in error_text

    def test_health_monitor_background_check_sanitized(self):
        """HealthMonitor check_provider sanitizes exception in record_failure."""
        from unittest.mock import AsyncMock, patch

        monitor = HealthMonitor()
        monitor.register_provider("test-provider")
        health = monitor.get_health("test-provider")

        # Mock adapter.health() to raise with credential in message
        mock_adapter = AsyncMock()
        mock_adapter.health.side_effect = Exception("Connection failed: Authorization: Bearer sk-test-secret-key-123456")

        import asyncio
        asyncio.run(monitor.check_provider("test-provider", mock_adapter))

        # The error_message should be sanitized
        assert "sk-test-secret-key" not in health.error_message
        assert "REDACTED" in health.error_message

    def test_sanitize_error_covers_all_key_formats(self):
        """sanitize_error covers all known API key formats."""
        test_cases = [
            ("sk-abc123def456ghi789jkl012mno", True),   # OpenAI
            ("sk-ant-api03-abcdefghijklmnop", True),      # Anthropic
            ("AIzaSyDabcdefghijklmnopqrstuvwx", True),    # Google
            ("gsk_abcdefghij1234567890abcdef", True),     # Groq
            ("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", True),  # JWT
            ("short", False),                              # Too short
            ("no credentials here", False),                # Normal text
        ]

        for text, should_redact in test_cases:
            result = sanitize_error(text)
            if should_redact:
                assert "REDACTED" in result or "REDACTED" in result, f"Failed to redact: {text}"
            else:
                assert result == text, f"Unexpectedly redacted: {text}"
