"""Tests for W8 — SmartRouter fallback chain (levels 0-7).

The AUTO resolution hierarchy:
  level 0 — preferred eligible route
  level 1 — same model, alternate instance
  level 2 — same provider type, alternate model
  level 3 — FREE cross-provider
  level 4 — FREE_TIER cross-provider
  level 5 — CREDIT_BASED cross-provider
  level 6 — LOCAL cross-provider
  level 7 — PAID / unknown (ALLOW_PAID only)
"""

import pytest

from aios.core.smart_router import SmartRouter
from aios.core.health_monitor import HealthMonitor
from aios.core.routing_types import CommercialPolicy, RoutingTrace
from aios.core.adapters.base import ChatRequest, ProviderStatus
from aios.core.model_info import ModelInfo, CommercialStatus
from tests.provider_framework.fake_adapter import FakeAdapter


def _model(pid: str, mid: str, commercial: CommercialStatus = CommercialStatus.FREE) -> ModelInfo:
    return ModelInfo(
        id=mid,
        display_name=mid,
        provider_id=pid,
        provider_name=pid,
        commercial_status=commercial,
        supports_streaming=True,
    )


class RouterHarness:
    """Build a router with N instances, each with models."""

    def __init__(self):
        self.health = HealthMonitor()
        self.router = SmartRouter(health_monitor=self.health)

    def add_provider(self, instance_id: str, provider_type: str, models: list[ModelInfo]):
        adapter = FakeAdapter(provider_type=provider_type, provider_name=provider_type)
        self.router.register_adapter(instance_id, adapter)
        self.router.set_provider_models(instance_id, models)

    def mark_unreachable(self, instance_id: str):
        h = self.health.get_health(instance_id)
        if h is None:
            self.health.register_provider(instance_id)
            h = self.health.get_health(instance_id)
        h.record_failure(ProviderStatus.OFFLINE, "simulated outage")

    async def route(self, provider_id=None, model=None, **kwargs):
        req = ChatRequest(messages=[{"role": "user", "content": "hi"}], provider_id=provider_id, model=model or "")
        return await self.router.route(req, **kwargs)


class TestLevel0Preferred:
    async def test_healthy_preferred_route_used(self):
        h = RouterHarness()
        h.add_provider("openai-1", "openai", [_model("openai", "gpt-4o")])
        resp = await h.route(provider_id="openai-1", model="gpt-4o")
        trace = resp.metadata["routing_trace"]
        assert trace["fallback_level"] == 0
        assert trace["fallback_reason"] == "none"
        assert trace["selected"]["provider_instance_id"] == "openai-1"
        assert trace["selected"]["model_id"] == "gpt-4o"


class TestLevel1SameModelAlternateInstance:
    async def test_same_model_alternate_instance(self):
        h = RouterHarness()
        h.add_provider("google-1", "google", [_model("google", "gemini-2.5-flash")])
        h.add_provider("google-2", "google", [_model("google", "gemini-2.5-flash")])
        h.mark_unreachable("google-1")
        resp = await h.route(provider_id="google-1", model="gemini-2.5-flash")
        trace = resp.metadata["routing_trace"]
        assert trace["fallback_level"] == 1
        assert trace["fallback_reason"] == "same_model_alternate_instance"
        assert trace["selected"]["provider_instance_id"] == "google-2"
        assert trace["selected"]["model_id"] == "gemini-2.5-flash"


class TestLevel2SameProviderAlternateModel:
    async def test_same_provider_alternate_model(self):
        h = RouterHarness()
        h.add_provider("google-1", "google", [_model("google", "gemini-2.5-flash")])
        h.add_provider("google-2", "google", [_model("google", "gemini-2.5-pro")])
        h.mark_unreachable("google-1")
        resp = await h.route(provider_id="google-1", model="gemini-2.5-flash")
        trace = resp.metadata["routing_trace"]
        assert trace["fallback_level"] == 2
        assert trace["fallback_reason"] == "same_provider_alternate_model"
        assert trace["selected"]["provider_instance_id"] == "google-2"
        assert trace["selected"]["model_id"] == "gemini-2.5-pro"


class TestLevel3FreeAlternateProvider:
    async def test_free_cross_provider(self):
        h = RouterHarness()
        h.add_provider("google-1", "google", [_model("google", "gemini-2.5-flash")])
        h.add_provider("openai-1", "openai", [_model("openai", "gpt-4o-mini", CommercialStatus.FREE)])
        h.mark_unreachable("google-1")
        resp = await h.route(provider_id="google-1", model="gemini-2.5-flash")
        trace = resp.metadata["routing_trace"]
        assert trace["fallback_level"] == 3
        assert trace["fallback_reason"] == "free_alternate_provider"
        assert trace["selected"]["provider_instance_id"] == "openai-1"


