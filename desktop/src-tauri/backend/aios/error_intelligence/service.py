"""Error Intelligence service — capture, classify, persist, query, report.

Persistence: bounded JSON ring at ``~/.eve/errors.json`` (default), mirroring the
providers.json / routing.json pattern. Captures are cheap and never raise.
"""

from __future__ import annotations

import json
import os
import threading
import traceback
from pathlib import Path
from typing import Any, Iterable

from aios.error_intelligence.classifier import classify_error
from aios.error_intelligence.diagnostics import format_report
from aios.error_intelligence.models import (
    Classification,
    ErrorCategory,
    ErrorEvent,
    Severity,
)

_DEFAULT_MAX_EVENTS = 1000
_DEFAULT_MAX_STACK = 4000


class ErrorIntelligenceService:
    def __init__(
        self,
        errors_path: str | Path | None = None,
        max_events: int = _DEFAULT_MAX_EVENTS,
    ):
        self._errors_path = Path(errors_path) if errors_path else Path.home() / ".eve" / "errors.json"
        self._max_events = max_events
        self._lock = threading.Lock()
        self._events: list[ErrorEvent] = []
        self._timeline: list[dict[str, Any]] = []
        self._load()

    # -- persistence --------------------------------------------------------

    def _load(self) -> None:
        try:
            if not self._errors_path.exists():
                return
            with open(self._errors_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            records = data.get("errors", []) if isinstance(data, dict) else data
            events = [ErrorEvent(**r) for r in records if isinstance(r, dict) and "error_id" in r]
            self._events = events[-(self._max_events):]
        except Exception:
            self._events = []

    def _save(self) -> None:
        try:
            self._errors_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"max_events": self._max_events, "errors": [e.to_dict() for e in self._events]}
            tmp = self._errors_path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, default=str)
            os.replace(tmp, self._errors_path)
        except Exception:
            pass

    def _bounded_append(self, event: ErrorEvent) -> None:
        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]

    # -- capture ------------------------------------------------------------

    def capture_event(self, event: ErrorEvent) -> ErrorEvent:
        """Store an already-built event. Never raises."""
        try:
            with self._lock:
                self._bounded_append(event)
                self._timeline.append({
                    "timestamp": event.timestamp,
                    "type": "error",
                    "message": event.message,
                    "error_id": event.error_id,
                    "category": event.category.value,
                    "severity": event.severity.value,
                    "provider": event.provider,
                    "model": event.model,
                    "resolved": event.resolved,
                })
                if len(self._timeline) > self._max_events:
                    self._timeline = self._timeline[-self._max_events:]
                self._save()
        except Exception:
            pass
        return event

    def capture_exception(
        self,
        exc: BaseException,
        *,
        module: str = "unknown",
        conversation_id: str | None = None,
        request_id: str | None = None,
        correlation_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        tool: str | None = None,
        http_status: int | None = None,
        duration: float | None = None,
        message: str | None = None,
        stack_trace: str | None = None,
        classification: Classification | None = None,
    ) -> ErrorEvent | None:
        """Classify and store a captured exception. Never raises."""
        try:
            cls = classification or classify_error(
                exc,
                provider_status=None,
                http_status=http_status,
                module=module,
                message=message or str(exc),
            )
            sanitized = message or str(exc) or cls.likely_cause
            if stack_trace is None:
                stack_trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            event = ErrorEvent(
                error_id=ErrorEvent.new_id(),
                timestamp=ErrorEvent.now_iso(),
                category=cls.category,
                severity=cls.severity,
                message=sanitized,
                module=module,
                root_cause=cls.root_cause,
                likely_cause=cls.likely_cause,
                recovery_suggestions=cls.recovery_suggestions,
                conversation_id=conversation_id,
                request_id=request_id,
                correlation_id=correlation_id,
                provider=provider,
                model=model,
                tool=tool,
                http_status=http_status,
                exception_type=type(exc).__name__,
                stack_trace=(stack_trace or "")[: _DEFAULT_MAX_STACK],
                duration=duration,
                recoverable=cls.recoverable,
                retryable=cls.retryable,
                raw_error=sanitized,
            )
            return self.capture_event(event)
        except Exception:
            return None

    def capture(
        self,
        message: str,
        *,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: Severity = Severity.MEDIUM,
        module: str = "unknown",
        provider: str | None = None,
        model: str | None = None,
        tool: str | None = None,
        http_status: int | None = None,
        conversation_id: str | None = None,
        request_id: str | None = None,
        recoverable: bool = True,
        retryable: bool = False,
        raw_error: str | None = None,
        classification: Classification | None = None,
    ) -> ErrorEvent | None:
        """Capture a plain error (no live exception). Never raises."""
        try:
            cls = classification or Classification(
                category=category,
                severity=severity,
                recoverable=recoverable,
                retryable=retryable,
                user_explanation=message,
                likely_cause=message,
                root_cause=message,
            )
            event = ErrorEvent(
                error_id=ErrorEvent.new_id(),
                timestamp=ErrorEvent.now_iso(),
                category=cls.category,
                severity=cls.severity,
                message=message,
                module=module,
                root_cause=cls.root_cause,
                likely_cause=cls.likely_cause,
                recovery_suggestions=cls.recovery_suggestions,
                conversation_id=conversation_id,
                request_id=request_id,
                provider=provider,
                model=model,
                tool=tool,
                http_status=http_status,
                recoverable=cls.recoverable,
                retryable=cls.retryable,
                raw_error=raw_error or message,
            )
            return self.capture_event(event)
        except Exception:
            return None

    # -- queries ------------------------------------------------------------

    def list_events(
        self,
        limit: int = 100,
        category: str | None = None,
        severity: str | None = None,
        resolved: bool | None = None,
    ) -> list[ErrorEvent]:
        with self._lock:
            events = list(reversed(self._events))
        if category:
            events = [e for e in events if e.category.value == category]
        if severity:
            events = [e for e in events if e.severity.value == severity]
        if resolved is not None:
            events = [e for e in events if e.resolved is resolved]
        return events[: max(limit, 0)]

    def get_event(self, error_id: str) -> ErrorEvent | None:
        with self._lock:
            return next((e for e in reversed(self._events) if e.error_id == error_id), None)

    def timeline(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            return list(reversed(self._timeline))[: max(limit, 0)]

    def recoveries(self, limit: int = 100) -> list[ErrorEvent]:
        with self._lock:
            events = [e for e in reversed(self._events) if e.auto_recovery_attempted]
        return events[: max(limit, 0)]

    def stats(self) -> dict[str, Any]:
        with self._lock:
            events = list(self._events)
        total = len(events)
        by_category: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        by_provider: dict[str, int] = {}
        by_message: dict[str, int] = {}
        auto_attempted = 0
        auto_recovered = 0
        resolved = 0
        for e in events:
            by_category[e.category.value] = by_category.get(e.category.value, 0) + 1
            by_severity[e.severity.value] = by_severity.get(e.severity.value, 0) + 1
            if e.provider:
                by_provider[e.provider] = by_provider.get(e.provider, 0) + 1
            by_message[e.message] = by_message.get(e.message, 0) + 1
            if e.auto_recovery_attempted:
                auto_attempted += 1
                if e.recovery_result == "recovered":
                    auto_recovered += 1
            if e.resolved:
                resolved += 1
        recovery_success_rate = (auto_recovered / auto_attempted * 100.0) if auto_attempted else 0.0
        return {
            "total": total,
            "resolved": resolved,
            "by_category": dict(sorted(by_category.items(), key=lambda kv: -kv[1])),
            "by_severity": dict(sorted(by_severity.items(), key=lambda kv: -kv[1])),
            "top_failing_providers": dict(sorted(by_provider.items(), key=lambda kv: -kv[1])[:10]),
            "most_common_errors": dict(sorted(by_message.items(), key=lambda kv: -kv[1])[:10]),
            "auto_recoveries": {"attempted": auto_attempted, "recovered": auto_recovered},
            "recovery_success_rate": round(recovery_success_rate, 1),
        }

    # -- recovery lifecycle -------------------------------------------------

    def record_recovery_result(self, error_id: str, success: bool, note: str | None = None) -> ErrorEvent | None:
        try:
            with self._lock:
                event = next((e for e in self._events if e.error_id == error_id), None)
                if event is None:
                    return None
                event.auto_recovery_attempted = True
                event.recovery_result = "recovered" if success else "failed"
                event.resolved = success or event.resolved
                self._timeline.append({
                    "timestamp": ErrorEvent.now_iso(),
                    "type": "recovery",
                    "message": note or ("Recovered automatically" if success else "Automatic recovery failed"),
                    "error_id": event.error_id,
                    "category": event.category.value,
                    "severity": event.severity.value,
                    "provider": event.provider,
                    "model": event.model,
                    "resolved": event.resolved,
                })
                if len(self._timeline) > self._max_events:
                    self._timeline = self._timeline[-self._max_events:]
                self._save()
            return event
        except Exception:
            return None

    def clear(self) -> None:
        try:
            with self._lock:
                self._events = []
                self._timeline = []
                self._save()
        except Exception:
            pass

    # -- diagnostics --------------------------------------------------------

    def report(self, error_id: str, fmt: str = "markdown") -> str | None:
        event = self.get_event(error_id)
        if event is None:
            return None
        return format_report(event, fmt=fmt)

    def export_all(self, fmt: str = "json") -> str:
        from aios.error_intelligence.diagnostics import format_events_report
        return format_events_report(self.list_events(limit=self._max_events), fmt=fmt)

    # -- lifecycle ----------------------------------------------------------

    def shutdown(self) -> None:
        with self._lock:
            self._save()


_instance: ErrorIntelligenceService | None = None


def configure_error_intelligence(**kwargs: Any) -> ErrorIntelligenceService:
    """Configure and cache the process-wide error intelligence service."""
    global _instance
    _instance = ErrorIntelligenceService(**kwargs)
    return _instance


def get_error_intelligence() -> ErrorIntelligenceService:
    """Process-wide error intelligence service (lazy singleton)."""
    global _instance
    if _instance is None:
        _instance = ErrorIntelligenceService()
    return _instance
