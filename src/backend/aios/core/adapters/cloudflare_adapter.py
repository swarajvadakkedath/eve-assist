"""Cloudflare Workers AI provider adapter — account-based auth via AI Gateway."""

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

# Common Cloudflare Workers AI models
_CF_MODELS: dict[str, dict] = {
    "@cf/meta/llama-3.3-70b-instruct-fp16": {
        "display": "Llama 3.3 70B", "ctx": 131072, "max_out": 4096,
        "tools": True, "quality": 8, "speed": 7,
    },
    "@cf/meta/llama-3.1-8b-instruct": {
        "display": "Llama 3.1 8B", "ctx": 131072, "max_out": 4096,
        "tools": True, "quality": 6, "speed": 9,
    },
    "@cf/meta/llama-3.2-3b-instruct": {
        "display": "Llama 3.2 3B", "ctx": 131072, "max_out": 4096,
        "quality": 5, "speed": 10,
    },
    "@cf/qwen/qwen1.5-14b-chat-awq": {
        "display": "Qwen 1.5 14B", "ctx": 32768, "max_out": 4096,
        "quality": 7, "speed": 8,
    },
    "@cf/microsoft/phi-3-medium-4k-instruct": {
        "display": "Phi-3 Medium 4K", "ctx": 4096, "max_out": 4096,
        "quality": 7, "speed": 8,
    },
}


class CloudflareAdapter(AIProviderAdapter):
    """Cloudflare Workers AI adapter using AI Gateway OpenAI-compatible endpoint.

    Requires:
      - account_id: Cloudflare account ID
      - api_token: Cloudflare API token with Workers AI permission
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "",
        account_id: str = "",
        timeout_config: TimeoutConfig | None = None,
        streaming_manager: StreamingManager | None = None,
    ):
        self._api_key = api_key
        self._account_id = account_id
        # AI Gateway provides OpenAI-compatible endpoint
        if base_url:
            self._base_url = base_url.rstrip("/")
        elif account_id:
            self._base_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1"
        else:
            self._base_url = ""
        self._timeout_config = timeout_config or TimeoutConfig()
        self._streaming = streaming_manager or StreamingManager()
        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        self._http_client = httpx.AsyncClient(timeout=self._timeout_config.chat)

    @property
    def provider_id(self) -> str:
        return "cloudflare"

    @property
    def provider_name(self) -> str:
        return "Cloudflare Workers AI"

    async def connect(self) -> ProviderStatus:
        return await self.health()

    async def disconnect(self) -> None:
        await self._http_client.aclose()

    async def validate_api_key(self) -> bool:
        return (await self.health()) == ProviderStatus.CONNECTED

    async def list_models(self) -> list[ModelInfo]:
        if not self._base_url:
            return []

        # AI Gateway provides /models endpoint
        try:
            resp = await call_with_timeout(
                self._http_client.get(f"{self._base_url}/models", headers=self._headers),
                timeout=self._timeout_config.list_models,
                provider_id="cloudflare",
                operation="list_models",
            )
            if resp.status_code == 200:
                data = resp.json()
                raw_models = data.get("data", []) if isinstance(data, dict) else []
                models = []
                for m in raw_models:
                    mid = m.get("id", "")
                    if not mid:
                        continue
                    cf_caps = _CF_MODELS.get(mid, {})
                    models.append(ModelInfo(
                        id=mid,
                        display_name=cf_caps.get("display", mid.split("/")[-1]),
                        provider_id="cloudflare",
                        provider_name="Cloudflare Workers AI",
                        provider_type="cloudflare",
                        context_window=cf_caps.get("ctx", 131072),
                        max_output_tokens=cf_caps.get("max_out", 4096),
                        supports_streaming=True,
                        supports_tools=cf_caps.get("tools", False),
                        supports_json=True,
                        supports_function_calling=cf_caps.get("tools", False),
                        quality=cf_caps.get("quality", 6),
                        speed=cf_caps.get("speed", 7),
                        commercial_status=CommercialStatus.FREE_TIER,
                        availability=AvailabilityStatus.AVAILABLE,
                        discovery_source="api",
                    ))
                return models
        except Exception as e:
            logger.warning("cloudflare.list_models.failed", error=sanitize_error(str(e)[:200]))

        # Fallback to static catalog
        models = []
        for mid, caps in _CF_MODELS.items():
            models.append(ModelInfo(
                id=mid,
                display_name=caps["display"],
                provider_id="cloudflare",
                provider_name="Cloudflare Workers AI",
                provider_type="cloudflare",
                context_window=caps["ctx"],
                max_output_tokens=caps["max_out"],
                supports_streaming=True,
                supports_tools=caps.get("tools", False),
                supports_json=True,
                supports_function_calling=caps.get("tools", False),
                quality=caps.get("quality", 6),
                speed=caps.get("speed", 7),
                commercial_status=CommercialStatus.FREE_TIER,
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

    async def chat(self, request: ChatRequest) -> ChatResponse:
        start = time.monotonic()
        model = request.model or "@cf/meta/llama-3.3-70b-instruct-fp16"

        if not self._base_url:
            return ChatResponse(provider="cloudflare", model=model, content="Cloudflare: account_id not configured")

        body: dict[str, Any] = {
            "model": model,
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
                provider_id="cloudflare",
                operation="chat",
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            detail = sanitize_error(e.response.text[:300])
            if status in (401, 403):
                return ChatResponse(provider="cloudflare", model=model, content=f"Auth failed ({status})")
            if status == 429:
                return ChatResponse(provider="cloudflare", model=model, content="Rate limited")
            return ChatResponse(provider="cloudflare", model=model, content=f"HTTP {status}: {detail}")
        except Exception as e:
            return ChatResponse(provider="cloudflare", model=model, content=f"Error: {sanitize_error(str(e)[:300])}")

        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        tool_calls = choice.get("message", {}).get("tool_calls", [])
        usage = data.get("usage", {})

        return ChatResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=choice.get("finish_reason", ""),
            model=data.get("model", model),
            provider="cloudflare",
            tokens_prompt=usage.get("prompt_tokens", 0),
            tokens_completion=usage.get("completion_tokens", 0),
            tokens_total=usage.get("total_tokens", 0),
            latency_ms=(time.monotonic() - start) * 1000,
        )

    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        model = request.model or "@cf/meta/llama-3.3-70b-instruct-fp16"

        if not self._base_url:
            return

        body: dict[str, Any] = {
            "model": model,
            "messages": request.messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": True,
        }
        if request.tools:
            body["tools"] = request.tools

        stream_id = f"cloudflare-{id(request)}"

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
        if not self._base_url:
            return ProviderStatus.NOT_CONFIGURED

        try:
            resp = await call_with_timeout(
                self._http_client.get(f"{self._base_url}/models", headers=self._headers),
                timeout=self._timeout_config.health,
                provider_id="cloudflare",
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
