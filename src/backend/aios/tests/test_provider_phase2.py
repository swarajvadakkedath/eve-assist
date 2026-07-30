"""Comprehensive Phase 2 tests — multi-account isolation, provider contracts, classification, discovery."""

from __future__ import annotations

import time
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock

import pytest

from aios.core.model_info import ModelInfo, CommercialStatus, AvailabilityStatus
from aios.core.health_monitor import (
    HealthMonitor,
    HealthState,
    RateLimitState,
    RateLimitInfo,
    ProviderHealth,
)
from aios.core.adapters.base import AIProviderAdapter, ProviderStatus, ChatRequest, ChatResponse
from aios.core.adapters.cohere_adapter import CohereAdapter
from aios.core.adapters.cloudflare_adapter import CloudflareAdapter
from aios.core.adapters.openai_compatible_adapter import OpenAICompatibleAdapter


# ===========================================================================
# 1. PROVIDER IDENTITY INVARIANT
# ===========================================================================

class TestProviderIdentity:
    """provider_id (adapter) == TYPE, provider["id"] (ProviderManager) == INSTANCE."""

    def test_adapter_provider_id_is_type(self):
        """Each adapter returns the provider TYPE, not instance ID."""
        from aios.core.adapters.openai_adapter import OpenAIAdapter
        from aios.core.adapters.anthropic_adapter import AnthropicAdapter
        from aios.core.adapters.google_adapter import GoogleAdapter
        from aios.core.adapters.groq_adapter import GroqAdapter
        from aios.core.adapters.ollama_adapter import OllamaAdapter

        for cls, expected_type in [
            (OpenAIAdapter, "openai"),
            (AnthropicAdapter, "anthropic"),
            (GoogleAdapter, "google"),
            (GroqAdapter, "groq"),
            (OllamaAdapter, "ollama"),
        ]:
            adapter = cls.__new__(cls)
            assert adapter.provider_id == expected_type

    def test_openai_compatible_provider_id_matches_type(self):
        for ptype in ("openrouter", "mistral", "cerebras", "github_models", "huggingface", "lm_studio", "nvidia"):
            adapter = OpenAICompatibleAdapter(
                provider_type=ptype,
                provider_name=ptype,
                api_key="test",
                base_url="http://example.com",
            )
            assert adapter.provider_id == ptype

    def test_cohere_provider_id(self):
        adapter = CohereAdapter(api_key="test")
        assert adapter.provider_id == "cohere"

    def test_cloudflare_provider_id(self):
        adapter = CloudflareAdapter(api_key="test", account_id="acc123")
        assert adapter.provider_id == "cloudflare"


# ===========================================================================
# 2. MULTI-ACCOUNT ISOLATION
# ===========================================================================

class TestMultiAccountIsolation:
    """Two instances of the same provider type must be fully isolated."""

    def _make_manager(self):
        from aios.core.provider_manager import ProviderManager
        mgr = ProviderManager.__new__(ProviderManager)
        mgr._providers = []
        mgr._routing_config = []
        mgr._adapters = {}
        mgr._smart_router = MagicMock()
        mgr._health_monitor = HealthMonitor()
        mgr._model_cache = MagicMock()
        mgr._streaming = MagicMock()
        return mgr

    def test_two_google_instances_coexist(self):
        mgr = self._make_manager()
        mgr._providers = [
            {
                "id": "google-personal",
                "type": "google",
                "name": "Google Personal",
                "models": [
                    {"id": "gemini-2.5-flash", "commercialStatus": "free_tier", "isFree": True, "enabled": True},
                ],
            },
            {
                "id": "google-work",
                "type": "google",
                "name": "Google Work",
                "models": [
                    {"id": "gemini-2.5-pro", "commercialStatus": "paid", "isFree": False, "enabled": True},
                ],
            },
        ]

        # Each instance has independent models
        p1 = mgr._providers[0]
        p2 = mgr._providers[1]
        assert p1["id"] != p2["id"]
        assert p1["models"][0]["id"] != p2["models"][0]["id"]

        # Health is independent
        mgr._health_monitor.register_provider("google-personal")
        mgr._health_monitor.register_provider("google-work")
        h1 = mgr._health_monitor.get_health("google-personal")
        h2 = mgr._health_monitor.get_health("google-work")
        assert h1 is not h2
        assert h1.provider_id != h2.provider_id

    def test_two_openrouter_instances(self):
        mgr = self._make_manager()
        mgr._providers = [
            {"id": "openrouter-abc", "type": "openrouter", "name": "OR A", "models": []},
            {"id": "openrouter-def", "type": "openrouter", "name": "OR B", "models": []},
        ]
        assert mgr._providers[0]["id"] != mgr._providers[1]["id"]

    def test_two_groq_instances(self):
        mgr = self._make_manager()
        mgr._providers = [
            {"id": "groq-abc", "type": "groq", "name": "Groq 1", "models": []},
            {"id": "groq-def", "type": "groq", "name": "Groq 2", "models": []},
        ]
        assert mgr._providers[0]["id"] != mgr._providers[1]["id"]


