"""Groq provider adapter — uses OpenAI-compatible API."""

from __future__ import annotations

import time
from typing import Any, AsyncIterator

import httpx
import structlog

from aios.core.adapters.base import AIProviderAdapter, ChatRequest, ChatResponse, ProviderStatus, sanitize_error
from aios.core.model_info import ModelInfo, CommercialStatus, AvailabilityStatus
from aios.core.streaming_manager import StreamingManager
from aios.core.timeout_retry import TimeoutConfig, call_with_timeout

logger = structlog.get_logger(__name__)


class GroqAdapter(AIProviderAdapter):
    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.groq.com/openai/v1",
        timeout_config: TimeoutConfig | None = None,
        streaming_manager: StreamingManager | None = None,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_config = timeout_config or TimeoutConfig()
        self._streaming = streaming_manager or StreamingManager()
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self._http_client = httpx.AsyncClient(timeout=self._timeout_config.chat)

    @property
    def provider_id(self) -> str:
        return "groq"

    @property
    def provider_name(self) -> str:
        return "Groq"

    async def connect(self) -> ProviderStatus:
        return await self.health()

    async def disconnect(self) -> None:
        await self._http_client.aclose()

    async def validate_api_key(self) -> bool:
        return (await self.health()) == ProviderStatus.CONNECTED

    async def list_models(self) -> list[ModelInfo]:
        try:
            resp = await call_with_timeout(
                self._http_client.get(f"{self._base_url}/models", headers=self._headers),
                timeout=self._timeout_config.list_models,
                provider_id="groq",
                operation="list_models",
            )
            if resp.status_code != 200:
                return []

            data = resp.json()
            models = []
            for m in data.get("data", []):
                mid = m.get("id", "")
                models.append(ModelInfo(
                    id=mid,
                    display_name=mid,
                    provider_id="groq",
                    provider_name="Groq",
                    provider_type="groq",
                    context_window=m.get("context_length", 32768) or 32768,
                    max_output_tokens=m.get("max_output_tokens", 8192) or 8192,
                    supports_streaming=True,
                    supports_tools=True,
                    supports_json=True,
                    supports_function_calling=True,
                    is_free=True,
                    commercial_status=CommercialStatus.FREE_TIER,
                    availability=AvailabilityStatus.AVAILABLE,
                    discovery_source="api",
                    metadata={k: v for k, v in m.items() if k not in ("id", "object")},
                ))
            return models
        except Exception as e:
            logger.error("groq.list_models.failed", error=sanitize_error(str(e)[:200]))
            return []

    async def get_model(self, model_id: str) -> ModelInfo | None:
        models = await self.list_models()
        for m in models:
            if m.id == model_id:
                return m
        return None

    async def chat(self, request: ChatRequest) -> ChatResponse:
        start = time.monotonic()
        body: dict[str, Any] = {
            "model": request.model or "llama-3.3-70b-versatile",
            "messages": request.messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        if request.tools:
            body["tools"] = request.tools

        try:
            resp = await call_with_timeout(
                self._http_client.post(
                    f"{self._base_url}/chat/completions",
                    json=body,
                    headers=self._headers,
                ),
                timeout=self._timeout_config.chat,
                provider_id="groq",
                operation="chat",
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            return ChatResponse(provider="groq", model=request.model,
                                content=f"Error {e.response.status_code}: {sanitize_error(e.response.text[:200])}")
        except Exception as e:
            return ChatResponse(provider="groq", model=request.model, content=f"Error: {sanitize_error(str(e)[:300])}")

        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        usage = data.get("usage", {})

        return ChatResponse(
            content=content,
            model=data.get("model", request.model),
            provider="groq",
            tokens_prompt=usage.get("prompt_tokens", 0),
            tokens_completion=usage.get("completion_tokens", 0),
            tokens_total=usage.get("total_tokens", 0),
            latency_ms=(time.monotonic() - start) * 1000,
        )

    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        body: dict[str, Any] = {
            "model": request.model or "llama-3.3-70b-versatile",
            "messages": request.messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": True,
        }

        stream_id = f"groq-{id(request)}"

        async def _gen():
            async with self._http_client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                json=body,
                headers=self._headers,
            ) as resp:
                resp.raise_for_status()
                async for chunk in StreamingManager.read_sse_lines(resp):
                    content = StreamingManager.extract_openai_chunk(chunk)
                    if content:
                        yield content

        async for token in self._streaming.stream(stream_id, _gen(), timeout=self._timeout_config.streaming):
            yield token

    async def health(self) -> ProviderStatus:
        try:
            resp = await call_with_timeout(
                self._http_client.get(f"{self._base_url}/models", headers=self._headers),
                timeout=self._timeout_config.health,
                provider_id="groq",
                operation="health",
            )
            if resp.status_code == 200:
                return ProviderStatus.CONNECTED
            if resp.status_code in (401, 403):
                return ProviderStatus.INVALID_KEY
            return ProviderStatus.ERROR
        except httpx.ConnectError:
            return ProviderStatus.OFFLINE
        except httpx.TimeoutException:
            return ProviderStatus.TIMEOUT
        except Exception:
            return ProviderStatus.ERROR
