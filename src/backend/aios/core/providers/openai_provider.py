"""OpenAI provider implementation."""

from typing import AsyncIterator

import structlog
from openai import AsyncOpenAI

from aios.core.ai_router import AIProvider, AIRequest, AIResponse
from aios.config.settings import AiosSettings

logger = structlog.get_logger(__name__)


class OpenAIProvider(AIProvider):
    def __init__(self, settings: AiosSettings | None = None):
        self._settings = settings or AiosSettings()
        api_key = self._settings.ai_api_key or None
        self._client = AsyncOpenAI(api_key=api_key or "", _enforce_credentials=False)
        self._model = self._settings.ai_model
        self._max_tokens = self._settings.ai_max_tokens
        self._temperature = self._settings.ai_temperature

    @property
    def model(self) -> str:
        return self._model

    @property
    def capabilities(self) -> set[str]:
        return {"chat", "streaming", "tools", "vision", "embedding"}

    async def chat(self, request: AIRequest) -> AIResponse:
        kwargs = {
            "model": self._model,
            "messages": request.messages,
            "max_tokens": request.max_tokens or self._max_tokens,
            "temperature": request.temperature or self._temperature,
        }
        if request.tools:
            kwargs["tools"] = request.tools

        response = await self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        content = choice.message.content or ""
        tool_calls = []
        if choice.message.tool_calls:
            tool_calls = [tc.model_dump() for tc in choice.message.tool_calls]

        cost = self._estimate_cost(
            response.usage.prompt_tokens if response.usage else 0,
            response.usage.completion_tokens if response.usage else 0,
        )

        logger.info(
            "openai.chat.completed",
            model=self._model,
            tokens=response.usage.total_tokens if response.usage else 0,
            cost=cost,
        )

        return AIResponse(
            content=content,
            provider="openai",
            model=self._model,
            tokens_used=response.usage.total_tokens if response.usage else 0,
            cost=cost,
            tool_calls=tool_calls,
        )

    async def chat_stream(self, request: AIRequest) -> AsyncIterator[str]:
        kwargs = {
            "model": self._model,
            "messages": request.messages,
            "max_tokens": request.max_tokens or self._max_tokens,
            "temperature": request.temperature or self._temperature,
            "stream": True,
        }
        if request.tools:
            kwargs["tools"] = request.tools

        stream = await self._client.chat.completions.create(**kwargs)
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    async def embed(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(
            model=self._settings.ai_embedding_model,
            input=text,
        )
        return response.data[0].embedding

    async def health_check(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception as e:
            logger.warning("openai.health_check.failed", error=str(e))
            return False

    def _estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        rates = {"gpt-4": (0.03, 0.06), "gpt-3.5-turbo": (0.0015, 0.002)}
        model_key = "gpt-4" if "gpt-4" in self._model else "gpt-3.5-turbo"
        prompt_rate, completion_rate = rates.get(model_key, (0.01, 0.03))
        return (prompt_tokens / 1000 * prompt_rate) + (completion_tokens / 1000 * completion_rate)
