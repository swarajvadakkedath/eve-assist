"""Recording abstraction — captures audio from input devices."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from .buffer import AudioBuffer
from .exceptions import AudioRecordingError


class RecordingState(Enum):
    """Recording lifecycle state."""
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class RecordingSession:
    """An active recording session."""
    id: str
    device_id: str
    sample_rate: int = 16000
    channels: int = 1
    sample_width: int = 2
    state: RecordingState = RecordingState.IDLE
    buffer: Optional[AudioBuffer] = None
    started_at: float = 0.0
    paused_at: float = 0.0
    total_paused_duration: float = 0.0
    bytes_recorded: int = 0
    error: Optional[str] = None

    @property
    def elapsed_seconds(self) -> float:
        if self.state == RecordingState.IDLE:
            return 0.0
        if self.state == RecordingState.PAUSED:
            return self.paused_at - self.started_at - self.total_paused_duration
        return time.monotonic() - self.started_at - self.total_paused_duration

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "device_id": self.device_id,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "sample_width": self.sample_width,
            "state": self.state.value,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "bytes_recorded": self.bytes_recorded,
            "error": self.error,
        }


class Recorder:
    """Audio recording abstraction.

    Manages recording sessions from input devices. Supports start/stop/pause/resume,
    streaming to handlers, and temporary recordings (no permanent storage by default).
    """

    def __init__(self, *, event_bus: Optional[object] = None,
                 device_manager: Optional[object] = None):
        self._event_bus = event_bus
        self._device_manager = device_manager
        self._sessions: dict[str, RecordingSession] = {}
        self._recording_tasks: dict[str, asyncio.Task] = {}
        self._data_handlers: dict[str, list[Callable]] = {}
        self._created_at = time.monotonic()

    @property
    def sessions(self) -> dict[str, RecordingSession]:
        return dict(self._sessions)

    @property
    def active_sessions(self) -> list[RecordingSession]:
        return [
            s for s in self._sessions.values()
            if s.state in (RecordingState.RECORDING, RecordingState.PAUSED)
        ]

    def create_session(self, device_id: str, *, sample_rate: int = 16000,
                       channels: int = 1, sample_width: int = 2,
                       buffer_size: int = 16384) -> RecordingSession:
        """Create a new recording session."""
        session_id = f"rec_{uuid.uuid4().hex[:12]}"
        session = RecordingSession(
            id=session_id,
            device_id=device_id,
            sample_rate=sample_rate,
            channels=channels,
            sample_width=sample_width,
            buffer=AudioBuffer(capacity=buffer_size),
        )
        self._sessions[session_id] = session
        self._data_handlers[session_id] = []
        return session

    async def start(self, session_id: str) -> None:
        """Start recording."""
        if session_id not in self._sessions:
            raise AudioRecordingError(f"Session not found: {session_id}")

        session = self._sessions[session_id]
        if session.state not in (RecordingState.IDLE, RecordingState.STOPPED):
            raise AudioRecordingError(
                f"Cannot start recording in state: {session.state.value}"
            )

        session.state = RecordingState.RECORDING
        session.started_at = time.monotonic()
        session.bytes_recorded = 0
        session.error = None

        if session.buffer:
            session.buffer.flush()

        task = asyncio.create_task(self._recording_loop(session_id))
        self._recording_tasks[session_id] = task

    async def stop(self, session_id: str) -> None:
        """Stop recording."""
        if session_id not in self._sessions:
            raise AudioRecordingError(f"Session not found: {session_id}")

        session = self._sessions[session_id]
        if session.state == RecordingState.IDLE:
            return

        session.state = RecordingState.STOPPED

        if session_id in self._recording_tasks:
            self._recording_tasks[session_id].cancel()
            try:
                await self._recording_tasks[session_id]
            except asyncio.CancelledError:
                pass
            del self._recording_tasks[session_id]

    async def pause(self, session_id: str) -> None:
        """Pause recording."""
        if session_id not in self._sessions:
            raise AudioRecordingError(f"Session not found: {session_id}")

        session = self._sessions[session_id]
        if session.state != RecordingState.RECORDING:
            raise AudioRecordingError(
                f"Cannot pause recording in state: {session.state.value}"
            )

        session.state = RecordingState.PAUSED
        session.paused_at = time.monotonic()

    async def resume(self, session_id: str) -> None:
        """Resume paused recording."""
        if session_id not in self._sessions:
            raise AudioRecordingError(f"Session not found: {session_id}")

        session = self._sessions[session_id]
        if session.state != RecordingState.PAUSED:
            raise AudioRecordingError(
                f"Cannot resume recording in state: {session.state.value}"
            )

        if session.paused_at > 0:
            session.total_paused_duration += time.monotonic() - session.paused_at

        session.state = RecordingState.RECORDING

    def destroy_session(self, session_id: str) -> None:
        """Destroy a recording session and free resources."""
        if session_id in self._recording_tasks:
            self._recording_tasks[session_id].cancel()
            del self._recording_tasks[session_id]

        session = self._sessions.pop(session_id, None)
        if session and session.buffer:
            session.buffer.close()

        self._data_handlers.pop(session_id, None)

    def on_data(self, session_id: str, handler: Callable) -> None:
        """Register a handler to receive recorded audio data.

        Handler receives (session_id, data: bytes).
        """
        if session_id not in self._data_handlers:
            self._data_handlers[session_id] = []
        self._data_handlers[session_id].append(handler)

    def off_data(self, session_id: str, handler: Callable) -> None:
        """Remove a data handler."""
        if session_id in self._data_handlers:
            self._data_handlers[session_id] = [
                h for h in self._data_handlers[session_id] if h != handler
            ]

    async def _recording_loop(self, session_id: str) -> None:
        """Simulate recording by generating mock audio data.

        In production, this would read from the actual microphone.
        """
        try:
            session = self._sessions[session_id]
            chunk_size = session.sample_rate * session.channels * session.sample_width // 10  # 100ms chunks
            chunk_size = max(chunk_size, 320)  # Minimum chunk size

            while session.state == RecordingState.RECORDING:
                # Mock audio data (silence with slight noise)
                mock_data = b'\x00' * chunk_size

                if session.buffer:
                    session.buffer.write(mock_data, block=False)
                    session.bytes_recorded += len(mock_data)

                # Notify handlers
                for handler in self._data_handlers.get(session_id, []):
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(session_id, mock_data)
                        else:
                            handler(session_id, mock_data)
                    except Exception:
                        pass

                await asyncio.sleep(0.1)  # 100ms chunks

        except asyncio.CancelledError:
            return
        except Exception as e:
            session.state = RecordingState.ERROR
            session.error = str(e)

    def to_dict(self) -> dict:
        """Serialize recorder state."""
        return {
            "session_count": len(self._sessions),
            "active_count": len(self.active_sessions),
            "sessions": {k: v.to_dict() for k, v in self._sessions.items()},
        }
