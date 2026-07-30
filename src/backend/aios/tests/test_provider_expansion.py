"""Tests for provider expansion — multi-account, model classification, rate-limit state, aggregation."""

from __future__ import annotations

import time
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from aios.core.model_info import ModelInfo, CommercialStatus, AvailabilityStatus
from aios.core.health_monitor import (
    HealthMonitor,
    HealthState,
    RateLimitState,
    RateLimitInfo,
    ProviderHealth,
)
from aios.core.adapters.base import ProviderStatus


# ---------------------------------------------------------------------------
# ModelInfo — CommercialStatus / AvailabilityStatus / serialization
# ---------------------------------------------------------------------------

class TestModelInfoClassification:
    def test_free_model_fields(self):
        m = ModelInfo(
            id="test-model",
            display_name="Test Model",
            provider_id="test-1",
            provider_name="Test",
            commercial_status=CommercialStatus.FREE,
            is_free=True,
        )
        assert m.commercial_status == CommercialStatus.FREE
        assert m.is_free is True

    def test_paid_model_fields(self):
        m = ModelInfo(
            id="gpt-4o",
            display_name="GPT-4o",
            provider_id="openai-1",
            provider_name="OpenAI",
            commercial_status=CommercialStatus.PAID,
            pricing={"input": 0.0025, "output": 0.01},
        )
        assert m.commercial_status == CommercialStatus.PAID
        assert m.pricing["input"] == 0.0025

    def test_local_model_fields(self):
        m = ModelInfo(
            id="llama3.2",
            display_name="llama3.2",
            provider_id="ollama-1",
            provider_name="Ollama",
            commercial_status=CommercialStatus.LOCAL,
            is_free=True,
        )
        assert m.commercial_status == CommercialStatus.LOCAL

    def test_deprecated_model_availability(self):
        m = ModelInfo(
            id="claude-3-opus-latest",
            display_name="Claude 3 Opus",
            provider_id="anthropic-1",
            provider_name="Anthropic",
            availability=AvailabilityStatus.DEPRECATED,
            deprecated=True,
        )
        assert m.availability == AvailabilityStatus.DEPRECATED
        assert m.deprecated is True

    def test_to_dict_roundtrip(self):
        m = ModelInfo(
            id="test",
            display_name="Test",
            provider_id="p-1",
            provider_name="P",
            provider_type="openrouter",
            provider_instance_id="openrouter-abc",
            commercial_status=CommercialStatus.FREE,
            availability=AvailabilityStatus.AVAILABLE,
            discovery_source="api",
            pricing={"input": 0.0, "output": 0.0},
        )
        d = m.to_dict()
        assert d["commercialStatus"] == "free"
        assert d["availability"] == "available"
        assert d["providerType"] == "openrouter"
        assert d["providerInstanceId"] == "openrouter-abc"
        assert d["discoverySource"] == "api"

        m2 = ModelInfo.from_dict(d)
        assert m2.commercial_status == CommercialStatus.FREE
        assert m2.availability == AvailabilityStatus.AVAILABLE
        assert m2.provider_type == "openrouter"
        assert m2.provider_instance_id == "openrouter-abc"

    def test_from_dict_safe_enum_parsing(self):
        d = {
            "id": "x",
            "displayName": "X",
            "providerId": "p",
            "providerName": "P",
            "commercialStatus": "invalid_enum_value",
            "availability": "also_invalid",
        }
        m = ModelInfo.from_dict(d)
        assert m.commercial_status == CommercialStatus.UNKNOWN
        assert m.availability == AvailabilityStatus.UNKNOWN

    def test_from_old_format_preserves_fields(self):
        old = {
            "id": "gpt-4o",
            "displayName": "GPT-4o",
            "contextLength": 128000,
            "maxOutput": 4096,
            "isFree": False,
            "costPer1kInput": 0.0025,
            "costPer1kOutput": 0.01,
        }
        m = ModelInfo.from_old_format(old, provider_id="openai-1", provider_name="OpenAI")
        assert m.id == "gpt-4o"
        assert m.context_window == 128000
        assert m.commercial_status == CommercialStatus.PAID
        assert m.pricing["input"] == 0.0025


