"""Provider Factory — creates adapters from registry definitions.

Single entry point: create_adapter(provider_type, ...) → AIProviderAdapter.
Looks up the ProviderDefinition from the registry, selects the correct
adapter class, and instantiates it with the right parameters.

No if/elif chain to maintain when adding new providers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aios.core.provider_registry import get

if TYPE_CHECKING:
    from aios.core.streaming_manager import StreamingManager
    from aios.core.timeout_retry import TimeoutConfig

logger = __import__("structlog").get_logger(__name__)


def create_adapter(
    provider_type: str,
    provider_name: str,
    api_key: str = "",
    base_url: str = "",
    organization: str = "",
    timeout_config: TimeoutConfig | None = None,
    streaming_manager: StreamingManager | None = None,
) -> Any:
    """Create and return an adapter instance for the given provider type.

    Uses the registry definition to determine which adapter class to instantiate
    and which parameters it needs. This replaces the old if/elif chain in
    ProviderManager._create_adapter().

    Raises:
        ValueError: If provider_type is not registered.
        ImportError: If the native adapter module cannot be imported.
    """
    definition = get(provider_type)
    if definition is None:
        raise ValueError(f"Unknown provider type: {provider_type!r}")

    adapter_class_name = definition.adapter_class

    # --- Native adapter classes (one per provider) ---
    native_map = {
        "GoogleAdapter": _create_google,
        "OpenAIAdapter": _create_openai,
        "AnthropicAdapter": _create_anthropic,
        "OllamaAdapter": _create_ollama,
        "CohereAdapter": _create_cohere,
        "CloudflareAdapter": _create_cloudflare,
        "GroqAdapter": _create_groq,
    }

    builder = native_map.get(adapter_class_name)
    if builder:
        return builder(
            definition=definition,
            api_key=api_key,
            base_url=base_url or definition.default_endpoint,
            organization=organization,
            provider_name=provider_name,
            timeout_config=timeout_config,
            streaming_manager=streaming_manager,
        )

    # --- OpenAI-compatible adapters (generic) ---
    if adapter_class_name == "OpenAICompatibleAdapter":
        return _create_openai_compatible(
            definition=definition,
            provider_type=provider_type,
            provider_name=provider_name,
            api_key=api_key,
            base_url=base_url or definition.default_endpoint,
            timeout_config=timeout_config,
            streaming_manager=streaming_manager,
        )

    raise ValueError(
        f"Provider {provider_type!r} has unknown adapter class: {adapter_class_name!r}"
    )


# ---------------------------------------------------------------------------
# Native builders
# ---------------------------------------------------------------------------

def _create_google(
    *,
    definition: Any,
    api_key: str,
    base_url: str,
    organization: str,
    provider_name: str,
    timeout_config: TimeoutConfig | None,
    streaming_manager: StreamingManager | None,
) -> Any:
    from aios.core.adapters.google_adapter import GoogleAdapter

    return GoogleAdapter(
        api_key=api_key,
        base_url=base_url,
        timeout_config=timeout_config,
        streaming_manager=streaming_manager,
    )


def _create_openai(
    *,
    definition: Any,
    api_key: str,
    base_url: str,
    organization: str,
    provider_name: str,
    timeout_config: TimeoutConfig | None,
    streaming_manager: StreamingManager | None,
) -> Any:
    from aios.core.adapters.openai_adapter import OpenAIAdapter

    return OpenAIAdapter(
        api_key=api_key,
        base_url=base_url,
        organization=organization,
        timeout_config=timeout_config,
        streaming_manager=streaming_manager,
    )


def _create_anthropic(
    *,
    definition: Any,
    api_key: str,
    base_url: str,
    organization: str,
    provider_name: str,
    timeout_config: TimeoutConfig | None,
    streaming_manager: StreamingManager | None,
) -> Any:
    from aios.core.adapters.anthropic_adapter import AnthropicAdapter

    return AnthropicAdapter(
        api_key=api_key,
        base_url=base_url,
        timeout_config=timeout_config,
        streaming_manager=streaming_manager,
    )


def _create_ollama(
    *,
    definition: Any,
    api_key: str,
    base_url: str,
    organization: str,
    provider_name: str,
    timeout_config: TimeoutConfig | None,
    streaming_manager: StreamingManager | None,
) -> Any:
    from aios.core.adapters.ollama_adapter import OllamaAdapter

    return OllamaAdapter(
        base_url=base_url,
        timeout_config=timeout_config,
        streaming_manager=streaming_manager,
    )


def _create_cohere(
    *,
    definition: Any,
    api_key: str,
    base_url: str,
    organization: str,
    provider_name: str,
    timeout_config: TimeoutConfig | None,
    streaming_manager: StreamingManager | None,
) -> Any:
    from aios.core.adapters.cohere_adapter import CohereAdapter

    return CohereAdapter(
        api_key=api_key,
        base_url=base_url,
        timeout_config=timeout_config,
        streaming_manager=streaming_manager,
    )


def _create_cloudflare(
    *,
    definition: Any,
    api_key: str,
    base_url: str,
    organization: str,
    provider_name: str,
    timeout_config: TimeoutConfig | None,
    streaming_manager: StreamingManager | None,
) -> Any:
    from aios.core.adapters.cloudflare_adapter import CloudflareAdapter

    # Cloudflare needs account_id to build the endpoint URL.
    # If a custom base_url is provided, use it directly.
    # Otherwise, account_id must come from extra_params (set by ProviderManager).
    account_id = getattr(definition, "account_id", "")
    return CloudflareAdapter(
        api_key=api_key,
        base_url=base_url,
        account_id=account_id,
        timeout_config=timeout_config,
        streaming_manager=streaming_manager,
    )


def _create_groq(
    *,
    definition: Any,
    api_key: str,
    base_url: str,
    organization: str,
    provider_name: str,
    timeout_config: TimeoutConfig | None,
    streaming_manager: StreamingManager | None,
) -> Any:
    from aios.core.adapters.groq_adapter import GroqAdapter

    return GroqAdapter(
        api_key=api_key,
        base_url=base_url,
        timeout_config=timeout_config,
        streaming_manager=streaming_manager,
    )


# ---------------------------------------------------------------------------
# OpenAI-compatible builder
# ---------------------------------------------------------------------------

def _create_openai_compatible(
    *,
    definition: Any,
    provider_type: str,
    provider_name: str,
    api_key: str,
    base_url: str,
    timeout_config: TimeoutConfig | None,
    streaming_manager: StreamingManager | None,
) -> Any:
    from aios.core.adapters.openai_compatible_adapter import OpenAICompatibleAdapter

    # Pass registry metadata so the adapter can configure headers,
    # commercial policy, and discovery strategy without hardcoding.
    metadata = {
        "commercial_policy": definition.commercial_policy,
        "discovery_strategy": definition.discovery_strategy,
        "extra_headers": definition.extra_headers,
        "priority": definition.priority,
    }

    return OpenAICompatibleAdapter(
        provider_type=provider_type,
        provider_name=provider_name,
        api_key=api_key,
        base_url=base_url,
        timeout_config=timeout_config,
        streaming_manager=streaming_manager,
        metadata=metadata,
    )
