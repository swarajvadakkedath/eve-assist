"""Rules-driven error classifier.

Maps exceptions, provider health statuses, HTTP status codes and module tags
onto the 21-category taxonomy plus a human/technical understanding and a safe
auto-recovery strategy. Deterministic and side-effect free so it can be unit
tested exhaustively.
"""

from __future__ import annotations

import re
from typing import Any

from aios.core.adapters.base import ProviderStatus
from aios.core.routing_types import (
    NoEligibleRouteError,
    PaidRoutingDisabledError,
    RouteAuthError,
    RouteError,
    RouteQuotaExhaustedError,
    RouteRateLimitedError,
)
from aios.conversation.exceptions import (
    AIProviderError,
    ConversationError,
    MemoryError,
    PlannerError,
    StreamError,
    ToolExecutionError,
)
from aios.core.timeout_retry import ProviderTimeoutError

from aios.error_intelligence.models import (
    AutoRecoveryStrategy,
    Classification,
    ErrorCategory,
    Severity,
)


# ---------------------------------------------------------------------------
# Rule tables
# ---------------------------------------------------------------------------

_ROUTE_ERROR_RULES: dict[str, tuple[ErrorCategory, Severity, bool, bool, str, str, AutoRecoveryStrategy]] = {
    "ROUTE_UNAVAILABLE": (
        ErrorCategory.ROUTING, Severity.HIGH, True, True,
        "The chosen route is unavailable.",
        "The provider or model went offline or was disabled.",
        AutoRecoveryStrategy.SWITCH_PROVIDER,
    ),
    "ROUTE_QUOTA_EXHAUSTED": (
        ErrorCategory.RATE_LIMIT, Severity.HIGH, True, True,
        "This provider has run out of quota.",
        "The provider's free quota is exhausted for now.",
        AutoRecoveryStrategy.COOLDOWN,
    ),
    "ROUTE_RATE_LIMITED": (
        ErrorCategory.RATE_LIMIT, Severity.MEDIUM, True, True,
        "This provider is rate-limiting requests.",
        "Too many requests were sent to the provider.",
        AutoRecoveryStrategy.COOLDOWN,
    ),
    "ROUTE_AUTH_ERROR": (
        ErrorCategory.AUTHENTICATION, Severity.HIGH, False, False,
        "The provider rejected our credentials.",
        "The API key may be invalid, expired, or missing.",
        AutoRecoveryStrategy.SUGGEST_ONLY,
    ),
    "ROUTE_CAPABILITY_ERROR": (
        ErrorCategory.ROUTING, Severity.MEDIUM, True, False,
        "The selected model can't do what was asked.",
        "The model lacks a required capability (tools, vision, ...).",
        AutoRecoveryStrategy.SWITCH_PROVIDER,
    ),
    "NO_ELIGIBLE_ROUTE": (
        ErrorCategory.ROUTING, Severity.MEDIUM, True, False,
        "No AI provider could be selected.",
        "No configured provider meets the request's requirements.",
        AutoRecoveryStrategy.SUGGEST_ONLY,
    ),
    "PAID_ROUTING_DISABLED": (
        ErrorCategory.CONFIGURATION, Severity.LOW, True, False,
        "Only free models are enabled.",
        "The request needs a paid model but free-only routing is active.",
        AutoRecoveryStrategy.SUGGEST_ONLY,
    ),
}