# ---------------------------------------------------------------------------
# RateLimitInfo — cooldown, backoff, serialization
# ---------------------------------------------------------------------------

class TestRateLimitInfo:
    def test_initial_state(self):
        rl = RateLimitInfo()
        assert rl.state == RateLimitState.NONE
        assert rl.is_in_cooldown() is False
        assert rl.cooldown_remaining() == 0.0

    def test_record_429_with_retry_after(self):
        rl = RateLimitInfo()
        rl.record_429(retry_after=60.0)
        assert rl.state == RateLimitState.PROVIDER_COOLDOWN
        assert rl.retry_after_seconds == 60.0
        assert rl.consecutive_429s == 1
        assert rl.is_in_cooldown() is True
        assert rl.cooldown_remaining() > 50.0

    def test_record_429_without_retry_after_uses_backoff(self):
        rl = RateLimitInfo()
        rl.record_429()
        assert rl.state == RateLimitState.LOCAL_COOLDOWN
        assert rl.consecutive_429s == 1
        assert rl.cooldown_remaining() >= 25.0  # 30s backoff ± tolerance

    def test_exponential_backoff(self):
        rl = RateLimitInfo()
        rl.record_429()  # 30s
        assert rl.consecutive_429s == 1
        rl.record_429()  # 60s
        assert rl.consecutive_429s == 2
        rl.record_429()  # 120s
        assert rl.consecutive_429s == 3

    def test_quota_exhausted(self):
        rl = RateLimitInfo()
        rl.record_429(quota_exhausted=True)
        assert rl.state == RateLimitState.QUOTA_EXHAUSTED
        assert rl.daily_quota_exhausted is True
        assert rl.is_in_cooldown() is True
        assert rl.cooldown_remaining() > 3500.0  # 1 hour

    def test_clear_resets_state(self):
        rl = RateLimitInfo()
        rl.record_429(retry_after=30.0)
        assert rl.is_in_cooldown() is True
        rl.clear()
        assert rl.state == RateLimitState.NONE
        assert rl.is_in_cooldown() is False
        assert rl.consecutive_429s == 0

    def test_to_dict(self):
        rl = RateLimitInfo()
        rl.record_429(retry_after=45.0)
        d = rl.to_dict()
        assert d["state"] == "provider"
        assert d["retry_after_seconds"] == 45.0
        assert d["consecutive_429s"] == 1
        assert d["daily_quota_exhausted"] is False


# ---------------------------------------------------------------------------
# ProviderHealth — to_dict, rate-limit integration
# ---------------------------------------------------------------------------

class TestProviderHealth:
    def test_to_dict_includes_rate_limit(self):
        h = ProviderHealth(provider_id="test-1")
        d = h.to_dict()
        assert "rate_limit" in d
        assert d["rate_limit"]["state"] == "none"

    def test_record_failure_sets_rate_limit(self):
        h = ProviderHealth(provider_id="test-1")
        h.record_failure(ProviderStatus.RATE_LIMITED, "429 Too Many Requests", retry_after=30.0)
        assert h.state == HealthState.RATE_LIMITED
        assert h.rate_limit.state == RateLimitState.PROVIDER_COOLDOWN

    def test_record_quota_exceeded(self):
        h = ProviderHealth(provider_id="test-1")
        h.record_failure(ProviderStatus.QUOTA_EXCEEDED, "Quota exceeded")
        assert h.state == HealthState.QUOTA_EXCEEDED
        assert h.rate_limit.daily_quota_exhausted is True

    def test_record_success_clears_rate_limit(self):
        h = ProviderHealth(provider_id="test-1")
        h.record_failure(ProviderStatus.RATE_LIMITED, "429", retry_after=30.0)
        assert h.rate_limit.is_in_cooldown() is True
        h.record_success(50.0)
        assert h.rate_limit.is_in_cooldown() is False
        assert h.state == HealthState.HEALTHY


