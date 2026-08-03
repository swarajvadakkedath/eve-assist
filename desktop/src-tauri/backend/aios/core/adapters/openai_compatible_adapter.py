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
from aios.core.model_info import ModelInfo, CommercialStatus, AvailabilityStatus
from aios.core.streaming_manager import StreamingManager
from aios.core.timeout_retry import TimeoutConfig, call_with_timeout
from aios.core.capability_inference import infer_capabilities, bool_from_inference, merge_into_modelinfo

logger = structlog.get_logger(__name__)

# OpenRouter pricing field: 0.0 means free-tier variant
_OPENROUTER_FREE_KEYWORDS = frozenset({
    ":free", "-free", "mistral-7b-instruct:free",
})


def _openrouter_classify(model_raw: dict) -> tuple[CommercialStatus, bool]:
    """Classify an OpenRouter model as free or paid using its pricing fields.

    OpenRouter returns `pricing.prompt` and `pricing.completion` as per-token
    strings.  "0" or "0.0" means free for that direction.
    """
    pricing = model_raw.get("pricing", {})
    if isinstance(pricing, dict):
        prompt_price = pricing.get("prompt", "1")
        completion_price = pricing.get("completion", "1")
        try:
            is_free = float(prompt_price) == 0.0 and float(completion_price) == 0.0
        except (ValueError, TypeError):
            is_free = False
    else:
        is_free = False

    # Also check the model ID for free variants (/:free suffix)
    mid = model_raw.get("id", "")
    if ":free" in mid.lower() or mid.lower().endswith(":free"):
        is_free = True

    cs = CommercialStatus.FREE if is_free else CommercialStatus.PAID
    return cs, is_free


# ---------------------------------------------------------------------------
# Commercial status strategies — keyed by commercial_policy from registry.
# Each strategy: (model_id, raw_dict) → (CommercialStatus, is_free)
# ---------------------------------------------------------------------------

def _classify_openrouter(mid: str, raw: dict) -> tuple[CommercialStatus, bool]:
    """OpenRouter: free if both pricing fields are 0.0 or model id ends with :free."""
    pricing = raw.get("pricing", {})
    if isinstance(pricing, dict):
        prompt_price = pricing.get("prompt", "1")
        completion_price = pricing.get("completion", "1")
        try:
            is_free = float(prompt_price) == 0.0 and float(completion_price) == 0.0
        except (ValueError, TypeError):
            is_free = False
    else:
        is_free = False
    if ":free" in mid.lower() or mid.lower().endswith(":free"):
        is_free = True
    cs = CommercialStatus.FREE if is_free else CommercialStatus.PAID
    return cs, is_free


def _classify_local(mid: str, raw: dict) -> tuple[CommercialStatus, bool]:
    return CommercialStatus.LOCAL, True


def _classify_free_tier(mid: str, raw: dict) -> tuple[CommercialStatus, bool]:
    return CommercialStatus.FREE_TIER, True


def _classify_free_tier_not_free(mid: str, raw: dict) -> tuple[CommercialStatus, bool]:
    return CommercialStatus.FREE_TIER, False


def _classify_mistral(mid: str, raw: dict) -> tuple[CommercialStatus, bool]:
    pricing = raw.get("pricing", raw.get("price", {}))
    if isinstance(pricing, dict):
        try:
            if float(pricing.get("prompt", "1") or "1") == 0.0:
                return CommercialStatus.FREE_TIER, True
        except (ValueError, TypeError):
            pass
    return CommercialStatus.PAID, False


def _classify_cerebras(mid: str, raw: dict) -> tuple[CommercialStatus, bool]:
    return CommercialStatus.PAID, False


