"""Error Intelligence domain models — categories, severities, classifications, events.

This module is pure data (no I/O, no framework imports) so the classifier and
service can be tested in isolation and mirrored byte-identically to the desktop
bundle.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Error categories — the 21-category taxonomy
# ---------------------------------------------------------------------------

class ErrorCategory(str, Enum):
    PROVIDER = "PROVIDER"
    ROUTING = "ROUTING"
    NETWORK = "NETWORK"
    VOICE = "VOICE"
    VISION = "VISION"
    MEMORY = "MEMORY"
    WORKSPACE = "WORKSPACE"
    FILE_SEARCH = "FILE_SEARCH"
    OCR = "OCR"
    PLUGIN = "PLUGIN"
    TOOL_EXECUTION = "TOOL_EXECUTION"
    DATABASE = "DATABASE"
    AUTHENTICATION = "AUTHENTICATION"
    PERMISSION = "PERMISSION"
    CONFIGURATION = "CONFIGURATION"
    API = "API"
    TIMEOUT = "TIMEOUT"
    STREAMING = "STREAMING"
    RATE_LIMIT = "RATE_LIMIT"
    INTERNAL_BUG = "INTERNAL_BUG"
    UNKNOWN = "UNKNOWN"


class Severity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AutoRecoveryStrategy(str, Enum):
    """Safe auto-recovery strategy selected by the classifier.

    Only strategies that are provably side-effect-free are performed
    automatically (safe-auto): RETRY, SWITCH_PROVIDER, REFRESH_MODELS and
    COOLDOWN never mutate user data or repeat irreversible actions.
    """

    NONE = "none"
    RETRY = "retry"                       # retry the request once
    SWITCH_PROVIDER = "switch_provider"   # fail over to another healthy provider
    REFRESH_MODELS = "refresh_models"     # 404 → refresh the model catalog
    COOLDOWN = "cooldown"                 # 429/quota → per-model cooldown + switch
    RETRY_OR_SWITCH = "retry_or_switch"   # timeout → retry once, then switch
    SUGGEST_ONLY = "suggest_only"         # permission/ambiguous → suggestions only


# ---------------------------------------------------------------------------
# Classification — human + technical understanding of a single failure
# ---------------------------------------------------------------------------

@dataclass
class Classification:
    category: ErrorCategory
    severity: Severity
    recoverable: bool
    retryable: bool
    user_explanation: str
    likely_cause: str
    root_cause: str
    recovery_suggestions: list[str] = field(default_factory=list)
    auto_recovery_strategy: AutoRecoveryStrategy = AutoRecoveryStrategy.NONE

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "recoverable": self.recoverable,
            "retryable": self.retryable,
            "user_explanation": self.user_explanation,
            "likely_cause": self.likely_cause,
            "root_cause": self.root_cause,
            "recovery_suggestions": list(self.recovery_suggestions),
            "auto_recovery_strategy": self.auto_recovery_strategy.value,
        }


# ---------------------------------------------------------------------------
# ErrorEvent — one captured failure
# ---------------------------------------------------------------------------

@dataclass
class ErrorEvent:
    error_id: str
    timestamp: str
    category: ErrorCategory
    severity: Severity
    message: str
    module: str
    root_cause: str = ""
    likely_cause: str = ""
    recovery_suggestions: list[str] = field(default_factory=list)
    auto_recovery_attempted: bool = False
    recovery_result: str | None = None
    conversation_id: str | None = None
    request_id: str | None = None
    correlation_id: str | None = None
    provider: str | None = None
    model: str | None = None
    tool: str | None = None
    http_status: int | None = None
    exception_type: str | None = None
    stack_trace: str | None = None
    duration: float | None = None
    recoverable: bool = True
    retryable: bool = False
    retry_after: float | None = None
    raw_error: str = ""
    resolved: bool = False

    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_id": self.error_id,
            "timestamp": self.timestamp,
            "category": self.category.value,
            "severity": self.severity.value,
            "module": self.module,
            "message": self.message,
            "root_cause": self.root_cause,
            "likely_cause": self.likely_cause,
            "recovery_suggestions": list(self.recovery_suggestions),
            "auto_recovery_attempted": self.auto_recovery_attempted,
            "recovery_result": self.recovery_result,
            "conversation_id": self.conversation_id,
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "provider": self.provider,
            "model": self.model,
            "tool": self.tool,
            "http_status": self.http_status,
            "exception_type": self.exception_type,
            "stack_trace": self.stack_trace,
            "duration": self.duration,
            "recoverable": self.recoverable,
            "retryable": self.retryable,
            "retry_after": self.retry_after,
            "raw_error": self.raw_error,
            "resolved": self.resolved,
        }
