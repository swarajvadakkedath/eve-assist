"""Vision event types and publisher."""

from typing import Any

VISION_EVENT_CAPTURE_START = "vision:capture:start"
VISION_EVENT_CAPTURE_COMPLETE = "vision:capture:complete"
VISION_EVENT_ANALYSIS_START = "vision:analysis:start"
VISION_EVENT_ANALYSIS_COMPLETE = "vision:analysis:complete"
VISION_EVENT_OBSERVATION = "vision:observation"
VISION_EVENT_ERROR = "vision:error"
VISION_EVENT_SESSION_START = "vision:session:start"
VISION_EVENT_SESSION_STOP = "vision:session:stop"


class VisionEventPublisher:
    """Publishes vision events to the EventBus."""

    def __init__(self, event_bus: Any | None = None):
        self.event_bus = event_bus

    async def publish_capture_start(self, target: str = "screen"):
        await self._publish(VISION_EVENT_CAPTURE_START, {"target": target})

    async def publish_capture_complete(self, target: str = "screen", size: int = 0):
        await self._publish(VISION_EVENT_CAPTURE_COMPLETE, {"target": target, "size_bytes": size})

    async def publish_analysis_start(self, source: str = "screen"):
        await self._publish(VISION_EVENT_ANALYSIS_START, {"source": source})

    async def publish_analysis_complete(self, source: str = "screen", element_count: int = 0, duration_ms: float = 0):
        await self._publish(VISION_EVENT_ANALYSIS_COMPLETE, {
            "source": source, "element_count": element_count, "duration_ms": duration_ms,
        })

    async def publish_observation(self, observation: dict):
        await self._publish(VISION_EVENT_OBSERVATION, observation)

    async def publish_error(self, error: str, details: dict | None = None):
        await self._publish(VISION_EVENT_ERROR, {"error": error, "details": details or {}})

    async def publish_session_start(self, session_id: str):
        await self._publish(VISION_EVENT_SESSION_START, {"session_id": session_id})

    async def publish_session_stop(self, session_id: str):
        await self._publish(VISION_EVENT_SESSION_STOP, {"session_id": session_id})

    async def _publish(self, event_type: str, data: dict):
        if self.event_bus:
            await self.event_bus.publish(event_type, data)
