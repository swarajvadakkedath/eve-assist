"""Speech Session — manages lifecycle of a streaming audio session.

A session represents an active audio stream from capture to processing.
It tracks lifecycle state, coordinates chunk flow, and handles
interruption recovery.
"""

from __future__ import annotations

import asyncio
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from .chunk import AudioChunk


class SessionState(Enum):
    """Session lifecycle states."""
    CREATED = "created"
    OPENING = "opening"
    STREAMING = "streaming"
    PAUSED = "paused"
    RECOVERING = "recovering"
    CLOSED = "closed"
    ERROR = "error"


class SessionEvent(Enum):
    """Events published by a session."""
    STATE_CHANGED = "state_changed"
    CHUNK_RECEIVED = "chunk_received"
    CHUNK_PROCESSED = "chunk_processed"
    CHUNK_DROPPED = "chunk_dropped"
    PAUSED = "paused"
    RESUMED = "resumed"
    RECOVERY_STARTED = "recovery_started"
    RECOVERY_FINISHED = "recovery_finished"
    ERROR = "error"


# Valid state transitions
SESSION_TRANSITIONS: dict[SessionState, set[SessionState]] = {
    SessionState.CREATED: {SessionState.OPENING, SessionState.CLOSED},
    SessionState.OPENING: {SessionState.STREAMING, SessionState.ERROR, SessionState.CLOSED},
    SessionState.STREAMING: {
        SessionState.PAUSED,
        SessionState.RECOVERING,
        SessionState.CLOSED,
        SessionState.ERROR,
    },
    SessionState.PAUSED: {
        SessionState.STREAMING,
        SessionState.RECOVERING,
        SessionState.CLOSED,
    },
    SessionState.RECOVERING: {
        SessionState.STREAMING,
        SessionState.ERROR,
        SessionState.CLOSED,
    },
    SessionState.CLOSED: set(),
    SessionState.ERROR: {SessionState.CREATED, SessionState.CLOSED},
}


@dataclass
class SessionStats:
    """Snapshot of session statistics."""
    session_id: str
    state: str
    chunks_received: int = 0
    chunks_processed: int = 0
    chunks_dropped: int = 0
    total_bytes: int = 0
    uptime_seconds: float = 0.0
    last_chunk_age_ms: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "state": self.state,
            "chunks_received": self.chunks_received,
            "chunks_processed": self.chunks_processed,
            "chunks_dropped": self.chunks_dropped,
            "total_bytes": self.total_bytes,
            "uptime_seconds": round(self.uptime_seconds, 3),
            "last_chunk_age_ms": round(self.last_chunk_age_ms, 3),
            "error": self.error,
        }


