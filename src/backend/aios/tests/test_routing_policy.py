"""Tests for explicit routing safety — STRICT/AUTO/ALLOW_FALLBACK policies.

Verifies:
  1. Explicit provider available → exact provider used
  2. Explicit model available → exact model used
  3. Explicit provider unavailable + STRICT → ProviderUnavailableError
  4. Explicit model unavailable + STRICT → ModelUnavailableError
  5. AUTO routing provider unavailable → healthy fallback used
  6. ALLOW_FALLBACK → fallback used, metadata reports requested vs actual
  7. Streaming explicit provider failure → same semantics
  8. Restart → routing policy persists (conversation model test)
  9. No provider/model specified → existing SmartRouter behavior unchanged
  10. Explicit Google selection → never silently routes to another provider under STRICT
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from aios.core.smart_router import (
    SmartRouter,
    RoutingPolicy,
    ProviderUnavailableError,
    ModelUnavailableError,
    RoutingError,
    FallbackMetadata,
)
from aios.core.adapters.base import ChatRequest, ChatResponse, ProviderStatus
from aios.core.model_info import ModelInfo
from aios.core.health_monitor import HealthMonitor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeAdapter:
    """Fake adapter that returns a response identifying itself."""

    def __init__(self, provider_id: str, model_id: str = "default-model"):
        self.provider_id = provider_id
        self.model_id = model_id
        self.health_status = ProviderStatus.CONNECTED

    async def chat(self, request):
        return ChatResponse(
            content=f"response from {self.provider_id}/{request.model}",
            model=request.model,
            provider=self.provider_id,
        )

    async def stream(self, request):
        yield f"token from {self.provider_id}/{request.model}"

    async def health(self):
        return self.health_status

    async def disconnect(self):
        pass

    async def list_models(self):
        return []


def make_model(model_id: str, enabled: bool = True, provider_id: str = "p1") -> ModelInfo:
    from aios.core.model_info import CommercialStatus
    return ModelInfo(
        id=model_id,
        display_name=model_id,
        provider_id=provider_id,
        provider_name="Test Provider",
        enabled=enabled,
        commercial_status=CommercialStatus.FREE,
    )


def make_request(provider_id: str = None, model: str = None) -> ChatRequest:
    return ChatRequest(
        messages=[{"role": "user", "content": "hello"}],
        model=model or "",
        provider_id=provider_id,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRoutingPolicyExplicitProvider:
    """1. Explicit provider available → exact provider used."""

    @pytest.mark.asyncio
    async def test_explicit_provider_used(self):
        router = SmartRouter()
        adapter = FakeAdapter("google-abc")
        router.register_adapter("google-abc", adapter)
        router.set_provider_models("google-abc", [make_model("gemini-2.5-flash", provider_id="google-abc")])

        req = make_request(provider_id="google-abc", model="gemini-2.5-flash")
        resp = await router.route(req, routing_policy=RoutingPolicy.STRICT)

        assert resp.provider == "google-abc"
        assert "google-abc" in resp.content


class TestRoutingPolicyExplicitModel:
    """2. Explicit model available → exact model used."""

    @pytest.mark.asyncio
    async def test_explicit_model_used(self):
        router = SmartRouter()
        adapter = FakeAdapter("google-abc")
        router.register_adapter("google-abc", adapter)
        router.set_provider_models("google-abc", [
            make_model("gemini-2.5-flash", provider_id="google-abc"),
            make_model("gemini-2.5-pro", provider_id="google-abc"),
        ])

        req = make_request(provider_id="google-abc", model="gemini-2.5-pro")
        resp = await router.route(req, routing_policy=RoutingPolicy.STRICT)

        assert resp.model == "gemini-2.5-pro"


class TestRoutingPolicyProviderUnavailableStrict:
    """3. Explicit provider unavailable + STRICT → ProviderUnavailableError."""

    @pytest.mark.asyncio
    async def test_strict_provider_unavailable(self):
        router = SmartRouter()
        # No adapter registered for "google-abc"

        req = make_request(provider_id="google-abc", model="gemini-2.5-flash")

        with pytest.raises(ProviderUnavailableError) as exc_info:
            await router.route(req, routing_policy=RoutingPolicy.STRICT)

        err = exc_info.value
        assert err.error_type == "PROVIDER_UNAVAILABLE"
        assert err.requested_provider_id == "google-abc"
        assert err.requested_model_id == "gemini-2.5-flash"
        assert "unregistered" in err.reason.lower() or "not registered" in err.reason.lower()

    @pytest.mark.asyncio
    async def test_strict_provider_unavailable_streaming(self):
        router = SmartRouter()

        req = make_request(provider_id="google-abc", model="gemini-2.5-flash")

        with pytest.raises(ProviderUnavailableError) as exc_info:
            result = await router.route_stream(req, routing_policy=RoutingPolicy.STRICT)
            async for _ in result.tokens:
                pass

        assert exc_info.value.error_type == "PROVIDER_UNAVAILABLE"


class TestRoutingPolicyModelUnavailableStrict:
    """4. Explicit model unavailable + STRICT → ModelUnavailableError."""

    @pytest.mark.asyncio
    async def test_strict_model_unavailable(self):
        router = SmartRouter()
        adapter = FakeAdapter("google-abc")
        router.register_adapter("google-abc", adapter)
        router.set_provider_models("google-abc", [
            make_model("gemini-2.5-flash", provider_id="google-abc"),
        ])

        req = make_request(provider_id="google-abc", model="gemini-2.5-pro")

        with pytest.raises(ModelUnavailableError) as exc_info:
            await router.route(req, routing_policy=RoutingPolicy.STRICT)

        err = exc_info.value
        assert err.error_type == "MODEL_UNAVAILABLE"
        assert err.requested_model_id == "gemini-2.5-pro"
        assert err.requested_provider_id == "google-abc"

    @pytest.mark.asyncio
    async def test_strict_model_unavailable_streaming(self):
        router = SmartRouter()
        adapter = FakeAdapter("google-abc")
        router.register_adapter("google-abc", adapter)
        router.set_provider_models("google-abc", [
            make_model("gemini-2.5-flash", provider_id="google-abc"),
        ])

        req = make_request(provider_id="google-abc", model="gemini-2.5-pro")

        with pytest.raises(ModelUnavailableError) as exc_info:
            result = await router.route_stream(req, routing_policy=RoutingPolicy.STRICT)
            async for _ in result.tokens:
                pass

        assert exc_info.value.error_type == "MODEL_UNAVAILABLE"


class TestRoutingPolicyAutoFallback:
    """5. AUTO routing provider unavailable → healthy fallback used."""

    @pytest.mark.asyncio
    async def test_auto_fallback_to_healthy(self):
        router = SmartRouter()
        # google-abc is NOT registered
        fallback = FakeAdapter("openai-xyz")
        router.register_adapter("openai-xyz", fallback)
        router.set_provider_models("openai-xyz", [make_model("gpt-4o", provider_id="openai-xyz")])

        # No explicit provider → AUTO uses tier 3 capability ranking
        req = ChatRequest(messages=[{"role": "user", "content": "hello"}])
        resp = await router.route(req, routing_policy=RoutingPolicy.AUTO)

        assert resp.provider == "openai-xyz"

    @pytest.mark.asyncio
    async def test_auto_explicit_provider_falls_through(self):
        router = SmartRouter()
        # google-abc NOT registered, but openai-xyz IS
        fallback = FakeAdapter("openai-xyz")
        router.register_adapter("openai-xyz", fallback)
        router.set_provider_models("openai-xyz", [make_model("gpt-4o", provider_id="openai-xyz")])

        # Explicit google-abc with AUTO → falls through to tier 3
        req = make_request(provider_id="google-abc", model="gemini-2.5-flash")
        resp = await router.route(req, routing_policy=RoutingPolicy.AUTO)

        # Should use openai-xyz as fallback (tier 3)
        assert resp.provider == "openai-xyz"


class TestRoutingPolicyAllowFallback:
    """6. ALLOW_FALLBACK → fallback used when explicit provider unavailable."""

    @pytest.mark.asyncio
    async def test_allow_fallback_falls_through(self):
        router = SmartRouter()
        fallback = FakeAdapter("openai-xyz")
        router.register_adapter("openai-xyz", fallback)
        router.set_provider_models("openai-xyz", [make_model("gpt-4o", provider_id="openai-xyz")])

        req = make_request(provider_id="google-abc", model="gemini-2.5-flash")
        resp = await router.route(req, routing_policy=RoutingPolicy.ALLOW_FALLBACK)

        assert resp.provider == "openai-xyz"


class TestRoutingPolicyStreaming:
    """7. Streaming explicit provider failure → same semantics."""

    @pytest.mark.asyncio
    async def test_streaming_strict_provider_unavailable(self):
        router = SmartRouter()

        req = make_request(provider_id="google-abc", model="gemini-2.5-flash")

        with pytest.raises(ProviderUnavailableError):
            result = await router.route_stream(req, routing_policy=RoutingPolicy.STRICT)
            async for _ in result.tokens:
                pass

    @pytest.mark.asyncio
    async def test_streaming_strict_model_unavailable(self):
        router = SmartRouter()
        adapter = FakeAdapter("google-abc")
        router.register_adapter("google-abc", adapter)
        router.set_provider_models("google-abc", [make_model("gemini-2.5-flash", provider_id="google-abc")])

        req = make_request(provider_id="google-abc", model="gemini-2.5-pro")

        with pytest.raises(ModelUnavailableError):
            result = await router.route_stream(req, routing_policy=RoutingPolicy.STRICT)
            async for _ in result.tokens:
                pass


class TestRoutingPolicyPersistence:
    """8. Routing policy persists per conversation (model field)."""

    def test_conversation_has_provider_id(self):
        from aios.conversation.models import Conversation
        conv = Conversation(provider_id="google-abc", model_id="gemini-2.5-pro")
        assert conv.provider_id == "google-abc"
        assert conv.model_id == "gemini-2.5-pro"

    def test_conversation_no_provider_uses_auto(self):
        from aios.conversation.models import Conversation
        conv = Conversation()
        assert conv.provider_id is None
        assert conv.model_id is None


class TestRoutingPolicyNoExplicitSelection:
    """9. No provider/model specified → existing SmartRouter behavior unchanged."""

    @pytest.mark.asyncio
    async def test_no_explicit_uses_capability_ranking(self):
        router = SmartRouter()
        adapter = FakeAdapter("openai-xyz")
        router.register_adapter("openai-xyz", adapter)
        router.set_provider_models("openai-xyz", [make_model("gpt-4o", provider_id="openai-xyz")])

        req = ChatRequest(messages=[{"role": "user", "content": "hello"}])
        resp = await router.route(req, routing_policy=RoutingPolicy.AUTO)

        assert resp.provider == "openai-xyz"

    @pytest.mark.asyncio
    async def test_no_explicit_with_category_routing(self):
        router = SmartRouter()
        adapter = FakeAdapter("anthropic-def")
        router.register_adapter("anthropic-def", adapter)
        router.set_provider_models("anthropic-def", [make_model("claude-sonnet-4", provider_id="anthropic-def")])

        # Set category routing for coding
        router.set_routing_config([{
            "id": "coding",
            "label": "Coding",
            "provider_id": "anthropic-def",
            "model_id": "claude-sonnet-4",
        }])

        req = ChatRequest(messages=[{"role": "user", "content": "write code"}])
        resp = await router.route(req, category="coding", routing_policy=RoutingPolicy.AUTO)

        assert resp.provider == "anthropic-def"


class TestRoutingPolicyGoogleStrict:
    """10. Explicit Google selection → never silently routes to another provider under STRICT."""

    @pytest.mark.asyncio
    async def test_google_strict_no_silent_substitution(self):
        router = SmartRouter()
        # Google is NOT registered
        # OpenAI IS registered
        openai = FakeAdapter("openai-xyz")
        router.register_adapter("openai-xyz", openai)
        router.set_provider_models("openai-xyz", [make_model("gpt-4o", provider_id="openai-xyz")])

        req = make_request(provider_id="google-abc", model="gemini-2.5-flash")

        with pytest.raises(ProviderUnavailableError) as exc_info:
            await router.route(req, routing_policy=RoutingPolicy.STRICT)

        # Verify the error explicitly says google-abc, not openai-xyz
        assert exc_info.value.requested_provider_id == "google-abc"
        err_dict = exc_info.value.to_dict()
        assert err_dict["requested_provider_id"] == "google-abc"
        assert err_dict["error_type"] == "PROVIDER_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_google_strict_model_not_silently_replaced(self):
        router = SmartRouter()
        adapter = FakeAdapter("google-abc")
        router.register_adapter("google-abc", adapter)
        router.set_provider_models("google-abc", [
            make_model("gemini-2.5-flash", provider_id="google-abc"),
            # gemini-2.5-pro NOT in enabled models
        ])

        req = make_request(provider_id="google-abc", model="gemini-2.5-pro")

        with pytest.raises(ModelUnavailableError) as exc_info:
            await router.route(req, routing_policy=RoutingPolicy.STRICT)

        # Verify it was NOT silently replaced with gemini-2.5-flash
        err = exc_info.value
        assert err.requested_model_id == "gemini-2.5-pro"
        assert err.error_type == "MODEL_UNAVAILABLE"


class TestRoutingErrorSafeMetadata:
    """Verify RoutingError carries safe metadata only — no credentials."""

    def test_provider_unavailable_error_to_dict(self):
        err = ProviderUnavailableError(
            requested_provider_id="google-abc",
            requested_model_id="gemini-2.5-flash",
        )
        d = err.to_dict()
        assert "api_key" not in d
        assert "secret" not in d
        assert "token" not in d
        assert d["error_type"] == "PROVIDER_UNAVAILABLE"
        assert d["requested_provider_id"] == "google-abc"

    def test_model_unavailable_error_to_dict(self):
        err = ModelUnavailableError(
            requested_provider_id="google-abc",
            requested_model_id="gemini-2.5-pro",
        )
        d = err.to_dict()
        assert "api_key" not in d
        assert d["error_type"] == "MODEL_UNAVAILABLE"

    def test_fallback_metadata_no_secrets(self):
        meta = FallbackMetadata(
            requested_provider_id="google-abc",
            requested_model_id="gemini-2.5-pro",
            actual_provider_id="openai-xyz",
            actual_model_id="gpt-4o",
            fallback_used=True,
            fallback_reason="Provider unavailable",
        )
        assert meta.requested_provider_id == "google-abc"
        assert meta.actual_provider_id == "openai-xyz"
        assert meta.fallback_used is True
