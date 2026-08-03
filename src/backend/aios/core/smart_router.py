"""Smart Router — quota-aware, multi-account, capability-first routing engine.

Capability-based routing:
  Request → Capability requirements → Eligible models → Health/quota filter →
  Commercial policy → Priority/performance ranking → Execution

Routing policies:
  AUTO            — Smart Routing: multi-account failover allowed (default)
  STRICT          — Explicit selection: exact route only, no silent fallback
  ALLOW_FALLBACK  — Explicit selection but failover permitted with metadata

Commercial policies:
  FREE_ONLY       — Only FREE + LOCAL models
  NO_DIRECT_PAID  — FREE + FREE_TIER + CREDIT_BASED + LOCAL
  ALLOW_PAID      — All valid routes
"""

from __future__ import annotations

import time
import uuid
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
from aios.core.model_info import ModelInfo, CommercialStatus, AvailabilityStatus
from aios.core.health_monitor import HealthMonitor, HealthState, RateLimitState
from aios.core.timeout_retry import (
    call_with_timeout,
    ProviderTimeoutError,
    ProviderRetryExhausted,
)
from aios.core.routing_types import (
    CommercialPolicy,
    FallbackReason,
    RouteError,
    RouteUnavailableError,
    RouteQuotaExhaustedError,
    RouteRateLimitedError,
    RouteAuthError,
    RouteCapabilityError,
    NoEligibleRouteError,
    PaidRoutingDisabledError,
    RouteCandidate,
    RoutingTrace,
    RoutingExecutionMetadata,
    CATEGORY_CAPABILITIES,
    required_capabilities_from_category,
)

# Backward-compatible alias
RoutingError = RouteError

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Routing policy
# ---------------------------------------------------------------------------

class RoutingPolicy(str, Enum):
    AUTO = "auto"
    STRICT = "strict"
    ALLOW_FALLBACK = "allow_fallback"


# ---------------------------------------------------------------------------
# Backward-compatible aliases (kept for test compatibility)
# ---------------------------------------------------------------------------

class ProviderUnavailableError(RouteError):
    """Legacy alias — use RouteUnavailableError for new code."""

    def __init__(
        self,
        requested_provider_id: str,
        requested_model_id: str | None = None,
        reason: str = "Selected provider is unavailable",
    ):
        self._requested_provider_id = requested_provider_id
        self._requested_model_id = requested_model_id
        super().__init__(
            error_type="PROVIDER_UNAVAILABLE",
            provider_instance_id=requested_provider_id,
            model_id=requested_model_id,
            reason=reason,
        )

    @property
    def requested_provider_id(self) -> str:
        return self._requested_provider_id

    @property
    def requested_model_id(self) -> str | None:
        return self._requested_model_id

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["requested_provider_id"] = self._requested_provider_id
        d["requested_model_id"] = self._requested_model_id
        return d


class ModelUnavailableError(RouteError):
    """Legacy alias — use RouteUnavailableError for new code."""

    def __init__(
        self,
        requested_provider_id: str | None = None,
        requested_model_id: str = "",
        reason: str = "Selected model is unavailable on this provider",
    ):
        self._requested_provider_id = requested_provider_id
        self._requested_model_id = requested_model_id
        super().__init__(
            error_type="MODEL_UNAVAILABLE",
            provider_instance_id=requested_provider_id,
            model_id=requested_model_id,
            reason=reason,
        )

    @property
    def requested_provider_id(self) -> str | None:
        return self._requested_provider_id

    @property
    def requested_model_id(self) -> str:
        return self._requested_model_id

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["requested_provider_id"] = self._requested_provider_id
        d["requested_model_id"] = self._requested_model_id
        return d


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


# ---------------------------------------------------------------------------
# Routing categories
# ---------------------------------------------------------------------------

_CATEGORY_LABELS = {
    "general_chat": "General Chat",
    "coding": "Coding",
    "vision": "Vision",
    "reasoning": "Reasoning",
    "fallback": "Fallback",
}