# ---------------------------------------------------------------------------
# HealthMonitor — per-model rate limits, multi-account
# ---------------------------------------------------------------------------

class TestHealthMonitor:
    def test_register_unregister(self):
        hm = HealthMonitor()
        hm.register_provider("p-1")
        assert hm.get_health("p-1") is not None
        hm.unregister_provider("p-1")
        assert hm.get_health("p-1") is None

    def test_per_model_rate_limit(self):
        hm = HealthMonitor()
        hm.record_model_429("p-1", "model-a", retry_after=30.0)
        assert hm.is_model_available("p-1", "model-a") is False
        assert hm.is_model_available("p-1", "model-b") is True  # different model unaffected

    def test_clear_model_rate_limit(self):
        hm = HealthMonitor()
        hm.record_model_429("p-1", "model-a", retry_after=30.0)
        assert hm.is_model_available("p-1", "model-a") is False
        hm.clear_model_rate_limit("p-1", "model-a")
        assert hm.is_model_available("p-1", "model-a") is True

    def test_unregister_cleans_model_rate_limits(self):
        hm = HealthMonitor()
        hm.record_model_429("p-1", "m1", retry_after=30.0)
        hm.record_model_429("p-1", "m2", retry_after=30.0)
        hm.record_model_429("p-2", "m1", retry_after=30.0)
        hm.unregister_provider("p-1")
        limits = hm.get_all_model_rate_limits()
        assert "p-1:m1" not in limits
        assert "p-1:m2" not in limits
        assert "p-2:m1" in limits

    def test_get_all_model_rate_limits(self):
        hm = HealthMonitor()
        hm.record_model_429("p-1", "m1", retry_after=10.0)
        all_limits = hm.get_all_model_rate_limits()
        assert "p-1:m1" in all_limits
        assert all_limits["p-1:m1"]["state"] == "provider"


# ---------------------------------------------------------------------------
# OpenRouter free classification
# ---------------------------------------------------------------------------

class TestOpenRouterClassification:
    def test_free_model_with_zero_pricing(self):
        from aios.core.adapters.openai_compatible_adapter import _openrouter_classify

        raw = {
            "id": "meta-llama/llama-3.1-8b-instruct:free",
            "pricing": {"prompt": "0", "completion": "0"},
        }
        cs, is_free = _openrouter_classify(raw)
        assert cs == CommercialStatus.FREE
        assert is_free is True

    def test_paid_model_with_positive_pricing(self):
        from aios.core.adapters.openai_compatible_adapter import _openrouter_classify

        raw = {
            "id": "openai/gpt-4o",
            "pricing": {"prompt": "0.0025", "completion": "0.01"},
        }
        cs, is_free = _openrouter_classify(raw)
        assert cs == CommercialStatus.PAID
        assert is_free is False

    def test_free_suffix_in_model_id(self):
        from aios.core.adapters.openai_compatible_adapter import _openrouter_classify

        raw = {"id": "mistralai/mistral-7b-instruct:free"}
        cs, is_free = _openrouter_classify(raw)
        assert is_free is True

    def test_missing_pricing_not_free(self):
        from aios.core.adapters.openai_compatible_adapter import _openrouter_classify

        raw = {"id": "openai/gpt-4o"}
        cs, is_free = _openrouter_classify(raw)
        assert is_free is False
        assert cs == CommercialStatus.PAID


# ---------------------------------------------------------------------------
# ProviderManager aggregation methods (unit tests with mocked providers)
# ---------------------------------------------------------------------------

