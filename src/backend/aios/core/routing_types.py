"""Routing types — policy, errors, candidates, traces, metadata.

All types used by the quota-aware SmartRouter. Isolated from SmartRouter
implementation to avoid circular imports and enable clean testing.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Commercial policy — controls which cost tiers are eligible
# ---------------------------------------------------------------------------

class CommercialPolicy(str, Enum):
    FREE_ONLY = "free_only"          # FREE + FREE_TIER + LOCAL only
    NO_DIRECT_PAID = "no_direct_paid"  # FREE + FREE_TIER + CREDIT_BASED + LOCAL
    ALLOW_PAID = "allow_paid"        # all valid routes


# ---------------------------------------------------------------------------
# Fallback reason — typed, inspectable
# ---------------------------------------------------------------------------

class FallbackReason(str, Enum):
    NONE = "none"
    SAME_MODEL_ALTERNATE_INSTANCE = "same_model_alternate_instance"
    SAME_PROVIDER_ALTERNATE_MODEL = "same_provider_alternate_model"
    FREE_ALTERNATE_PROVIDER = "free_alternate_provider"
    FREE_TIER_ALTERNATE_PROVIDER = "free_tier_alternate_provider"
    CREDIT_ALTERNATE_PROVIDER = "credit_alternate_provider"
    LOCAL_ALTERNATE = "local_alternate"
    PAID_ALTERNATE = "paid_alternate"


# ---------------------------------------------------------------------------
# Routing errors — typed, safe, no credential leakage
# ---------------------------------------------------------------------------

class RouteError(Exception):
    """Base for all routing errors. Carries safe metadata only."""

    def __init__(
        self,
        error_type: str,
        provider_type: str | None = None,
        provider_instance_id: str | None = None,
        model_id: str | None = None,
        reason: str = "",
        retry_after: float | None = None,
    ):
        self.error_type = error_type
        self.provider_type = provider_type
        self.provider_instance_id = provider_instance_id
        self.model_id = model_id
        self.reason = reason
        self.retry_after = retry_after
        super().__init__(reason)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "error_type": self.error_type,
            "reason": self.reason,
        }
        if self.provider_type:
            d["provider_type"] = self.provider_type
        if self.provider_instance_id:
            d["provider_instance_id"] = self.provider_instance_id
        if self.model_id:
            d["model_id"] = self.model_id
        if self.retry_after is not None:
            d["retry_after"] = self.retry_after
        return d


class RouteUnavailableError(RouteError):
    """Selected route is not available (offline, disabled, auth error)."""

    def __init__(
        self,
        provider_type: str | None = None,
        provider_instance_id: str | None = None,
        model_id: str | None = None,
        reason: str = "Route unavailable",
    ):
        super().__init__(
            error_type="ROUTE_UNAVAILABLE",
            provider_type=provider_type,
            provider_instance_id=provider_instance_id,
            model_id=model_id,
            reason=reason,
        )


class RouteQuotaExhaustedError(RouteError):
    """Selected route has exhausted its quota."""

    def __init__(
        self,
        provider_type: str | None = None,
        provider_instance_id: str | None = None,
        model_id: str | None = None,
        reason: str = "Quota exhausted",
        retry_after: float | None = None,
    ):
        super().__init__(
            error_type="ROUTE_QUOTA_EXHAUSTED",
            provider_type=provider_type,
            provider_instance_id=provider_instance_id,
            model_id=model_id,
            reason=reason,
            retry_after=retry_after,
        )


class RouteRateLimitedError(RouteError):
    """Selected route is rate-limited (cooldown active)."""

    def __init__(
        self,
        provider_type: str | None = None,
        provider_instance_id: str | None = None,
        model_id: str | None = None,
        reason: str = "Rate limited",
        retry_after: float | None = None,
    ):
        super().__init__(
            error_type="ROUTE_RATE_LIMITED",
            provider_type=provider_type,
            provider_instance_id=provider_instance_id,
            model_id=model_id,
            reason=reason,
            retry_after=retry_after,
        )


class RouteAuthError(RouteError):
    """Selected route has authentication failure."""

    def __init__(
        self,
        provider_type: str | None = None,
        provider_instance_id: str | None = None,
        model_id: str | None = None,
        reason: str = "Authentication failed",
    ):
        super().__init__(
            error_type="ROUTE_AUTH_ERROR",
            provider_type=provider_type,
            provider_instance_id=provider_instance_id,
            model_id=model_id,
            reason=reason,
        )


class RouteCapabilityError(RouteError):
    """Selected route does not satisfy required capabilities."""

    def __init__(
        self,
        provider_type: str | None = None,
        provider_instance_id: str | None = None,
        model_id: str | None = None,
        missing_capabilities: list[str] | None = None,
        reason: str = "Capability mismatch",
    ):
        self.missing_capabilities = missing_capabilities or []
        super().__init__(
            error_type="ROUTE_CAPABILITY_ERROR",
            provider_type=provider_type,
            provider_instance_id=provider_instance_id,
            model_id=model_id,
            reason=reason,
        )

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        if self.missing_capabilities:
            d["missing_capabilities"] = self.missing_capabilities
        return d


class NoEligibleRouteError(RouteError):
    """No eligible route found after all candidates exhausted."""

    def __init__(
        self,
        reason: str = "No eligible route found",
        candidates_attempted: int = 0,
    ):
        self.candidates_attempted = candidates_attempted
        super().__init__(
            error_type="NO_ELIGIBLE_ROUTE",
            reason=reason,
        )

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["candidates_attempted"] = self.candidates_attempted
        return d


class PaidRoutingDisabledError(RouteError):
    """Only paid routes available but commercial policy disallows paid routing."""

    def __init__(
        self,
        provider_type: str | None = None,
        model_id: str | None = None,
        reason: str = "Only paid routes available but paid routing is disabled",
    ):
        super().__init__(
            error_type="PAID_ROUTING_DISABLED",
            provider_type=provider_type,
            model_id=model_id,
            reason=reason,
        )


# ---------------------------------------------------------------------------
# Route candidate — normalized internal representation
# ---------------------------------------------------------------------------

@dataclass
class RouteCandidate:
    """A potential route through provider instance + model."""

    provider_type: str                    # e.g. "google"
    provider_instance_id: str             # e.g. "google-abc123"
    model_id: str                         # e.g. "gemini-2.5-flash"
    adapter: Any = None                   # AIProviderAdapter instance

    # Model metadata
    context_window: int = 4096
    supports_streaming: bool = True
    supports_vision: bool = False
    supports_reasoning: bool = False
    supports_thinking: bool = False
    supports_tools: bool = False
    supports_function_calling: bool = False
    supports_json: bool = False

    # Commercial
    commercial_status: str = "unknown"    # CommercialStatus.value
    availability: str = "available"       # AvailabilityStatus.value

    # Health
    provider_health: str = "unknown"      # HealthState.value
    rate_limit_state: str = "none"        # RateLimitState.value
    cooldown_until: float = 0.0

    # Scoring
    priority: int = 0                     # configured priority (higher = preferred)
    latency: float = 0.0                  # last known latency in ms
    quality: int = 5                      # 1-10
    speed: int = 5                        # 1-10
    score: float = 0.0                    # computed ranking score

    # Rejection tracking
    rejected: bool = False
    reject_reason: str = ""

    def is_eligible(self) -> bool:
        """Check if this candidate can serve the request right now."""
        if self.rejected:
            return False
        if not self.adapter:
            return False
        if self.provider_health in ("unreachable", "invalid_key"):
            return False
        if self.availability in ("removed",):
            return False
        if self.rate_limit_state in ("quota",):
            return False
        if self.rate_limit_state in ("local", "provider") and time.monotonic() < self.cooldown_until:
            return False
        return True

    def rejection_reason(self) -> str:
        """Human-readable reason why this candidate is ineligible."""
        if self.rejected:
            return self.reject_reason
        if not self.adapter:
            return "no_adapter"
        if self.provider_health in ("unreachable", "invalid_key"):
            return f"provider_{self.provider_health}"
        if self.availability == "removed":
            return "model_removed"
        if self.rate_limit_state == "quota":
            return "quota_exhausted"
        if self.rate_limit_state in ("local", "provider") and time.monotonic() < self.cooldown_until:
            return "rate_limited_cooldown"
        return ""


# ---------------------------------------------------------------------------
# Routing trace — sanitized diagnostics
# ---------------------------------------------------------------------------

@dataclass
class RoutingTrace:
    """Sanitized routing trace for debugging. Never contains credentials.

    Each trace is request-scoped: created per route/route_stream call and never
    stored on shared singleton state. The ``request_id`` field ensures traces
    can be correlated across the request lifecycle without risk of crossover.
    """

    request_id: str = ""
    policy: str = ""
    required_capabilities: list[str] = field(default_factory=list)
    preferred_provider_id: str | None = None
    preferred_model_id: str | None = None
    commercial_policy: str = "allow_paid"

    candidate_count: int = 0
    rejected_candidates: list[dict[str, str]] = field(default_factory=list)

    selected_provider_type: str | None = None
    selected_provider_instance_id: str | None = None
    selected_model_id: str | None = None

    fallback_level: int = 0
    fallback_reason: str = "none"

    attempts: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "policy": self.policy,
            "required_capabilities": self.required_capabilities,
            "preferred_provider_id": self.preferred_provider_id,
            "preferred_model_id": self.preferred_model_id,
            "commercial_policy": self.commercial_policy,
            "candidate_count": self.candidate_count,
            "rejected_candidates": self.rejected_candidates,
            "selected": {
                "provider_type": self.selected_provider_type,
                "provider_instance_id": self.selected_provider_instance_id,
                "model_id": self.selected_model_id,
            } if self.selected_provider_type else None,
            "fallback_level": self.fallback_level,
            "fallback_reason": self.fallback_reason,
            "attempts": self.attempts,
        }


# ---------------------------------------------------------------------------
# Routing execution metadata — returned in response
# ---------------------------------------------------------------------------

@dataclass
class RoutingExecutionMetadata:
    """Safe execution metadata for response. No credentials."""

    requested_provider_id: str | None = None
    requested_model: str | None = None
    actual_provider_id: str | None = None
    actual_model: str | None = None
    actual_provider_type: str | None = None
    fallback_used: bool = False
    fallback_reason: str = "none"
    fallback_level: int = 0
    candidates_evaluated: int = 0
    routing_trace: RoutingTrace | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "requested_provider_id": self.requested_provider_id,
            "requested_model": self.requested_model,
            "actual_provider_id": self.actual_provider_id,
            "actual_model": self.actual_model,
            "actual_provider_type": self.actual_provider_type,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "fallback_level": self.fallback_level,
            "candidates_evaluated": self.candidates_evaluated,
        }
        if self.routing_trace:
            d["routing_trace"] = self.routing_trace.to_dict()
        return d


# ---------------------------------------------------------------------------
# Capability requirement helper
# ---------------------------------------------------------------------------

# Single source of truth: routing category id → required ModelInfo capability fields.
# Both SmartRouter.ROUTING_CATEGORIES and the API derive from this map.
CATEGORY_CAPABILITIES: dict[str, list[str]] = {
    "general_chat": ["supports_streaming"],
    "coding": ["supports_tools", "supports_function_calling", "supports_reasoning"],
    "vision": ["supports_vision", "supports_streaming"],
    "reasoning": ["supports_reasoning", "supports_thinking"],
    "fallback": [],
    # Additional capability categories (for feature routing / dedup across consumers)
    "chat": [],
    "tool_calling": ["supports_tools", "supports_function_calling"],
    "structured_output": ["supports_json"],
    "streaming": ["supports_streaming"],
    "audio": ["supports_audio"],
}

CAPABILITY_MAP = CATEGORY_CAPABILITIES


def capabilities_for_category(category: str) -> list[str]:
    """Return ModelInfo field names required for a routing category."""
    return list(CATEGORY_CAPABILITIES.get(category, []))


def required_capabilities_from_category(category: str) -> list[str]:
    """Return capability strings from a routing category id."""
    return list(CATEGORY_CAPABILITIES.get(category, []))