class SpeechSession:
    """Manages the lifecycle of a streaming audio session.

    A session tracks chunk flow through the pipeline, manages state
    transitions, and supports interruption recovery.

    Args:
        session_id: Unique identifier for this session.
        silence_timeout: Seconds of silence before auto-pause.
        max_speech_duration: Maximum seconds of continuous speech.
    """

    def __init__(
        self,
        *,
        session_id: str = "",
        silence_timeout: float = 1.5,
        max_speech_duration: float = 300.0,
    ):
        self._session_id = session_id or f"session_{int(time.time() * 1000)}"
        self._silence_timeout = silence_timeout
        self._max_speech_duration = max_speech_duration
        self._state = SessionState.CREATED
        self._created_at = time.monotonic()
        self._state_entered_at = self._created_at
        self._last_chunk_time: float = 0.0
        self._error: Optional[str] = None

        # Counters
        self._chunks_received = 0
        self._chunks_processed = 0
        self._chunks_dropped = 0
        self._total_bytes = 0

        # Event handlers
        self._event_handlers: dict[SessionEvent, list[Callable]] = {}
        self._lock = threading.Lock()

    @property
    def id(self) -> str:
        return self._session_id

    @property
    def state(self) -> SessionState:
        return self._state

    @property
    def elapsed(self) -> float:
        """Seconds since current state was entered."""
        return time.monotonic() - self._state_entered_at

    @property
    def uptime(self) -> float:
        """Seconds since session was created."""
        return time.monotonic() - self._created_at

    @property
    def is_active(self) -> bool:
        """Session is in an active state (not closed/error)."""
        return self._state in (
            SessionState.CREATED,
            SessionState.OPENING,
            SessionState.STREAMING,
            SessionState.PAUSED,
            SessionState.RECOVERING,
        )

    def on(self, event: SessionEvent, handler: Callable) -> None:
        """Subscribe to a session event."""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def off(self, event: SessionEvent, handler: Callable) -> None:
        """Unsubscribe from a session event."""
        if event in self._event_handlers:
            self._event_handlers[event] = [
                h for h in self._event_handlers[event] if h != handler
            ]

    async def _emit(self, event: SessionEvent, data: dict) -> None:
        """Emit a session event."""
        for handler in self._event_handlers.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event, data)
                else:
                    handler(event, data)
            except Exception:
                pass

    def _transition(self, new_state: SessionState, reason: str = "") -> bool:
        """Attempt a state transition.

        Returns True if transition was valid.
        """
        valid = SESSION_TRANSITIONS.get(self._state, set())
        if new_state not in valid:
            return False

        now = time.monotonic()
        prev = self._state
        self._state = new_state
        self._state_entered_at = now

        # Emit event
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._emit(SessionEvent.STATE_CHANGED, {
                "from": prev.value,
                "to": new_state.value,
                "reason": reason,
                "session_id": self._session_id,
            }))
        except RuntimeError:
            pass

        return True

    def open(self) -> bool:
        """Open the session for streaming."""
        return self._transition(SessionState.OPENING, "open")

    def start_streaming(self) -> bool:
        """Begin streaming (OPENING → STREAMING)."""
        return self._transition(SessionState.STREAMING, "start_streaming")

    def receive_chunk(self, chunk: AudioChunk) -> bool:
        """Record that a chunk was received.

        Returns True if session accepted the chunk.
        """
        with self._lock:
            if self._state not in (SessionState.STREAMING, SessionState.RECOVERING):
                return False

            self._chunks_received += 1
            self._total_bytes += chunk.size_bytes
            self._last_chunk_time = time.monotonic()

        # Emit event
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._emit(SessionEvent.CHUNK_RECEIVED, {
                "session_id": self._session_id,
                "sequence": chunk.sequence,
                "size": chunk.size_bytes,
            }))
        except RuntimeError:
            pass

        return True

    def process_chunk(self, chunk: AudioChunk) -> None:
        """Record that a chunk was processed."""
        with self._lock:
            self._chunks_processed += 1

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._emit(SessionEvent.CHUNK_PROCESSED, {
                "session_id": self._session_id,
                "sequence": chunk.sequence,
            }))
        except RuntimeError:
            pass

    def drop_chunk(self, chunk: AudioChunk, reason: str = "") -> None:
        """Record that a chunk was dropped."""
        with self._lock:
            self._chunks_dropped += 1

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._emit(SessionEvent.CHUNK_DROPPED, {
                "session_id": self._session_id,
                "sequence": chunk.sequence,
                "reason": reason,
            }))
        except RuntimeError:
            pass

    def pause(self) -> bool:
        """Pause the session."""
        return self._transition(SessionState.PAUSED, "pause")

    def resume(self) -> bool:
        """Resume from paused state."""
        return self._transition(SessionState.STREAMING, "resume")

    def recover(self) -> bool:
        """Begin recovery from error or interruption."""
        return self._transition(SessionState.RECOVERING, "recover")

    def finish_recovery(self) -> bool:
        """Complete recovery successfully."""
        return self._transition(SessionState.STREAMING, "recovery_complete")

    def close(self) -> None:
        """Close the session."""
        with self._lock:
            was_streaming = self._state in (
                SessionState.STREAMING,
                SessionState.PAUSED,
                SessionState.RECOVERING,
            )
        self._transition(SessionState.CLOSED, "close")

    def set_error(self, error: str) -> None:
        """Set error state."""
        self._error = error
        self._transition(SessionState.ERROR, error)

    def stats(self) -> SessionStats:
        """Get current session statistics."""
        with self._lock:
            last_age = 0.0
            if self._last_chunk_time > 0:
                last_age = (time.monotonic() - self._last_chunk_time) * 1000

            return SessionStats(
                session_id=self._session_id,
                state=self._state.value,
                chunks_received=self._chunks_received,
                chunks_processed=self._chunks_processed,
                chunks_dropped=self._chunks_dropped,
                total_bytes=self._total_bytes,
                uptime_seconds=self.uptime,
                last_chunk_age_ms=last_age,
                error=self._error,
            )

    def check_timeout(self, silence_timeout: Optional[float] = None) -> bool:
        """Check if session should timeout due to silence.

        Returns True if timeout was triggered.
        """
        timeout = silence_timeout or self._silence_timeout
        if self._state == SessionState.STREAMING:
            if self.elapsed >= timeout:
                self._transition(SessionState.PAUSED, "silence_timeout")
                return True
        return False
