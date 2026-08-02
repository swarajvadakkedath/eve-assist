"""Provider Registry — single source of truth for all provider definitions.

Every provider type registers itself here. The registry is the authoritative
metadata for adapter selection, model discovery, credential handling, and
frontend rendering.

Adding a new provider:
  1. Register a ProviderDefinition in _register_builtins() (or at runtime)
  2. No edits to ProviderManager, SmartRouter, or frontend code required
  3. If OpenAI-compatible: just set openai_compatible=True
  4. If native API: also add a dedicated adapter class + factory builder
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProviderDefinition:
    """Metadata for a provider type. Immutable once registered."""

    provider_type: str
    display_name: str
    default_endpoint: str = ""
    models_endpoint: str | None = "/models"
    chat_endpoint: str | None = "/chat/completions"
    auth_header: str | None = "Authorization"
    auth_prefix: str | None = "Bearer "
    api_key_required: bool = True
    needs_endpoint: bool = False
    supports_organization: bool = False
    adapter_class: str = "OpenAICompatibleAdapter"
    openai_compatible: bool = True
    discovery_strategy: str = "openai_v1"  # openai_v1 | static | native
    commercial_policy: str = "generic"  # generic | openrouter | local | free_tier | ...
    extra_headers: dict[str, str] = field(default_factory=dict)
    icon: str | None = None
    priority: int = 100


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, ProviderDefinition] = {}


def register(definition: ProviderDefinition) -> None:
    """Register a provider definition. Overwrites if type already exists."""
    _REGISTRY[definition.provider_type] = definition


def get(provider_type: str) -> ProviderDefinition | None:
    """Look up a provider definition by type."""
    return _REGISTRY.get(provider_type)


def all() -> list[ProviderDefinition]:
    """Return all registered definitions, sorted by priority."""
    return sorted(_REGISTRY.values(), key=lambda d: d.priority)


def all_as_dicts() -> list[dict[str, Any]]:
    """Return all definitions as dicts (for API responses)."""
    return [
        {
            "id": d.provider_type,
            "name": d.display_name,
            "needs_endpoint": d.needs_endpoint,
            "supports_organization": d.supports_organization,
            "default_endpoint": d.default_endpoint,
            "has_models_endpoint": d.models_endpoint is not None,
            "adapter_class": d.adapter_class,
            "openai_compatible": d.openai_compatible,
            "discovery_strategy": d.discovery_strategy,
            "commercial_policy": d.commercial_policy,
            "api_key_required": d.api_key_required,
            "icon": d.icon,
        }
        for d in all()
    ]


# ---------------------------------------------------------------------------
# Built-in provider definitions
# ---------------------------------------------------------------------------
# Migrated from PROVIDER_META in provider_manager.py (16 entries).
# Each entry preserves the original endpoint/auth metadata exactly.

def _register_builtins() -> None:
    """Register the 16 built-in provider types."""

    register(ProviderDefinition(
        provider_type="google",
        display_name="Google AI Studio",
        default_endpoint="https://generativelanguage.googleapis.com/v1beta",
        models_endpoint="/models",
        chat_endpoint="/models/{model}:generateContent",
        auth_header="x-goog-api-key",
        auth_prefix=None,
        api_key_required=True,
        needs_endpoint=False,
        adapter_class="GoogleAdapter",
        openai_compatible=False,
        discovery_strategy="native",
        commercial_policy="generic",
        icon="google",
    ))

    register(ProviderDefinition(
        provider_type="openai",
        display_name="OpenAI",
        default_endpoint="https://api.openai.com/v1",
        models_endpoint="/models",
        chat_endpoint="/chat/completions",
        auth_header="Authorization",
        auth_prefix="Bearer ",
        api_key_required=True,
        needs_endpoint=False,
        supports_organization=True,
        adapter_class="OpenAIAdapter",
        openai_compatible=False,
        discovery_strategy="native",
        commercial_policy="generic",
        icon="openai",
    ))

    register(ProviderDefinition(
        provider_type="anthropic",
        display_name="Anthropic",
        default_endpoint="https://api.anthropic.com/v1",
        models_endpoint=None,
        chat_endpoint="/messages",
        auth_header="x-api-key",
        auth_prefix=None,
        api_key_required=True,
        needs_endpoint=False,
        adapter_class="AnthropicAdapter",
        openai_compatible=False,
        discovery_strategy="static",
        commercial_policy="generic",
        icon="anthropic",
    ))

    register(ProviderDefinition(
        provider_type="ollama",
        display_name="Ollama",
        default_endpoint="http://localhost:11434",
        models_endpoint="/api/tags",
        chat_endpoint="/api/chat",
        auth_header=None,
        auth_prefix=None,
        api_key_required=False,
        needs_endpoint=True,
        adapter_class="OllamaAdapter",
        openai_compatible=False,
        discovery_strategy="native",
        commercial_policy="local",
        icon="ollama",
    ))

    register(ProviderDefinition(
        provider_type="groq",
        display_name="Groq",
        default_endpoint="https://api.groq.com/openai/v1",
        models_endpoint="/models",
        chat_endpoint="/chat/completions",
        auth_header="Authorization",
        auth_prefix="Bearer ",
        api_key_required=True,
        needs_endpoint=False,
        adapter_class="GroqAdapter",
        openai_compatible=False,
        discovery_strategy="native",
        commercial_policy="free_tier",
        icon="groq",
    ))

    register(ProviderDefinition(
        provider_type="cohere",
        display_name="Cohere",
        default_endpoint="https://api.cohere.com",
        models_endpoint=None,
        chat_endpoint="/v2/chat",
        auth_header="Authorization",
        auth_prefix="Bearer ",
        api_key_required=True,
        needs_endpoint=False,
        adapter_class="CohereAdapter",
        openai_compatible=False,
        discovery_strategy="static",
        commercial_policy="generic",
        icon="cohere",
    ))

    register(ProviderDefinition(
        provider_type="cloudflare",
        display_name="Cloudflare Workers AI",
        default_endpoint="",
        models_endpoint="/models",
        chat_endpoint="/chat/completions",
        auth_header="Authorization",
        auth_prefix="Bearer ",
        api_key_required=True,
        needs_endpoint=True,
        adapter_class="CloudflareAdapter",
        openai_compatible=False,
        discovery_strategy="static",
        commercial_policy="free_tier",
        icon="cloudflare",
    ))

    register(ProviderDefinition(
        provider_type="mistral",
        display_name="Mistral",
        default_endpoint="https://api.mistral.ai/v1",
        models_endpoint="/models",
        chat_endpoint="/chat/completions",
        auth_header="Authorization",
        auth_prefix="Bearer ",
        api_key_required=True,
        needs_endpoint=False,
        adapter_class="OpenAICompatibleAdapter",
        openai_compatible=True,
        discovery_strategy="openai_v1",
        commercial_policy="mistral",
        icon="mistral",
    ))

    register(ProviderDefinition(
        provider_type="cerebras",
        display_name="Cerebras",
        default_endpoint="https://api.cerebras.ai/v1",
        models_endpoint="/models",
        chat_endpoint="/chat/completions",
        auth_header="Authorization",
        auth_prefix="Bearer ",
        api_key_required=True,
        needs_endpoint=False,
        adapter_class="OpenAICompatibleAdapter",
        openai_compatible=True,
        discovery_strategy="openai_v1",
        commercial_policy="paid",
        icon="cerebras",
    ))

    register(ProviderDefinition(
        provider_type="openrouter",
        display_name="OpenRouter",
        default_endpoint="https://openrouter.ai/api/v1",
        models_endpoint="/models",
        chat_endpoint="/chat/completions",
        auth_header="Authorization",
        auth_prefix="Bearer ",
        api_key_required=True,
        needs_endpoint=False,
        adapter_class="OpenAICompatibleAdapter",
        openai_compatible=True,
        discovery_strategy="openai_v1",
        commercial_policy="openrouter",
        extra_headers={
            "HTTP-Referer": "https://eve-ai.app",
            "X-Title": "Eve AI",
        },
        icon="openrouter",
    ))

    register(ProviderDefinition(
        provider_type="github_models",
        display_name="GitHub Models",
        default_endpoint="https://models.inference.ai.azure.com",
        models_endpoint="/models",
        chat_endpoint="/chat/completions",
        auth_header="Authorization",
        auth_prefix="Bearer ",
        api_key_required=True,
        needs_endpoint=False,
        adapter_class="OpenAICompatibleAdapter",
        openai_compatible=True,
        discovery_strategy="openai_v1",
        commercial_policy="free_tier",
        extra_headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
        },
        icon="github",
    ))

    register(ProviderDefinition(
        provider_type="huggingface",
        display_name="Hugging Face",
        default_endpoint="https://api-inference.huggingface.co",
        models_endpoint="/models",
        chat_endpoint="/chat/completions",
        auth_header="Authorization",
        auth_prefix="Bearer ",
        api_key_required=True,
        needs_endpoint=False,
        adapter_class="OpenAICompatibleAdapter",
        openai_compatible=True,
        discovery_strategy="openai_v1",
        commercial_policy="credit_based",
        icon="huggingface",
    ))

    register(ProviderDefinition(
        provider_type="lm_studio",
        display_name="LM Studio",
        default_endpoint="http://localhost:1234/v1",
        models_endpoint="/models",
        chat_endpoint="/chat/completions",
        auth_header="Authorization",
        auth_prefix="Bearer ",
        api_key_required=False,
        needs_endpoint=True,
        adapter_class="OpenAICompatibleAdapter",
        openai_compatible=True,
        discovery_strategy="lmstudio",
        commercial_policy="local",
        icon="lmstudio",
    ))

    register(ProviderDefinition(
        provider_type="nvidia",
        display_name="NVIDIA NIM",
        default_endpoint="https://integrate.api.nvidia.com/v1",
        models_endpoint="/models",
        chat_endpoint="/chat/completions",
        auth_header="Authorization",
        auth_prefix="Bearer ",
        api_key_required=True,
        needs_endpoint=False,
        adapter_class="OpenAICompatibleAdapter",
        openai_compatible=True,
        discovery_strategy="openai_v1",
        commercial_policy="free_tier",
        extra_headers={"Content-Type": "application/json"},
        icon="nvidia",
    ))

    register(ProviderDefinition(
        provider_type="openai_compatible",
        display_name="OpenAI Compatible",
        default_endpoint="",
        models_endpoint="/models",
        chat_endpoint="/chat/completions",
        auth_header="Authorization",
        auth_prefix="Bearer ",
        api_key_required=True,
        needs_endpoint=True,
        adapter_class="OpenAICompatibleAdapter",
        openai_compatible=True,
        discovery_strategy="openai_v1",
        commercial_policy="generic",
        icon=None,
    ))

    register(ProviderDefinition(
        provider_type="custom",
        display_name="Custom Provider",
        default_endpoint="",
        models_endpoint=None,
        chat_endpoint="/chat/completions",
        auth_header="Authorization",
        auth_prefix="Bearer ",
        api_key_required=True,
        needs_endpoint=True,
        adapter_class="OpenAICompatibleAdapter",
        openai_compatible=True,
        discovery_strategy="openai_v1",
        commercial_policy="generic",
        icon=None,
    ))


# ---------------------------------------------------------------------------
# Auto-register builtins on module import
# ---------------------------------------------------------------------------
_register_builtins()
