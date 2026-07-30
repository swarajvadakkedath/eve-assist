"""Generic OpenAI-compatible provider adapter.

Covers OpenRouter, LM Studio, GitHub Models, HuggingFace, Mistral,
Cerebras, and any other provider with an OpenAI-compatible /v1 API.
"""

from __future__ import annotations

import json
import time
from typing import Any, AsyncIterator

import httpx
import structlog

from aios.core.adapters.base import AIProviderAdapter, ChatRequest, ChatResponse, ProviderStatus, sanitize_error
from aios.core.model_info import ModelInfo
from aios.core.streaming_manager import StreamingManager
from aios.core.timeout_retry import TimeoutConfig, call_with_timeout

logger = structlog.get_logger(__name__)


class OpenAICompatibleAdapter(AIProviderAdapter):
    """Adapter for any OpenAI-compatible API (OpenRouter, LM Studio, etc.)."""

    def __init__(
        self,
        provider_type: str,
        provider_name: str,
        api_key: str = "",
        base_url: str = "",
        timeout_config: TimeoutConfig | None = None,
        streaming_manager: StreamingManager | None = None,
    ):
        self._provider_type = provider_type
        self._provider_name = provider_name
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_config = timeout_config or TimeoutConfig()
        self._streaming = streaming_manager or StreamingManager()
        self._headers = {"Content-Type": "application/json"}
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"
        if provider_type == "openrouter":
            self._headers["HTTP-Referer"] = "https://eve-ai.app"
            self._headers["X-Title"] = "Eve AI"
        self._http_client = httpx.AsyncClient(timeout=self._timeout_config.chat)

    @property
    def provider_id(self) -> str:
        return self._provider_type

    @property
    def provider_name(self) -> str:
        return self._provider_name

    async def connect(self) -> ProviderStatus:
        return await self.health()

    async def disconnect(self) -> None:
        await self._http_client.aclose()

    async def validate_api_key(self) -> bool:
        return (await self.health()) == ProviderStatus.CONNECTED

    async def list_models(self) -> list[ModelInfo]:
        url = f"{self._base_url}/models"
        try:
            resp = await call_with_timeout(
                self._http_client.get(url, headers=self._headers),
                timeout=self._timeout_config.list_models,
                provider_id=self._provider_type,
                operation="list_models",
            )
            if resp.status_code != 200:
                logger.warning("compatible.list_models.http_error", status=resp.status_code, body=resp.text[:200])
                return []

            data = resp.json()
            models = []
            raw_models = []

            if isinstance(data, dict) and "data" in data:
                raw_models = data["data"]
            elif isinstance(data, list):
                raw_models = data

            for m in raw_models:
                if isinstance(m, str):
                    mid = m
                elif isinstance(m, dict):
                    mid = m.get("id", "")
                else:
                    continue

                if not mid:
                    continue

                def _get_ctx(m: dict) -> int:
                    return (
                        m.get("context_length")
                        or m.get("context_window")
                        or m.get("max_context_length")
                        or m.get("max_context")
                        or 128000
                    )
                def _get_max_out(m: dict) -> int:
                    return (
                        m.get("max_output_tokens")
                        or m.get("max_completion_tokens")
                        or m.get("max_tokens")
                        or 16384
                    )

                model_info = ModelInfo(
                    id=mid,
                    display_name=mid,
                    provider_id=self._provider_type,
                    provider_name=self._provider_name,
                    context_window=_get_ctx(m) if isinstance(m, dict) else 128000,
                    max_output_tokens=_get_max_out(m) if isinstance(m, dict) else 16384,
                    supports_streaming=True,
                    is_free=self._provider_type in ("openrouter", "ollama"),
                    metadata=m if isinstance(m, dict) else {},
                )
                models.append(model_info)

            return models
        except httpx.ConnectError:
            logger.warning("compatible.list_models.connect_error", url=url)
            return []
        except Exception as e:
            logger.error("compatible.list_models.failed", provider=self._provider_type, error=str(e))
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
            "model": request.model,
            "messages": request.messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        if request.top_p != 1.0:
            body["top_p"] = request.top_p
        if request.stop:
            body["stop"] = request.stop
        if request.tools:
            body["tools"] = request.tools
        if request.tool_choice:
            body["tool_choice"] = request.tool_choice
        if request.seed is not None:
            body["seed"] = request.seed

        try:
            resp = await call_with_timeout(
                self._http_client.post(
                    f"{self._base_url}/chat/completions",
                    json=body,
                    headers=self._headers,
                ),
                timeout=self._timeout_config.chat,
                provider_id=self._provider_type,
                operation="chat",
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            detail = sanitize_error(e.response.text[:300])
            if status == 401 or status == 403:
                return ChatResponse(provider=self._provider_type, model=request.model, content=f"Auth failed ({status})")
            if status == 429:
                return ChatResponse(provider=self._provider_type, model=request.model, content="Rate limited")
            return ChatResponse(provider=self._provider_type, model=request.model, content=f"HTTP {status}: {detail}")
        except Exception as e:
            return ChatResponse(provider=self._provider_type, model=request.model, content=f"Error: {e}")

        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        content = msg.get("content", "")
        tool_calls = msg.get("tool_calls", [])
        usage = data.get("usage", {})

        return ChatResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=choice.get("finish_reason", ""),
            model=data.get("model", request.model),
            provider=self._provider_type,
            tokens_prompt=usage.get("prompt_tokens", 0),
            tokens_completion=usage.get("completion_tokens", 0),
            tokens_total=usage.get("total_tokens", 0),
            latency_ms=(time.monotonic() - start) * 1000,
        )

    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        body: dict[str, Any] = {
            "model": request.model,
            "messages": request.messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": True,
        }
        if request.tools:
            body["tools"] = request.tools

        stream_id = f"{self._provider_type}-{id(request)}"

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
                provider_id=self._provider_type,
                operation="health",
            )
            if resp.status_code == 200:
                return ProviderStatus.CONNECTED
            if resp.status_code in (401, 403):
                return ProviderStatus.INVALID_KEY
            if resp.status_code == 429:
                return ProviderStatus.RATE_LIMITED
            return ProviderStatus.ERROR
        except httpx.ConnectError:
            return ProviderStatus.OFFLINE
        except httpx.TimeoutException:
            return ProviderStatus.TIMEOUT
        except Exception:
            return ProviderStatus.ERROR
