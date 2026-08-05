"""Hermes Events — forwards Hermes lifecycle events to the AI Operations Center.

Hermes emits internal events (reasoning started, plan created, tool called, etc.).
This module captures them and republishes as EVE events for the AI Operations Center,
stripping any Hermes identity before they reach the user.

Event flow:
  Hermes Agent → HermesEventsBridge → EventBus → AI Operations Center API → Frontend
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from aios.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Hermes event types (internal — never exposed to user with "Hermes" in name)
# ---------------------------------------------------------------------------

class HermesEventType(str, Enum):
    """Internal Hermes event types — displayed as "EVE" events in the UI."""
    REASONING_STARTED = "reasoning_started"
    REASONING_COMPLETED = "reasoning_completed"
    PLAN_CREATED = "plan_created"
    PLAN_STEP_STARTED = "plan_step_started"
    PLAN_STEP_COMPLETED = "plan_step_completed"
    TOOL_REQUESTED = "tool_requested"
    TOOL_COMPLETED = "tool_completed"
    SKILL_LOADED = "skill_loaded"
    SUBAGENT_SPAWNED = "subagent_spawned"
    SUBAGENT_COMPLETED = "subagent_completed"
    ERROR = "error"
    STATUS_CHANGED = "status_changed"


# Display names — always "EVE", never "Hermes"
_EVENT_DISPLAY_NAMES: dict[str, str] = {
    HermesEventType.REASONING_STARTED: "EVE reasoning started",
    HermesEventType.REASONING_COMPLETED: "EVE reasoning completed",
    HermesEventType.PLAN_CREATED: "EVE created a plan",
    HermesEventType.PLAN_STEP_STARTED: "EVE started plan step",
    HermesEventType.PLAN_STEP_COMPLETED: "EVE completed plan step",
    HermesEventType.TOOL_REQUESTED: "EVE requested tool",
    HermesEventType.TOOL_COMPLETED: "EVE completed tool execution",
    HermesEventType.SKILL_LOADED: "EVE loaded skill",
    HermesEventType.SUBAGENT_SPAWNED: "EVE delegated to sub-task",
    HermesEventType.SUBAGENT_COMPLETED: "EVE sub-task completed",
    HermesEventType.ERROR: "EVE encountered an error",
    HermesEventType.STATUS_CHANGED: "EVE status changed",
}


@dataclass
class HermesEvent:
    """Internal Hermes event before identity sanitisation."""
    event_type: HermesEventType
    data: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: str = field(default_factory=lambda: uuid4().hex)
    source: str = "hermes"


@dataclass
class SanitisedEvent:
    """EVE event ready for the AI Operations Center."""
    event_type: str
    display_name: str
    data: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: str = ""
    source: str = "eve"
    severity: str = "info"


# ---------------------------------------------------------------------------
# Identity sanitisation
# ---------------------------------------------------------------------------

_HERMES_PATTERNS = [
    (r"\bhermes\b", "EVE"),
    (r"\bnous\s*research\b", "EVE AI"),
    (r"\bhermes[-_]agent\b", "eve-ai"),
]


def _sanitise_dict(d: dict) -> dict:
    """Recursively sanitise all string values in a dict."""
    import re
    result = {}
    for key, value in d.items():
        if isinstance(value, str):
            for pattern, replacement in _HERMES_PATTERNS:
                value = re.sub(pattern, replacement, value, flags=re.IGNORECASE)
            result[key] = value
        elif isinstance(value, dict):
            result[key] = _sanitise_dict(value)
        elif isinstance(value, list):
            result[key] = [
                _sanitise_dict(item) if isinstance(item, dict) else
                re.sub(r"\bhermes\b", "EVE", str(item), flags=re.IGNORECASE)
                if isinstance(item, str) else item
                for item in value
            ]
        else:
            result[key] = value
    return result


# ---------------------------------------------------------------------------
# HermesEventsBridge
# ---------------------------------------------------------------------------

class HermesEventsBridge:
    """Captures Hermes lifecycle events and republishes them as EVE events.

    The bridge:
      1. Receives raw Hermes events
      2. Sanitises identity (Hermes → EVE)
      3. Maps to user-friendly display names
      4. Publishes to EVE's EventBus for AI Operations Center
      5. Maintains a bounded ring of recent events for API queries
    """

    def __init__(self, event_bus: Any | None = None, max_events: int = 500):
        self._event_bus = event_bus
        self._max_events = max_events
        self._events: list[SanitisedEvent] = []
        self._subscribers: list[Any] = []

    # ── Event ingestion ────────────────────────────────────────────

    async def on_hermes_event(self, event: HermesEvent) -> None:
        """Receive a raw Hermes event, sanitise, and republish."""
        sanitised = self._sanitise_event(event)
        self._events.append(sanitised)
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]

        # Publish to EventBus for AI Operations Center
        if self._event_bus is not None:
            try:
                await self._event_bus.publish(
                    f"hermes:{event.event_type.value}",
                    {
                        "event_id": sanitised.event_id,
                        "event_type": sanitised.event_type,
                        "display_name": sanitised.display_name,
                        "data": sanitised.data,
                        "severity": sanitised.severity,
                        "source": "eve",
                    },
                    source="hermes_bridge",
                )
            except Exception as exc:
                logger.warning("hermes_bridge.publish_failed", error=str(exc))

        # Notify direct subscribers
        for sub in self._subscribers:
            try:
                await sub(sanitised)
            except Exception:
                pass

    # ── Convenience methods for common events ──────────────────────

    async def reasoning_started(self, query: str, context: dict | None = None) -> None:
        await self.on_hermes_event(HermesEvent(
            event_type=HermesEventType.REASONING_STARTED,
            data={"query": query, **(context or {})},
        ))

    async def reasoning_completed(self, result: str, duration_ms: float = 0) -> None:
        await self.on_hermes_event(HermesEvent(
            event_type=HermesEventType.REASONING_COMPLETED,
            data={"result_preview": result[:200], "duration_ms": duration_ms},
        ))

    async def plan_created(self, steps: list[str], objective: str = "") -> None:
        await self.on_hermes_event(HermesEvent(
            event_type=HermesEventType.PLAN_CREATED,
            data={"step_count": len(steps), "objective": objective},
        ))

    async def plan_step_started(self, step_index: int, step_desc: str) -> None:
        await self.on_hermes_event(HermesEvent(
            event_type=HermesEventType.PLAN_STEP_STARTED,
            data={"step_index": step_index, "step": step_desc},
        ))

    async def plan_step_completed(self, step_index: int, success: bool) -> None:
        await self.on_hermes_event(HermesEvent(
            event_type=HermesEventType.PLAN_STEP_COMPLETED,
            data={"step_index": step_index, "success": success},
        ))

    async def tool_requested(self, tool_name: str, params: dict | None = None) -> None:
        await self.on_hermes_event(HermesEvent(
            event_type=HermesEventType.TOOL_REQUESTED,
            data={"tool": tool_name, "params": params or {}},
        ))

    async def tool_completed(self, tool_name: str, success: bool, duration_ms: float = 0) -> None:
        await self.on_hermes_event(HermesEvent(
            event_type=HermesEventType.TOOL_COMPLETED,
            data={"tool": tool_name, "success": success, "duration_ms": duration_ms},
        ))

    async def skill_loaded(self, skill_name: str) -> None:
        await self.on_hermes_event(HermesEvent(
            event_type=HermesEventType.SKILL_LOADED,
            data={"skill": skill_name},
        ))

    async def error(self, message: str, details: dict | None = None) -> None:
        await self.on_hermes_event(HermesEvent(
            event_type=HermesEventType.ERROR,
            data={"message": message, **(details or {})},
            severity="error",
        ))

    async def status_changed(self, old_status: str, new_status: str) -> None:
        await self.on_hermes_event(HermesEvent(
            event_type=HermesEventType.STATUS_CHANGED,
            data={"old_status": old_status, "new_status": new_status},
        ))

    # ── Query API (for AI Operations Center) ───────────────────────

    def get_events(self, limit: int = 100, event_type: str | None = None) -> list[dict]:
        """Return recent sanitised events."""
        events = self._events
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "display_name": e.display_name,
                "data": e.data,
                "timestamp": e.timestamp.isoformat(),
                "severity": e.severity,
                "source": e.source,
            }
            for e in events[-limit:]
        ]

    def get_stats(self) -> dict:
        """Return event statistics."""
        type_counts: dict[str, int] = {}
        for e in self._events:
            type_counts[e.event_type] = type_counts.get(e.event_type, 0) + 1
        return {
            "total_events": len(self._events),
            "by_type": type_counts,
            "last_event": self._events[-1].timestamp.isoformat() if self._events else None,
        }

    # ── Subscription ───────────────────────────────────────────────

    def subscribe(self, callback: Any) -> None:
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Any) -> None:
        self._subscribers = [s for s in self._subscribers if s is not callback]

    # ── Internal ───────────────────────────────────────────────────

    def _sanitise_event(self, event: HermesEvent) -> SanitisedEvent:
        """Convert raw Hermes event to sanitised EVE event."""
        display_name = _EVENT_DISPLAY_NAMES.get(
            event.event_type,
            f"EVE {event.event_type.value.replace('_', ' ')}",
        )
        sanitised_data = _sanitise_dict(event.data)
        return SanitisedEvent(
            event_type=event.event_type.value,
            display_name=display_name,
            data=sanitised_data,
            timestamp=event.timestamp,
            event_id=event.event_id,
            source="eve",
            severity=event.data.get("severity", "info"),
        )