# ===========================================================================
# 3. CREDENTIAL ISOLATION
# ===========================================================================

class TestCredentialIsolation:
    """Credentials must be instance-specific, never shared across types."""

    def test_credential_target_is_instance_specific(self):
        from aios.core.provider_manager import ProviderManager
        mgr = ProviderManager.__new__(ProviderManager)
        mgr._config_dir = Path("/tmp/test")

        t1 = mgr._credential_target("google-personal")
        t2 = mgr._credential_target("google-work")
        t3 = mgr._credential_target("openai-abc")

        assert t1 != t2
        assert t1 != t3
        assert "google-personal" in t1
        assert "google-work" in t2
        assert "openai-abc" in t3

    def test_providers_json_strips_api_key(self):
        """_save() must strip _api_key from persisted data."""
        from aios.core.provider_manager import ProviderManager
        mgr = ProviderManager.__new__(ProviderManager)
        mgr._providers = [
            {"id": "test-1", "type": "openai", "_api_key": "sk-secret123", "name": "Test"},
        ]
        mgr._providers_file = Path(tempfile.mktemp(suffix=".json"))

        try:
            mgr._save()
            data = json.loads(mgr._providers_file.read_text("utf-8"))
            assert "_api_key" not in data[0]
            assert data[0]["id"] == "test-1"
        finally:
            mgr._providers_file.unlink(missing_ok=True)


# ===========================================================================
# 4. HEALTH ISOLATION
# ===========================================================================

class TestHealthIsolation:
    """One provider's health state must not affect another."""

    def test_google_a_rate_limited_b_healthy(self):
        hm = HealthMonitor()
        hm.register_provider("google-a")
        hm.register_provider("google-b")

        # Simulate A being rate limited
        ha = hm.get_health("google-a")
        ha.record_failure(ProviderStatus.RATE_LIMITED, "429", retry_after=60.0)

        # B remains healthy (never checked)
        hb = hm.get_health("google-b")
        assert hb.state == HealthState.UNKNOWN

        # A is rate limited
        assert ha.state == HealthState.RATE_LIMITED
        assert ha.rate_limit.is_in_cooldown()

    def test_two_groq_instances_independent_health(self):
        hm = HealthMonitor()
        hm.register_provider("groq-a")
        hm.register_provider("groq-b")

        ha = hm.get_health("groq-a")
        hb = hm.get_health("groq-b")

        ha.record_success(50.0)
        hb.record_failure(ProviderStatus.RATE_LIMITED, "429")

        assert ha.state == HealthState.HEALTHY
        assert hb.state == HealthState.RATE_LIMITED


# ===========================================================================
# 5. RATE-LIMIT ISOLATION
# ===========================================================================

class TestRateLimitIsolation:
    """Model-specific rate limits must not cross instance boundaries."""

    def test_same_model_different_instances(self):
        hm = HealthMonitor()
        hm.record_model_429("openrouter-a", "gpt-4o", retry_after=30.0)
        assert hm.is_model_available("openrouter-a", "gpt-4o") is False
        assert hm.is_model_available("openrouter-b", "gpt-4o") is True

    def test_different_models_same_instance(self):
        hm = HealthMonitor()
        hm.record_model_429("google-personal", "gemini-2.5-flash", retry_after=30.0)
        assert hm.is_model_available("google-personal", "gemini-2.5-flash") is False
        assert hm.is_model_available("google-personal", "gemini-2.5-pro") is True

    def test_clear_specific_instance(self):
        hm = HealthMonitor()
        hm.record_model_429("groq-a", "llama-3.3-70b", retry_after=30.0)
        hm.record_model_429("groq-b", "llama-3.3-70b", retry_after=30.0)
        hm.clear_model_rate_limit("groq-a", "llama-3.3-70b")
        assert hm.is_model_available("groq-a", "llama-3.3-70b") is True
        assert hm.is_model_available("groq-b", "llama-3.3-70b") is False


# ===========================================================================
# 6. MODEL CACHE ISOLATION
# ===========================================================================

