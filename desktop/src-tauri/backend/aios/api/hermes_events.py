"""Agent Events API — /api/v1/agent/events endpoints for AI Operations Center.

All events are identity-sanitised — "Hermes" never appears in any response.
The frontend displays these as "EVE" events.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from aios.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/agent", tags=["agent-events"])

# Module-level bridge instance — set during app startup
_bridge: HermesEventsBridge | None = None


def configure(bridge: HermesEventsBridge) -> None:
    """Set the bridge instance during app startup."""
    global _bridge
    _bridge = bridge


@router.get("/events")
async def get_events(
    limit: int = Query(100, ge=1, le=500),
    event_type: str | None = Query(None),
):
    """Return recent Hermes lifecycle events (sanitised for EVE identity)."""
    if _bridge is None:
        return {"events": [], "count": 0}
    events = _bridge.get_events(limit=limit, event_type=event_type)
    return {"events": events, "count": len(events)}


@router.get("/events/stats")
async def get_event_stats():
    """Return Hermes event statistics."""
    if _bridge is None:
        return {"total_events": 0, "by_type": {}, "last_event": None}
    return _bridge.get_stats()


# Need to import at function level to avoid circular imports
from aios.hermes_bridge.events import HermesEventsBridge  # noqa: E402
