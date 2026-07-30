"""Model definitions and static catalog for all known AI provider models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Model:
    id: str
    display_name: str
    provider: str
    context_length: int = 4096
    max_output: int = 4096
    supports_streaming: bool = True
    supports_vision: bool = False
    supports_image_generation: bool = False
    supports_audio: bool = False
    supports_reasoning: bool = False
    supports_function_calling: bool = True
    supports_embeddings: bool = False
    supports_thinking: bool = False
    supports_json: bool = True
    enabled: bool = True
    is_free: bool = False
    recommended: bool = False
    deprecated: bool = False
    speed: int = 5
    quality: int = 5
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "displayName": self.display_name,
            "provider": self.provider,
            "contextLength": self.context_length,
            "maxOutput": self.max_output,
            "supportsStreaming": self.supports_streaming,
            "supportsVision": self.supports_vision,
            "supportsImageGeneration": self.supports_image_generation,
            "supportsAudio": self.supports_audio,
            "supportsReasoning": self.supports_reasoning,
            "supportsFunctionCalling": self.supports_function_calling,
            "supportsEmbeddings": self.supports_embeddings,
            "supportsThinking": self.supports_thinking,
            "supportsJSON": self.supports_json,
            "enabled": self.enabled,
            "isFree": self.is_free,
            "recommended": self.recommended,
            "deprecated": self.deprecated,
            "speed": self.speed,
            "quality": self.quality,
            "costPer1kInput": self.cost_per_1k_input,
            "costPer1kOutput": self.cost_per_1k_output,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Model:
        return cls(
            id=d["id"],
            display_name=d.get("displayName", d["id"]),
            provider=d.get("provider", ""),
            context_length=d.get("contextLength", 4096),
            max_output=d.get("maxOutput", 4096),
            supports_streaming=d.get("supportsStreaming", True),
            supports_vision=d.get("supportsVision", False),
            supports_image_generation=d.get("supportsImageGeneration", False),
            supports_audio=d.get("supportsAudio", False),
            supports_reasoning=d.get("supportsReasoning", False),
            supports_function_calling=d.get("supportsFunctionCalling", True),
            supports_embeddings=d.get("supportsEmbeddings", False),
            supports_thinking=d.get("supportsThinking", False),
            supports_json=d.get("supportsJSON", True),
            enabled=d.get("enabled", True),
            is_free=d.get("isFree", False),
            recommended=d.get("recommended", False),
            deprecated=d.get("deprecated", False),
            speed=d.get("speed", 5),
            quality=d.get("quality", 5),
            cost_per_1k_input=d.get("costPer1kInput", 0.0),
            cost_per_1k_output=d.get("costPer1kOutput", 0.0),
        )


# ---------------------------------------------------------------------------
# Model Catalog — known models for each provider
# ---------------------------------------------------------------------------

MODEL_CATALOG: dict[str, list[dict[str, Any]]] = {
    "google": [
        {"id": "gemini-2.5-flash", "displayName": "Gemini 2.5 Flash", "contextLength": 1048576, "maxOutput": 8192, "supportsVision": True, "supportsReasoning": True, "supportsFunctionCalling": True, "supportsJSON": True, "isFree": True, "recommended": True, "speed": 9, "quality": 8, "costPer1kInput": 0.00015, "costPer1kOutput": 0.00060},
        {"id": "gemini-2.5-pro", "displayName": "Gemini 2.5 Pro", "contextLength": 1048576, "maxOutput": 65536, "supportsVision": True, "supportsReasoning": True, "supportsFunctionCalling": True, "supportsJSON": True, "isFree": False, "recommended": True, "speed": 6, "quality": 10, "costPer1kInput": 0.00125, "costPer1kOutput": 0.01000},
        {"id": "gemini-2.0-flash", "displayName": "Gemini 2.0 Flash", "contextLength": 1048576, "maxOutput": 8192, "supportsVision": True, "supportsFunctionCalling": True, "supportsJSON": True, "isFree": True, "speed": 9, "quality": 7, "costPer1kInput": 0.00010, "costPer1kOutput": 0.00040},
        {"id": "gemini-2.0-flash-lite", "displayName": "Gemini 2.0 Flash Lite", "contextLength": 1048576, "maxOutput": 8192, "supportsVision": True, "supportsJSON": True, "isFree": True, "speed": 10, "quality": 5, "costPer1kInput": 0.000075, "costPer1kOutput": 0.00030},
        {"id": "gemini-1.5-flash", "displayName": "Gemini 1.5 Flash", "contextLength": 1048576, "maxOutput": 8192, "supportsVision": True, "supportsFunctionCalling": True, "supportsJSON": True, "isFree": True, "speed": 9, "quality": 6, "costPer1kInput": 0.000075, "costPer1kOutput": 0.00030},
        {"id": "gemini-1.5-pro", "displayName": "Gemini 1.5 Pro", "contextLength": 2097152, "maxOutput": 8192, "supportsVision": True, "supportsReasoning": True, "supportsFunctionCalling": True, "supportsJSON": True, "isFree": False, "speed": 6, "quality": 9, "costPer1kInput": 0.00350, "costPer1kOutput": 0.01050},
    ],
    "openai": [
        {"id": "gpt-4o", "displayName": "GPT-4o", "contextLength": 128000, "maxOutput": 16384, "supportsVision": True, "supportsFunctionCalling": True, "supportsJSON": True, "supportsAudio": True, "isFree": False, "recommended": True, "speed": 7, "quality": 9, "costPer1kInput": 0.00250, "costPer1kOutput": 0.01000},
        {"id": "gpt-4o-mini", "displayName": "GPT-4o Mini", "contextLength": 128000, "maxOutput": 16384, "supportsVision": True, "supportsFunctionCalling": True, "supportsJSON": True, "isFree": False, "speed": 9, "quality": 7, "costPer1kInput": 0.00015, "costPer1kOutput": 0.00060},
        {"id": "gpt-4-turbo", "displayName": "GPT-4 Turbo", "contextLength": 128000, "maxOutput": 4096, "supportsVision": True, "supportsFunctionCalling": True, "isFree": False, "speed": 5, "quality": 9, "costPer1kInput": 0.01000, "costPer1kOutput": 0.03000},
        {"id": "gpt-4", "displayName": "GPT-4", "contextLength": 8192, "maxOutput": 4096, "supportsFunctionCalling": True, "isFree": False, "speed": 4, "quality": 9, "costPer1kInput": 0.03000, "costPer1kOutput": 0.06000},
        {"id": "gpt-3.5-turbo", "displayName": "GPT-3.5 Turbo", "contextLength": 16385, "maxOutput": 4096, "supportsFunctionCalling": True, "isFree": False, "speed": 10, "quality": 5, "costPer1kInput": 0.00050, "costPer1kOutput": 0.00150},
        {"id": "o1", "displayName": "o1", "contextLength": 200000, "maxOutput": 100000, "supportsReasoning": True, "supportsFunctionCalling": True, "isFree": False, "speed": 3, "quality": 10, "costPer1kInput": 0.01500, "costPer1kOutput": 0.06000},
        {"id": "o1-mini", "displayName": "o1 Mini", "contextLength": 128000, "maxOutput": 65536, "supportsReasoning": True, "isFree": False, "speed": 4, "quality": 8, "costPer1kInput": 0.00110, "costPer1kOutput": 0.00440},
        {"id": "o3-mini", "displayName": "o3 Mini", "contextLength": 200000, "maxOutput": 100000, "supportsReasoning": True, "supportsFunctionCalling": True, "isFree": False, "recommended": True, "speed": 5, "quality": 9, "costPer1kInput": 0.00110, "costPer1kOutput": 0.00440},
    ],
    "anthropic": [
        {"id": "claude-sonnet-4-20250514", "displayName": "Claude Sonnet 4", "contextLength": 200000, "maxOutput": 8192, "supportsVision": True, "supportsReasoning": True, "supportsFunctionCalling": True, "supportsJSON": True, "isFree": False, "recommended": True, "speed": 7, "quality": 9, "costPer1kInput": 0.00300, "costPer1kOutput": 0.01500},
        {"id": "claude-3-5-sonnet-20241022", "displayName": "Claude 3.5 Sonnet", "contextLength": 200000, "maxOutput": 8192, "supportsVision": True, "supportsFunctionCalling": True, "supportsJSON": True, "isFree": False, "speed": 7, "quality": 9, "costPer1kInput": 0.00300, "costPer1kOutput": 0.01500},
        {"id": "claude-3-5-haiku-20241022", "displayName": "Claude 3.5 Haiku", "contextLength": 200000, "maxOutput": 8192, "supportsVision": True, "supportsFunctionCalling": True, "supportsJSON": True, "isFree": False, "speed": 9, "quality": 7, "costPer1kInput": 0.00080, "costPer1kOutput": 0.00400},
        {"id": "claude-opus-4-20250514", "displayName": "Claude Opus 4", "contextLength": 200000, "maxOutput": 8192, "supportsVision": True, "supportsReasoning": True, "supportsFunctionCalling": True, "supportsJSON": True, "isFree": False, "speed": 4, "quality": 10, "costPer1kInput": 0.01500, "costPer1kOutput": 0.07500},
    ],
    "groq": [
        {"id": "llama-3.3-70b-versatile", "displayName": "Llama 3.3 70B", "contextLength": 131072, "maxOutput": 32768, "supportsFunctionCalling": True, "supportsJSON": True, "isFree": True, "recommended": True, "speed": 8, "quality": 8, "costPer1kInput": 0.00059, "costPer1kOutput": 0.00079},
        {"id": "llama-3.1-8b-instant", "displayName": "Llama 3.1 8B Instant", "contextLength": 131072, "maxOutput": 8192, "supportsFunctionCalling": True, "supportsJSON": True, "isFree": True, "speed": 10, "quality": 5, "costPer1kInput": 0.00005, "costPer1kOutput": 0.00008},
        {"id": "mixtral-8x7b-32768", "displayName": "Mixtral 8x7B", "contextLength": 32768, "maxOutput": 4096, "isFree": True, "speed": 7, "quality": 7, "costPer1kInput": 0.00024, "costPer1kOutput": 0.00024},
        {"id": "gemma2-9b-it", "displayName": "Gemma 2 9B", "contextLength": 8192, "maxOutput": 4096, "isFree": True, "speed": 9, "quality": 6, "costPer1kInput": 0.00008, "costPer1kOutput": 0.00008},
        {"id": "qwen/qwen3-32b", "displayName": "Qwen 3 32B", "contextLength": 131072, "maxOutput": 16384, "supportsFunctionCalling": True, "supportsJSON": True, "isFree": True, "speed": 7, "quality": 8, "costPer1kInput": 0.00024, "costPer1kOutput": 0.00024},
        {"id": "mistral-saba-24b", "displayName": "Mistral Saba 24B", "contextLength": 32768, "maxOutput": 4096, "isFree": True, "speed": 7, "quality": 7, "costPer1kInput": 0.00020, "costPer1kOutput": 0.00020},
        {"id": "deepseek-r1-distill-llama-70b", "displayName": "DeepSeek R1 Distill Llama 70B", "contextLength": 131072, "maxOutput": 16384, "supportsReasoning": True, "isFree": True, "speed": 6, "quality": 8, "costPer1kInput": 0.00075, "costPer1kOutput": 0.00099},
    ],
    "openrouter": [],  # dynamic — fetched from API
    "mistral": [
        {"id": "mistral-large-latest", "displayName": "Mistral Large", "contextLength": 131072, "maxOutput": 8192, "supportsFunctionCalling": True, "supportsJSON": True, "isFree": False, "recommended": True, "speed": 7, "quality": 8, "costPer1kInput": 0.00200, "costPer1kOutput": 0.00600},
        {"id": "mistral-small-latest", "displayName": "Mistral Small", "contextLength": 32768, "maxOutput": 8192, "supportsFunctionCalling": True, "isFree": False, "speed": 9, "quality": 6, "costPer1kInput": 0.00100, "costPer1kOutput": 0.00300},
        {"id": "open-mistral-nemo", "displayName": "Mistral Nemo", "contextLength": 131072, "maxOutput": 8192, "isFree": True, "speed": 9, "quality": 6, "costPer1kInput": 0.00000, "costPer1kOutput": 0.00000},
    ],
    "cerebras": [
        {"id": "llama3.1-8b", "displayName": "Llama 3.1 8B", "contextLength": 8192, "maxOutput": 4096, "isFree": False, "speed": 10, "quality": 5, "costPer1kInput": 0.00010, "costPer1kOutput": 0.00010},
        {"id": "llama3.1-70b", "displayName": "Llama 3.1 70B", "contextLength": 8192, "maxOutput": 4096, "isFree": False, "speed": 8, "quality": 8, "costPer1kInput": 0.00060, "costPer1kOutput": 0.00060},
    ],
    "github_models": [],
    "huggingface": [],
    "ollama": [
        {"id": "llama3.1", "displayName": "Llama 3.1", "contextLength": 8192, "maxOutput": 4096, "isFree": True, "recommended": True, "speed": 5, "quality": 7},
        {"id": "llama3.2", "displayName": "Llama 3.2", "contextLength": 8192, "maxOutput": 4096, "isFree": True, "speed": 6, "quality": 7},
        {"id": "mistral", "displayName": "Mistral", "contextLength": 8192, "maxOutput": 4096, "isFree": True, "speed": 7, "quality": 7},
        {"id": "codellama", "displayName": "CodeLlama", "contextLength": 16384, "maxOutput": 4096, "supportsReasoning": True, "isFree": True, "speed": 5, "quality": 6},
        {"id": "gemma2", "displayName": "Gemma 2", "contextLength": 8192, "maxOutput": 4096, "isFree": True, "speed": 7, "quality": 6},
        {"id": "phi3", "displayName": "Phi-3", "contextLength": 128000, "maxOutput": 4096, "isFree": True, "speed": 8, "quality": 6},
        {"id": "qwen2.5", "displayName": "Qwen 2.5", "contextLength": 32768, "maxOutput": 8192, "isFree": True, "speed": 6, "quality": 7},
        {"id": "deepseek-r1", "displayName": "DeepSeek R1", "contextLength": 131072, "maxOutput": 16384, "supportsReasoning": True, "isFree": True, "speed": 4, "quality": 8},
    ],
    "lm_studio": [],
    "cohere": [
        {"id": "command-a-plus-05-2026", "displayName": "Command A Plus", "contextLength": 200000, "maxOutput": 4096, "supportsVision": True, "supportsFunctionCalling": True, "supportsJSON": True, "isFree": False, "recommended": True, "speed": 7, "quality": 9, "costPer1kInput": 0.00250, "costPer1kOutput": 0.01000},
        {"id": "command-a-05-2026", "displayName": "Command A", "contextLength": 200000, "maxOutput": 4096, "supportsVision": True, "supportsFunctionCalling": True, "supportsJSON": True, "isFree": False, "speed": 8, "quality": 8, "costPer1kInput": 0.00250, "costPer1kOutput": 0.01000},
        {"id": "command-r-plus-08-2024", "displayName": "Command R Plus", "contextLength": 128000, "maxOutput": 4096, "supportsFunctionCalling": True, "supportsJSON": True, "isFree": False, "speed": 7, "quality": 8, "costPer1kInput": 0.00250, "costPer1kOutput": 0.01000},
        {"id": "command-r-08-2024", "displayName": "Command R", "contextLength": 128000, "maxOutput": 4096, "supportsFunctionCalling": True, "supportsJSON": True, "isFree": False, "speed": 8, "quality": 7, "costPer1kInput": 0.00015, "costPer1kOutput": 0.00060},
    ],
    "cloudflare": [
        {"id": "@cf/meta/llama-3.3-70b-instruct-fp16", "displayName": "Llama 3.3 70B", "contextLength": 131072, "maxOutput": 4096, "supportsFunctionCalling": True, "supportsJSON": True, "isFree": True, "recommended": True, "speed": 7, "quality": 8},
        {"id": "@cf/meta/llama-3.1-8b-instruct", "displayName": "Llama 3.1 8B", "contextLength": 131072, "maxOutput": 4096, "supportsFunctionCalling": True, "isFree": True, "speed": 9, "quality": 6},
        {"id": "@cf/meta/llama-3.2-3b-instruct", "displayName": "Llama 3.2 3B", "contextLength": 131072, "maxOutput": 4096, "isFree": True, "speed": 10, "quality": 5},
    ],
    "nvidia": [
        {"id": "meta/llama-3.3-70b-instruct", "displayName": "Llama 3.3 70B", "contextLength": 131072, "maxOutput": 4096, "supportsFunctionCalling": True, "supportsJSON": True, "isFree": True, "recommended": True, "speed": 7, "quality": 8},
        {"id": "nvidia/llama-3.1-nemotron-70b-instruct", "displayName": "Nemotron 70B", "contextLength": 131072, "maxOutput": 4096, "supportsFunctionCalling": True, "supportsJSON": True, "isFree": True, "speed": 7, "quality": 8},
    ],
    "openai_compatible": [],
    "custom": [],
}


def get_catalog_models(provider_type: str) -> list[dict[str, Any]]:
    """Return static catalog entries for a provider type."""
    return list(MODEL_CATALOG.get(provider_type, []))


def model_from_catalog(provider_type: str, model_id: str) -> dict[str, Any] | None:
    """Look up a specific model in the catalog."""
    for entry in get_catalog_models(provider_type):
        if entry["id"] == model_id:
            return dict(entry)
    return None


def merge_models(
    catalog_models: list[dict[str, Any]],
    existing_models: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Merge catalog models with user's existing model config (enabled state preserved)."""
    if not existing_models:
        return catalog_models

    existing_by_id = {m["id"]: m for m in existing_models}
    merged = []
    seen = set()

    for cat_model in catalog_models:
        mid = cat_model["id"]
        seen.add(mid)
        if mid in existing_by_id:
            merged.append({**cat_model, "enabled": existing_by_id[mid].get("enabled", True)})
        else:
            merged.append(cat_model)

    for existing in existing_models:
        if existing["id"] not in seen:
            merged.append(existing)

    return merged