_PROVIDER_STATUS_RULES: dict[ProviderStatus, tuple[ErrorCategory, Severity, bool, bool, str, str, AutoRecoveryStrategy]] = {
    ProviderStatus.TIMEOUT: (
        ErrorCategory.TIMEOUT, Severity.HIGH, True, True,
        "The AI provider took too long to respond.",
        "The provider did not answer within the timeout window.",
        AutoRecoveryStrategy.RETRY_OR_SWITCH,
    ),
    ProviderStatus.AUTH_FAILED: (
        ErrorCategory.AUTHENTICATION, Severity.HIGH, False, False,
        "The provider rejected our credentials.",
        "The API key may be invalid, expired, or missing.",
        AutoRecoveryStrategy.SUGGEST_ONLY,
    ),
    ProviderStatus.INVALID_KEY: (
        ErrorCategory.AUTHENTICATION, Severity.HIGH, False, False,
        "The provider rejected our API key.",
        "The configured API key is invalid or missing.",
        AutoRecoveryStrategy.SUGGEST_ONLY,
    ),
    ProviderStatus.RATE_LIMITED: (
        ErrorCategory.RATE_LIMIT, Severity.MEDIUM, True, True,
        "This provider is rate-limiting requests.",
        "Too many requests were sent to the provider.",
        AutoRecoveryStrategy.COOLDOWN,
    ),
    ProviderStatus.QUOTA_EXCEEDED: (
        ErrorCategory.RATE_LIMIT, Severity.HIGH, True, True,
        "This provider has run out of quota.",
        "The provider's quota is exhausted for now.",
        AutoRecoveryStrategy.COOLDOWN,
    ),
    ProviderStatus.OFFLINE: (
        ErrorCategory.NETWORK, Severity.HIGH, True, True,
        "The AI provider is unreachable.",
        "The provider's servers could not be reached.",
        AutoRecoveryStrategy.SWITCH_PROVIDER,
    ),
    ProviderStatus.DISCONNECTED: (
        ErrorCategory.NETWORK, Severity.HIGH, True, True,
        "The AI provider disconnected.",
        "The connection to the provider was interrupted.",
        AutoRecoveryStrategy.SWITCH_PROVIDER,
    ),
    ProviderStatus.ERROR: (
        ErrorCategory.PROVIDER, Severity.MEDIUM, True, True,
        "The AI provider failed.",
        "The provider returned an error response.",
        AutoRecoveryStrategy.RETRY,
    ),
}

_HTTP_STATUS_RULES: dict[int, tuple[ErrorCategory, Severity, bool, bool, str, str, AutoRecoveryStrategy]] = {
    400: (
        ErrorCategory.PROVIDER, Severity.MEDIUM, False, False,
        "The provider rejected the request.",
        "The request was malformed or unsupported by the model.",
        AutoRecoveryStrategy.SUGGEST_ONLY,
    ),
    401: (
        ErrorCategory.AUTHENTICATION, Severity.HIGH, False, False,
        "The provider rejected our credentials.",
        "The API key may be invalid, expired, or missing.",
        AutoRecoveryStrategy.SUGGEST_ONLY,
    ),
    403: (
        ErrorCategory.AUTHENTICATION, Severity.HIGH, False, False,
        "The provider denied access.",
        "The API key lacks permission for this model.",
        AutoRecoveryStrategy.SUGGEST_ONLY,
    ),
    404: (
        ErrorCategory.PROVIDER, Severity.MEDIUM, True, True,
        "The requested model wasn't found.",
        "The provider no longer serves this model ID.",
        AutoRecoveryStrategy.REFRESH_MODELS,
    ),
    408: (
        ErrorCategory.TIMEOUT, Severity.HIGH, True, True,
        "The provider took too long to respond.",
        "The request timed out at the provider.",
        AutoRecoveryStrategy.RETRY_OR_SWITCH,
    ),
    429: (
        ErrorCategory.RATE_LIMIT, Severity.MEDIUM, True, True,
        "This provider is rate-limiting requests.",
        "Too many requests were sent to the provider.",
        AutoRecoveryStrategy.COOLDOWN,
    ),
    500: (
        ErrorCategory.PROVIDER, Severity.HIGH, True, True,
        "The provider hit an internal error.",
        "The provider's servers returned a 5xx error.",
        AutoRecoveryStrategy.RETRY,
    ),
    502: (
        ErrorCategory.PROVIDER, Severity.HIGH, True, True,
        "The provider is temporarily unavailable.",
        "An upstream gateway returned a 502 error.",
        AutoRecoveryStrategy.RETRY_OR_SWITCH,
    ),
    503: (
        ErrorCategory.PROVIDER, Severity.HIGH, True, True,
        "The provider is temporarily unavailable.",
        "The provider's servers are busy or down.",
        AutoRecoveryStrategy.RETRY_OR_SWITCH,
    ),
    504: (
        ErrorCategory.TIMEOUT, Severity.HIGH, True, True,
        "The provider's gateway timed out.",
        "An upstream gateway did not respond in time.",
        AutoRecoveryStrategy.RETRY_OR_SWITCH,
    ),
}

