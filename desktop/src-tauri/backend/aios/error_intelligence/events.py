"""Error Intelligence event adapters.

Converts ErrorEvent objects into:
  * stream events compatible with the existing ``error`` SSE event shape
    (backward compatible with ``create_error_event``), enriched with the
    structured intelligence fields;
  * optional EventBus notifications for the in-process bus.
"""

from __future__ import annotations

from typing import Any

from aios.error_intelligence.models import ErrorEvent


def error_to_stream_event(event: ErrorEvent) -> dict[str, Any]:
    """Build an ``error`` stream event enriched with Error Intelligence data.

    The base shape matches ``create_error_event(error, recoverable)`` so the
    frontend's existing error handling keeps working; extra structured fields
    feed the rich ErrorCard / Recovery Center.
    """
    data: dict[str, Any] = {
        "error": event.message,
        "recoverable": event.recoverable,
    }
    for key in (
        "error_id",
        "timestamp",
        "category",
        "severity",
        "module",
        "provider",
        "model",
        "tool",
        "http_status",
        "exception_type",
    ):
        value = getattr(event, key, None)
        if isinstance(value, object) and hasattr(value, "value"):
            value = value.value
        if value is not None:
            data[key] = value
    if event.likely_cause:
        data["likely_cause"] = event.likely_cause
    if event.root_cause:
        data["root_cause"] = event.root_cause
    if event.recovery_suggestions:
        data["recovery_suggestions"] = list(event.recovery_suggestions)
    return {"type": "error", "data": data}


async def publish_to_event_bus(event_bus: Any, event: ErrorEvent) -> str | None:
    """Publish an Error Intelligence notification to the process EventBus."""
    if event_bus is None:
        return None
    try:
        event_id = await event_bus.publish(
            event_type="error_intelligence",
            payload=event.to_dict(),
            source=event.module,
            correlation_id=event.correlation_id or event.request_id or event.error_id,
        )
        return event_id
    except Exception:
        return None
