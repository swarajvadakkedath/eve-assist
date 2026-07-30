"""Cohere provider adapter — native v2 API (NOT OpenAI-compatible)."""

from __future__ import annotations

import json
import time
from typing import Any, AsyncIterator

import httpx
import structlog

from aios.core.adapters.base import AIProviderAdapter, ChatRequest, ChatResponse, ProviderStatus, sanitize_error
from aios.core.model_info import ModelInfo, CommercialStatus, AvailabilityStatus
from aios.core.streaming_manager import StreamingManager
from aios.core.timeout_retry import TimeoutConfig, call_with_timeout

logger = structlog.get_logger(__name__)

# Cohere v2 models — verified from docs (July 2026)
_COHERE_MODELS: dict[str, dict] = {
    "command-a-plus-05-2026": {
        "ctx": 200000, "max_out": 4096, "vision": True, "tools": True,
        "quality": 9, "speed": 7, "input_price": 0.0025, "output_price": 0.01,
    },
    "command-a-05-2026": {
        "ctx": 200000, "max_out": 4096, "vision": True, "tools": True,
        "quality": 8, "speed": 8, "input_price": 0.0025, "output_price": 0.01,
    },
    "command-r-plus-08-2024": {
        "ctx": 128000, "max_out": 4096, "tools": True,
        "quality": 8, "speed": 7, "input_price": 0.0025, "output_price": 0.01,
    },
    "command-r-08-2024": {
        "ctx": 128000, "max_out": 4096, "tools": True,
        "quality": 7, "speed": 8, "input_price": 0.00015, "output_price": 0.0006,
    },
    "command-r": {
        "ctx": 128000, "max_out": 4096, "tools": True,
        "quality": 7, "speed": 8, "input_price": 0.00015, "output_price": 0.0006,
    },
    "command": {
        "ctx": 4096, "max_out": 4096,
        "quality": 5, "speed": 9, "input_price": 0.00015, "output_price": 0.0006,
    },
}


