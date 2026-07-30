"""Anthropic provider adapter."""

from __future__ import annotations

import time
from typing import Any, AsyncIterator

import httpx
import structlog
from anthropic import AsyncAnthropic

from aios.core.adapters.base import AIProviderAdapter, ChatRequest, ChatResponse, ProviderStatus
from aios.core.model_info import ModelInfo, CommercialStatus, AvailabilityStatus
from aios.core.streaming_manager import StreamingManager
from aios.core.timeout_retry import TimeoutConfig, call_with_timeout, retry_with_backoff

logger = structlog.get_logger(__name__)

# Anthropic has no public /models endpoint; catalog is maintained here.
# Updated 2026-07 — includes Claude 4 family.
MODEL_CAPABILITIES: dict[str, dict] = {
    "claude-opus-4-20250514": {
        "ctx": 200000, "max_out": 8192, "vision": True, "tools": True,
        "json": True, "reasoning": True, "quality": 10, "speed": 4,
        "input_price": 0.015, "output_price": 0.075,
        "availability": "available",
    },
    "claude-opus-4-latest": {
        "ctx": 200000, "max_out": 8192, "vision": True, "tools": True,
        "json": True, "reasoning": True, "quality": 10, "speed": 4,
        "input_price": 0.015, "output_price": 0.075,
        "availability": "available",
    },
    "claude-sonnet-4-20250514": {
        "ctx": 200000, "max_out": 8192, "vision": True, "tools": True,
        "json": True, "reasoning": True, "quality": 9, "speed": 7,
        "input_price": 0.003, "output_price": 0.015,
        "availability": "available",
    },
    "claude-sonnet-4-latest": {
        "ctx": 200000, "max_out": 8192, "vision": True, "tools": True,
        "json": True, "reasoning": True, "quality": 9, "speed": 7,
        "input_price": 0.003, "output_price": 0.015,
        "availability": "available",
    },
    "claude-3-5-sonnet-20241022": {
        "ctx": 200000, "max_out": 8192, "vision": True, "tools": True,
        "json": True, "quality": 9, "speed": 7,
        "input_price": 0.003, "output_price": 0.015,
        "availability": "available",
    },
    "claude-3-5-sonnet-latest": {
        "ctx": 200000, "max_out": 8192, "vision": True, "tools": True,
        "json": True, "quality": 9, "speed": 7,
        "input_price": 0.003, "output_price": 0.015,
        "availability": "available",
    },
    "claude-3-5-haiku-20241022": {
        "ctx": 200000, "max_out": 8192, "vision": True, "tools": True,
        "json": True, "quality": 7, "speed": 9,
        "input_price": 0.00080, "output_price": 0.00400,
        "availability": "available",
    },
    "claude-3-5-haiku-latest": {
        "ctx": 200000, "max_out": 8192, "vision": True, "tools": True,
        "json": True, "quality": 7, "speed": 9,
        "input_price": 0.00080, "output_price": 0.00400,
        "availability": "available",
    },
    "claude-3-opus-latest": {
        "ctx": 200000, "max_out": 4096, "vision": True, "tools": True,
        "json": True, "quality": 9, "speed": 5,
        "input_price": 0.015, "output_price": 0.075,
        "availability": "deprecated",
    },
}


