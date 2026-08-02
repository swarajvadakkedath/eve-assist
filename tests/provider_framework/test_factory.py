"""Tests for ProviderFactory — creates adapters from registry definitions."""

import pytest
from aios.core.provider_factory import create_adapter
from aios.core.adapters.openai_compatible_adapter import OpenAICompatibleAdapter
from aios.core.adapters.google_adapter import GoogleAdapter
from aios.core.adapters.openai_adapter import OpenAIAdapter
from aios.core.adapters.anthropic_adapter import AnthropicAdapter
from aios.core.adapters.ollama_adapter import OllamaAdapter


class TestFactoryNativeAdapters:
    """Verify factory creates correct native adapter classes."""

    def test_google(self):
        a = create_adapter("google", "My Google", api_key="test-key")
        assert isinstance(a, GoogleAdapter)

    def test_openai(self):
        a = create_adapter("openai", "My OpenAI", api_key="test-key")
        assert isinstance(a, OpenAIAdapter)

    def test_anthropic(self):
        a = create_adapter("anthropic", "My Anthropic", api_key="test-key")
        assert isinstance(a, AnthropicAdapter)

    def test_ollama(self):
        a = create_adapter("ollama", "My Ollama")
        assert isinstance(a, OllamaAdapter)

    def test_groq(self):
        """Groq has its own native adapter."""
        a = create_adapter("groq", "My Groq", api_key="test-key")
        from aios.core.adapters.groq_adapter import GroqAdapter
        assert isinstance(a, GroqAdapter)

    def test_ollama_base_url(self):
        """Ollama should use provided base_url."""
        a = create_adapter("ollama", "Local", base_url="http://my-ollama:11434")
        assert a._base_url == "http://my-ollama:11434"


class TestFactoryOpenAICompatible:
    """Verify factory creates OpenAI-compatible adapters with metadata."""

    @pytest.mark.parametrize("provider_type", [
        "mistral", "cerebras", "openrouter", "github_models",
        "huggingface", "lm_studio", "nvidia", "openai_compatible", "custom",
    ])
    def test_compatible_creates_correct_class(self, provider_type):
        a = create_adapter(provider_type, f"Test {provider_type}", api_key="test-key")
        assert isinstance(a, OpenAICompatibleAdapter)

    def test_openrouter_metadata(self):
        """OpenRouter adapter should receive extra headers via metadata."""
        a = create_adapter("openrouter", "My OpenRouter", api_key="test-key")
        assert a._commercial_policy == "openrouter"
        assert "HTTP-Referer" in a._headers

    def test_groq_native(self):
        """Groq uses its own native adapter, not OpenAI-compatible."""
        a = create_adapter("groq", "My Groq", api_key="test-key")
        from aios.core.adapters.groq_adapter import GroqAdapter
        assert isinstance(a, GroqAdapter)

    def test_lmstudio_metadata(self):
        a = create_adapter("lm_studio", "My LM Studio")
        assert a._discovery_strategy == "lmstudio"
        assert a._commercial_policy == "local"

    def test_nvidia_metadata(self):
        a = create_adapter("nvidia", "My NVIDIA", api_key="test-key")
        assert a._commercial_policy == "free_tier"
        assert "Content-Type" in a._headers


class TestFactoryErrorHandling:
    """Verify factory raises on unknown provider types."""

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider type"):
            create_adapter("nonexistent", "Test")

    def test_invalid_adapter_class_raises(self):
        from aios.core.provider_registry import register, ProviderDefinition, _REGISTRY
        register(ProviderDefinition(
            provider_type="broken",
            display_name="Broken",
            adapter_class="NonexistentAdapter",
        ))
        try:
            with pytest.raises(ValueError, match="unknown adapter class"):
                create_adapter("broken", "Test")
        finally:
            _REGISTRY.pop("broken", None)