_MODULE_HINTS: list[tuple[re.Pattern[str], ErrorCategory]] = [
    (re.compile(r"(^|\.)voice", re.IGNORECASE), ErrorCategory.VOICE),
    (re.compile(r"(^|\.)vision", re.IGNORECASE), ErrorCategory.VISION),
    (re.compile(r"(^|\.)ocr", re.IGNORECASE), ErrorCategory.OCR),
    (re.compile(r"(^|\.)memory", re.IGNORECASE), ErrorCategory.MEMORY),
    (re.compile(r"(^|\.)workspace", re.IGNORECASE), ErrorCategory.WORKSPACE),
    (re.compile(r"file.?search", re.IGNORECASE), ErrorCategory.FILE_SEARCH),
    (re.compile(r"(^|\.)plugin", re.IGNORECASE), ErrorCategory.PLUGIN),
    (re.compile(r"(^|\.)database|\.db\.", re.IGNORECASE), ErrorCategory.DATABASE),
    (re.compile(r"permission", re.IGNORECASE), ErrorCategory.PERMISSION),
    (re.compile(r"config", re.IGNORECASE), ErrorCategory.CONFIGURATION),
    (re.compile(r"tool", re.IGNORECASE), ErrorCategory.TOOL_EXECUTION),
]

_SUGGEST_RETRY = "Retry the request"
_SUGGEST_SWITCH = "Switch to another healthy provider"
_SUGGEST_REFRESH = "Refresh the model list"
_SUGGEST_CHECK_KEY = "Check your API key in Provider Settings"
_SUGGEST_COOLDOWN = "Wait a moment and try again"
_SUGGEST_ENABLE_PROVIDER = "Enable a provider or add more models"


def _suggestions_for(strategy: AutoRecoveryStrategy, category: ErrorCategory) -> list[str]:
    suggestions: list[str] = []
    if strategy in (AutoRecoveryStrategy.RETRY, AutoRecoveryStrategy.RETRY_OR_SWITCH):
        suggestions.append(_SUGGEST_RETRY)
    if strategy in (AutoRecoveryStrategy.SWITCH_PROVIDER, AutoRecoveryStrategy.RETRY_OR_SWITCH):
        suggestions.append(_SUGGEST_SWITCH)
    if strategy == AutoRecoveryStrategy.REFRESH_MODELS:
        suggestions.append(_SUGGEST_REFRESH)
        suggestions.append(_SUGGEST_SWITCH)
    if strategy == AutoRecoveryStrategy.COOLDOWN:
        suggestions.append(_SUGGEST_COOLDOWN)
        suggestions.append(_SUGGEST_SWITCH)
    if strategy == AutoRecoveryStrategy.SUGGEST_ONLY:
        if category == ErrorCategory.AUTHENTICATION:
            suggestions.append(_SUGGEST_CHECK_KEY)
        elif category == ErrorCategory.ROUTING:
            suggestions.append(_SUGGEST_ENABLE_PROVIDER)
        elif category == ErrorCategory.PERMISSION:
            suggestions.append("Review the permission that was requested")
        elif category == ErrorCategory.CONFIGURATION:
            suggestions.append("Adjust the relevant setting and try again")
        else:
            suggestions.append(_SUGGEST_RETRY)
    if not suggestions:
        suggestions.append(_SUGGEST_RETRY)
    return suggestions


def _rule_from_tuple(
    rule: tuple[ErrorCategory, Severity, bool, bool, str, str, AutoRecoveryStrategy],
) -> Classification:
    category, severity, recoverable, retryable, user_explanation, likely_cause, strategy = rule
    return Classification(
        category=category,
        severity=severity,
        recoverable=recoverable,
        retryable=retryable,
        user_explanation=user_explanation,
        likely_cause=likely_cause,
        root_cause=likely_cause,
        recovery_suggestions=_suggestions_for(strategy, category),
        auto_recovery_strategy=strategy,
    )


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