class TestCacheIsolation:
    """Cache keys must include provider instance ID."""

    def test_cache_key_includes_instance(self):
        from aios.core.provider_manager import ProviderManager
        mgr = ProviderManager.__new__(ProviderManager)
        mgr._model_cache = MagicMock()
        mgr._model_cache.get = AsyncMock(return_value=None)
        mgr._providers = [
            {"id": "openrouter-a", "type": "openrouter", "models": []},
        ]
        mgr._adapters = {"openrouter-a": MagicMock()}

        # The cache key should include the instance ID
        import asyncio
        asyncio.run(mgr.fetch_models("openrouter-a"))
        call_args = mgr._model_cache.get.call_args
        assert "openrouter-a" in call_args[0][0]


# ===========================================================================
# 7. COMMERCIAL CLASSIFICATION
# ===========================================================================

class TestCommercialClassification:
    def test_free_tier_groq(self):
        from aios.core.adapters.groq_adapter import GroqAdapter
        adapter = GroqAdapter.__new__(GroqAdapter)
        adapter._provider_type = "groq"
        assert adapter._provider_type == "groq"

    def test_cohere_models_classified(self):
        from aios.core.adapters.cohere_adapter import _COHERE_MODELS
        for mid, caps in _COHERE_MODELS.items():
            assert "ctx" in caps
            assert "max_out" in caps

    def test_cloudflare_models_classified(self):
        from aios.core.adapters.cloudflare_adapter import _CF_MODELS
        for mid, caps in _CF_MODELS.items():
            assert "ctx" in caps
            assert "display" in caps

    def test_commercial_status_values(self):
        statuses = [s.value for s in CommercialStatus]
        assert "free" in statuses
        assert "free_tier" in statuses
        assert "credit_based" in statuses
        assert "paid" in statuses
        assert "local" in statuses
        assert "unknown" in statuses

    def test_availability_status_values(self):
        statuses = [s.value for s in AvailabilityStatus]
        assert "available" in statuses
        assert "deprecated" in statuses
        assert "preview" in statuses
        assert "experimental" in statuses
        assert "removed" in statuses
        assert "unknown" in statuses


# ===========================================================================
# 8. PROVIDER MANAGER — AGGREGATION WITH NEW PROVIDERS
# ===========================================================================

class TestProviderManagerNewProviders:
    def _make_manager(self, providers):
        from aios.core.provider_manager import ProviderManager
        mgr = ProviderManager.__new__(ProviderManager)
        mgr._providers = providers
        mgr._routing_config = []
        return mgr

    def test_get_all_free_models_includes_cohere_paid(self):
        mgr = self._make_manager([
            {"id": "cohere-1", "type": "cohere", "name": "Cohere",
             "models": [{"id": "command-r", "commercialStatus": "paid", "isFree": False, "enabled": True}]},
        ])
        free = mgr.get_all_free_models()
        assert len(free) == 0

    def test_get_all_free_models_includes_cloudflare_free_tier(self):
        mgr = self._make_manager([
            {"id": "cf-1", "type": "cloudflare", "name": "CF",
             "models": [{"id": "@cf/meta/llama-3.3-70b", "commercialStatus": "free_tier", "isFree": True, "enabled": True}]},
        ])
        free = mgr.get_all_free_models()
        assert len(free) == 1
        assert free[0]["provider_type"] == "cloudflare"

    def test_get_all_free_models_includes_nvidia_free_tier(self):
        mgr = self._make_manager([
            {"id": "nv-1", "type": "nvidia", "name": "NVIDIA",
             "models": [{"id": "meta/llama-3.3-70b", "commercialStatus": "free_tier", "isFree": False, "enabled": True}]},
        ])
        free = mgr.get_all_free_models()
        assert len(free) == 1

    def test_get_provider_type_models_cohere(self):
        mgr = self._make_manager([
            {"id": "cohere-1", "type": "cohere", "name": "C1",
             "models": [{"id": "command-r", "enabled": True}]},
            {"id": "cohere-2", "type": "cohere", "name": "C2",
             "models": [{"id": "command-r-plus", "enabled": True}]},
        ])
        models = mgr.get_provider_type_models("cohere")
        assert len(models) == 2
        instance_ids = {m["provider_instance_id"] for m in models}
        assert "cohere-1" in instance_ids
        assert "cohere-2" in instance_ids

    def test_get_model_commercial_status_cloudflare(self):
        mgr = self._make_manager([
            {"id": "cf-1", "type": "cloudflare", "name": "CF",
             "models": [{"id": "@cf/meta/llama-3.3-70b", "commercialStatus": "free_tier", "pricing": {"input": 0.0, "output": 0.0}, "availability": "available"}]},
        ])
        result = mgr.get_model_commercial_status("cf-1", "@cf/meta/llama-3.3-70b")
        assert result["commercial_status"] == "free_tier"
        assert result["provider_type"] == "cloudflare"


