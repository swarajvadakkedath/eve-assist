"""Ollama (local) provider implementation."""

from typing import AsyncIterator

import httpx
import structlog

from aios.core.ai_router import AIProvider, AIRequest, AIResponse
from aios.config.settings import AiosSettings

logger = structlog.get_logger(__name__)


class OllamaProvider(AIProvider):
    def __init__(self, settings: AiosSettings | None = None):
        self._settings = settings or AiosSettings()
        self._base_url = "http://localhost:11434"
        self._model = "llama3.2"
        self._client = httpx.AsyncClient(timeout=120.0)

    @property
    def model(self) -> str:
        return self._model

    @property
    def capabilities(self) -> set[str]:
        return {"chat", "streaming", "embedding", "local"}

    async def chat(self, request: AIRequest) -> AIResponse:
        payload = {
            "model": self._model,
            "messages": request.messages,
            "stream": False,
            "options": {
                "num_predict": request.max_tokens,
                "temperature": request.temperature,
            },
        }
        response = await self._client.post(f"{self._base_url}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()

        content = data.get("message", {}).get("content", "")
        total_tokens = data.get("eval_count", 0)

        logger.info(
            "ollama.chat.completed",
            model=self._model,
            tokens=total_tokens,
        )

        return AIResponse(
            content=content,
            provider="ollama",
            model=self._model,
            tokens_used=total_tokens,
        )

    async def chat_stream(self, request: AIRequest) -> AsyncIterator[str]:
        payload = {
            "model": self._model,
            "messages": request.messages,
            "stream": True,
            "options": {
                "num_predict": request.max_tokens,
                "temperature": request.temperature,
            },
        }
        async with self._client.stream("POST", f"{self._base_url}/api/chat", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                import json
                chunk = json.loads(line)
                content = chunk.get("message", {}).get("content", "")
                if content:
                    yield content

    async def embed(self, text: str) -> list[float]:
        response = await self._client.post(
            f"{self._base_url}/api/embeddings",
            json={"model": self._model, "prompt": text},
        )
        response.raise_for_status()
        data = response.json()
        return data.get("embedding", [])

    async def health_check(self) -> bool:
        try:
            response = await self._client.get(f"{self._base_url}/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.warning("ollama.health_check.failed", error=str(e))
            return False
