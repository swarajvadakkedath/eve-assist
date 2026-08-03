"""Google AI Studio / Gemini provider adapter."""

from __future__ import annotations

import json
import time
from typing import Any, AsyncIterator

import httpx
import structlog

from aios.core.adapters.base import AIProviderAdapter, ChatRequest, ChatResponse, ProviderStatus, sanitize_error
from aios.core.model_info import ModelInfo
from aios.core.streaming_manager import StreamingManager
from aios.core.timeout_retry import TimeoutConfig, call_with_timeout, ProviderTimeoutError
from aios.core.capability_inference import infer_capabilities, bool_from_inference

logger = structlog.get_logger(__name__)


class GoogleAdapter(AIProviderAdapter):
    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout_config: TimeoutConfig | None = None,
        streaming_manager: StreamingManager | None = None,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_config = timeout_config or TimeoutConfig()
        self._streaming = streaming_manager or StreamingManager()
        self._headers = {"Content-Type": "application/json"}
        if api_key:
            self._headers["x-goog-api-key"] = api_key
        self._http_client = httpx.AsyncClient(timeout=self._timeout_config.chat)

    @property
    def provider_id(self) -> str:
        return "google"

    @property
    def provider_name(self) -> str:
        return "Google AI Studio"

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
                provider_id="google",
                operation="list_models",
            )
            if resp.status_code != 200:
                return []

            data = resp.json()
            models = []
            for m in data.get("models", []):
                name = m.get("name", "")
                model_id = name.split("/")[-1] if "/" in name else name
                supported = m.get("supportedGenerationMethods", [])
                raw = {"name": name}
                inferred = infer_capabilities(model_id, raw, "google")
                caps = bool_from_inference(inferred)
                models.append(ModelInfo(
                    id=model_id,
                    display_name=m.get("displayName", model_id),
                    provider_id="google",
                    provider_name="Google AI Studio",
                    context_window=1048576,
                    max_output_tokens=8192,
                    supports_streaming=True,
                    supports_vision=caps["supports_vision"] or "vision" in model_id.lower() or "gemini" in model_id.lower(),
                    supports_tools=True,
                    supports_json=True,
                    supports_function_calling=True,
                    supports_reasoning=caps["supports_reasoning"],
                    supports_thinking=caps["supports_thinking"],
                    supports_system_prompt=True,
                    raw_provider_metadata={"raw_name": name, "methods": supported},
                ))
            return models
        except Exception as e:
            logger.error("google.list_models.failed", error=sanitize_error(str(e)[:200]))
            return []

    async def get_model(self, model_id: str) -> ModelInfo | None:
        models = await self.list_models()
        for m in models:
            if m.id == model_id:
                return m
        return None

    def _chat_url(self, model: str, stream: bool = False) -> str:
        endpoint = "streamGenerateContent" if stream else "generateContent"
        return f"{self._base_url}/models/{model}:{endpoint}"

    def _build_contents(self, messages: list[dict]) -> tuple[list[dict], str | None]:
        contents = []
        system_instruction = None
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_instruction = content
            elif role == "user":
                contents.append({"role": "user", "parts": [{"text": content}]})
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": content}]})
        if not contents:
            contents.append({"role": "user", "parts": [{"text": "..."}]})
        return contents, system_instruction

    async def chat(self, request: ChatRequest) -> ChatResponse:
        start = time.monotonic()
        model = request.model or "gemini-2.5-flash"
        logger.info("google.chat.request", model=model, provider_id=self.provider_id)
        contents, system = self._build_contents(request.messages)

        body: dict[str, Any] = {"contents": contents}
        if system:
            body["system_instruction"] = {"parts": [{"text": system}]}
        gen_config: dict[str, Any] = {}
        if request.max_tokens:
            gen_config["maxOutputTokens"] = request.max_tokens
        if request.temperature:
            gen_config["temperature"] = request.temperature
        if gen_config:
            body["generationConfig"] = gen_config

        try:
            resp = await call_with_timeout(
                self._http_client.post(
                    self._chat_url(model, stream=False),
                    json=body,
                    headers=self._headers,
                ),
                timeout=self._timeout_config.chat,
                provider_id="google",
                operation="chat",
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 401 or status == 403:
                return ChatResponse(provider="google", model=model, content=f"Auth error: {status}")
            if status == 429:
                return ChatResponse(provider="google", model=model, content="Rate limited")
            return ChatResponse(provider="google", model=model, content=f"HTTP {status}: {sanitize_error(e.response.text[:200])}")
        except ProviderTimeoutError:
            return ChatResponse(provider="google", model=model, content="Request timed out")

        candidates = data.get("candidates", [])
        content = ""
        for c in candidates:
            parts = c.get("content", {}).get("parts", [])
            for p in parts:
                content += p.get("text", "")

        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", 0)
        output_tokens = usage.get("candidatesTokenCount", 0)

        cost = self._estimate_cost(model, prompt_tokens, output_tokens)

        return ChatResponse(
            content=content,
            model=model,
            provider="google",
            tokens_prompt=prompt_tokens,
            tokens_completion=output_tokens,
            tokens_total=prompt_tokens + output_tokens,
            cost=cost,
            latency_ms=(time.monotonic() - start) * 1000,
        )

    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        model = request.model or "gemini-2.5-flash"
        logger.info("google.stream.request", model=model, provider_id=self.provider_id)
        contents, system = self._build_contents(request.messages)
        body: dict[str, Any] = {"contents": contents}
        if system:
            body["system_instruction"] = {"parts": [{"text": system}]}
        if request.max_tokens:
            body["generationConfig"] = {"maxOutputTokens": request.max_tokens}

        stream_id = f"google-{id(request)}"

        async def _gen():
            async with self._http_client.stream(
                "POST",
                self._chat_url(model, stream=True),
                json=body,
                headers=self._headers,
            ) as resp:
                resp.raise_for_status()
                async for chunk in StreamingManager.read_sse_lines(resp):
                    text = StreamingManager.extract_google_chunk(chunk)
                    if text:
                        yield text

        async for token in self._streaming.stream(stream_id, _gen(), timeout=self._timeout_config.streaming):
            yield token

    async def health(self) -> ProviderStatus:
        try:
            url = f"{self._base_url}/models"
            resp = await call_with_timeout(
                self._http_client.get(url, headers=self._headers),
                timeout=self._timeout_config.health,
                provider_id="google",
                operation="health",
            )
            return ProviderStatus.CONNECTED if resp.status_code == 200 else ProviderStatus.ERROR
        except Exception as e:
            return self._map_error(e)

    def _estimate_cost(self, model: str, prompt_tokens: int, output_tokens: int) -> float:
        rates = {
            "gemini-2.5-flash": (0.00015, 0.00060),
            "gemini-2.5-pro": (0.00125, 0.01000),
            "gemini-2.0-flash": (0.00010, 0.00040),
            "gemini-2.0-flash-lite": (0.000075, 0.00030),
            "gemini-1.5-flash": (0.000075, 0.00030),
            "gemini-1.5-pro": (0.00350, 0.01050),
        }
        for prefix, (ir, ocr) in rates.items():
            if prefix in model:
                return (prompt_tokens / 1000 * ir) + (output_tokens / 1000 * ocr)
        return 0.0

    def _map_error(self, error: Exception) -> ProviderStatus:
        err_str = str(error).lower()
        if "401" in err_str or "unauthorized" in err_str or "api key" in err_str:
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