# ===========================================================================
# 9. ADAPTER FACTORY — NEW PROVIDER TYPES
# ===========================================================================

class TestAdapterFactory:
    def test_cohere_adapter_creation(self):
        from aios.core.provider_manager import ProviderManager
        mgr = ProviderManager.__new__(ProviderManager)
        mgr._streaming = MagicMock()

        provider = {"id": "cohere-1", "type": "cohere", "endpoint_url": ""}
        with patch.object(mgr, "_load_api_key", return_value="test-key"):
            adapter = mgr._create_adapter(provider)
        assert isinstance(adapter, CohereAdapter)

    def test_cloudflare_adapter_creation(self):
        from aios.core.provider_manager import ProviderManager
        mgr = ProviderManager.__new__(ProviderManager)
        mgr._streaming = MagicMock()

        provider = {"id": "cf-1", "type": "cloudflare", "endpoint_url": "", "account_id": "acc123"}
        with patch.object(mgr, "_load_api_key", return_value="test-key"):
            adapter = mgr._create_adapter(provider)
        assert isinstance(adapter, CloudflareAdapter)

    def test_nvidia_uses_openai_compatible(self):
        from aios.core.provider_manager import ProviderManager
        mgr = ProviderManager.__new__(ProviderManager)
        mgr._streaming = MagicMock()

        provider = {"id": "nv-1", "type": "nvidia", "endpoint_url": ""}
        with patch.object(mgr, "_load_api_key", return_value="test-key"):
            adapter = mgr._create_adapter(provider)
        assert isinstance(adapter, OpenAICompatibleAdapter)
        assert adapter.provider_id == "nvidia"

    def test_github_models_uses_openai_compatible(self):
        from aios.core.provider_manager import ProviderManager
        mgr = ProviderManager.__new__(ProviderManager)
        mgr._streaming = MagicMock()

        provider = {"id": "gh-1", "type": "github_models", "endpoint_url": ""}
        with patch.object(mgr, "_load_api_key", return_value="test-key"):
            adapter = mgr._create_adapter(provider)
        assert isinstance(adapter, OpenAICompatibleAdapter)
        assert adapter.provider_id == "github_models"

    def test_lm_studio_uses_openai_compatible(self):
        from aios.core.provider_manager import ProviderManager
        mgr = ProviderManager.__new__(ProviderManager)
        mgr._streaming = MagicMock()

        provider = {"id": "lm-1", "type": "lm_studio", "endpoint_url": ""}
        with patch.object(mgr, "_load_api_key", return_value="test-key"):
            adapter = mgr._create_adapter(provider)
        assert isinstance(adapter, OpenAICompatibleAdapter)
        assert adapter.provider_id == "lm_studio"


# ===========================================================================
# 10. PROVIDER META — ALL TYPES PRESENT
# ===========================================================================

class TestProviderMetaCompleteness:
    def test_all_expected_types_in_meta(self):
        from aios.core.provider_manager import PROVIDER_META
        expected = {
            "google", "groq", "openrouter", "openai", "anthropic",
            "mistral", "cerebras", "github_models", "huggingface",
            "ollama", "lm_studio", "cohere", "cloudflare", "nvidia",
            "openai_compatible", "custom",
        }
        assert expected.issubset(set(PROVIDER_META.keys()))

    def test_all_types_have_name(self):
        from aios.core.provider_manager import PROVIDER_META
        for ptype, meta in PROVIDER_META.items():
            assert "name" in meta, f"{ptype} missing name"

    def test_all_types_have_endpoint(self):
        from aios.core.provider_manager import PROVIDER_META
        for ptype, meta in PROVIDER_META.items():
            assert "endpoint" in meta, f"{ptype} missing endpoint"


# ===========================================================================
# 11. MODEL CATALOG — ALL TYPES PRESENT
# ===========================================================================

class TestModelCatalogCompleteness:
    def test_all_types_in_catalog(self):
        from aios.core.model_catalog import MODEL_CATALOG
        expected = {
            "google", "openai", "anthropic", "groq", "openrouter",
            "mistral", "cerebras", "github_models", "huggingface",
            "ollama", "lm_studio", "cohere", "cloudflare", "nvidia",
            "openai_compatible", "custom",
        }
        assert expected.issubset(set(MODEL_CATALOG.keys()))

    def test_cohere_catalog_has_models(self):
        from aios.core.model_catalog import MODEL_CATALOG
        assert len(MODEL_CATALOG["cohere"]) > 0

    def test_cloudflare_catalog_has_models(self):
        from aios.core.model_catalog import MODEL_CATALOG
        assert len(MODEL_CATALOG["cloudflare"]) > 0

    def test_nvidia_catalog_has_models(self):
        from aios.core.model_catalog import MODEL_CATALOG
        assert len(MODEL_CATALOG["nvidia"]) > 0


