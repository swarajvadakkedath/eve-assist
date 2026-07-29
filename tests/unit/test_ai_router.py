"""Unit tests for AI Router, providers, rate limiter, cost tracker, and circuit breaker."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aios.core.ai_router import (
    AIRequest,
    AIResponse,
    AIProvider,
    AIRouter,
    RoutingStrategy,
    RateLimiter,
    CostTracker,
    CircuitBreaker,
)


# ---------------------------------------------------------------------------
# Fake provider helpers
# ---------------------------------------------------------------------------

class _FakeProvider(AIProvider):
    def __init__(self, name: str = "fake", caps: set[str] | None = None, fail: bool = False):
        self._name = name
        self._caps = caps or {"chat", "streaming"}
        self._fail = fail

    @property
    def model(self) -> str:
        return f"{self._name}-model"

    @property
    def capabilities(self) -> set[str]:
        return self._caps

    async def chat(self, request: AIRequest) -> AIResponse:
        if self._fail:
            raise RuntimeError(f"{self._name} failed")
        return AIResponse(content=f"response from {self._name}", provider=self._name, model=self.model, tokens_used=10, cost=0.001)

    async def chat_stream(self, request: AIRequest):
        if self._fail:
            raise RuntimeError(f"{self._name} failed")
        yield f"stream from {self._name}"

    async def embed(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]

    async def health_check(self) -> bool:
        return not self._fail


# ---------------------------------------------------------------------------
# RateLimiter
# ---------------------------------------------------------------------------

class TestRateLimiter:
    def test_allows_within_limit(self):
        limiter = RateLimiter(requests_per_minute=60, tokens_per_minute=1000)
        assert limiter.check("test", 10) is True

    def test_blocks_excess_requests(self):
        limiter = RateLimiter(requests_per_minute=1, tokens_per_minute=10000)
        assert limiter.check("test") is True
        assert limiter.check("test") is False

    def test_blocks_excess_tokens(self):
        limiter = RateLimiter(requests_per_minute=100, tokens_per_minute=100)
        assert limiter.check("test", 50) is True
        assert limiter.check("test", 60) is False

    def test_different_providers_independent(self):
        limiter = RateLimiter(requests_per_minute=1, tokens_per_minute=10000)
        assert limiter.check("a") is True
        assert limiter.check("a") is False
        assert limiter.check("b") is True

    def test_reset(self):
        limiter = RateLimiter(requests_per_minute=1, tokens_per_minute=10000)
        assert limiter.check("test") is True
        assert limiter.check("test") is False
        limiter.reset("test")
        assert limiter.check("test") is True

    def test_zero_rpm_rejects_all(self):
        limiter = RateLimiter(requests_per_minute=0, tokens_per_minute=1000)
        assert limiter.check("test") is False


# ---------------------------------------------------------------------------
# CostTracker
# ---------------------------------------------------------------------------

class TestCostTracker:
    def test_records_cost(self):
        tracker = CostTracker()
        tracker.record("openai", 0.01, 100)
        assert tracker.get_total_cost() == 0.01
        assert tracker.get_provider_cost("openai").total_tokens == 100

    def test_aggregates_multiple_requests(self):
        tracker = CostTracker()
        tracker.record("openai", 0.01, 100)
        tracker.record("openai", 0.02, 200)
        assert tracker.get_total_cost() == 0.03
        assert tracker.get_provider_cost("openai").request_count == 2
        assert tracker.get_provider_cost("openai").total_tokens == 300

    def test_multiple_providers(self):
        tracker = CostTracker()
        tracker.record("openai", 0.01, 100)
        tracker.record("anthropic", 0.02, 200)
        assert tracker.get_total_cost() == 0.03

    def test_summary(self):
        tracker = CostTracker()
        tracker.record("openai", 0.01, 100)
        summary = tracker.summary()
        assert summary["total_cost"] == 0.01
        assert summary["providers"]["openai"]["requests"] == 1

    def test_unknown_provider_returns_empty(self):
        tracker = CostTracker()
        pc = tracker.get_provider_cost("nonexistent")
        assert pc.total_cost == 0.0
        assert pc.request_count == 0

    def test_reset(self):
        tracker = CostTracker()
        tracker.record("openai", 0.01, 100)
        tracker.reset()
        assert tracker.get_total_cost() == 0.0


# ---------------------------------------------------------------------------
# CircuitBreaker
# ---------------------------------------------------------------------------

class TestCircuitBreaker:
    def test_closed_initially(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)
        assert cb.is_open("test") is False

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=30.0)
        assert cb.is_open("test") is False
        cb.record_failure("test")
        assert cb.is_open("test") is False
        cb.record_failure("test")
        assert cb.is_open("test") is True

    def test_records_success_resets(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=30.0)
        cb.record_failure("test")
        cb.record_success("test")
        assert cb.is_open("test") is False

    def test_reset(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=30.0)
        cb.record_failure("test")
        assert cb.is_open("test") is True
        cb.reset("test")
        assert cb.is_open("test") is False

    def test_independent_per_provider(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=30.0)
        cb.record_failure("a")
        assert cb.is_open("a") is True
        assert cb.is_open("b") is False


# ---------------------------------------------------------------------------
# AIRouter
# ---------------------------------------------------------------------------

class TestAIRouter:
    @pytest.mark.asyncio
    async def test_register_and_route(self):
        router = AIRouter()
        provider = _FakeProvider("primary")
        await router.register_provider("primary", provider)
        response = await router.route(AIRequest(messages=[{"role": "user", "content": "hi"}]))
        assert response.content == "response from primary"
        assert response.provider == "primary"

    @pytest.mark.asyncio
    async def test_fallback_on_failure(self):
        router = AIRouter()
        await router.register_provider("fail", _FakeProvider("fail", fail=True))
        await router.register_provider("backup", _FakeProvider("backup"))
        response = await router.route(AIRequest(messages=[{"role": "user", "content": "hi"}]))
        assert response.provider == "backup"

    @pytest.mark.asyncio
    async def test_all_providers_fail_raises(self):
        router = AIRouter()
        await router.register_provider("fail1", _FakeProvider("fail1", fail=True))
        await router.register_provider("fail2", _FakeProvider("fail2", fail=True))
        with pytest.raises(RuntimeError, match="All AI providers failed"):
            await router.route(AIRequest(messages=[{"role": "user", "content": "hi"}]))

    @pytest.mark.asyncio
    async def test_route_stream(self):
        router = AIRouter()
        await router.register_provider("primary", _FakeProvider("primary"))
        tokens = []
        async for token in router.route_stream(AIRequest(messages=[{"role": "user", "content": "hi"}])):
            tokens.append(token)
        assert "".join(tokens) == "stream from primary"

    @pytest.mark.asyncio
    async def test_route_stream_fallback(self):
        router = AIRouter()
        await router.register_provider("fail", _FakeProvider("fail", fail=True))
        await router.register_provider("backup", _FakeProvider("backup"))
        tokens = []
        async for token in router.route_stream(AIRequest(messages=[{"role": "user", "content": "hi"}])):
            tokens.append(token)
        assert "".join(tokens) == "stream from backup"

    @pytest.mark.asyncio
    async def test_health_check(self):
        router = AIRouter()
        await router.register_provider("healthy", _FakeProvider("healthy"))
        await router.register_provider("sick", _FakeProvider("sick", fail=True))
        results = await router.health_check()
        assert results["healthy"] is True
        assert results["sick"] is False

    @pytest.mark.asyncio
    async def test_get_capabilities(self):
        router = AIRouter()
        await router.register_provider("p1", _FakeProvider("p1", caps={"chat", "vision"}))
        caps = router.get_capabilities()
        assert "chat" in caps["p1"]
        assert "vision" in caps["p1"]

    @pytest.mark.asyncio
    async def test_unregister_provider(self):
        router = AIRouter()
        await router.register_provider("p1", _FakeProvider("p1"))
        assert router.get_provider("p1") is not None
        await router.unregister_provider("p1")
        assert router.get_provider("p1") is None

    @pytest.mark.asyncio
    async def test_cost_tracking_on_route(self):
        router = AIRouter()
        await router.register_provider("p1", _FakeProvider("p1"))
        await router.route(AIRequest(messages=[{"role": "user", "content": "hi"}]))
        cost = router.cost_tracker.get_provider_cost("p1")
        assert cost.request_count == 1
        assert cost.total_tokens == 10

    @pytest.mark.asyncio
    async def test_circuit_breaker_skips_open_provider(self):
        router = AIRouter()
        await router.register_provider("fail", _FakeProvider("fail", fail=True))
        await router.register_provider("backup", _FakeProvider("backup"))

        router.circuit_breaker.record_failure("fail")
        router.circuit_breaker.record_failure("fail")
        router.circuit_breaker.record_failure("fail")

        response = await router.route(AIRequest(messages=[{"role": "user", "content": "hi"}]))
        assert response.provider == "backup"

    @pytest.mark.asyncio
    async def test_rate_limiter_blocks(self):
        router = AIRouter()
        router._rate_limiter = RateLimiter(requests_per_minute=0, tokens_per_minute=1000)
        await router.register_provider("p1", _FakeProvider("p1"))
        await router.register_provider("p2", _FakeProvider("p2"))
        with pytest.raises(RuntimeError):
            await router.route(AIRequest(messages=[{"role": "user", "content": "hi"}]))

    @pytest.mark.asyncio
    async def test_can_change_strategy(self):
        router = AIRouter()
        router.set_strategy(RoutingStrategy.COST)
        await router.register_provider("a", _FakeProvider("a"))
        await router.register_provider("b", _FakeProvider("b"))
        response = await router.route(AIRequest(messages=[{"role": "user", "content": "hi"}]))
        assert response.content


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------

class TestOpenAIProvider:
    @pytest.mark.asyncio
    async def test_health_check_returns_false_when_unavailable(self):
        with patch("aios.core.providers.openai_provider.AsyncOpenAI") as mock_client:
            instance = mock_client.return_value
            instance.models.list = AsyncMock(side_effect=Exception("API error"))
            from aios.core.providers.openai_provider import OpenAIProvider
            provider = OpenAIProvider()
            result = await provider.health_check()
            assert result is False

    def test_model_property(self):
        from aios.core.providers.openai_provider import OpenAIProvider
        provider = OpenAIProvider()
        assert provider.model is not None

    def test_capabilities(self):
        from aios.core.providers.openai_provider import OpenAIProvider
        provider = OpenAIProvider()
        assert "chat" in provider.capabilities
        assert "streaming" in provider.capabilities

    def test_estimate_cost(self):
        from aios.core.providers.openai_provider import OpenAIProvider
        provider = OpenAIProvider()
        cost = provider._estimate_cost(100, 50)
        assert cost > 0


class TestAnthropicProvider:
    @pytest.mark.asyncio
    async def test_health_check_returns_false_when_unavailable(self):
        with patch("aios.core.providers.anthropic_provider.AsyncAnthropic") as mock_client:
            instance = mock_client.return_value
            instance.messages.create = AsyncMock(side_effect=Exception("API error"))
            from aios.core.providers.anthropic_provider import AnthropicProvider
            provider = AnthropicProvider()
            result = await provider.health_check()
            assert result is False

    def test_model_property(self):
        from aios.core.providers.anthropic_provider import AnthropicProvider
        provider = AnthropicProvider()
        assert provider.model is not None

    def test_capabilities(self):
        from aios.core.providers.anthropic_provider import AnthropicProvider
        provider = AnthropicProvider()
        assert "chat" in provider.capabilities

    def test_convert_messages_with_system(self):
        from aios.core.providers.anthropic_provider import AnthropicProvider
        provider = AnthropicProvider()
        msgs = [{"role": "system", "content": "You are helpful"}, {"role": "user", "content": "Hi"}]
        converted, system = provider._convert_messages(msgs)
        assert system == "You are helpful"
        assert len(converted) == 1
        assert converted[0]["role"] == "user"


class TestOllamaProvider:
    @pytest.mark.asyncio
    async def test_health_check_returns_false_when_unavailable(self):
        with patch("aios.core.providers.ollama_provider.httpx.AsyncClient") as mock_client:
            instance = mock_client.return_value
            instance.get = AsyncMock(side_effect=Exception("Connection refused"))
            from aios.core.providers.ollama_provider import OllamaProvider
            provider = OllamaProvider()
            result = await provider.health_check()
            assert result is False

    def test_model_property(self):
        from aios.core.providers.ollama_provider import OllamaProvider
        provider = OllamaProvider()
        assert provider.model is not None

    def test_capabilities(self):
        from aios.core.providers.ollama_provider import OllamaProvider
        provider = OllamaProvider()
        assert "local" in provider.capabilities
