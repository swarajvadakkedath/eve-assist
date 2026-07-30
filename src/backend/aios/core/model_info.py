"""Unified ModelInfo schema — normalizes every provider model into one canonical format."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CommercialStatus(str, Enum):
    """How a model is billed — never guess, use explicit classification."""
    FREE = "free"              # Explicitly free (e.g. OpenRouter free variant, Ollama local)
    FREE_TIER = "free_tier"    # Zero-cost under account rate limits (e.g. Google free tier)
    CREDIT_BASED = "credit_based"  # Uses account credits (e.g. HuggingFace)
    PAID = "paid"              # Standard paid model
    LOCAL = "local"            # Local inference (Ollama, LM Studio)
    UNKNOWN = "unknown"        # Cannot determine — never equate with FREE


class AvailabilityStatus(str, Enum):
    """Current availability of a model from a provider."""
    AVAILABLE = "available"
    DEPRECATED = "deprecated"
    PREVIEW = "preview"
    EXPERIMENTAL = "experimental"
    REMOVED = "removed"
    UNKNOWN = "unknown"


@dataclass
class ModelInfo:
    """Canonical model info normalized across all providers."""

    id: str
    display_name: str
    provider_id: str
    provider_name: str

    context_window: int = 4096
    max_output_tokens: int = 4096

    supports_streaming: bool = True
    supports_vision: bool = False
    supports_reasoning: bool = False
    supports_thinking: bool = False
    supports_tools: bool = False
    supports_json: bool = False
    supports_embeddings: bool = False
    supports_audio: bool = False
    supports_image_generation: bool = False
    supports_video: bool = False
    supports_files: bool = False
    supports_caching: bool = False
    supports_function_calling: bool = False
    supports_system_prompt: bool = True
    supports_temperature: bool = True
    supports_top_p: bool = True
    supports_top_k: bool = False
    supports_seed: bool = False
    supports_log_probs: bool = False

    speed: int = 5
    quality: int = 5
    latency: float = 0.0

    pricing: dict[str, float] = field(default_factory=lambda: {"input": 0.0, "output": 0.0})
    is_free: bool = False
    recommended: bool = False
    deprecated: bool = False
    experimental: bool = False
    enabled: bool = True

    # --- New fields for provider expansion ---
    commercial_status: CommercialStatus = CommercialStatus.UNKNOWN
    availability: AvailabilityStatus = AvailabilityStatus.AVAILABLE
    provider_type: str = ""                    # e.g. "google", "openrouter"
    provider_instance_id: str = ""             # e.g. "google-abc123" (distinct from provider_type)
    discovered_at: str = ""                    # ISO timestamp of when this model was discovered
    discovery_source: str = ""                 # "api", "catalog", "merged"
    raw_provider_metadata: dict[str, Any] = field(default_factory=dict)  # Safe subset of provider response

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "displayName": self.display_name,
            "providerId": self.provider_id,
            "providerName": self.provider_name,
            "providerType": self.provider_type,
            "providerInstanceId": self.provider_instance_id,
            "contextWindow": self.context_window,
            "maxOutputTokens": self.max_output_tokens,
            "supportsStreaming": self.supports_streaming,
            "supportsVision": self.supports_vision,
            "supportsReasoning": self.supports_reasoning,
            "supportsThinking": self.supports_thinking,
            "supportsTools": self.supports_tools,
            "supportsJSON": self.supports_json,
            "supportsEmbeddings": self.supports_embeddings,
            "supportsAudio": self.supports_audio,
            "supportsImageGeneration": self.supports_image_generation,
            "supportsVideo": self.supports_video,
            "supportsFiles": self.supports_files,
            "supportsCaching": self.supports_caching,
            "supportsFunctionCalling": self.supports_function_calling,
            "supportsSystemPrompt": self.supports_system_prompt,
            "supportsTemperature": self.supports_temperature,
            "supportsTopP": self.supports_top_p,
            "supportsTopK": self.supports_top_k,
            "supportsSeed": self.supports_seed,
            "supportsLogProbs": self.supports_log_probs,
            "speed": self.speed,
            "quality": self.quality,
            "latency": self.latency,
            "pricing": self.pricing,
            "isFree": self.is_free,
            "commercialStatus": self.commercial_status.value,
            "availability": self.availability.value,
            "recommended": self.recommended,
            "deprecated": self.deprecated,
            "experimental": self.experimental,
            "enabled": self.enabled,
            "discoveredAt": self.discovered_at,
            "discoverySource": self.discovery_source,
            "rawProviderMetadata": self.raw_provider_metadata,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ModelInfo:
        # Parse enums safely
        cs = d.get("commercialStatus", d.get("commercial_status", "unknown"))
        if isinstance(cs, str):
            try:
                cs = CommercialStatus(cs)
            except ValueError:
                cs = CommercialStatus.UNKNOWN

        av = d.get("availability", "available")
        if isinstance(av, str):
            try:
                av = AvailabilityStatus(av)
            except ValueError:
                av = AvailabilityStatus.UNKNOWN

        return cls(
            id=d["id"],
            display_name=d.get("displayName", d["id"]),
            provider_id=d.get("providerId", d.get("provider", "")),
            provider_name=d.get("providerName", d.get("provider", "")),
            provider_type=d.get("providerType", d.get("provider_type", "")),
            provider_instance_id=d.get("providerInstanceId", d.get("provider_instance_id", "")),
            context_window=d.get("contextWindow", d.get("contextLength", 4096)),
            max_output_tokens=d.get("maxOutputTokens", d.get("maxOutput", 4096)),
            supports_streaming=d.get("supportsStreaming", True),
            supports_vision=d.get("supportsVision", False),
            supports_reasoning=d.get("supportsReasoning", False),
            supports_thinking=d.get("supportsThinking", False),
            supports_tools=d.get("supportsTools", False),
            supports_json=d.get("supportsJSON", False),
            supports_embeddings=d.get("supportsEmbeddings", False),
            supports_audio=d.get("supportsAudio", False),
            supports_image_generation=d.get("supportsImageGeneration", False),
            supports_video=d.get("supportsVideo", False),
            supports_files=d.get("supportsFiles", False),
            supports_caching=d.get("supportsCaching", False),
            supports_function_calling=d.get("supportsFunctionCalling", False),
            supports_system_prompt=d.get("supportsSystemPrompt", True),
            supports_temperature=d.get("supportsTemperature", True),
            supports_top_p=d.get("supportsTopP", True),
            supports_top_k=d.get("supportsTopK", False),
            supports_seed=d.get("supportsSeed", False),
            supports_log_probs=d.get("supportsLogProbs", False),
            speed=d.get("speed", 5),
            quality=d.get("quality", 5),
            latency=d.get("latency", 0.0),
            pricing=d.get("pricing", {"input": 0.0, "output": 0.0}),
            is_free=d.get("isFree", False),
            commercial_status=cs,
            availability=av,
            recommended=d.get("recommended", False),
            deprecated=d.get("deprecated", False),
            experimental=d.get("experimental", False),
            enabled=d.get("enabled", True),
            discovered_at=d.get("discoveredAt", d.get("discovered_at", "")),
            discovery_source=d.get("discoverySource", d.get("discovery_source", "")),
            raw_provider_metadata=d.get("rawProviderMetadata", d.get("raw_provider_metadata", {})),
            metadata=d.get("metadata", {}),
        )

    @classmethod
    def from_old_format(cls, d: dict[str, Any], provider_id: str, provider_name: str) -> ModelInfo:
        """Convert legacy model dict to ModelInfo (backward compat with model_catalog format)."""
        pricing = {
            "input": d.get("costPer1kInput", d.get("cost_per_1k_input", 0.0)),
            "output": d.get("costPer1kOutput", d.get("cost_per_1k_output", 0.0)),
        }

        # Determine commercial status from legacy is_free / pricing
        is_free = d.get("isFree", d.get("is_free", False))
        if is_free:
            cs = CommercialStatus.FREE
        elif pricing["input"] == 0.0 and pricing["output"] == 0.0:
            cs = CommercialStatus.FREE_TIER
        else:
            cs = CommercialStatus.PAID

        return cls(
            id=d["id"],
            display_name=d.get("displayName", d["id"]),
            provider_id=provider_id,
            provider_name=provider_name,
            context_window=d.get("contextLength", d.get("context_length", 4096)),
            max_output_tokens=d.get("maxOutput", d.get("max_output", 4096)),
            supports_streaming=d.get("supportsStreaming", d.get("supports_streaming", True)),
            supports_vision=d.get("supportsVision", d.get("supports_vision", False)),
            supports_reasoning=d.get("supportsReasoning", d.get("supports_reasoning", False)),
            supports_thinking=d.get("supportsThinking", d.get("supports_thinking", False)),
            supports_function_calling=d.get("supportsFunctionCalling", d.get("supports_function_calling", False)),
            supports_json=d.get("supportsJSON", d.get("supports_json", False)),
            supports_embeddings=d.get("supportsEmbeddings", d.get("supports_embeddings", False)),
            supports_audio=d.get("supportsAudio", d.get("supports_audio", False)),
            supports_image_generation=d.get("supportsImageGeneration", d.get("supports_image_generation", False)),
            supports_system_prompt=d.get("supportsSystemPrompt", d.get("supports_system_prompt", True)),
            supports_temperature=d.get("supportsTemperature", d.get("supports_temperature", True)),
            supports_top_p=d.get("supportsTopP", d.get("supports_top_p", True)),
            speed=d.get("speed", 5),
            quality=d.get("quality", 5),
            pricing=pricing,
            is_free=is_free,
            commercial_status=cs,
            recommended=d.get("recommended", False),
            deprecated=d.get("deprecated", False),
            enabled=d.get("enabled", True),
            discovery_source="catalog",
        )