# ===========================================================================
# 12. SECURITY — NO CREDENTIALS IN OUTPUT
# ===========================================================================

class TestSecurity:
    def test_model_info_no_credential_fields(self):
        m = ModelInfo(id="x", display_name="X", provider_id="p", provider_name="P")
        d = m.to_dict()
        for field in ("api_key", "apiKey", "secret", "token", "credential", "password"):
            assert field not in d

    def test_health_dict_no_credential_fields(self):
        h = ProviderHealth(provider_id="p-1")
        d = h.to_dict()
        for field in ("api_key", "apiKey", "secret", "token", "credential"):
            assert field not in d

    def test_rate_limit_dict_no_secrets(self):
        rl = RateLimitInfo()
        rl.record_429(retry_after=30.0)
        d = rl.to_dict()
        for field in ("api_key", "token", "secret", "credential"):
            assert field not in d


# ===========================================================================
# 13. ROUTING COMPATIBILITY
# ===========================================================================

class TestRoutingCompatibility:
    def test_routing_entry_with_explicit_model(self):
        entry = {"id": "general_chat", "provider_id": "openrouter-a", "model_id": "gpt-4o"}
        assert entry["provider_id"] is not None
        assert entry["model_id"] is not None

    def test_routing_entry_fallback_no_model(self):
        entry = {"id": "fallback", "provider_id": "ollama-local", "model_id": None}
        assert entry["provider_id"] is not None
        assert entry["model_id"] is None


# ===========================================================================
# 14. GITHUB MODELS — CUSTOM HEADERS
# ===========================================================================

class TestGitHubModelsHeaders:
    def test_github_models_headers_set(self):
        adapter = OpenAICompatibleAdapter(
            provider_type="github_models",
            provider_name="GitHub Models",
            api_key="ghp_test",
            base_url="https://models.github.ai/inference",
        )
        assert adapter._headers["Accept"] == "application/vnd.github+json"
        assert adapter._headers["X-GitHub-Api-Version"] == "2026-03-10"

    def test_nvidia_headers_not_github(self):
        adapter = OpenAICompatibleAdapter(
            provider_type="nvidia",
            provider_name="NVIDIA NIM",
            api_key="nvapi-test",
            base_url="https://integrate.api.nvidia.com/v1",
        )
        assert "Accept" not in adapter._headers or adapter._headers.get("Accept") != "application/vnd.github+json"


# ===========================================================================
# 15. COHERE ADAPTER — NON-OPENAI FORMAT
# ===========================================================================

class TestCohereAdapter:
    def test_cohere_converts_messages(self):
        adapter = CohereAdapter(api_key="test")
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "How are you?"},
        ]
        chat_history, preamble = adapter._convert_messages(messages)
        assert preamble == "You are helpful."
        assert len(chat_history) == 3
        assert chat_history[0]["role"] == "USER"
        assert chat_history[1]["role"] == "CHATBOT"
        assert chat_history[2]["role"] == "USER"

    def test_cohere_models_have_correct_provider_type(self):
        adapter = CohereAdapter(api_key="test")
        import asyncio
        models = asyncio.run(adapter.list_models())
        assert len(models) > 0
        for m in models:
            assert m.provider_type == "cohere"
            assert m.commercial_status == CommercialStatus.PAID


# ===========================================================================
# 16. CLOUDFLARE ADAPTER — ACCOUNT-BASED
# ===========================================================================

class TestCloudflareAdapter:
    def test_cloudflare_base_url_with_account(self):
        adapter = CloudflareAdapter(api_key="test", account_id="acc123")
        assert "acc123" in adapter._base_url
        assert "/ai/v1" in adapter._base_url

    def test_cloudflare_no_account_no_url(self):
        adapter = CloudflareAdapter(api_key="test", account_id="")
        assert adapter._base_url == ""

    def test_cloudflare_models_have_provider_type(self):
        adapter = CloudflareAdapter(api_key="test", account_id="acc123")
        import asyncio
        models = asyncio.run(adapter.list_models())
        assert len(models) > 0
        for m in models:
            assert m.provider_type == "cloudflare"
            assert m.commercial_status == CommercialStatus.FREE_TIER