class AnthropicAdapter(AIProviderAdapter):
    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.anthropic.com/v1",
        timeout_config: TimeoutConfig | None = None,
        streaming_manager: StreamingManager | None = None,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_config = timeout_config or TimeoutConfig()
        self._streaming = streaming_manager or StreamingManager()
        self._client = AsyncAnthropic(api_key=api_key)
        self._http_client = httpx.AsyncClient(timeout=self._timeout_config.chat)

    @property
    def provider_id(self) -> str:
        return "anthropic"

    @property
    def provider_name(self) -> str:
        return "Anthropic"

    async def connect(self) -> ProviderStatus:
        return await self.health()

    async def disconnect(self) -> None:
        await self._http_client.aclose()

    async def validate_api_key(self) -> bool:
        return (await self.health()) == ProviderStatus.CONNECTED

    async def list_models(self) -> list[ModelInfo]:
        models = []
        for mid, caps in MODEL_CAPABILITIES.items():
            avail_str = caps.get("availability", "available")
            try:
                avail = AvailabilityStatus(avail_str)
            except ValueError:
                avail = AvailabilityStatus.AVAILABLE

            is_deprecated = avail == AvailabilityStatus.DEPRECATED

            models.append(ModelInfo(
                id=mid,
                display_name=mid.replace("-", " ").title(),
                provider_id="anthropic",
                provider_name="Anthropic",
                provider_type="anthropic",
                context_window=caps["ctx"],
                max_output_tokens=caps["max_out"],
                supports_streaming=True,
                supports_vision=caps.get("vision", False),
                supports_reasoning=caps.get("reasoning", False),
                supports_tools=caps.get("tools", False),
                supports_json=caps.get("json", False),
                supports_function_calling=caps.get("tools", False),
                quality=caps.get("quality", 7),
                speed=caps.get("speed", 5),
                pricing={
                    "input": caps.get("input_price", 0.0),
                    "output": caps.get("output_price", 0.0),
                },
                commercial_status=CommercialStatus.PAID,
                availability=avail,
                deprecated=is_deprecated,
                discovery_source="catalog",
            ))
        return models

    async def get_model(self, model_id: str) -> ModelInfo | None:
        models = await self.list_models()
        for m in models:
            if m.id == model_id:
                return m
        return None

    @staticmethod
    def _convert_messages(messages: list[dict]) -> tuple[list[dict], str | None]:
        system = None
        converted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system = content
                continue
            converted.append({"role": role, "content": content})
        if not converted:
            converted.append({"role": "user", "content": "..."})
        return converted, system

    async def chat(self, request: ChatRequest) -> ChatResponse:
        start = time.monotonic()
        messages, system = self._convert_messages(request.messages)

        async def _do_chat() -> ChatResponse:
            kwargs: dict[str, Any] = {
                "model": request.model or "claude-sonnet-4-20250514",
                "messages": messages,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
            }
            if system:
                kwargs["system"] = system
            if request.tools:
                kwargs["tools"] = request.tools

            response = await self._client.messages.create(**kwargs)
            content = ""
            tool_calls = []
            for block in response.content:
                if block.type == "text":
                    content += block.text
                elif block.type == "tool_use":
                    tool_calls.append({
                        "id": block.id,
                        "type": "function",
                        "function": {"name": block.name, "input": block.input},
                    })

            cost = self._estimate_cost(request.model, response.usage.input_tokens, response.usage.output_tokens)

            return ChatResponse(
                content=content,
                tool_calls=tool_calls,
                model=response.model,
                provider="anthropic",
                tokens_prompt=response.usage.input_tokens,
                tokens_completion=response.usage.output_tokens,
                tokens_total=response.usage.input_tokens + response.usage.output_tokens,
                cost=cost,
                latency_ms=(time.monotonic() - start) * 1000,
            )

        return await call_with_timeout(
            retry_with_backoff(_do_chat, provider_id="anthropic", operation="chat"),
            timeout=self._timeout_config.chat,
            provider_id="anthropic",
            operation="chat",
        )

    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        messages, system = self._convert_messages(request.messages)
        kwargs: dict[str, Any] = {
            "model": request.model or "claude-sonnet-4-20250514",
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": True,
        }
        if system:
            kwargs["system"] = system
        if request.tools:
            kwargs["tools"] = request.tools

        stream_id = f"anthropic-{id(request)}"

        async def _gen():
            async with self._client.messages.stream(**kwargs) as stream:
                async for chunk in stream:
                    if chunk.type == "content_block_delta" and chunk.delta.type == "text_delta":
                        yield chunk.delta.text

        async for token in self._streaming.stream(stream_id, _gen(), timeout=self._timeout_config.streaming):
            yield token

    async def health(self) -> ProviderStatus:
        try:
            await call_with_timeout(
                self._client.messages.create(
                    model="claude-sonnet-4-20250514",
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=1,
                ),
                timeout=self._timeout_config.health,
                provider_id="anthropic",
                operation="health",
            )
            return ProviderStatus.CONNECTED
        except Exception as e:
            return self._map_error(e)

    def _estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        caps = MODEL_CAPABILITIES.get(model, {})
        if caps:
            return (input_tokens / 1000 * caps["input_price"]) + (output_tokens / 1000 * caps["output_price"])
        # Fallback prefix matching
        rates = {
            "claude-opus-4": (0.015, 0.075),
            "claude-sonnet-4": (0.003, 0.015),
            "claude-3-5-sonnet": (0.003, 0.015),
            "claude-3-5-haiku": (0.00080, 0.00400),
            "claude-3-opus": (0.015, 0.075),
            "claude-3-sonnet": (0.003, 0.015),
            "claude-3-haiku": (0.00025, 0.00125),
        }
        for prefix, (ir, ocr) in rates.items():
            if prefix in model:
                return (input_tokens / 1000 * ir) + (output_tokens / 1000 * ocr)
        return 0.0

    def _map_error(self, error: Exception) -> ProviderStatus:
        err_str = str(error).lower()
        if "401" in err_str or "unauthorized" in err_str:
            return ProviderStatus.INVALID_KEY
        if "429" in err_str or "rate" in err_str:
            return ProviderStatus.RATE_LIMITED
        if "quota" in err_str:
            return ProviderStatus.QUOTA_EXCEEDED
        if "timeout" in err_str:
            return ProviderStatus.TIMEOUT
        if "connection" in err_str or "refused" in err_str:
            return ProviderStatus.OFFLINE
        return ProviderStatus.ERROR