class TestLevel4FreeTierAlternateProvider:
    async def test_free_tier_cross_provider(self):
        h = RouterHarness()
        h.add_provider("google-1", "google", [_model("google", "gemini-2.5-flash")])
        h.add_provider("openai-1", "openai", [_model("openai", "gpt-4o-mini", CommercialStatus.FREE_TIER)])
        h.mark_unreachable("google-1")
        resp = await h.route(
            provider_id="google-1",
            model="gemini-2.5-flash",
            commercial_policy=CommercialPolicy.NO_DIRECT_PAID,
        )
        trace = resp.metadata["routing_trace"]
        assert trace["fallback_level"] == 4
        assert trace["fallback_reason"] == "free_tier_alternate_provider"


class TestLevel5CreditBasedAlternateProvider:
    async def test_credit_cross_provider(self):
        h = RouterHarness()
        h.add_provider("google-1", "google", [_model("google", "gemini-2.5-flash")])
        h.add_provider("hf-1", "huggingface", [_model("hf", "mistral-7b", CommercialStatus.CREDIT_BASED)])
        h.mark_unreachable("google-1")
        resp = await h.route(
            provider_id="google-1",
            model="gemini-2.5-flash",
            commercial_policy=CommercialPolicy.NO_DIRECT_PAID,
        )
        trace = resp.metadata["routing_trace"]
        assert trace["fallback_level"] == 5
        assert trace["fallback_reason"] == "credit_alternate_provider"


class TestLevel6LocalAlternateProvider:
    async def test_local_cross_provider(self):
        h = RouterHarness()
        h.add_provider("google-1", "google", [_model("google", "gemini-2.5-flash")])
        h.add_provider("ollama-1", "ollama", [_model("ollama", "llama3", CommercialStatus.LOCAL)])
        h.mark_unreachable("google-1")
        resp = await h.route(provider_id="google-1", model="gemini-2.5-flash")
        trace = resp.metadata["routing_trace"]
        assert trace["fallback_level"] == 6
        assert trace["fallback_reason"] == "local_alternate"


class TestLevel7PaidAlternateProvider:
    async def test_paid_cross_provider_with_allow_paid(self):
        h = RouterHarness()
        h.add_provider("google-1", "google", [_model("google", "gemini-2.5-flash")])
        h.add_provider("openai-1", "openai", [_model("openai", "gpt-4o", CommercialStatus.PAID)])
        h.mark_unreachable("google-1")
        resp = await h.route(
            provider_id="google-1",
            model="gemini-2.5-flash",
            commercial_policy=CommercialPolicy.ALLOW_PAID,
        )
        trace = resp.metadata["routing_trace"]
        assert trace["fallback_level"] == 7
        assert trace["fallback_reason"] == "paid_alternate"

    async def test_paid_blocked_by_default_policy(self):
        from aios.core.smart_router import PaidRoutingDisabledError

        h = RouterHarness()
        h.add_provider("google-1", "google", [_model("google", "gemini-2.5-flash")])
        h.add_provider("openai-1", "openai", [_model("openai", "gpt-4o", CommercialStatus.PAID)])
        h.mark_unreachable("google-1")
        with pytest.raises(PaidRoutingDisabledError):
            await h.route(provider_id="google-1", model="gemini-2.5-flash")


class TestFallbackChainFallthrough:
    async def test_full_chain_hits_lowest_eligible(self):
        h = RouterHarness()
        h.add_provider("google-1", "google", [_model("google", "gemini-2.5-flash")])
        h.add_provider("openai-1", "openai", [_model("openai", "gpt-4o-mini", CommercialStatus.FREE)])
        h.add_provider("ollama-1", "ollama", [_model("ollama", "llama3", CommercialStatus.LOCAL)])
        h.mark_unreachable("google-1")
        # Both FREE and LOCAL are eligible under FREE_ONLY — FREE ranks first.
        resp = await h.route(provider_id="google-1", model="gemini-2.5-flash")
        trace = resp.metadata["routing_trace"]
        assert trace["fallback_level"] == 3
        assert trace["selected"]["provider_instance_id"] == "openai-1"

    async def test_auto_without_preference_uses_ranked_best(self):
        h = RouterHarness()
        h.add_provider("openai-1", "openai", [_model("openai", "gpt-4o-mini", CommercialStatus.FREE)])
        h.add_provider("google-1", "google", [_model("google", "gemini-2.5-flash")])
        resp = await h.route()
        trace = resp.metadata["routing_trace"]
        assert trace["fallback_level"] == 0
        assert trace["selected"]["provider_instance_id"] == "openai-1"


class TestStrictNoFallback:
    async def test_strict_raises_when_primary_down(self):
        from aios.core.smart_router import RouteUnavailableError, RoutingPolicy

        h = RouterHarness()
        h.add_provider("google-1", "google", [_model("google", "gemini-2.5-flash")])
        h.add_provider("google-2", "google", [_model("google", "gemini-2.5-flash")])
        h.mark_unreachable("google-1")
        with pytest.raises(RouteUnavailableError):
            await h.route(
                provider_id="google-1",
                model="gemini-2.5-flash",
                routing_policy=RoutingPolicy.STRICT,
            )