def _classify_deepinfra(mid: str, raw: dict) -> tuple[CommercialStatus, bool]:
    """DeepInfra: free if per-token pricing fields are zero, otherwise paid.

    DeepInfra's `/models` endpoint returns `input_cost_per_token` /
    `output_cost_per_token` (or `per_token_costs`) per model when queried
    with ``?include_costs=true``.  Fall back to the generic classifier when
    those fields are absent.
    """
    pricing = raw.get("pricing", raw)
    if isinstance(pricing, dict):
        input_cost = (
            pricing.get("input_cost_per_token")
            or pricing.get("input_cost")
            or pricing.get("per_token_costs", {}).get("input")
        )
        output_cost = (
            pricing.get("output_cost_per_token")
            or pricing.get("output_cost")
            or pricing.get("per_token_costs", {}).get("output")
        )
        if input_cost is not None and output_cost is not None:
            try:
                is_free = float(input_cost) == 0.0 and float(output_cost) == 0.0
                cs = CommercialStatus.FREE_TIER if is_free else CommercialStatus.PAID
                return cs, is_free
            except (ValueError, TypeError):
                pass
    return _generic_classify(mid, raw)


def _classify_credit_based(mid: str, raw: dict) -> tuple[CommercialStatus, bool]:
    return CommercialStatus.CREDIT_BASED, False


def _classify_paid(mid: str, raw: dict) -> tuple[CommercialStatus, bool]:
    return CommercialStatus.PAID, False


def _generic_classify(mid: str, raw: dict) -> tuple[CommercialStatus, bool]:
    """Generic: check pricing fields for zero-cost indicators."""
    pricing = raw.get("pricing", raw.get("price", {}))
    if isinstance(pricing, dict):
        prompt_p = pricing.get("prompt", pricing.get("input", "1"))
        compl_p = pricing.get("completion", pricing.get("output", "1"))
        try:
            if float(prompt_p) == 0.0 and float(compl_p) == 0.0:
                return CommercialStatus.FREE_TIER, True
        except (ValueError, TypeError):
            pass
    return CommercialStatus.UNKNOWN, False


# Maps registry commercial_policy → classifier function
_COMMERCIAL_POLICIES: dict[str, Any] = {
    "openrouter": _classify_openrouter,
    "local": _classify_local,
    "free_tier": _classify_free_tier,
    "free_tier_not_free": _classify_free_tier_not_free,
    "mistral": _classify_mistral,
    "cerebras": _classify_cerebras,
    "deepinfra": _classify_deepinfra,
    "credit_based": _classify_credit_based,
    "paid": _classify_paid,
    "generic": _generic_classify,
}


# ---------------------------------------------------------------------------
# Capability extraction from raw provider metadata (W2)
# ---------------------------------------------------------------------------

def _extract_capabilities(mid: str, raw: dict) -> dict[str, bool]:
    """Delegate to centralized inference module (client-facing bool API)."""
    inferred = infer_capabilities(mid, raw)
    return bool_from_inference(inferred)


def _extract_deprecation(raw: dict) -> tuple[bool, AvailabilityStatus]:
    """Detect deprecated/removed/preview/experimental from provider metadata.

    OpenAI-compatible providers signal deprecation via ``deprecation`` /
    ``deprecated`` fields or a ``status`` enum.  Returns (deprecated, availability).
    """
    status = raw.get("status")
    if isinstance(status, str):
        s = status.lower()
        if s in ("deprecated", "deprecation"):
            return True, AvailabilityStatus.DEPRECATED
        if s in ("removed", "deleted"):
            return True, AvailabilityStatus.REMOVED
        if s in ("preview", "beta"):
            return False, AvailabilityStatus.PREVIEW
        if s in ("experimental", "research"):
            return False, AvailabilityStatus.EXPERIMENTAL

    dep = raw.get("deprecation")
    if dep not in (None, "", "null"):
        if isinstance(dep, bool):
            return dep, AvailabilityStatus.DEPRECATED if dep else (False, AvailabilityStatus.AVAILABLE)
        return True, AvailabilityStatus.DEPRECATED

    dep2 = raw.get("deprecated")
    if dep2 in (True, "true", "yes", "1"):
        return True, AvailabilityStatus.DEPRECATED
    if dep2 is False:
        return False, AvailabilityStatus.AVAILABLE

    return False, AvailabilityStatus.AVAILABLE


