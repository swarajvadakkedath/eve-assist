"""Contract tests — verify every registered adapter satisfies AIProviderAdapter.

Run with: pytest tests/provider_framework/test_contract_suite.py -v
"""

import pytest
import asyncio
from aios.core.adapters.base import AIProviderAdapter
from aios.core.provider_factory import create_adapter


# All provider types that can be instantiated with a fake key
INSTANTIABLE = [
    ("google", {"api_key": "fake"}),
    ("openai", {"api_key": "fake"}),
    ("anthropic", {"api_key": "fake"}),
    ("ollama", {}),
    ("groq", {"api_key": "fake"}),
    ("cohere", {"api_key": "fake"}),
    ("cloudflare", {"api_key": "fake"}),
    ("mistral", {"api_key": "fake"}),
    ("cerebras", {"api_key": "fake"}),
    ("openrouter", {"api_key": "fake"}),
    ("github_models", {"api_key": "fake"}),
    ("huggingface", {"api_key": "fake"}),
    ("lm_studio", {}),
    ("nvidia", {"api_key": "fake"}),
    ("openai_compatible", {"api_key": "fake"}),
    ("custom", {"api_key": "fake"}),
]


class TestAdapterContract:
    """Every adapter must satisfy the AIProviderAdapter interface."""

    @pytest.mark.parametrize("provider_type,kwargs", INSTANTIABLE)
    def test_is_adapter_subclass(self, provider_type, kwargs):
        a = create_adapter(provider_type, f"Test {provider_type}", **kwargs)
        assert isinstance(a, AIProviderAdapter)

    @pytest.mark.parametrize("provider_type,kwargs", INSTANTIABLE)
    def test_has_provider_id(self, provider_type, kwargs):
        a = create_adapter(provider_type, f"Test {provider_type}", **kwargs)
        assert hasattr(a, "provider_id")
        assert isinstance(a.provider_id, str)
        assert len(a.provider_id) > 0

    @pytest.mark.parametrize("provider_type,kwargs", INSTANTIABLE)
    def test_has_provider_name(self, provider_type, kwargs):
        a = create_adapter(provider_type, f"Test {provider_type}", **kwargs)
        assert hasattr(a, "provider_name")
        assert isinstance(a.provider_name, str)

    @pytest.mark.parametrize("provider_type,kwargs", INSTANTIABLE)
    def test_has_required_methods(self, provider_type, kwargs):
        a = create_adapter(provider_type, f"Test {provider_type}", **kwargs)
        for method in ("connect", "disconnect", "validate_api_key",
                       "list_models", "get_model", "chat", "stream", "health"):
            assert callable(getattr(a, method, None)), f"{provider_type} missing {method}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("provider_type,kwargs", INSTANTIABLE)
    async def test_connect_returns_status(self, provider_type, kwargs):
        a = create_adapter(provider_type, f"Test {provider_type}", **kwargs)
        from aios.core.adapters.base import ProviderStatus
        status = await a.connect()
        assert isinstance(status, ProviderStatus)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("provider_type,kwargs", INSTANTIABLE)
    async def test_health_returns_status(self, provider_type, kwargs):
        a = create_adapter(provider_type, f"Test {provider_type}", **kwargs)
        from aios.core.adapters.base import ProviderStatus
        status = await a.health()
        assert isinstance(status, ProviderStatus)