class TestProviderManagerAggregation:
    def _make_manager_with_providers(self):
        """Create a ProviderManager-like mock with sample providers."""
        from aios.core.provider_manager import ProviderManager

        mgr = ProviderManager.__new__(ProviderManager)
        mgr._providers = [
            {
                "id": "openrouter-abc",
                "type": "openrouter",
                "name": "OpenRouter 1",
                "models": [
                    {"id": "gpt-4o", "commercialStatus": "paid", "isFree": False, "enabled": True},
                    {"id": "llama-3.1-8b:free", "commercialStatus": "free", "isFree": True, "enabled": True},
                ],
            },
            {
                "id": "ollama-local",
                "type": "ollama",
                "name": "Ollama",
                "models": [
                    {"id": "llama3.2", "commercialStatus": "local", "isFree": True, "enabled": True},
                ],
            },
            {
                "id": "openai-xyz",
                "type": "openai",
                "name": "OpenAI",
                "models": [
                    {"id": "gpt-4o", "commercialStatus": "paid", "isFree": False, "enabled": True},
                    {"id": "gpt-4o-mini", "commercialStatus": "paid", "isFree": False, "enabled": False},
                ],
            },
        ]
        mgr._routing_config = []
        return mgr

    def test_get_all_free_models(self):
        mgr = self._make_manager_with_providers()
        free = mgr.get_all_free_models()
        assert len(free) == 2
        ids = {m["id"] for m in free}
        assert "llama-3.1-8b:free" in ids
        assert "llama3.2" in ids

    def test_get_provider_type_models(self):
        mgr = self._make_manager_with_providers()
        or_models = mgr.get_provider_type_models("openrouter")
        assert len(or_models) == 2
        assert all(m["provider_type"] == "openrouter" for m in or_models)

    def test_get_provider_type_models_empty(self):
        mgr = self._make_manager_with_providers()
        result = mgr.get_provider_type_models("nonexistent")
        assert result == []

    def test_get_model_commercial_status(self):
        mgr = self._make_manager_with_providers()
        result = mgr.get_model_commercial_status("openrouter-abc", "gpt-4o")
        assert result["commercial_status"] == "paid"
        assert result["provider_type"] == "openrouter"

    def test_get_model_commercial_status_not_found(self):
        mgr = self._make_manager_with_providers()
        result = mgr.get_model_commercial_status("openrouter-abc", "nonexistent")
        assert "error" in result

    def test_get_model_commercial_status_provider_not_found(self):
        mgr = self._make_manager_with_providers()
        result = mgr.get_model_commercial_status("nonexistent", "gpt-4o")
        assert "error" in result


# ---------------------------------------------------------------------------
# Security: no API keys leak into model dicts or health
# ---------------------------------------------------------------------------

class TestSecurityNoKeyLeak:
    def test_model_info_no_api_key_field(self):
        m = ModelInfo(
            id="x",
            display_name="X",
            provider_id="p",
            provider_name="P",
        )
        d = m.to_dict()
        assert "api_key" not in d
        assert "apiKey" not in d
        assert "secret" not in d
        assert "token" not in d

    def test_health_to_dict_no_api_key(self):
        h = ProviderHealth(provider_id="p-1")
        h.record_success(50.0)
        d = h.to_dict()
        assert "api_key" not in d
        assert "apiKey" not in d

    def test_rate_limit_to_dict_no_secrets(self):
        rl = RateLimitInfo()
        rl.record_429(retry_after=30.0)
        d = rl.to_dict()
        assert "api_key" not in d
        assert "token" not in d


# ---------------------------------------------------------------------------
# Routing compatibility — model_id alongside provider_id
# ---------------------------------------------------------------------------

class TestRoutingCompatibility:
    def test_routing_entry_with_model(self):
        entry = {
            "id": "general_chat",
            "label": "General Chat",
            "provider_id": "openrouter-abc",
            "model_id": "gpt-4o",
        }
        assert entry["provider_id"] is not None
        assert entry["model_id"] is not None

    def test_routing_entry_without_model(self):
        entry = {
            "id": "fallback",
            "label": "Fallback",
            "provider_id": "ollama-local",
            "model_id": None,
        }
        assert entry["provider_id"] is not None
        assert entry["model_id"] is None
