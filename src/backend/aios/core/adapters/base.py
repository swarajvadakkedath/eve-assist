"""AIProviderAdapter — abstract base for all provider adapters."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator

from aios.core.model_info import ModelInfo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sanitize_error(text: str) -> str:
    """Redact API keys, tokens, and secrets from error strings.

    Covers: OpenAI (sk-*), Anthropic (sk-ant-*), Google (AIza*),
    Groq (gsk_*), Bearer tokens, and generic api_key patterns.
    """
    patterns = [
        # OpenAI / generic sk- prefix keys
        (r'(sk-)[a-zA-Z0-9_\-]{8,}', r'\1***REDACTED***'),
        # Anthropic sk-ant-* keys
        (r'(sk-ant-)[a-zA-Z0-9_\-]{8,}', r'\1***REDACTED***'),
        # Google AIza* keys
        (r'(AIza)[a-zA-Z0-9_\-]{20,}', r'\1***REDACTED***'),
        # Groq gsk_* keys
        (r'(gsk_)[a-zA-Z0-9_\-]{8,}', r'\1***REDACTED***'),
        # Bearer tokens (any long alphanumeric after Bearer)
        (r'(Bearer\s+)[a-zA-Z0-9_\-]{20,}', r'\1***REDACTED***'),
        # x-api-key header values
        (r'(x-api-key["\s:=]+)[a-zA-Z0-9_\-]{8,}', r'\1***REDACTED***'),
        # api_key / api-key / apikey with value
        (r'(api[_-]?key["\s:=]+)[a-zA-Z0-9_\-]{8,}', r'\1***REDACTED***'),
    ]
    result = text
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

class ProviderStatus(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    OFFLINE = "offline"
    RATE_LIMITED = "rate_limited"
    INVALID_KEY = "invalid_key"
    QUOTA_EXCEEDED = "quota_exceeded"
    AUTH_FAILED = "auth_failed"
    TIMEOUT = "timeout"
    ERROR = "error"
    NOT_CONFIGURED = "not_configured"


# ---------------------------------------------------------------------------
# Request/Response types
# ---------------------------------------------------------------------------

@dataclass
class ChatRequest:
    messages: list[dict]
    model: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 1.0
    top_k: int = 0
    seed: int | None = None
    stop: list[str] | None = None
    stream: bool = False
    tools: list[dict] | None = None
    tool_choice: str | dict | None = None
    system_prompt: str | None = None
    thinking_mode: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    provider_id: str | None = None

    def __post_init__(self):
        if not 1 <= self.max_tokens <= 200000:
            raise ValueError(f"max_tokens must be between 1 and 200000, got {self.max_tokens}")
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError(f"temperature must be between 0.0 and 2.0, got {self.temperature}")


@dataclass
class ChatResponse:
    content: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    finish_reason: str = ""
    model: str = ""
    provider: str = ""
    tokens_prompt: int = 0
    tokens_completion: int = 0
    tokens_total: int = 0
    cost: float = 0.0
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class AIProviderAdapter(ABC):
    """Every provider adapter must implement every method below.

    Adding a new provider only requires creating a new subclass.
    """

    # -- Identity -----------------------------------------------------------

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique provider type identifier (e.g. 'openai', 'anthropic')."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name (e.g. 'OpenAI', 'Anthropic')."""

    # -- Lifecycle ----------------------------------------------------------

    @abstractmethod
    async def connect(self) -> ProviderStatus:
        """Initialize connections, validate config, return current status."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Clean up resources, close connections."""

    @abstractmethod
    async def validate_api_key(self) -> bool:
        """Check whether the configured API key is valid."""

    # -- Model discovery ----------------------------------------------------

    @abstractmethod
    async def list_models(self) -> list[ModelInfo]:
        """Fetch ALL available models from the provider.

        Must return every model the provider exposes — no capping, no truncation.
        If the provider paginates, implement pagination internally.
        """

    @abstractmethod
    async def get_model(self, model_id: str) -> ModelInfo | None:
        """Get metadata for a specific model."""

    # -- Chat / Completion --------------------------------------------------

    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Non-streaming chat completion."""

    @abstractmethod
    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        """Streaming chat completion — yields content tokens as they arrive."""

    # -- Vision -------------------------------------------------------------

    async def vision(
        self,
        image_data: bytes,
        prompt: str,
        model: str = "",
        max_tokens: int = 4096,
    ) -> ChatResponse:
        """Analyze an image. Raise NotImplementedError if unsupported."""
        raise NotImplementedError(f"{self.provider_id} does not support vision")

    # -- Image generation ---------------------------------------------------

    async def image_generation(
        self,
        prompt: str,
        model: str = "",
        n: int = 1,
        size: str = "1024x1024",
    ) -> list[bytes]:
        """Generate images from a text prompt."""
        raise NotImplementedError(f"{self.provider_id} does not support image generation")

    # -- Speech -------------------------------------------------------------

    async def speech_to_text(
        self,
        audio_data: bytes,
        model: str = "",
        language: str = "",
    ) -> str:
        """Transcribe audio to text."""
        raise NotImplementedError(f"{self.provider_id} does not support speech-to-text")

    async def text_to_speech(
        self,
        text: str,
        model: str = "",
        voice: str = "",
    ) -> bytes:
        """Synthesize speech from text."""
        raise NotImplementedError(f"{self.provider_id} does not support text-to-speech")

    # -- Embeddings ---------------------------------------------------------

    async def embeddings(
        self,
        texts: list[str],
        model: str = "",
    ) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        raise NotImplementedError(f"{self.provider_id} does not support embeddings")

    # -- Rerank -------------------------------------------------------------

    async def rerank(
        self,
        query: str,
        documents: list[str],
        model: str = "",
        top_n: int = 5,
    ) -> list[dict]:
        """Re-rank documents by relevance to a query."""
        raise NotImplementedError(f"{self.provider_id} does not support reranking")

    # -- Moderation ---------------------------------------------------------

    async def moderation(
        self,
        text: str,
        model: str = "",
    ) -> dict[str, Any]:
        """Check text for policy violations."""
        raise NotImplementedError(f"{self.provider_id} does not support moderation")

    # -- Health -------------------------------------------------------------

    @abstractmethod
    async def health(self) -> ProviderStatus:
        """Check if the provider is reachable and operational."""
