"""Ollama (local) provider adapter."""

from __future__ import annotations

import json
import time
from typing import Any, AsyncIterator

import httpx
import structlog

from aios.core.adapters.base import AIProviderAdapter, ChatRequest, ChatResponse, ProviderStatus
from aios.core.model_info import ModelInfo
from aios.core.streaming_manager import StreamingManager
from aios.core.timeout_retry import TimeoutConfig, call_with_timeout

logger = structlog.get_logger(__name__)


class OllamaAdapter(AIProviderAdapter):
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout_config: TimeoutConfig | None = None,
        streaming_manager: StreamingManager | None = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._timeout_config = timeout_config or TimeoutConfig()
        self._streaming = streaming_manager or StreamingManager()
        self._http_client = httpx.AsyncClient(timeout=self._timeout_config.streaming)

    @property
    def provider_id(self) -> str:
        return "ollama"

    @property
    def provider_name(self) -> str:
        return "Ollama"

    async def connect(self) -> ProviderStatus:
        return await self.health()

    async def disconnect(self) -> None:
        await self._http_client.aclose()

    async def validate_api_key(self) -> bool:
        return True

    async def list_models(self) -> list[ModelInfo]:
        try:
            resp = await call_with_timeout(
                self._http_client.get(f"{self._base_url}/api/tags"),
                timeout=self._timeout_config.list_models,
                provider_id="ollama",
                operation="list_models",
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            models = []
            for m in data.get("models", []):
                name = m.get("name", "")
                details = m.get("details", {})
                model_info = ModelInfo(
                    id=name,
                    display_name=name,
                    provider_id="ollama",
                    provider_name="Ollama",
                    context_window=m.get("context_length", 8192) or 8192,
                    max_output_tokens=4096,
                    supports_streaming=True,
                    supports_tools=True,
                    supports_json=True,
                    is_free=True,
                    metadata={
                        "modified_at": m.get("modified_at", ""),
                        "size": m.get("size", 0),
                        "parameter_size": details.get("parameter_size", ""),
                        "quantization": details.get("quantization_level", ""),
                    },
                )
                models.append(model_info)

            return models
        except Exception as e:
            logger.error("ollama.list_models.failed", error=str(e))
            return []

    async def get_model(self, model_id: str) -> ModelInfo | None:
        models = await self.list_models()
        for m in models:
            if m.id == model_id:
                return m
        return None

    async def chat(self, request: ChatRequest) -> ChatResponse:
        start = time.monotonic()
        payload = {
            "model": request.model or "llama3.2",
            "messages": request.messages,
            "stream": False,
            "options": {
                "num_predict": request.max_tokens,
                "temperature": request.temperature,
            },
        }

        try:
            resp = await call_with_timeout(
                self._http_client.post(f"{self._base_url}/api/chat", json=payload),
                timeout=self._timeout_config.chat,
                provider_id="ollama",
                operation="chat",
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            return ChatResponse(provider="ollama", model=request.model, content=f"Error: {e}")

        content = data.get("message", {}).get("content", "")
        total_tokens = data.get("eval_count", 0)
        prompt_tokens = data.get("prompt_eval_count", 0)
        completion_tokens = max(0, total_tokens - prompt_tokens)

        return ChatResponse(
            content=content,
            model=request.model,
            provider="ollama",
            tokens_prompt=prompt_tokens,
            tokens_completion=completion_tokens,
            tokens_total=total_tokens,
            latency_ms=(time.monotonic() - start) * 1000,
        )

    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        payload = {
            "model": request.model or "llama3.2",
            "messages": request.messages,
            "stream": True,
            "options": {
                "num_predict": request.max_tokens,
                "temperature": request.temperature,
            },
        }

        stream_id = f"ollama-{id(request)}"

        async def _gen():
            async with self._http_client.stream(
                "POST", f"{self._base_url}/api/chat", json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    import json
                    chunk = json.loads(line)
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        yield content

        async for token in self._streaming.stream(stream_id, _gen(), timeout=self._timeout_config.streaming):
            yield token

    async def embeddings(
        self,
        texts: list[str],
        model: str = "",
    ) -> list[list[float]]:
        results = []
        for text in texts:
            resp = await call_with_timeout(
                self._http_client.post(
                    f"{self._base_url}/api/embeddings",
                    json={"model": model or "llama3.2", "prompt": text},
                ),
                timeout=self._timeout_config.embeddings,
                provider_id="ollama",
                operation="embeddings",
            )
            resp.raise_for_status()
            data = resp.json()
            results.append(data.get("embedding", []))
        return results

    async def health(self) -> ProviderStatus:
        try:
            resp = await call_with_timeout(
                self._http_client.get(f"{self._base_url}/api/tags"),
                timeout=self._timeout_config.health,
                provider_id="ollama",
                operation="health",
            )
            return ProviderStatus.CONNECTED if resp.status_code == 200 else ProviderStatus.ERROR
        except httpx.ConnectError:
            return ProviderStatus.OFFLINE
        except httpx.TimeoutException:
            return ProviderStatus.TIMEOUT
        except Exception:
            return ProviderStatus.ERROR