ROUTING_CATEGORIES = [
    {"id": cat_id, "label": _CATEGORY_LABELS.get(cat_id, cat_id), "capabilities": caps}
    for cat_id, caps in CATEGORY_CAPABILITIES.items()
    if cat_id in _CATEGORY_LABELS
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


# ---------------------------------------------------------------------------
# Commercial policy helpers
# ---------------------------------------------------------------------------

COMMERCIAL_RANK = {
    CommercialStatus.FREE: 0,
    CommercialStatus.LOCAL: 1,
    CommercialStatus.FREE_TIER: 2,
    CommercialStatus.CREDIT_BASED: 3,
    CommercialStatus.PAID: 4,
    CommercialStatus.UNKNOWN: 5,
}


def _is_commercially_eligible(status: CommercialStatus, policy: CommercialPolicy) -> bool:
    """Check if a model's commercial status is allowed by policy."""
    if policy == CommercialPolicy.ALLOW_PAID:
        return True
    if policy == CommercialPolicy.FREE_ONLY:
        return status in (CommercialStatus.FREE, CommercialStatus.LOCAL)
    if policy == CommercialPolicy.NO_DIRECT_PAID:
        return status in (
            CommercialStatus.FREE,
            CommercialStatus.FREE_TIER,
            CommercialStatus.CREDIT_BASED,
            CommercialStatus.LOCAL,
        )
    return False


# ---------------------------------------------------------------------------
# Route candidate builder
# ---------------------------------------------------------------------------

def _build_candidates(
    adapters: dict[str, AIProviderAdapter],
    provider_models: dict[str, list[ModelInfo]],
    health_monitor: HealthMonitor,
) -> list[RouteCandidate]:
    """Build all possible route candidates from registered adapters + models."""
    candidates = []
    for instance_id, adapter in adapters.items():
        # Extract provider_type from adapter (e.g. "google" from "google-abc123")
        provider_type = adapter.provider_id
        health = health_monitor.get_health(instance_id)
        models = provider_models.get(instance_id, [])

        for model in models:
            if not model.enabled:
                continue

            # Get model-specific rate limit
            model_rl = health_monitor.get_model_rate_limit(instance_id, model.id)

            candidate = RouteCandidate(
                provider_type=provider_type,
                provider_instance_id=instance_id,
                model_id=model.id,
                adapter=adapter,
                context_window=model.context_window,
                supports_streaming=model.supports_streaming,
                supports_vision=model.supports_vision,
                supports_reasoning=model.supports_reasoning,
                supports_thinking=model.supports_thinking,
                supports_tools=model.supports_tools,
                supports_function_calling=model.supports_function_calling,
                supports_json=model.supports_json,
                commercial_status=model.commercial_status.value,
                availability=model.availability.value,
                provider_health=health.state.value if health else "unknown",
                rate_limit_state=model_rl.state.value if model_rl else "none",
                cooldown_until=model_rl.cooldown_until if model_rl else 0.0,
                latency=model.latency or (health.latency_ms if health else 0.0),
                quality=model.quality,
                speed=model.speed,
                priority=getattr(adapter, "priority", 100),
            )
            candidates.append(candidate)

    return candidates


# ---------------------------------------------------------------------------
# Eligibility filter
# ---------------------------------------------------------------------------

def _filter_eligible(
    candidates: list[RouteCandidate],
    required_capabilities: list[str],
    commercial_policy: CommercialPolicy,
    trace: RoutingTrace | None = None,
) -> list[RouteCandidate]:
    """Filter candidates by eligibility. Reject ineligible, return eligible sorted for ranking."""
    eligible = []
    for c in candidates:
        reject_reason = ""

        # Provider health check
        # UNKNOWN/HEALTHY/DEGRADED are all eligible — only explicit failures reject
        if c.provider_health in ("unreachable",):
            reject_reason = "provider_unreachable"
        elif c.provider_health in ("invalid_key",):
            reject_reason = "provider_auth_error"
        elif c.provider_health in ("quota_exceeded",):
            reject_reason = "provider_quota_exhausted"
        # UNKNOWN, HEALTHY, DEGRADED, rate_limited are all eligible
        # (rate_limited is checked at model level below)

        # Availability check
        elif c.availability == "removed":
            reject_reason = "model_removed"

        # Rate limit / quota check
        elif c.rate_limit_state == "quota":
            reject_reason = "quota_exhausted"
        elif c.rate_limit_state in ("local", "provider") and time.monotonic() < c.cooldown_until:
            reject_reason = "rate_limited_cooldown"

        # Commercial policy check
        elif not _is_commercially_eligible(
            CommercialStatus(c.commercial_status), commercial_policy
        ):
            reject_reason = f"commercial_policy_{commercial_policy.value}"

        # Capability check (skip for deprecated unless explicitly allowed)
        else:
            missing = []
            for cap_field in required_capabilities:
                if not getattr(c, cap_field, False):
                    missing.append(cap_field)
            if missing:
                reject_reason = f"missing_capabilities: {','.join(missing)}"

        if reject_reason:
            c.rejected = True
            c.reject_reason = reject_reason
            if trace:
                trace.rejected_candidates.append({
                    f"{c.provider_instance_id}/{c.model_id}": reject_reason,
                })
        else:
            eligible.append(c)

    return eligible


# ---------------------------------------------------------------------------
# Ranking pipeline
# ---------------------------------------------------------------------------

def _rank_candidates(
    candidates: list[RouteCandidate],
    strategy: RoutingStrategy = RoutingStrategy.PERFORMANCE,
) -> list[RouteCandidate]:
    """Rank eligible candidates. Returns sorted list (best first)."""
    for c in candidates:
        # Base: commercial rank (lower is better)
        cs = CommercialStatus(c.commercial_status)
        cost_score = COMMERCIAL_RANK.get(cs, 5)

        # Health score
        health_score = 0 if c.provider_health == "healthy" else (1 if c.provider_health == "degraded" else 2)

        # Capability quality (average of quality + speed)
        quality_score = (c.quality + c.speed) / 20.0

        # Provider priority (higher = preferred). Normalized to [0,1].
        priority_score = min(1.0, max(0.0, c.priority / 100.0))

        # Context window (larger = preferred). Normalized log-scale to [0,1].
        ctx_score = min(1.0, max(0.0, c.context_window / 200000.0))

        # Strategy-specific weighting
        if strategy == RoutingStrategy.PERFORMANCE:
            c.score = (
                quality_score * 0.4
                + (1.0 / (cost_score + 1)) * 0.3
                + (1.0 / (health_score + 1)) * 0.2
                + (1.0 / (c.latency / 1000 + 0.1)) * 0.1
            )
        elif strategy == RoutingStrategy.COST:
            c.score = (
                (1.0 / (cost_score + 1)) * 0.5
                + quality_score * 0.3
                + (1.0 / (health_score + 1)) * 0.2
            )
        elif strategy == RoutingStrategy.LATENCY:
            c.score = (
                (1.0 / (c.latency / 1000 + 0.1)) * 0.5
                + quality_score * 0.3
                + (1.0 / (health_score + 1)) * 0.2
            )
        elif strategy == RoutingStrategy.PRIORITY:
            c.score = (
                priority_score * 0.5
                + quality_score * 0.3
                + (1.0 / (health_score + 1)) * 0.2
            )
        else:
            c.score = quality_score

        # Tie-breakers: prefer higher-priority provider and larger context
        c.score += priority_score * 0.02 + ctx_score * 0.01

        # Penalty for degraded health
        if health_score > 0:
            c.score *= 0.8

    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates


# ---------------------------------------------------------------------------
# Failover group helpers
# ---------------------------------------------------------------------------

def _same_model_alternate_instances(
    candidates: list[RouteCandidate],
    provider_type: str,
    model_id: str,
    exclude_instance: str,
) -> list[RouteCandidate]:
    """Find same model on different instances of the same provider type."""
    return [
        c for c in candidates
        if c.provider_type == provider_type
        and c.model_id == model_id
        and c.provider_instance_id != exclude_instance
    ]


def _same_provider_alternate_models(
    candidates: list[RouteCandidate],
    provider_type: str,
    exclude_model: str,
) -> list[RouteCandidate]:
    """Find different models on any instance of the same provider type."""
    return [
        c for c in candidates
        if c.provider_type == provider_type
        and c.model_id != exclude_model
    ]


def _free_alternate_providers(
    candidates: list[RouteCandidate],
    exclude_provider_type: str,
) -> list[RouteCandidate]:
    """Find FREE routes on different provider types."""
    return [
        c for c in candidates
        if c.provider_type != exclude_provider_type
        and CommercialStatus(c.commercial_status) in (CommercialStatus.FREE, CommercialStatus.LOCAL)
    ]


def _free_tier_alternate_providers(
    candidates: list[RouteCandidate],
    exclude_provider_type: str,
) -> list[RouteCandidate]:
    """Find FREE_TIER routes on different provider types."""
    return [
        c for c in candidates
        if c.provider_type != exclude_provider_type
        and CommercialStatus(c.commercial_status) == CommercialStatus.FREE_TIER
    ]


def _credit_alternate_providers(
    candidates: list[RouteCandidate],
    exclude_provider_type: str,
) -> list[RouteCandidate]:
    """Find CREDIT_BASED routes on different provider types."""
    return [
        c for c in candidates
        if c.provider_type != exclude_provider_type
        and CommercialStatus(c.commercial_status) == CommercialStatus.CREDIT_BASED
    ]


def _paid_alternate_providers(
    candidates: list[RouteCandidate],
    exclude_provider_type: str,
) -> list[RouteCandidate]:
    """Find PAID routes on different provider types."""
    return [
        c for c in candidates
        if c.provider_type != exclude_provider_type
        and CommercialStatus(c.commercial_status) == CommercialStatus.PAID
    ]


# ---------------------------------------------------------------------------
# SmartRouter
# ---------------------------------------------------------------------------

class SmartRouter:
    """Quota-aware, multi-account, capability-first routing engine."""

    MAX_CANDIDATE_ATTEMPTS = 20

    def __init__(
        self,
        health_monitor: HealthMonitor | None = None,
        strategy: RoutingStrategy = RoutingStrategy.PERFORMANCE,
        commercial_policy: CommercialPolicy = CommercialPolicy.FREE_ONLY,
    ):
        self._adapters: dict[str, AIProviderAdapter] = {}
        self._provider_models: dict[str, list[ModelInfo]] = {}
        self._routing_config: list[RoutingEntry] = []
        self._strategy = strategy
        self._commercial_policy = commercial_policy
        self._health_monitor = health_monitor or HealthMonitor()

    @property
    def adapters(self) -> dict[str, AIProviderAdapter]:
        return dict(self._adapters)

    @property
    def commercial_policy(self) -> CommercialPolicy:
        return self._commercial_policy

    @commercial_policy.setter
    def commercial_policy(self, policy: CommercialPolicy):
        self._commercial_policy = policy

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

    def _resolve_category(self, category: str) -> list[RoutingEntry]:
        """Return routing entries matching a category."""
        for entry in self._routing_config:
            if entry.id == category:
                return [entry]
        return []

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

    # -- Public API ---------------------------------------------------------

    async def route(
        self,
        request: Any,
        category: str = "general_chat",
        routing_policy: RoutingPolicy = RoutingPolicy.AUTO,
        commercial_policy: CommercialPolicy | None = None,
    ) -> ChatResponse:
        """Route a non-streaming request. Returns ChatResponse."""
        req = self._to_chat_request(request)
        result = await self._resolve_route(req, category, routing_policy, commercial_policy, streaming=False)
        return await self._execute_candidate(result.candidate, result.request, result.trace)

    async def route_stream(
        self,
        request: Any,
        category: str = "general_chat",
        routing_policy: RoutingPolicy = RoutingPolicy.AUTO,
        commercial_policy: CommercialPolicy | None = None,
    ) -> RouteStreamResult:
        """Route a streaming request. Returns RouteStreamResult with tokens + trace.

        The trace is request-scoped: returned to the caller directly rather
        than stored on shared singleton state. This prevents trace corruption
        when multiple streams execute concurrently.
        """
        req = self._to_chat_request(request)
        result = await self._resolve_route(req, category, routing_policy, commercial_policy, streaming=True)
        request_id = result.trace.request_id

        async def _token_generator():
            try:
                async for token in result.candidate.adapter.stream(result.request):
                    yield token
            except Exception:
                # Post-token failure: do NOT attempt failover (avoid duplicate answers)
                raise

        return RouteStreamResult(
            tokens=_token_generator(),
            trace=result.trace,
            request_id=request_id,
        )

    # -- Core routing: resolve_route() --------------------------------------

    async def _resolve_route(
        self,
        request: ChatRequest,
        category: str,
        routing_policy: RoutingPolicy,
        commercial_policy: CommercialPolicy | None,
        streaming: bool = False,
    ) -> _RouteResolution:
        """Shared candidate selection for both route() and route_stream()."""
        cp = commercial_policy or self._commercial_policy
        required_caps = required_capabilities_from_category(category)
        request_id = uuid.uuid4().hex
        trace = RoutingTrace(
            request_id=request_id,
            policy=routing_policy.value,
            required_capabilities=required_caps,
            commercial_policy=cp.value,
        )

        # Build all candidates
        all_candidates = _build_candidates(
            self._adapters, self._provider_models, self._health_monitor
        )
        trace.candidate_count = len(all_candidates)

        # Check category routing config override (before STRICT/AUTO dispatch)
        cat_config = next((c for c in ROUTING_CATEGORIES if c["id"] == category), None)
        required_caps = cat_config["capabilities"] if cat_config else []
        trace.required_capabilities = required_caps

        category_override = self._resolve_category(category)
        has_category_override = category_override and category_override[0].provider_id

        # === STRICT: exact route only ===
        if routing_policy == RoutingPolicy.STRICT:
            return await self._resolve_strict(request, all_candidates, required_caps, cp, trace)

        # === AUTO / ALLOW_FALLBACK: failover allowed ===
        return await self._resolve_auto(request, category, all_candidates, required_caps, cp, trace)

    # -- STRICT resolution --------------------------------------------------

    async def _resolve_strict(
        self,
        request: ChatRequest,
        all_candidates: list[RouteCandidate],
        required_caps: list[str],
        commercial_policy: CommercialPolicy,
        trace: RoutingTrace,
    ) -> _RouteResolution:
        """STRICT: use exactly the requested route. No fallback."""
        requested_instance = request.provider_id
        requested_model = request.model

        if not requested_instance:
            # No explicit selection — use capability ranking but still strict (no failover)
            eligible = _filter_eligible(all_candidates, required_caps, commercial_policy, trace)
            if not eligible:
                raise NoEligibleRouteError(
                    reason="No eligible route found (STRICT, no explicit selection)",
                    candidates_attempted=len(all_candidates),
                )
            ranked = _rank_candidates(eligible, self._strategy)
            best = ranked[0]
            req = self._make_request(request, best.model_id)
            trace.selected_provider_type = best.provider_type
            trace.selected_provider_instance_id = best.provider_instance_id
            trace.selected_model_id = best.model_id
            return _RouteResolution(candidate=best, request=req, trace=trace)

        # Find the exact candidate matching requested instance + model
        target_model = requested_model or ""

        # Filter to the exact requested route
        matching = [
            c for c in all_candidates
            if c.provider_instance_id == requested_instance
            and (not target_model or c.model_id == target_model)
        ]

        if not matching:
            # Check if adapter exists at all
            if requested_instance not in self._adapters:
                raise ProviderUnavailableError(
                    requested_provider_id=requested_instance,
                    requested_model_id=requested_model,
                    reason=f"Provider '{requested_instance}' is not registered",
                )
            raise ModelUnavailableError(
                requested_provider_id=requested_instance,
                requested_model_id=requested_model or "",
                reason=f"Model '{requested_model}' is not available on provider '{requested_instance}'",
            )

        candidate = matching[0]

        # Validate eligibility
        eligible = _filter_eligible([candidate], required_caps, commercial_policy, trace)
        if not eligible:
            reason = candidate.rejection_reason()
            if reason.startswith("provider_auth"):
                raise RouteAuthError(
                    provider_type=candidate.provider_type,
                    provider_instance_id=candidate.provider_instance_id,
                    model_id=candidate.model_id,
                    reason=f"Auth error on {candidate.provider_instance_id}",
                )
            elif reason == "provider_quota_exhausted":
                raise RouteQuotaExhaustedError(
                    provider_type=candidate.provider_type,
                    provider_instance_id=candidate.provider_instance_id,
                    model_id=candidate.model_id,
                )
            elif reason == "quota_exhausted":
                raise RouteQuotaExhaustedError(
                    provider_type=candidate.provider_type,
                    provider_instance_id=candidate.provider_instance_id,
                    model_id=candidate.model_id,
                )
            elif reason.startswith("rate_limited"):
                raise RouteRateLimitedError(
                    provider_type=candidate.provider_type,
                    provider_instance_id=candidate.provider_instance_id,
                    model_id=candidate.model_id,
                    retry_after=candidate.cooldown_until - time.monotonic() if candidate.cooldown_until else None,
                )
            elif reason.startswith("missing_capabilities"):
                raise RouteCapabilityError(
                    provider_type=candidate.provider_type,
                    provider_instance_id=candidate.provider_instance_id,
                    model_id=candidate.model_id,
                    reason=f"Model '{candidate.model_id}' missing required capabilities",
                )
            elif "commercial_policy" in reason:
                raise PaidRoutingDisabledError(
                    provider_type=candidate.provider_type,
                    model_id=candidate.model_id,
                    reason=f"Route blocked by commercial policy: {reason}",
                )
            else:
                raise RouteUnavailableError(
                    provider_type=candidate.provider_type,
                    provider_instance_id=candidate.provider_instance_id,
                    model_id=candidate.model_id,
                    reason=f"Route unavailable: {reason}",
                )

        req = self._make_request(request, candidate.model_id)
        trace.selected_provider_type = candidate.provider_type
        trace.selected_provider_instance_id = candidate.provider_instance_id
        trace.selected_model_id = candidate.model_id
        return _RouteResolution(candidate=candidate, request=req, trace=trace)

    # -- AUTO resolution with failover hierarchy ----------------------------

    async def _resolve_auto(
        self,
        request: ChatRequest,
        category: str,
        all_candidates: list[RouteCandidate],
        required_caps: list[str],
        commercial_policy: CommercialPolicy,
        trace: RoutingTrace,
    ) -> _RouteResolution:
        """AUTO: failover through the hierarchy."""
        requested_instance = request.provider_id
        requested_model = request.model
        attempted: set[str] = set()

        # Filter all candidates to eligible only
        eligible = _filter_eligible(all_candidates, required_caps, commercial_policy, trace)
        ranked = _rank_candidates(eligible, self._strategy)

        fallback_level = 0
        fallback_reason = FallbackReason.NONE

        # If explicit preference, try that first
        if requested_instance:
            preferred = [
                c for c in ranked
                if c.provider_instance_id == requested_instance
                and (not requested_model or c.model_id == requested_model)
            ]
            if preferred:
                candidate = preferred[0]
                attempted.add(f"{candidate.provider_instance_id}/{candidate.model_id}")
                req = self._make_request(request, candidate.model_id)
                trace.selected_provider_type = candidate.provider_type
                trace.selected_provider_instance_id = candidate.provider_instance_id
                trace.selected_model_id = candidate.model_id
                trace.fallback_level = 0
                trace.fallback_reason = FallbackReason.NONE.value
                return _RouteResolution(
                    candidate=candidate, request=req, trace=trace,
                    requested_provider_id=requested_instance,
                    requested_model=requested_model,
                )

            # Preferred not eligible — start failover
            # Get provider_type of the preferred instance
            preferred_type = None
            for c in all_candidates:
                if c.provider_instance_id == requested_instance:
                    preferred_type = c.provider_type
                    break

            # Level 1: Same model, alternate instance
            if preferred_type and requested_model:
                level1 = [
                    c for c in ranked
                    if c.provider_type == preferred_type
                    and c.model_id == requested_model
                    and c.provider_instance_id != requested_instance
                    and f"{c.provider_instance_id}/{c.model_id}" not in attempted
                ]
                if level1:
                    candidate = level1[0]
                    attempted.add(f"{candidate.provider_instance_id}/{candidate.model_id}")
                    req = self._make_request(request, candidate.model_id)
                    trace.selected_provider_type = candidate.provider_type
                    trace.selected_provider_instance_id = candidate.provider_instance_id
                    trace.selected_model_id = candidate.model_id
                    trace.fallback_level = 1
                    trace.fallback_reason = FallbackReason.SAME_MODEL_ALTERNATE_INSTANCE.value
                    return _RouteResolution(
                        candidate=candidate, request=req, trace=trace,
                        fallback_used=True,
                        fallback_reason=FallbackReason.SAME_MODEL_ALTERNATE_INSTANCE,
                        fallback_level=1,
                        requested_provider_id=requested_instance,
                        requested_model=requested_model,
                    )

            # Level 2: Same provider type, alternate model
            if preferred_type:
                level2 = [
                    c for c in ranked
                    if c.provider_type == preferred_type
                    and c.provider_instance_id != requested_instance
                    and f"{c.provider_instance_id}/{c.model_id}" not in attempted
                ]
                if level2:
                    candidate = level2[0]
                    attempted.add(f"{candidate.provider_instance_id}/{candidate.model_id}")
                    req = self._make_request(request, candidate.model_id)
                    trace.selected_provider_type = candidate.provider_type
                    trace.selected_provider_instance_id = candidate.provider_instance_id
                    trace.selected_model_id = candidate.model_id
                    trace.fallback_level = 2
                    trace.fallback_reason = FallbackReason.SAME_PROVIDER_ALTERNATE_MODEL.value
                    return _RouteResolution(
                        candidate=candidate, request=req, trace=trace,
                        fallback_used=True,
                        fallback_reason=FallbackReason.SAME_PROVIDER_ALTERNATE_MODEL,
                        fallback_level=2,
                        requested_provider_id=requested_instance,
                        requested_model=requested_model,
                    )

        # No explicit preference: check category routing config, then ranked
        if not requested_instance:
            # Check category routing config override against ALL candidates
            # (category overrides are explicit routing config, not subject to capability filtering)
            category_override = self._resolve_category(category)
            if category_override and category_override[0].provider_id:
                override = category_override[0]
                override_candidates = [
                    c for c in all_candidates
                    if c.provider_instance_id == override.provider_id
                    and (not override.model_id or c.model_id == override.model_id)
                ]
                # Filter to eligible only
                eligible_overrides = _filter_eligible(override_candidates, [], commercial_policy, trace)
                if eligible_overrides:
                    candidate = eligible_overrides[0]
                    attempted.add(f"{candidate.provider_instance_id}/{candidate.model_id}")
                    req = self._make_request(request, candidate.model_id)
                    trace.selected_provider_type = candidate.provider_type
                    trace.selected_provider_instance_id = candidate.provider_instance_id
                    trace.selected_model_id = candidate.model_id
                    return _RouteResolution(
                        candidate=candidate, request=req, trace=trace,
                        requested_provider_id=None,
                        requested_model=None,
                    )

            # Pick the best ranked candidate directly
            if ranked:
                candidate = ranked[0]
                attempted.add(f"{candidate.provider_instance_id}/{candidate.model_id}")
                req = self._make_request(request, candidate.model_id)
                trace.selected_provider_type = candidate.provider_type
                trace.selected_provider_instance_id = candidate.provider_instance_id
                trace.selected_model_id = candidate.model_id
                return _RouteResolution(
                    candidate=candidate, request=req, trace=trace,
                    requested_provider_id=None,
                    requested_model=None,
                )
            # Check if the issue is commercial policy blocking paid routes
            paid_blocked = [
                c for c in all_candidates
                if CommercialStatus(c.commercial_status) == CommercialStatus.PAID
                and c.rejected and "commercial_policy" in c.reject_reason
            ]
            if paid_blocked and commercial_policy != CommercialPolicy.ALLOW_PAID:
                raise PaidRoutingDisabledError(
                    provider_type=paid_blocked[0].provider_type,
                    model_id=paid_blocked[0].model_id,
                    reason=f"Only paid routes available but policy is {commercial_policy.value}",
                )
            raise NoEligibleRouteError(
                reason="No eligible route found",
                candidates_attempted=0,
            )

        # Levels 3-7: Cross-provider failover by commercial tier
        # Build remaining candidates (not yet attempted)
        remaining = [c for c in ranked if f"{c.provider_instance_id}/{c.model_id}" not in attempted]

        # Safety cap: never evaluate more than MAX_CANDIDATE_ATTEMPTS candidates.
        if len(attempted) + len(remaining) > self.MAX_CANDIDATE_ATTEMPTS:
            remaining = remaining[: max(0, self.MAX_CANDIDATE_ATTEMPTS - len(attempted))]

        # Group by commercial tier
        free = [c for c in remaining if CommercialStatus(c.commercial_status) == CommercialStatus.FREE]
        free_tier = [c for c in remaining if CommercialStatus(c.commercial_status) == CommercialStatus.FREE_TIER]
        credit = [c for c in remaining if CommercialStatus(c.commercial_status) == CommercialStatus.CREDIT_BASED]
        local = [c for c in remaining if CommercialStatus(c.commercial_status) == CommercialStatus.LOCAL]
        paid = [c for c in remaining if CommercialStatus(c.commercial_status) == CommercialStatus.PAID]

        # Level 3: FREE
        if free:
            candidate = free[0]
            attempted.add(f"{candidate.provider_instance_id}/{candidate.model_id}")
            req = self._make_request(request, candidate.model_id)
            trace.selected_provider_type = candidate.provider_type
            trace.selected_provider_instance_id = candidate.provider_instance_id
            trace.selected_model_id = candidate.model_id
            trace.fallback_level = 3
            trace.fallback_reason = FallbackReason.FREE_ALTERNATE_PROVIDER.value
            return _RouteResolution(
                candidate=candidate, request=req, trace=trace,
                fallback_used=True,
                fallback_reason=FallbackReason.FREE_ALTERNATE_PROVIDER,
                fallback_level=3,
                requested_provider_id=requested_instance,
                requested_model=requested_model,
            )

        # Level 4: FREE_TIER
        if free_tier:
            candidate = free_tier[0]
            attempted.add(f"{candidate.provider_instance_id}/{candidate.model_id}")
            req = self._make_request(request, candidate.model_id)
            trace.selected_provider_type = candidate.provider_type
            trace.selected_provider_instance_id = candidate.provider_instance_id
            trace.selected_model_id = candidate.model_id
            trace.fallback_level = 4
            trace.fallback_reason = FallbackReason.FREE_TIER_ALTERNATE_PROVIDER.value
            return _RouteResolution(
                candidate=candidate, request=req, trace=trace,
                fallback_used=True,
                fallback_reason=FallbackReason.FREE_TIER_ALTERNATE_PROVIDER,
                fallback_level=4,
                requested_provider_id=requested_instance,
                requested_model=requested_model,
            )

        # Level 5: CREDIT_BASED
        if credit:
            candidate = credit[0]
            attempted.add(f"{candidate.provider_instance_id}/{candidate.model_id}")
            req = self._make_request(request, candidate.model_id)
            trace.selected_provider_type = candidate.provider_type
            trace.selected_provider_instance_id = candidate.provider_instance_id
            trace.selected_model_id = candidate.model_id
            trace.fallback_level = 5
            trace.fallback_reason = FallbackReason.CREDIT_ALTERNATE_PROVIDER.value
            return _RouteResolution(
                candidate=candidate, request=req, trace=trace,
                fallback_used=True,
                fallback_reason=FallbackReason.CREDIT_ALTERNATE_PROVIDER,
                fallback_level=5,
                requested_provider_id=requested_instance,
                requested_model=requested_model,
            )

        # Level 6: LOCAL
        if local:
            candidate = local[0]
            attempted.add(f"{candidate.provider_instance_id}/{candidate.model_id}")
            req = self._make_request(request, candidate.model_id)
            trace.selected_provider_type = candidate.provider_type
            trace.selected_provider_instance_id = candidate.provider_instance_id
            trace.selected_model_id = candidate.model_id
            trace.fallback_level = 6
            trace.fallback_reason = FallbackReason.LOCAL_ALTERNATE.value
            return _RouteResolution(
                candidate=candidate, request=req, trace=trace,
                fallback_used=True,
                fallback_reason=FallbackReason.LOCAL_ALTERNATE,
                fallback_level=6,
                requested_provider_id=requested_instance,
                requested_model=requested_model,
            )

        # Level 7: UNKNOWN/other (treat as eligible when policy allows)
        unknown_or_other = [
            c for c in remaining
            if CommercialStatus(c.commercial_status) not in (
                CommercialStatus.FREE, CommercialStatus.FREE_TIER,
                CommercialStatus.CREDIT_BASED, CommercialStatus.LOCAL, CommercialStatus.PAID,
            )
        ]
        if unknown_or_other:
            if commercial_policy == CommercialPolicy.ALLOW_PAID:
                candidate = unknown_or_other[0]
                attempted.add(f"{candidate.provider_instance_id}/{candidate.model_id}")
                req = self._make_request(request, candidate.model_id)
                trace.selected_provider_type = candidate.provider_type
                trace.selected_provider_instance_id = candidate.provider_instance_id
                trace.selected_model_id = candidate.model_id
                trace.fallback_level = 7
                trace.fallback_reason = FallbackReason.PAID_ALTERNATE.value
                return _RouteResolution(
                    candidate=candidate, request=req, trace=trace,
                    fallback_used=True,
                    fallback_reason=FallbackReason.PAID_ALTERNATE,
                    fallback_level=7,
                    requested_provider_id=requested_instance,
                    requested_model=requested_model,
                )

        # Level 8: PAID (only if commercial policy allows)
        if paid:
            if commercial_policy == CommercialPolicy.ALLOW_PAID:
                candidate = paid[0]
                attempted.add(f"{candidate.provider_instance_id}/{candidate.model_id}")
                req = self._make_request(request, candidate.model_id)
                trace.selected_provider_type = candidate.provider_type
                trace.selected_provider_instance_id = candidate.provider_instance_id
                trace.selected_model_id = candidate.model_id
                trace.fallback_level = 7
                trace.fallback_reason = FallbackReason.PAID_ALTERNATE.value
                return _RouteResolution(
                    candidate=candidate, request=req, trace=trace,
                    fallback_used=True,
                    fallback_reason=FallbackReason.PAID_ALTERNATE,
                    fallback_level=7,
                    requested_provider_id=requested_instance,
                    requested_model=requested_model,
                )
            else:
                # Paid routes exist but policy disallows
                raise PaidRoutingDisabledError(
                    provider_type=paid[0].provider_type,
                    model_id=paid[0].model_id,
                    reason=f"Only paid routes available but policy is {commercial_policy.value}",
                )

        # Nothing eligible
        # Check if the issue is commercial policy blocking paid routes
        paid_blocked = [
            c for c in all_candidates
            if CommercialStatus(c.commercial_status) == CommercialStatus.PAID
            and c.rejected and "commercial_policy" in c.reject_reason
        ]
        if paid_blocked and commercial_policy != CommercialPolicy.ALLOW_PAID:
            raise PaidRoutingDisabledError(
                provider_type=paid_blocked[0].provider_type,
                model_id=paid_blocked[0].model_id,
                reason=f"Only paid routes available but policy is {commercial_policy.value}",
            )

        raise NoEligibleRouteError(
            reason="No eligible route found after all failover levels",
            candidates_attempted=len(attempted),
        )

    # -- Request builder ----------------------------------------------------

    def _make_request(self, original: ChatRequest, model_id: str) -> ChatRequest:
        """Create a new ChatRequest with the resolved model."""
        return ChatRequest(
            messages=original.messages,
            model=model_id,
            max_tokens=original.max_tokens,
            temperature=original.temperature,
            top_p=original.top_p,
            top_k=original.top_k,
            seed=original.seed,
            stop=original.stop,
            stream=original.stream,
            tools=original.tools,
            tool_choice=original.tool_choice,
            system_prompt=original.system_prompt,
            thinking_mode=original.thinking_mode,
            metadata=original.metadata,
        )

    # -- Execution ----------------------------------------------------------

    async def _execute_candidate(
        self,
        candidate: RouteCandidate,
        request: ChatRequest,
        trace: RoutingTrace,
    ) -> ChatResponse:
        """Execute a request through a candidate adapter. Updates health on completion."""
        start = time.monotonic()
        try:
            response = await candidate.adapter.chat(request)
            elapsed_ms = (time.monotonic() - start) * 1000
            await self._health_monitor.check_provider(candidate.provider_instance_id, candidate.adapter)
            # Attach routing metadata to response
            response.metadata["routing_trace"] = trace.to_dict()
            return response
        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000
            await self._health_monitor.check_provider(candidate.provider_instance_id, candidate.adapter)
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


# ---------------------------------------------------------------------------
# Internal resolution result
# ---------------------------------------------------------------------------

@dataclass
class RouteStreamResult:
    """Request-scoped result from route_stream().

    Holds both the token generator AND the routing trace so that callers
    receive the trace directly instead of reading from shared singleton state.
    This prevents trace corruption under concurrent streaming requests.
    """
    tokens: AsyncIterator[str]
    trace: RoutingTrace
    request_id: str


@dataclass
class _RouteResolution:
    """Internal result from resolve_route()."""
    candidate: RouteCandidate
    request: ChatRequest
    trace: RoutingTrace
    fallback_used: bool = False
    fallback_reason: FallbackReason = FallbackReason.NONE
    fallback_level: int = 0
    requested_provider_id: str | None = None
    requested_model: str | None = None