def classify_error(
    exc: BaseException | str | None = None,
    *,
    error_type: str | None = None,
    provider_status: ProviderStatus | str | None = None,
    http_status: int | None = None,
    module: str | None = None,
    message: str | None = None,
) -> Classification:
    """Classify a failure into a Classification.

    Priority: typed routing error → provider health status → known exception
    type → HTTP status → module heuristic → UNKNOWN.
    """
    # 1) Typed routing errors carry the most signal.
    if isinstance(exc, RouteError) or error_type:
        rtype = error_type or exc.error_type  # type: ignore[union-attr]
        if rtype in _ROUTE_ERROR_RULES:
            rule = _ROUTE_ERROR_RULES[rtype]
            classification = _rule_from_tuple(rule)
            return _apply_route_metadata(classification, exc, rtype)

    status = _coerce_provider_status(provider_status)

    # 2) Provider health status rules.
    if status in _PROVIDER_STATUS_RULES:
        return _rule_from_tuple(_PROVIDER_STATUS_RULES[status])

    # 3) Known exception types.
    exc_rule = _rule_for_exception(exc)
    if exc_rule is not None:
        classification = _rule_from_tuple(exc_rule)
        if isinstance(exc, BaseException) and str(exc):
            classification.root_cause = str(exc)
        return classification

    # 4) Message heuristics — for captures that only carry sanitized text.
    msg_hint = _message_hint(message or (str(exc) if isinstance(exc, BaseException) else exc or ""))
    if msg_hint is not None:
        classification = _rule_from_tuple(msg_hint)
        if str(exc):
            classification.root_cause = str(exc)
        return classification

    # 5) HTTP status.
    if http_status in _HTTP_STATUS_RULES:
        return _rule_from_tuple(_HTTP_STATUS_RULES[http_status])

    # 6) Module heuristic (only when nothing stronger matched).
    if module:
        for pattern, category in _MODULE_HINTS:
            if pattern.search(module):
                return Classification(
                    category=category,
                    severity=Severity.MEDIUM,
                    recoverable=True,
                    retryable=False,
                    user_explanation=f"Something failed in the {category.value.lower().replace('_', ' ')} subsystem.",
                    likely_cause=f"An unexpected error occurred in {module}.",
                    root_cause=str(exc) if exc else message or "Unknown module-level failure",
                    recovery_suggestions=[_SUGGEST_RETRY],
                    auto_recovery_strategy=AutoRecoveryStrategy.NONE,
                )

    # 7) Fallback.
    return Classification(
        category=ErrorCategory.UNKNOWN,
        severity=Severity.MEDIUM,
        recoverable=True,
        retryable=False,
        user_explanation="Something went wrong.",
        likely_cause="EVE could not determine the exact cause.",
        root_cause=str(exc) if exc else message or "Unknown error",
        recovery_suggestions=[_SUGGEST_RETRY],
        auto_recovery_strategy=AutoRecoveryStrategy.NONE,
    )


_MESSAGE_HINTS: list[tuple[re.Pattern[str], tuple[ErrorCategory, Severity, bool, bool, str, str, AutoRecoveryStrategy]]] = [
    (re.compile(r"empty response|empty stream", re.IGNORECASE), (
        ErrorCategory.PROVIDER, Severity.MEDIUM, True, True,
        "The AI provider returned nothing.",
        "The provider produced an empty response.",
        AutoRecoveryStrategy.RETRY,
    )),
    (re.compile(r"timed?\s?out|timeout", re.IGNORECASE), (
        ErrorCategory.TIMEOUT, Severity.HIGH, True, True,
        "The operation timed out.",
        "The provider did not respond in time.",
        AutoRecoveryStrategy.RETRY_OR_SWITCH,
    )),
    (re.compile(r"\b429\b|rate\s?limit|too many requests", re.IGNORECASE), (
        ErrorCategory.RATE_LIMIT, Severity.MEDIUM, True, True,
        "This provider is rate-limiting requests.",
        "Too many requests were sent to the provider.",
        AutoRecoveryStrategy.COOLDOWN,
    )),
    (re.compile(r"quota", re.IGNORECASE), (
        ErrorCategory.RATE_LIMIT, Severity.HIGH, True, True,
        "This provider has run out of quota.",
        "The provider's quota is exhausted for now.",
        AutoRecoveryStrategy.COOLDOWN,
    )),
    (re.compile(r"\b401\b|unauthorized|invalid.{0,3}key|api key", re.IGNORECASE), (
        ErrorCategory.AUTHENTICATION, Severity.HIGH, False, False,
        "The provider rejected our credentials.",
        "The API key may be invalid, expired, or missing.",
        AutoRecoveryStrategy.SUGGEST_ONLY,
    )),
    (re.compile(r"\b404\b|not found", re.IGNORECASE), (
        ErrorCategory.PROVIDER, Severity.MEDIUM, True, True,
        "The requested model wasn't found.",
        "The provider no longer serves this model ID.",
        AutoRecoveryStrategy.REFRESH_MODELS,
    )),
    (re.compile(r"connection|connect error|refused|unreachable", re.IGNORECASE), (
        ErrorCategory.NETWORK, Severity.HIGH, True, True,
        "A network error occurred.",
        "EVE could not reach the provider or the network.",
        AutoRecoveryStrategy.SWITCH_PROVIDER,
    )),
]


