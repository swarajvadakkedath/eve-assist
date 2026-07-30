"""Smart Router — routes requests by capability instead of hardcoded mappings.

Capability-based routing:
  Request → Find enabled models matching required capabilities → Rank → Select best.

Users can also manually override provider/model per routing category.

Routing policies:
  AUTO            — Smart Routing: automatic failover allowed (default for categories)
  STRICT          — Explicit selection: no silent fallback, error on unavailability
  ALLOW_FALLBACK  — Explicit selection but failover permitted with metadata
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator

import structlog

from aios.core.adapters.base import (
    AIProviderAdapter,
    ChatRequest,
    ChatResponse,
    ProviderStatus,
)
from aios.core.model_info import ModelInfo
from aios.core.health_monitor import HealthMonitor
from aios.core.timeout_retry import (
    call_with_timeout,
    ProviderTimeoutError,
    ProviderRetryExhausted,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Routing policy
# ---------------------------------------------------------------------------

class RoutingPolicy(str, Enum):
    AUTO = "auto"
    STRICT = "strict"
    ALLOW_FALLBACK = "allow_fallback"


# ---------------------------------------------------------------------------
# Routing errors — typed, safe, no credential leakage
# ---------------------------------------------------------------------------

class RoutingError(Exception):
    """Base for all routing errors. Carries safe metadata only."""

    def __init__(
        self,
        error_type: str,
        requested_provider_id: str | None = None,
        requested_model_id: str | None = None,
        reason: str = "",
        fallback_available: bool = False,
    ):
        self.error_type = error_type
        self.requested_provider_id = requested_provider_id
        self.requested_model_id = requested_model_id
        self.reason = reason
        self.fallback_available = fallback_available
        super().__init__(reason)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": self.error_type,
            "requested_provider_id": self.requested_provider_id,
            "requested_model_id": self.requested_model_id,
            "reason": self.reason,
            "fallback_available": self.fallback_available,
        }


class ProviderUnavailableError(RoutingError):
    """Explicitly selected provider is not registered or not healthy."""

    def __init__(
        self,
        requested_provider_id: str,
        requested_model_id: str | None = None,
        reason: str = "Selected provider is unavailable",
    ):
        super().__init__(
            error_type="PROVIDER_UNAVAILABLE",
            requested_provider_id=requested_provider_id,
            requested_model_id=requested_model_id,
            reason=reason,
            fallback_available=False,
        )


class ModelUnavailableError(RoutingError):
    """Explicitly selected model is not available on the requested provider."""

    def __init__(
        self,
        requested_provider_id: str | None = None,
        requested_model_id: str = "",
        reason: str = "Selected model is unavailable on this provider",
    ):
        super().__init__(
            error_type="MODEL_UNAVAILABLE",
            requested_provider_id=requested_provider_id,
            requested_model_id=requested_model_id,
            reason=reason,
            fallback_available=False,
        )


# ---------------------------------------------------------------------------
# Fallback metadata — observable when fallback occurs
# ---------------------------------------------------------------------------

@dataclass
class FallbackMetadata:
    """Attached to response when fallback occurred."""
    requested_provider_id: str | None = None
    requested_model_id: str | None = None
    actual_provider_id: str | None = None
    actual_model_id: str | None = None
    fallback_used: bool = False
    fallback_reason: str = ""


ROUTING_CATEGORIES = [
    {"id": "general_chat", "label": "General Chat", "capabilities": ["supports_streaming"]},
    {"id": "coding", "label": "Coding", "capabilities": ["supports_tools", "supports_function_calling", "supports_reasoning"]},
    {"id": "vision", "label": "Vision", "capabilities": ["supports_vision", "supports_streaming"]},
    {"id": "reasoning", "label": "Reasoning", "capabilities": ["supports_reasoning", "supports_thinking"]},
    {"id": "fallback", "label": "Fallback", "capabilities": []},
]


class RoutingStrategy(Enum):
    PRIORITY = "priority"
    PERFORMANCE = "performance"
    COST = "cost"
    LATENCY = "latency"


@dataclass
class RoutingEntry:
    id: str
    label: str
    provider_id: str | None = None
    model_id: str | None = None


@dataclass
class RoutingResult:
    provider_id: str
    model_id: str
    adapter: AIProviderAdapter
    score: float = 0.0


class SmartRouter:
    """Capability-based router for chat requests."""

    def __init__(
        self,
        health_monitor: HealthMonitor | None = None,
        strategy: RoutingStrategy = RoutingStrategy.PERFORMANCE,
    ):
        self._adapters: dict[str, AIProviderAdapter] = {}
        self._provider_models: dict[str, list[ModelInfo]] = {}
        self._routing_config: list[RoutingEntry] = []
        self._strategy = strategy
        self._health_monitor = health_monitor or HealthMonitor()

    @property
    def adapters(self) -> dict[str, AIProviderAdapter]:
        return dict(self._adapters)

    # -- Adapter management -------------------------------------------------

    def register_adapter(self, provider_id: str, adapter: AIProviderAdapter):
        self._adapters[provider_id] = adapter
        self._health_monitor.register_provider(provider_id)

    def unregister_adapter(self, provider_id: str):
        self._adapters.pop(provider_id, None)
        self._provider_models.pop(provider_id, None)
        self._health_monitor.unregister_provider(provider_id)

    def get_adapter(self, provider_id: str) -> AIProviderAdapter | None:
        return self._adapters.get(provider_id)

    def get_all_adapters(self) -> dict[str, AIProviderAdapter]:
        return dict(self._adapters)

    def set_provider_models(self, provider_id: str, models: list[ModelInfo]):
        self._provider_models[provider_id] = models

    # -- Routing config -----------------------------------------------------

    def set_routing_config(self, config: list[dict]):
        self._routing_config = [
            RoutingEntry(
                id=entry["id"],
                label=entry.get("label", entry["id"]),
                provider_id=entry.get("provider_id"),
                model_id=entry.get("model_id"),
            )
            for entry in config
        ]

    def get_routing_config(self) -> list[RoutingEntry]:
        return list(self._routing_config)

    # -- Backward-compatible duck-typing -----------------------------------

    @staticmethod
    def _to_chat_request(request: Any) -> ChatRequest:
        if isinstance(request, ChatRequest):
            return request
        return ChatRequest(
            messages=getattr(request, "messages", []),
            model=getattr(request, "model", ""),
            max_tokens=getattr(request, "max_tokens", 4096),
            temperature=getattr(request, "temperature", 0.7),
            top_p=getattr(request, "top_p", 1.0),
            tools=getattr(request, "tools", None),
            stream=getattr(request, "stream", False),
            stop=getattr(request, "stop", None),
            provider_id=getattr(request, "provider_id", None),
        )

    async def route(
        self,
        request: Any,
        category: str = "general_chat",
        routing_policy: RoutingPolicy = RoutingPolicy.AUTO,
    ) -> Any:
        """Accept both ChatRequest and duck-typed AIRequest.

        routing_policy:
          AUTO            — failover allowed (default for categories)
          STRICT          — explicit selection, no fallback
          ALLOW_FALLBACK  — explicit selection, fallback permitted with metadata
        """
        return await self._route_internal(
            self._to_chat_request(request), category, routing_policy
        )

    async def route_stream(
        self,
        request: Any,
        category: str = "general_chat",
        routing_policy: RoutingPolicy = RoutingPolicy.AUTO,
    ) -> AsyncIterator[str]:
        req = self._to_chat_request(request)
        async for token in self._route_stream_internal(req, category, routing_policy):
            yield token

    # -- Core routing -------------------------------------------------------

    def _get_enabled_models(self) -> list[tuple[str, str, ModelInfo, AIProviderAdapter]]:
        results = []
        for pid, adapter in self._adapters.items():
            health = self._health_monitor.get_health(pid)
            if health and health.state.value in ("unreachable", "invalid_key"):
                continue
            models = self._provider_models.get(pid, [])
            for model in models:
                if model.enabled:
                    results.append((pid, model.id, model, adapter))
        return results

    def _rank_for_capabilities(
        self,
        candidates: list[tuple[str, str, ModelInfo, AIProviderAdapter]],
        required_capabilities: list[str],
    ) -> list[RoutingResult]:
        scored = []
        for pid, mid, model, adapter in candidates:
            fit_score = 0.0
            for cap in required_capabilities:
                if hasattr(model, cap) and getattr(model, cap):
                    fit_score += 1.0
            if required_capabilities:
                fit_score /= len(required_capabilities)
            else:
                fit_score = 0.5

            if self._strategy == RoutingStrategy.PERFORMANCE:
                score = fit_score * 0.6 + (model.quality / 10.0) * 0.2 + (model.speed / 10.0) * 0.2
            elif self._strategy == RoutingStrategy.COST:
                cost = model.pricing.get("input", 0) + model.pricing.get("output", 0)
                score = fit_score * 0.7 + (1.0 / (cost + 0.001)) * 0.3 if cost > 0 else fit_score
            elif self._strategy == RoutingStrategy.LATENCY:
                score = fit_score * 0.5 + (model.speed / 10.0) * 0.5
            else:
                score = fit_score

            scored.append(RoutingResult(provider_id=pid, model_id=mid, adapter=adapter, score=score))

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored

    def _resolve_category(self, category: str) -> list[RoutingEntry]:
        for entry in self._routing_config:
            if entry.id == category:
                return [entry]
        return []

    async def _route_internal(
        self,
        request: ChatRequest,
        category: str = "general_chat",
        routing_policy: RoutingPolicy = RoutingPolicy.AUTO,
    ) -> ChatResponse:
        # 1. Per-conversation provider override (highest priority)
        if request.provider_id:
            adapter = self._adapters.get(request.provider_id)
            if adapter:
                # Validate model belongs to this provider if explicitly set
                if request.model:
                    provider_models = self._provider_models.get(request.provider_id, [])
                    model_ids = {m.id for m in provider_models if m.enabled}
                    if model_ids and request.model not in model_ids:
                        if routing_policy == RoutingPolicy.STRICT:
                            raise ModelUnavailableError(
                                requested_provider_id=request.provider_id,
                                requested_model_id=request.model,
                                reason=f"Model '{request.model}' is not available on provider '{request.provider_id}'",
                            )
                        # ALLOW_FALLBACK or AUTO: log and use anyway (adapter may support it)

                logger.info(
                    "router.resolve.provider_override",
                    provider_id=request.provider_id,
                    model=request.model,
                )
                req = ChatRequest(
                    messages=request.messages,
                    model=request.model or "gemini-2.5-flash",
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    tools=request.tools,
                    stream=False,
                )
                return await self._execute_with_adapter(adapter, request.provider_id, req)
            else:
                # Provider explicitly requested but not available
                if routing_policy == RoutingPolicy.STRICT:
                    raise ProviderUnavailableError(
                        requested_provider_id=request.provider_id,
                        requested_model_id=request.model,
                        reason=f"Provider '{request.provider_id}' is not registered or not healthy",
                    )
                # ALLOW_FALLBACK / AUTO: log and fall through
                logger.warning(
                    "router.explicit_provider_unavailable",
                    provider_id=request.provider_id,
                    falling_back=True,
                    policy=routing_policy.value,
                )

        # 2. Category routing config override
        cat_config = next((c for c in ROUTING_CATEGORIES if c["id"] == category), None)
        required_caps = cat_config["capabilities"] if cat_config else []
        overrides = self._resolve_category(category)

        if overrides and overrides[0].provider_id:
            override = overrides[0]
            adapter = self._adapters.get(override.provider_id)
            if adapter:
                req = ChatRequest(
                    messages=request.messages,
                    model=override.model_id or request.model or "gemini-2.5-flash",
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    tools=request.tools,
                    stream=False,
                )
                return await self._execute_with_adapter(adapter, override.provider_id, req)

        # 3. Capability-based ranking (lowest priority)
        candidates = self._get_enabled_models()
        ranked = self._rank_for_capabilities(candidates, required_caps)

        last_error: Exception | None = None
        for result in ranked:
            req = ChatRequest(
                messages=request.messages,
                model=result.model_id,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                tools=request.tools,
                stream=False,
            )
            try:
                return await self._execute_with_adapter(result.adapter, result.provider_id, req)
            except (ProviderTimeoutError, ProviderRetryExhausted) as e:
                last_error = e
                logger.warning("router.fallback", provider=result.provider_id, error=str(e))
                continue
            except Exception as e:
                last_error = e
                logger.warning("router.fallback", provider=result.provider_id, error=str(e))
                continue

        raise RuntimeError(f"All providers failed for category '{category}'") from last_error

    async def _route_stream_internal(
        self,
        request: ChatRequest,
        category: str = "general_chat",
        routing_policy: RoutingPolicy = RoutingPolicy.AUTO,
    ) -> AsyncIterator[str]:
        # 1. Per-conversation provider override (highest priority)
        if request.provider_id:
            adapter = self._adapters.get(request.provider_id)
            if adapter:
                # Validate model belongs to this provider if explicitly set
                if request.model:
                    provider_models = self._provider_models.get(request.provider_id, [])
                    model_ids = {m.id for m in provider_models if m.enabled}
                    if model_ids and request.model not in model_ids:
                        if routing_policy == RoutingPolicy.STRICT:
                            raise ModelUnavailableError(
                                requested_provider_id=request.provider_id,
                                requested_model_id=request.model,
                                reason=f"Model '{request.model}' is not available on provider '{request.provider_id}'",
                            )

                logger.info(
                    "router.resolve.provider_override",
                    provider_id=request.provider_id,
                    model=request.model,
                )
                req = ChatRequest(
                    messages=request.messages,
                    model=request.model or "gemini-2.5-flash",
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    tools=request.tools,
                    stream=True,
                )
                async for token in adapter.stream(req):
                    yield token
                return
            else:
                # Provider explicitly requested but not available
                if routing_policy == RoutingPolicy.STRICT:
                    raise ProviderUnavailableError(
                        requested_provider_id=request.provider_id,
                        requested_model_id=request.model,
                        reason=f"Provider '{request.provider_id}' is not registered or not healthy",
                    )
                logger.warning(
                    "router.explicit_provider_unavailable",
                    provider_id=request.provider_id,
                    falling_back=True,
                    policy=routing_policy.value,
                )

        # 2. Category routing config override
        cat_config = next((c for c in ROUTING_CATEGORIES if c["id"] == category), None)
        required_caps = cat_config["capabilities"] if cat_config else []
        overrides = self._resolve_category(category)

        if overrides and overrides[0].provider_id:
            override = overrides[0]
            adapter = self._adapters.get(override.provider_id)
            if adapter:
                logger.info(
                    "router.resolve.category_override",
                    category=category,
                    provider_id=override.provider_id,
                    model=override.model_id,
                )
                req = ChatRequest(
                    messages=request.messages,
                    model=override.model_id or request.model or "gemini-2.5-flash",
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    tools=request.tools,
                    stream=True,
                )
                async for token in adapter.stream(req):
                    yield token
                return

        # 3. Capability-based ranking (lowest priority)
        candidates = self._get_enabled_models()
        ranked = self._rank_for_capabilities(candidates, required_caps)

        last_error: Exception | None = None
        for result in ranked:
            req = ChatRequest(
                messages=request.messages,
                model=result.model_id,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                tools=request.tools,
                stream=True,
            )
            try:
                async for token in result.adapter.stream(req):
                    yield token
                return
            except Exception as e:
                last_error = e
                logger.warning("router.stream_fallback", provider=result.provider_id, error=str(e))
                continue

        raise RuntimeError(f"All providers failed for streaming category '{category}'") from last_error

    async def _execute_with_adapter(
        self,
        adapter: AIProviderAdapter,
        provider_id: str,
        request: ChatRequest,
    ) -> ChatResponse:
        start = time.monotonic()
        try:
            response = await adapter.chat(request)
            await self._health_monitor.check_provider(provider_id, adapter)
            return response
        except Exception as e:
            await self._health_monitor.check_provider(provider_id, adapter)
            raise

    # -- Capability summary -------------------------------------------------

    def get_capability_summary(self) -> dict[str, dict]:
        summary = {}
        for pid, adapter in self._adapters.items():
            models = self._provider_models.get(pid, [])
            enabled = [m for m in models if m.enabled]
            caps = set()
            for m in enabled:
                for attr in [
                    "supports_streaming", "supports_vision", "supports_reasoning",
                    "supports_thinking", "supports_tools", "supports_function_calling",
                    "supports_json", "supports_embeddings", "supports_audio",
                    "supports_image_generation",
                ]:
                    if getattr(m, attr, False):
                        caps.add(attr.replace("supports_", ""))
            summary[pid] = {
                "models": [m.to_dict() for m in enabled],
                "capabilities": sorted(caps),
            }
        return summary
