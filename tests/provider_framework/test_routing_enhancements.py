"""Tests for W4 — RouteCandidate context_window, priority weighting, MAX_CANDIDATE_ATTEMPTS."""

import pytest

from aios.core.routing_types import (
    RouteCandidate,
    CATEGORY_CAPABILITIES,
    capabilities_for_category,
    required_capabilities_from_category,
)
from aios.core.smart_router import (
    _build_candidates,
    _rank_candidates,
    SmartRouter,
    RoutingStrategy,
)
from aios.core.model_info import ModelInfo, CommercialStatus


class TestRouteCandidateContextWindow:
    def test_context_window_field_defaults(self):
        c = RouteCandidate(
            provider_type="google",
            provider_instance_id="google-1",
            model_id="gemini-2.5-flash",
        )
        assert c.context_window == 4096

    def test_build_candidates_populates_context_window(self):
        model = ModelInfo(
            id="gemini-2.5-flash",
            display_name="Gemini 2.5 Flash",
            provider_id="google",
            provider_name="Google",
            context_window=1048576,
            max_output_tokens=8192,
            commercial_status=CommercialStatus.FREE_TIER,
        )
        adapter = _FakeAdapter("google-1")

        class _HM:
            def get_health(self, pid):
                return None
            def get_model_rate_limit(self, pid, mid):
                return None

        candidates = _build_candidates({"google-1": adapter}, {"google-1": [model]}, _HM())
        assert len(candidates) == 1
        assert candidates[0].context_window == 1048576
        assert candidates[0].priority == 100


class TestPriorityWeighting:
    def test_priority_tie_breaker(self):
        base = dict(
            provider_type="google",
            supports_streaming=True,
            quality=8,
            speed=8,
            commercial_status="free_tier",
            provider_health="healthy",
            latency=100,
        )
        low = RouteCandidate(provider_instance_id="a", model_id="m1", priority=10, context_window=4096, **base)
        high = RouteCandidate(provider_instance_id="b", model_id="m2", priority=90, context_window=4096, **base)
        ranked = _rank_candidates([low, high], RoutingStrategy.PERFORMANCE)
        assert ranked[0].provider_instance_id == "b"
        assert high.score > low.score

    def test_priority_strategy_prefers_high_priority(self):
        base = dict(
            provider_type="google",
            supports_streaming=True,
            quality=5,
            speed=5,
            commercial_status="free_tier",
            provider_health="healthy",
            latency=500,
        )
        low = RouteCandidate(provider_instance_id="a", model_id="m1", priority=10, context_window=4096, **base)
        high = RouteCandidate(provider_instance_id="b", model_id="m2", priority=100, context_window=4096, **base)
        ranked = _rank_candidates([low, high], RoutingStrategy.PRIORITY)
        assert ranked[0].provider_instance_id == "b"

    def test_larger_context_window_preferred(self):
        base = dict(
            provider_type="google",
            supports_streaming=True,
            quality=5,
            speed=5,
            commercial_status="free_tier",
            provider_health="healthy",
            latency=500,
            priority=50,
        )
        small = RouteCandidate(provider_instance_id="a", model_id="m1", context_window=8192, **base)
        large = RouteCandidate(provider_instance_id="b", model_id="m2", context_window=1048576, **base)
        ranked = _rank_candidates([small, large], RoutingStrategy.PERFORMANCE)
        assert ranked[0].provider_instance_id == "b"


class TestMaxCandidateAttempts:
    def test_max_candidate_attempts_default(self):
        assert SmartRouter.MAX_CANDIDATE_ATTEMPTS == 20


class TestCapabilityMapDedup:
    def test_single_source_of_truth(self):
        """ROUTING_CATEGORIES must derive from CATEGORY_CAPABILITIES."""
        from aios.core.smart_router import ROUTING_CATEGORIES
        for cat in ROUTING_CATEGORIES:
            assert cat["capabilities"] == CATEGORY_CAPABILITIES[cat["id"]]

    def test_capabilities_and_required_agree(self):
        for cat_id in ("general_chat", "coding", "vision", "reasoning", "fallback"):
            assert capabilities_for_category(cat_id) == required_capabilities_from_category(cat_id)

    def test_category_map_has_expected_categories(self):
        assert "general_chat" in CATEGORY_CAPABILITIES
        assert "coding" in CATEGORY_CAPABILITIES
        assert "vision" in CATEGORY_CAPABILITIES
        assert "reasoning" in CATEGORY_CAPABILITIES
        assert "fallback" in CATEGORY_CAPABILITIES


class _FakeAdapter:
    """Minimal adapter stub with priority default."""

    def __init__(self, provider_id):
        self._provider_id = provider_id

    @property
    def provider_id(self):
        return self._provider_id

    @property
    def priority(self):
        return 100