def _message_hint(text: str) -> tuple[ErrorCategory, Severity, bool, bool, str, str, AutoRecoveryStrategy] | None:
    if not text:
        return None
    for pattern, rule in _MESSAGE_HINTS:
        if pattern.search(text):
            return rule
    return None


def _coerce_provider_status(status: ProviderStatus | str | None) -> ProviderStatus | None:
    if status is None:
        return None
    if isinstance(status, ProviderStatus):
        return status
    try:
        return ProviderStatus(status)
    except ValueError:
        return None


def _rule_for_exception(exc: BaseException | str | None) -> tuple[ErrorCategory, Severity, bool, bool, str, str, AutoRecoveryStrategy] | None:
    if exc is None:
        return None
    exc_type = exc if isinstance(exc, type) else type(exc)

    if issubclass(exc_type, ToolExecutionError):
        return (
            ErrorCategory.TOOL_EXECUTION, Severity.MEDIUM, True, False,
            "A tool failed while executing.",
            "The requested tool returned an error.",
            AutoRecoveryStrategy.SUGGEST_ONLY,
        )
    if issubclass(exc_type, (MemoryError,)):
        return (
            ErrorCategory.MEMORY, Severity.MEDIUM, True, False,
            "A memory operation failed.",
            "EVE's memory system hit an error.",
            AutoRecoveryStrategy.SUGGEST_ONLY,
        )
    if issubclass(exc_type, PlannerError):
        return (
            ErrorCategory.INTERNAL_BUG, Severity.MEDIUM, False, False,
            "Planning failed internally.",
            "The task planner hit an internal error.",
            AutoRecoveryStrategy.SUGGEST_ONLY,
        )
    if issubclass(exc_type, StreamError):
        return (
            ErrorCategory.STREAMING, Severity.HIGH, True, True,
            "The AI response stream failed.",
            "The streamed response was interrupted.",
            AutoRecoveryStrategy.RETRY,
        )
    if issubclass(exc_type, AIProviderError):
        return (
            ErrorCategory.PROVIDER, Severity.HIGH, True, True,
            "The AI provider failed.",
            "The provider returned an error.",
            AutoRecoveryStrategy.RETRY,
        )
    if issubclass(exc_type, ProviderTimeoutError):
        return (
            ErrorCategory.TIMEOUT, Severity.HIGH, True, True,
            "The AI provider took too long to respond.",
            "The provider did not answer within the timeout window.",
            AutoRecoveryStrategy.RETRY_OR_SWITCH,
        )
    if issubclass(exc_type, TimeoutError):
        return (
            ErrorCategory.TIMEOUT, Severity.HIGH, True, True,
            "The operation timed out.",
            "The operation exceeded its allowed time.",
            AutoRecoveryStrategy.RETRY,
        )
    if issubclass(exc_type, ConnectionError):
        return (
            ErrorCategory.NETWORK, Severity.HIGH, True, True,
            "A network error occurred.",
            "EVE could not reach the network or the provider.",
            AutoRecoveryStrategy.SWITCH_PROVIDER,
        )
    if issubclass(exc_type, PermissionError):
        return (
            ErrorCategory.PERMISSION, Severity.MEDIUM, False, False,
            "A permission was denied.",
            "The operation requires a permission that is not granted.",
            AutoRecoveryStrategy.SUGGEST_ONLY,
        )
    if issubclass(exc_type, (KeyError, ValueError, TypeError)):
        return (
            ErrorCategory.INTERNAL_BUG, Severity.LOW, False, False,
            "An internal error occurred.",
            "EVE hit an unexpected internal condition.",
            AutoRecoveryStrategy.SUGGEST_ONLY,
        )
    return None


def _apply_route_metadata(classification: Classification, exc: BaseException | None, error_type: str) -> Classification:
    """Attach route metadata (provider/model) to the classification's root cause."""
    if not isinstance(exc, RouteError):
        return classification
    bits: list[str] = []
    if exc.provider_instance_id:
        bits.append(f"provider={exc.provider_instance_id}")
    if exc.model_id:
        bits.append(f"model={exc.model_id}")
    if bits:
        classification.root_cause = f"{classification.root_cause} ({', '.join(bits)})"
    if exc.reason:
        classification.likely_cause = f"{classification.likely_cause} {exc.reason}"
    return classification
