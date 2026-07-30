"""Voice event publisher — emits voice lifecycle events to the event bus."""

from aios.utils.logger import get_logger

logger = get_logger(__name__)

EVENT_LISTENING_START = "voice:listening:start"
EVENT_LISTENING_STOP = "voice:listening:stop"
EVENT_TRANSCRIPT_PARTIAL = "voice:transcript:partial"
EVENT_TRANSCRIPT_FINAL = "voice:transcript:final"
EVENT_SPEAKING_START = "voice:speaking:start"
EVENT_SPEAKING_STOP = "voice:speaking:stop"
EVENT_ERROR = "voice:error"
EVENT_STATE_CHANGE = "voice:state:change"
EVENT_AUDIO_LEVEL = "voice:audio:level"


class VoiceEventPublisher:
    def __init__(self, event_bus):
        self._event_bus = event_bus

    async def publish_listening_start(self, session_id: str, device: str | None = None):
        await self._event_bus.publish(
            EVENT_LISTENING_START,
            {"session_id": session_id, "device": device},
            source="voice",
        )

    async def publish_listening_stop(self, session_id: str, reason: str = "manual"):
        await self._event_bus.publish(
            EVENT_LISTENING_STOP,
            {"session_id": session_id, "reason": reason},
            source="voice",
        )

    async def publish_transcript_partial(self, session_id: str, text: str, confidence: float = 0.0):
        await self._event_bus.publish(
            EVENT_TRANSCRIPT_PARTIAL,
            {"session_id": session_id, "text": text, "confidence": confidence},
            source="voice",
        )

    async def publish_transcript_final(self, session_id: str, text: str, confidence: float = 0.0):
        await self._event_bus.publish(
            EVENT_TRANSCRIPT_FINAL,
            {"session_id": session_id, "text": text, "confidence": confidence},
            source="voice",
        )

    async def publish_speaking_start(self, session_id: str, utterance_id: str):
        await self._event_bus.publish(
            EVENT_SPEAKING_START,
            {"session_id": session_id, "utterance_id": utterance_id},
            source="voice",
        )

    async def publish_speaking_stop(self, session_id: str, utterance_id: str, reason: str = "completed"):
        await self._event_bus.publish(
            EVENT_SPEAKING_STOP,
            {"session_id": session_id, "utterance_id": utterance_id, "reason": reason},
            source="voice",
        )

    async def publish_error(self, session_id: str, error: str):
        await self._event_bus.publish(
            EVENT_ERROR,
            {"session_id": session_id, "error": error},
            source="voice",
        )

    async def publish_state_change(self, session_id: str, state: str, previous_state: str):
        await self._event_bus.publish(
            EVENT_STATE_CHANGE,
            {"session_id": session_id, "state": state, "previous_state": previous_state},
            source="voice",
        )

    async def publish_audio_level(self, session_id: str, level: float):
        await self._event_bus.publish(
            EVENT_AUDIO_LEVEL,
            {"session_id": session_id, "level": level},
            source="voice",
        )