class CohereAdapter(AIProviderAdapter):
    """Cohere v2 API adapter — native format, not OpenAI-compatible."""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.cohere.com",
        timeout_config: TimeoutConfig | None = None,
        streaming_manager: StreamingManager | None = None,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_config = timeout_config or TimeoutConfig()
        self._streaming = streaming_manager or StreamingManager()
        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        self._http_client = httpx.AsyncClient(timeout=self._timeout_config.chat)

    @property
    def provider_id(self) -> str:
        return "cohere"

    @property
    def provider_name(self) -> str:
        return "Cohere"

    async def connect(self) -> ProviderStatus:
        return await self.health()

    async def disconnect(self) -> None:
        await self._http_client.aclose()

    async def validate_api_key(self) -> bool:
        return (await self.health()) == ProviderStatus.CONNECTED

    async def list_models(self) -> list[ModelInfo]:
        models = []
        for mid, caps in _COHERE_MODELS.items():
            models.append(ModelInfo(
                id=mid,
                display_name=mid.replace("-", " ").title(),
                provider_id="cohere",
                provider_name="Cohere",
                provider_type="cohere",
                context_window=caps["ctx"],
                max_output_tokens=caps["max_out"],
                supports_streaming=True,
                supports_vision=caps.get("vision", False),
                supports_tools=caps.get("tools", False),
                supports_json=True,
                supports_function_calling=caps.get("tools", False),
                quality=caps.get("quality", 7),
                speed=caps.get("speed", 5),
                pricing={"input": caps.get("input_price", 0.0), "output": caps.get("output_price", 0.0)},
                commercial_status=CommercialStatus.PAID,
                availability=AvailabilityStatus.AVAILABLE,
                discovery_source="catalog",
            ))
        return models

    async def get_model(self, model_id: str) -> ModelInfo | None:
        models = await self.list_models()
        for m in models:
            if m.id == model_id:
                return m
        return None

    def _convert_messages(self, messages: list[dict]) -> tuple[list[dict], str | None]:
        """Convert OpenAI-style messages to Cohere v2 format."""
        chat_history = []
        system = None
        preamble = None

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                # Cohere v2 uses "preamble" for system instructions
                preamble = content
                continue

            if role == "user":
                chat_history.append({"role": "USER", "message": content})
            elif role == "assistant":
                chat_history.append({"role": "CHATBOT", "message": content})

        if not chat_history:
            chat_history.append({"role": "USER", "message": "..."})

        return chat_history, preamble

    async def chat(self, request: ChatRequest) -> ChatResponse:
        start = time.monotonic()
        model = request.model or "command-r-plus-08-2024"
        chat_history, preamble = self._convert_messages(request.messages)

        # The last message is the query
        query = chat_history.pop()["message"] if chat_history else "..."

        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "USER", "message": query}],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }

        # Add chat history (all messages except the last)
        if chat_history:
            body["chat_history"] = chat_history

        if preamble:
            body["preamble"] = preamble

        if request.tools:
            cohere_tools = []
            for tool in request.tools:
                func = tool.get("function", {})
                cohere_tools.append({
                    "name": func.get("name", ""),
                    "description": func.get("description", ""),
                    "parameters": func.get("parameters", {}),
                })
            body["tools"] = cohere_tools

        try:
            resp = await call_with_timeout(
                self._http_client.post(
                    f"{self._base_url}/v2/chat",
                    json=body,
                    headers=self._headers,
                ),
                timeout=self._timeout_config.chat,
                provider_id="cohere",
                operation="chat",
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            detail = sanitize_error(e.response.text[:300])
            if status in (401, 403):
                return ChatResponse(provider="cohere", model=model, content=f"Auth failed ({status})")
            if status == 429:
                return ChatResponse(provider="cohere", model=model, content="Rate limited")
            return ChatResponse(provider="cohere", model=model, content=f"HTTP {status}: {detail}")
        except Exception as e:
            return ChatResponse(provider="cohere", model=model, content=f"Error: {sanitize_error(str(e)[:300])}")

        content = ""
        tool_calls = []
        for item in data.get("message", {}).get("content", []):
            if item.get("type") == "text":
                content += item.get("text", "")

        # Parse tool calls from response
        for tc in data.get("tool_calls", []):
            tool_calls.append({
                "id": tc.get("id", ""),
                "type": "function",
                "function": {
                    "name": tc.get("function", {}).get("name", ""),
                    "input": tc.get("function", {}).get("arguments", {}),
                },
            })

        usage = data.get("usage", {})
        tokens_prompt = usage.get("tokens", {}).get("input_tokens", 0)
        tokens_output = usage.get("tokens", {}).get("output_tokens", 0)

        cost = self._estimate_cost(model, tokens_prompt, tokens_output)

        return ChatResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=data.get("finish_reason", ""),
            model=model,
            provider="cohere",
            tokens_prompt=tokens_prompt,
            tokens_completion=tokens_output,
            tokens_total=tokens_prompt + tokens_output,
            cost=cost,
            latency_ms=(time.monotonic() - start) * 1000,
        )

    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        model = request.model or "command-r-plus-08-2024"
        chat_history, preamble = self._convert_messages(request.messages)
        query = chat_history.pop()["message"] if chat_history else "..."

        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "USER", "message": query}],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": True,
        }
        if chat_history:
            body["chat_history"] = chat_history
        if preamble:
            body["preamble"] = preamble

        stream_id = f"cohere-{id(request)}"

        async def _gen():
            async with self._http_client.stream(
                "POST",
                f"{self._base_url}/v2/chat",
                json=body,
                headers=self._headers,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    payload_str = line[6:]
                    try:
                        payload = json.loads(payload_str)
                    except json.JSONDecodeError:
                        continue

                    event_type = payload.get("type", "")

                    if event_type == "content-delta":
                        delta = payload.get("delta", {})
                        text = delta.get("message", {}).get("content", {}).get("text", "")
                        if text:
                            yield text
                    elif event_type == "tool-call-delta":
                        # Tool call deltas are accumulated but for now we yield nothing
                        pass

        async for token in self._streaming.stream(stream_id, _gen(), timeout=self._timeout_config.streaming):
            yield token

    async def health(self) -> ProviderStatus:
        try:
            # Cohere v2 has no dedicated health endpoint; use models endpoint
            # The v2 API doesn't have a /models endpoint, so we try a minimal chat
            resp = await call_with_timeout(
                self._http_client.post(
                    f"{self._base_url}/v2/chat",
                    json={"model": "command-r", "messages": [{"role": "USER", "message": "ping"}], "max_tokens": 1},
                    headers=self._headers,
                ),
                timeout=self._timeout_config.health,
                provider_id="cohere",
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

    def _estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        caps = _COHERE_MODELS.get(model, {})
        if caps:
            return (input_tokens / 1000 * caps["input_price"]) + (output_tokens / 1000 * caps["output_price"])
        return 0.0
