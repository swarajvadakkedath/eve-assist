"""OpenAI provider adapter — full AIProviderAdapter implementation."""

from __future__ import annotations

import time
from typing import Any, AsyncIterator

import httpx
import structlog
from openai import AsyncOpenAI

from aios.core.adapters.base import AIProviderAdapter, ChatRequest, ChatResponse, ProviderStatus, sanitize_error
from aios.core.model_info import ModelInfo, CommercialStatus, AvailabilityStatus
from aios.core.streaming_manager import StreamingManager
from aios.core.timeout_retry import (
    TimeoutConfig,
    call_with_timeout,
    retry_with_backoff,
    ProviderTimeoutError,
)
from aios.core.capability_inference import infer_capabilities, bool_from_inference

logger = structlog.get_logger(__name__)


class OpenAIAdapter(AIProviderAdapter):
    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        organization: str = "",
        timeout_config: TimeoutConfig | None = None,
        streaming_manager: StreamingManager | None = None,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._organization = organization
        self._timeout_config = timeout_config or TimeoutConfig()
        self._streaming = streaming_manager or StreamingManager()

        client_kwargs: dict[str, Any] = {
            "api_key": api_key or "_",
            "base_url": self._base_url,
        }
        if organization:
            client_kwargs["organization"] = organization
        self._client = AsyncOpenAI(**client_kwargs)
        self._http_client = httpx.AsyncClient(timeout=self._timeout_config.chat)
        self._connected = False

    @property
    def provider_id(self) -> str:
        return "openai"

    @property
    def provider_name(self) -> str:
        return "OpenAI"

    async def connect(self) -> ProviderStatus:
        try:
            await call_with_timeout(
                self._client.models.list(),
                timeout=self._timeout_config.health,
                provider_id="openai",
                operation="connect",
            )
            self._connected = True
            return ProviderStatus.CONNECTED
        except Exception as e:
            self._connected = False
            return self._map_error(e)

    async def disconnect(self) -> None:
        self._connected = False
        await self._http_client.aclose()

    async def validate_api_key(self) -> bool:
        try:
            await call_with_timeout(
                self._client.models.list(),
                timeout=self._timeout_config.validate_key,
                provider_id="openai",
                operation="validate_api_key",
            )
            return True
        except Exception:
            return False

    async def list_models(self) -> list[ModelInfo]:
        try:
            resp = await call_with_timeout(
                self._client.models.list(),
                timeout=self._timeout_config.list_models,
                provider_id="openai",
                operation="list_models",
            )
            models = []
            for m in resp.data:
                raw = {"owned_by": m.owned_by if hasattr(m, "owned_by") else ""}
                inferred = infer_capabilities(m.id, raw, "openai")
                caps = bool_from_inference(inferred)
                models.append(ModelInfo(
                    id=m.id,
                    display_name=m.id,
                    provider_id="openai",
                    provider_name="OpenAI",
                    provider_type="openai",
                    context_window=128000,
                    max_output_tokens=16384,
                    supports_streaming=True,
                    supports_tools=caps["supports_tools"],
                    supports_json=caps["supports_json"],
                    supports_function_calling=caps["supports_function_calling"],
                    supports_reasoning=caps["supports_reasoning"],
                    supports_thinking=caps["supports_thinking"],
                    commercial_status=CommercialStatus.PAID,
                    availability=AvailabilityStatus.AVAILABLE,
                    discovery_source="api",
                    metadata={
                        "owned_by": m.owned_by if hasattr(m, "owned_by") else "",
                        **caps,
                    },
                ))
            return models
        except Exception as e:
            logger.error("openai.list_models.failed", error=sanitize_error(str(e)[:200]))
            return []

    async def get_model(self, model_id: str) -> ModelInfo | None:
        models = await self.list_models()
        for m in models:
            if m.id == model_id:
                return m
        return None

    async def chat(self, request: ChatRequest) -> ChatResponse:
        start = time.monotonic()

        async def _do_chat() -> ChatResponse:
            kwargs: dict[str, Any] = {
                "model": request.model or "gpt-4o",
                "messages": request.messages,
            }
            is_reasoning = request.model and request.model.startswith(("o1", "o3"))
            if is_reasoning:
                kwargs["max_completion_tokens"] = request.max_tokens
            else:
                kwargs["max_tokens"] = request.max_tokens
                kwargs["temperature"] = request.temperature
            if request.top_p != 1.0:
                kwargs["top_p"] = request.top_p
            if request.stop:
                kwargs["stop"] = request.stop
            if request.tools:
                kwargs["tools"] = request.tools
            if request.tool_choice:
                kwargs["tool_choice"] = request.tool_choice
            if request.seed is not None:
                kwargs["seed"] = request.seed

            response = await self._client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            content = choice.message.content or ""
            tool_calls = []
            if choice.message.tool_calls:
                tool_calls = [tc.model_dump() for tc in choice.message.tool_calls]

            usage = response.usage
            prompt_tokens = usage.prompt_tokens if usage else 0
            completion_tokens = usage.completion_tokens if usage else 0

            cost = self._estimate_cost(request.model, prompt_tokens, completion_tokens)

            return ChatResponse(
                content=content,
                tool_calls=tool_calls,
                finish_reason=choice.finish_reason or "",
                model=response.model,
                provider="openai",
                tokens_prompt=prompt_tokens,
                tokens_completion=completion_tokens,
                tokens_total=prompt_tokens + completion_tokens,
                cost=cost,
                latency_ms=(time.monotonic() - start) * 1000,
            )

        return await call_with_timeout(
            retry_with_backoff(_do_chat, provider_id="openai", operation="chat"),
            timeout=self._timeout_config.chat,
            provider_id="openai",
            operation="chat",
        )

    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        kwargs: dict[str, Any] = {
            "model": request.model or "gpt-4o",
            "messages": request.messages,
            "stream": True,
        }
        is_reasoning = request.model and request.model.startswith(("o1", "o3"))
        if is_reasoning:
            kwargs["max_completion_tokens"] = request.max_tokens
        else:
            kwargs["max_tokens"] = request.max_tokens
            kwargs["temperature"] = request.temperature
        if request.tools:
            kwargs["tools"] = request.tools
        if request.seed is not None:
            kwargs["seed"] = request.seed

        stream_id = f"openai-{id(request)}"

        async def _gen():
            s = await call_with_timeout(
                self._client.chat.completions.create(**kwargs),
                timeout=self._timeout_config.streaming,
                provider_id="openai",
                operation="stream",
            )
            async for chunk in s:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield delta.content

        async for token in self._streaming.stream(stream_id, _gen(), timeout=self._timeout_config.streaming):
            yield token

    async def embeddings(
        self,
        texts: list[str],
        model: str = "",
    ) -> list[list[float]]:
        resp = await call_with_timeout(
            self._client.embeddings.create(
                model=model or "text-embedding-3-small",
                input=texts,
            ),
            timeout=self._timeout_config.embeddings,
            provider_id="openai",
            operation="embeddings",
        )
        return [d.embedding for d in resp.data]

    async def moderation(
        self,
        text: str,
        model: str = "",
    ) -> dict[str, Any]:
        resp = await call_with_timeout(
            self._client.moderations.create(
                model=model or "omni-moderation-latest",
                input=text,
            ),
            timeout=self._timeout_config.chat,
            provider_id="openai",
            operation="moderation",
        )
        results = resp.results[0] if resp.results else {}
        return results.model_dump() if hasattr(results, "model_dump") else dict(results)

    async def health(self) -> ProviderStatus:
        try:
            await call_with_timeout(
                self._client.models.list(),
                timeout=self._timeout_config.health,
                provider_id="openai",
                operation="health",
            )
            return ProviderStatus.CONNECTED
        except Exception as e:
            return self._map_error(e)

    def _estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        rates = {
            "gpt-4o": (0.00250, 0.01000),
            "gpt-4o-mini": (0.00015, 0.00060),
            "gpt-4.1": (0.00200, 0.00800),
            "gpt-4.1-mini": (0.00040, 0.00160),
            "gpt-4.1-nano": (0.00010, 0.00040),
            "gpt-4-turbo": (0.01000, 0.03000),
            "gpt-4": (0.03000, 0.06000),
            "gpt-3.5-turbo": (0.00050, 0.00150),
            "o1": (0.01500, 0.06000),
            "o1-mini": (0.00110, 0.00440),
            "o3-mini": (0.00110, 0.00440),
            "o4-mini": (0.00110, 0.00440),
        }
        for prefix, (ir, ocr) in rates.items():
            if prefix in model:
                return (prompt_tokens / 1000 * ir) + (completion_tokens / 1000 * ocr)
        return 0.0

    def _map_error(self, error: Exception) -> ProviderStatus:
        err_str = str(error).lower()
        if "401" in err_str or "unauthorized" in err_str or "invalid" in err_str:
            return ProviderStatus.INVALID_KEY
        if "429" in err_str or "rate" in err_str:
            return ProviderStatus.RATE_LIMITED
        if "quota" in err_str or "insufficient" in err_str:
            return ProviderStatus.QUOTA_EXCEEDED
        if "timeout" in err_str or "timed out" in err_str:
            return ProviderStatus.TIMEOUT
        if "connection" in err_str or "refused" in err_str or "resolve" in err_str:
            return ProviderStatus.OFFLINE
        return ProviderStatus.ERROR
