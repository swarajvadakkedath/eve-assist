"""Anthropic provider implementation."""

from typing import AsyncIterator

import structlog
from anthropic import AsyncAnthropic

from aios.core.ai_router import AIProvider, AIRequest, AIResponse
from aios.config.settings import AiosSettings

logger = structlog.get_logger(__name__)


class AnthropicProvider(AIProvider):
    def __init__(self, settings: AiosSettings | None = None):
        self._settings = settings or AiosSettings()
        api_key = self._settings.ai_api_key or None
        self._client = AsyncAnthropic(api_key=api_key or "")
        self._model = self._settings.ai_model
        self._max_tokens = self._settings.ai_max_tokens
        self._temperature = self._settings.ai_temperature

    @property
    def model(self) -> str:
        return self._model

    @property
    def capabilities(self) -> set[str]:
        return {"chat", "streaming", "tools", "vision"}

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

    async def chat(self, request: AIRequest) -> AIResponse:
        messages, system = self._convert_messages(request.messages)

        kwargs = {
            "model": self._model,
            "messages": messages,
            "max_tokens": request.max_tokens or self._max_tokens,
            "temperature": request.temperature or self._temperature,
        }
        if system:
            kwargs["system"] = system

        response = await self._client.messages.create(**kwargs)

        content = ""
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append({"id": block.id, "type": "function", "function": {"name": block.name, "input": block.input}})

        cost = self._estimate_cost(
            response.usage.input_tokens,
            response.usage.output_tokens,
        )

        logger.info(
            "anthropic.chat.completed",
            model=self._model,
            tokens=response.usage.input_tokens + response.usage.output_tokens,
            cost=cost,
        )

        return AIResponse(
            content=content,
            provider="anthropic",
            model=self._model,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
            cost=cost,
            tool_calls=tool_calls,
        )

    async def chat_stream(self, request: AIRequest) -> AsyncIterator[str]:
        messages, system = self._convert_messages(request.messages)

        kwargs = {
            "model": self._model,
            "messages": messages,
            "max_tokens": request.max_tokens or self._max_tokens,
            "temperature": request.temperature or self._temperature,
        }
        if system:
            kwargs["system"] = system

        async with self._client.messages.stream(**kwargs) as stream:
            async for chunk in stream:
                if chunk.type == "content_block_delta" and chunk.delta.type == "text_delta":
                    yield chunk.delta.text

    async def embed(self, text: str) -> list[float]:
        response = await self._client.messages.create(
            model=self._model,
            messages=[{"role": "user", "content": text}],
            max_tokens=1,
        )
        return [0.0]

    async def health_check(self) -> bool:
        try:
            await self._client.messages.create(
                model=self._model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            return True
        except Exception as e:
            logger.warning("anthropic.health_check.failed", error=str(e))
            return False

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        rates = {"claude-3-opus": (0.015, 0.075), "claude-3-sonnet": (0.003, 0.015), "claude-3-haiku": (0.00025, 0.00125)}
        model_key = "claude-3-sonnet"
        for prefix, (ir, ocr) in rates.items():
            if prefix in self._model:
                model_key = prefix
                break
        input_rate, output_rate = rates[model_key]
        return (input_tokens / 1000 * input_rate) + (output_tokens / 1000 * output_rate)