class OpenAICompatibleAdapter(AIProviderAdapter):
    """Adapter for any OpenAI-compatible API (OpenRouter, LM Studio, etc.).

    Now config-driven: headers, commercial policy, and discovery strategy
    are passed via the ``metadata`` dict (populated from ProviderDefinition)
    instead of being hardcoded per provider_type.
    """

    def __init__(
        self,
        provider_type: str,
        provider_name: str,
        api_key: str = "",
        base_url: str = "",
        timeout_config: TimeoutConfig | None = None,
        streaming_manager: StreamingManager | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self._provider_type = provider_type
        self._provider_name = provider_name
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_config = timeout_config or TimeoutConfig()
        self._streaming = streaming_manager or StreamingManager()
        meta = metadata or {}
        self._commercial_policy: str = meta.get("commercial_policy", "generic")
        self._discovery_strategy: str = meta.get("discovery_strategy", "openai_v1")
        self._priority: int = int(meta.get("priority", 100))
        self._headers = {"Content-Type": "application/json"}
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"
        # Apply provider-specific extra headers from registry
        extra = meta.get("extra_headers", {})
        self._headers.update(extra)
        self._http_client = httpx.AsyncClient(timeout=self._timeout_config.chat)

    @property
    def provider_id(self) -> str:
        return self._provider_type

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def priority(self) -> int:
        return self._priority

    async def connect(self) -> ProviderStatus:
        return await self.health()

    async def disconnect(self) -> None:
        await self._http_client.aclose()

    async def validate_api_key(self) -> bool:
        return (await self.health()) == ProviderStatus.CONNECTED

    def _classify_free(self, mid: str, raw: dict) -> tuple[CommercialStatus, bool]:
        """Determine commercial status for a discovered model.

        Dispatches to a strategy function based on ``self._commercial_policy``
        (set from the registry).  Adding a new commercial model requires only
        registering the policy string and writing a small classifier — no edits
        to this adapter.
        """
        strategy = _COMMERCIAL_POLICIES.get(self._commercial_policy)
        if strategy:
            return strategy(mid, raw)
        # Fallback: generic pricing inspection
        return _generic_classify(mid, raw)

    async def list_models(self) -> list[ModelInfo]:
        # Use discovery_strategy from registry metadata instead of hardcoded provider_type
        if self._discovery_strategy == "lmstudio":
            return await self._list_lmstudio_models()
        return await self._list_standard_models()

    async def _list_standard_models(self) -> list[ModelInfo]:
        """Standard OpenAI-compatible GET {base_url}/models discovery."""
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
                    raw_dict: dict = {}
                elif isinstance(m, dict):
                    mid = m.get("id", "")
                    raw_dict = m
                else:
                    continue

                if not mid:
                    continue

                def _get_ctx(d: dict) -> int:
                    return (
                        d.get("context_length")
                        or d.get("context_window")
                        or d.get("max_context_length")
                        or d.get("max_context")
                        or 128000
                    )
                def _get_max_out(d: dict) -> int:
                    return (
                        d.get("max_output_tokens")
                        or d.get("max_completion_tokens")
                        or d.get("max_tokens")
                        or 16384
                    )

                commercial_status, is_free = self._classify_free(mid, raw_dict)

                # Extract pricing for paid models
                pricing = {"input": 0.0, "output": 0.0}
                if commercial_status == CommercialStatus.PAID:
                    raw_pricing = raw_dict.get("pricing", {})
                    if isinstance(raw_pricing, dict):
                        try:
                            pricing["input"] = float(raw_pricing.get("prompt", 0) or 0)
                            pricing["output"] = float(raw_pricing.get("completion", 0) or 0)
                        except (ValueError, TypeError):
                            pass

                # Capability extraction from raw provider metadata (W2)
                caps = _extract_capabilities(mid, raw_dict)
                deprecated, availability = _extract_deprecation(raw_dict)

                model_info = ModelInfo(
                    id=mid,
                    display_name=raw_dict.get("name", mid) if isinstance(raw_dict, dict) else mid,
                    provider_id=self._provider_type,
                    provider_name=self._provider_name,
                    provider_type=self._provider_type,
                    context_window=_get_ctx(raw_dict),
                    max_output_tokens=_get_max_out(raw_dict),
                    supports_streaming=True,
                    supports_vision=caps["supports_vision"],
                    supports_reasoning=caps["supports_reasoning"],
                    supports_thinking=caps["supports_thinking"],
                    supports_tools=caps["supports_tools"],
                    supports_function_calling=caps["supports_function_calling"],
                    supports_json=caps["supports_json"],
                    supports_embeddings=caps["supports_embeddings"],
                    supports_audio=caps["supports_audio"],
                    supports_image_generation=caps["supports_image_generation"],
                    supports_video=caps["supports_video"],
                    supports_files=caps["supports_files"],
                    is_free=is_free,
                    commercial_status=commercial_status,
                    availability=availability,
                    deprecated=deprecated,
                    pricing=pricing,
                    discovery_source="api",
                    raw_provider_metadata={k: v for k, v in raw_dict.items() if k not in ("id", "object")} if raw_dict else {},
                )
                models.append(model_info)

            return models
        except httpx.ConnectError:
            logger.warning("compatible.list_models.connect_error", url=url)
            return []
        except Exception as e:
            logger.error("compatible.list_models.failed", provider=self._provider_type, error=sanitize_error(str(e)[:200]))
            return []

    async def get_model(self, model_id: str) -> ModelInfo | None:
        models = await self.list_models()
        for m in models:
            if m.id == model_id:
                return m
        return None

    async def _list_lmstudio_models(self) -> list[ModelInfo]:
        """LM Studio native model discovery via /api/v1/models."""
        native_url = f"{self._base_url.rsplit('/v1', 1)[0]}/api/v1/models"
        try:
            resp = await call_with_timeout(
                self._http_client.get(native_url, headers=self._headers),
                timeout=self._timeout_config.list_models,
                provider_id="lm_studio",
                operation="list_models",
            )
            if resp.status_code == 200:
                data = resp.json()
                models = []
                for m in data.get("data", []):
                    mid = m.get("id", "")
                    if not mid:
                        continue
                    caps = m.get("capabilities", {})
                    details = m.get("details", {})
                    models.append(ModelInfo(
                        id=mid,
                        display_name=m.get("display_name", mid),
                        provider_id="lm_studio",
                        provider_name="LM Studio",
                        provider_type="lm_studio",
                        context_window=m.get("max_context_length", 8192) or 8192,
                        max_output_tokens=m.get("max_output_tokens", 4096) or 4096,
                        supports_streaming=True,
                        supports_vision=caps.get("vision", False),
                        supports_tools=caps.get("trained_for_tool_use", False),
                        supports_json=True,
                        supports_function_calling=caps.get("trained_for_tool_use", False),
                        supports_reasoning=caps.get("reasoning", False),
                        commercial_status=CommercialStatus.LOCAL,
                        availability=AvailabilityStatus.AVAILABLE,
                        is_free=True,
                        discovery_source="api",
                        metadata={
                            "architecture": details.get("architecture", ""),
                            "quantization": details.get("quantization", ""),
                            "publisher": m.get("publisher", ""),
                            "type": m.get("type", ""),
                        },
                    ))
                return models
        except Exception as e:
            logger.warning("lmstudio.native_discovery.failed", error=sanitize_error(str(e)[:200]))

        # Fallback to standard OpenAI-compatible /v1/models
        return await self._list_standard_models()

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
            return ChatResponse(provider=self._provider_type, model=request.model, content=f"Error: {sanitize_error(str(e)[:300])}")

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
        url = f"{self._base_url}/chat/completions"
        logger.info("compatible.stream.request", provider=self._provider_type, model=request.model, url=url)

        async def _gen():
            async with self._http_client.stream(
                "POST",
                url,
                json=body,
                headers=self._headers,
            ) as resp:
                logger.info("compatible.stream.response", provider=self._provider_type, status=resp.status_code, content_type=resp.headers.get("content-type", ""))
                resp.raise_for_status()
                chunk_count = 0
                async for chunk in StreamingManager.read_sse_lines(resp):
                    content = StreamingManager.extract_openai_chunk(chunk)
                    chunk_count += 1
                    if content:
                        yield content
                logger.info("compatible.stream.done", provider=self._provider_type, chunks_processed=chunk_count)

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
