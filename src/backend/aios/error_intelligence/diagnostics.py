"""Diagnostics formatting — Markdown / JSON / plain-text reports.

The rendered reports are the payload behind the "Copy diagnostics" action in
the Recovery Center, so they must be self-contained and human-readable.
"""

from __future__ import annotations

import json
from typing import Any

from aios.error_intelligence.models import ErrorEvent


def format_report(event: ErrorEvent, fmt: str = "markdown") -> str:
    if fmt == "json":
        return json.dumps(event.to_dict(), indent=2, default=str)
    if fmt == "plain":
        return _format_plain(event)
    return _format_markdown(event)


def format_events_report(events: list[ErrorEvent], fmt: str = "json") -> str:
    if fmt == "markdown":
        sections = [_format_markdown(e) for e in events]
        return "\n\n---\n\n".join(sections) if sections else "# Error Intelligence\n\n_No errors recorded._"
    if fmt == "plain":
        return "\n\n".join(_format_plain(e) for e in events) or "No errors recorded."
    return json.dumps([e.to_dict() for e in events], indent=2, default=str)


def _format_markdown(event: ErrorEvent) -> str:
    lines: list[str] = [
        "# Error Diagnostic",
        "",
        f"- **Error ID**: `{event.error_id}`",
        f"- **Timestamp**: {event.timestamp}",
        f"- **Category**: {event.category.value}",
        f"- **Severity**: {event.severity.value}",
        f"- **Module**: {event.module}",
        f"- **Message**: {event.message}",
    ]
    for label, value in (
        ("Provider", event.provider),
        ("Model", event.model),
        ("Tool", event.tool),
        ("HTTP Status", event.http_status),
        ("Exception", event.exception_type),
        ("Duration (ms)", event.duration),
        ("Conversation", event.conversation_id),
        ("Request", event.request_id),
        ("Correlation", event.correlation_id),
    ):
        if value is not None:
            lines.append(f"- **{label}**: {value}")
    lines += [
        "",
        "## Likely Cause",
        "",
        event.likely_cause or "Unknown",
        "",
        "## Root Cause",
        "",
        event.root_cause or "Unknown",
        "",
        "## What EVE can do",
        "",
    ]
    lines += [f"- {s}" for s in event.recovery_suggestions] or ["- Retry the request"]
    if event.auto_recovery_attempted:
        lines += [
            "",
            "## Auto Recovery",
            "",
            f"- **Attempted**: yes",
            f"- **Result**: {event.recovery_result or 'unknown'}",
        ]
    if event.stack_trace:
        lines += [
            "",
            "## Technical Details",
            "",
            "```",
            event.stack_trace.rstrip(),
            "```",
        ]
    return "\n".join(lines)


def _format_plain(event: ErrorEvent) -> str:
    lines = [
        f"Error ID: {event.error_id}",
        f"Timestamp: {event.timestamp}",
        f"Category: {event.category.value}",
        f"Severity: {event.severity.value}",
        f"Module: {event.module}",
        f"Message: {event.message}",
    ]
    for label, value in (
        ("Provider", event.provider),
        ("Model", event.model),
        ("Tool", event.tool),
        ("HTTP Status", event.http_status),
        ("Exception", event.exception_type),
        ("Duration (ms)", event.duration),
    ):
        if value is not None:
            lines.append(f"{label}: {value}")
    lines += [
        "",
        f"Likely Cause: {event.likely_cause or 'Unknown'}",
        f"Root Cause: {event.root_cause or 'Unknown'}",
        "",
        "Suggested actions:",
    ]
    lines += [f"- {s}" for s in event.recovery_suggestions] or ["- Retry the request"]
    if event.stack_trace:
        lines += ["", "--- Technical Details ---", event.stack_trace.rstrip()]
    return "\n".join(lines)


def to_dict(event: ErrorEvent) -> dict[str, Any]:
    return event.to_dict()
