"""Tests for ProviderRegistry — verifies all 16 builtin providers."""

import pytest
from aios.core.provider_registry import get, all, all_as_dicts, register, ProviderDefinition


class TestBuiltinRegistrations:
    """Verify the 16 built-in providers are registered on import."""

    def test_all_16_registered(self):
        defs = all()
        assert len(defs) == 16

    @pytest.mark.parametrize("provider_type", [
        "google", "openai", "anthropic", "ollama", "groq",
        "cohere", "cloudflare", "mistral", "cerebras", "openrouter",
        "github_models", "huggingface", "lm_studio", "nvidia",
        "openai_compatible", "custom",
    ])
    def test_provider_registered(self, provider_type):
        d = get(provider_type)
        assert d is not None, f"{provider_type} not registered"
        assert d.provider_type == provider_type

    def test_native_adapters(self):
        """Native adapters should have their own class name."""
        native_types = ["google", "openai", "anthropic", "ollama", "cohere", "cloudflare"]
        for pt in native_types:
            d = get(pt)
            assert d.adapter_class != "OpenAICompatibleAdapter", f"{pt} should be native"

    def test_openai_compatible_adapters(self):
        """OpenAI-compatible providers should use OpenAICompatibleAdapter."""
        compat_types = ["mistral", "cerebras", "openrouter", "github_models",
                        "huggingface", "lm_studio", "nvidia", "openai_compatible", "custom"]
        for pt in compat_types:
            d = get(pt)
            assert d.adapter_class == "OpenAICompatibleAdapter", f"{pt} should use OpenAICompatibleAdapter"

    def test_extra_headers(self):
        """OpenRouter should have extra headers."""
        d = get("openrouter")
        assert "HTTP-Referer" in d.extra_headers
        assert "X-Title" in d.extra_headers

    def test_commercial_policies(self):
        """Each provider should have a commercial_policy."""
        for d in all():
            assert d.commercial_policy, f"{d.provider_type} missing commercial_policy"

    def test_discovery_strategies(self):
        """Each provider should have a discovery_strategy."""
        for d in all():
            assert d.discovery_strategy, f"{d.provider_type} missing discovery_strategy"

    def test_api_key_required(self):
        """Ollama should not require API key."""
        d = get("ollama")
        assert not d.api_key_required

    def test_needs_endpoint(self):
        """Ollama and lm_studio should need endpoint."""
        assert get("ollama").needs_endpoint
        assert get("lm_studio").needs_endpoint
        assert not get("openai").needs_endpoint

    def test_supports_organization(self):
        """Only OpenAI should support organization."""
        assert get("openai").supports_organization
        assert not get("anthropic").supports_organization

    def test_as_dicts(self):
        """all_as_dicts should return serializable dicts."""
        dicts = all_as_dicts()
        assert len(dicts) == 16
        for d in dicts:
            assert "id" in d
            assert "name" in d
            assert "needs_endpoint" in d


class TestCustomRegistration:
    """Test runtime registration of custom providers."""

    def test_register_custom_provider(self):
        from aios.core.provider_registry import _REGISTRY
        custom = ProviderDefinition(
            provider_type="my_custom",
            display_name="My Custom",
            default_endpoint="https://custom.api.com/v1",
            adapter_class="OpenAICompatibleAdapter",
        )
        register(custom)
        d = get("my_custom")
        assert d is not None
        assert d.display_name == "My Custom"
        assert d.default_endpoint == "https://custom.api.com/v1"
        _REGISTRY.pop("my_custom", None)

    def test_overwrite_existing(self):
        """Registering the same provider_type should overwrite."""
        original = get("openai")
        assert original is not None
        new_def = ProviderDefinition(
            provider_type="openai",
            display_name="Overwritten",
        )
        register(new_def)
        assert get("openai").display_name == "Overwritten"
        register(original)

    def test_unknown_provider_returns_none(self):
        assert get("nonexistent") is None
