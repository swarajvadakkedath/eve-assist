"""AI Error Intelligence — centralized capture, classification, recovery, diagnostics.

Public surface:
    ErrorCategory, Severity, AutoRecoveryStrategy, Classification, ErrorEvent
    classify_error()
    ErrorIntelligenceService
    get_error_intelligence(), configure_error_intelligence()
    RecoveryEngine, RecoveryResult
"""

from __future__ import annotations

from aios.error_intelligence.models import (
    AutoRecoveryStrategy,
    Classification,
    ErrorCategory,
    ErrorEvent,
    Severity,
)
from aios.error_intelligence.classifier import classify_error
from aios.error_intelligence.service import (
    ErrorIntelligenceService,
    configure_error_intelligence,
    get_error_intelligence,
)
from aios.error_intelligence.diagnostics import format_report
from aios.error_intelligence.events import error_to_stream_event, publish_to_event_bus
from aios.error_intelligence.recovery_engine import RecoveryEngine, RecoveryResult

__all__ = [
    "ErrorCategory",
    "Severity",
    "AutoRecoveryStrategy",
    "Classification",
    "ErrorEvent",
    "classify_error",
    "ErrorIntelligenceService",
    "configure_error_intelligence",
    "get_error_intelligence",
    "format_report",
    "error_to_stream_event",
    "publish_to_event_bus",
    "RecoveryEngine",
    "RecoveryResult",
]
