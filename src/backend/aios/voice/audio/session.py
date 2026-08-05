"""Audio session — manages the lifecycle of a voice interaction."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from .exceptions import AudioSessionError, AudioSessionStateError
from .recorder import Recorder, RecordingSession
from .playback import Playback, PlaybackSession


class AudioSessionState(Enum):
    """Audio session lifecycle state."""
    CREATED = "created"
    OPENING = "opening"
    READY = "ready"
    STREAMING = "streaming"
    PAUSED = "paused"
    CLOSING = "closing"
    CLOSED = "closed"
    ERROR = "error"


@dataclass
class AudioSessionSnapshot:
    """Snapshot of audio session state for diagnostics."""
    session_id: str
    state: AudioSessionState
    input_device_id: str
    output_device_id: str
    sample_rate: int
    channels: int
    sample_width: int
    is_streaming: bool
    recording_bytes: int
    playback_bytes: int
    duration_seconds: float
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "input_device_id": self.input_device_id,
            "output_device_id": self.output_device_id,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "sample_width": self.sample_width,
            "is_streaming": self.is_streaming,
            "recording_bytes": self.recording_bytes,
            "playback_bytes": self.playback_bytes,
            "duration_seconds": round(self.duration_seconds, 2),
            "error": self.error,
        }


class AudioSession:
    """Manages the lifecycle of a single audio interaction.

    Coordinates recording from input, routing through the pipeline,
    and playback to output. Supports multiple concurrent sessions
    for future voice calls, recording, and streaming.
    """

    def __init__(self, session_id: Optional[str] = None, *,
                 recorder: Optional[Recorder] = None,
                 playback: Optional[Playback] = None,
                 input_device_id: str = "mock_input",
                 output_device_id: str = "mock_output",
                 sample_rate: int = 16000,
                 channels: int = 1,
                 sample_width: int = 2):
        self._session_id = session_id or f"audio_{uuid.uuid4().hex[:12]}"
        self._recorder = recorder
        self._playback = playback
        self._input_device_id = input_device_id
        self._output_device_id = output_device_id
        self._sample_rate = sample_rate
        self._channels = channels
        self._sample_width = sample_width

        self._state = AudioSessionState.CREATED
        self._recording_session: Optional[RecordingSession] = None
        self._playback_session: Optional[PlaybackSession] = None
        self._data_handlers: list[Callable] = []
        self._error: Optional[str] = None
        self._created_at = time.monotonic()
        self._opened_at: float = 0.0
        self._closed_at: float = 0.0
        self._lock = asyncio.Lock()

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def state(self) -> AudioSessionState:
        return self._state

    @property
    def is_streaming(self) -> bool:
        return self._state == AudioSessionState.STREAMING

    @property
    def input_device_id(self) -> str:
        return self._input_device_id

    @property
    def output_device_id(self) -> str:
        return self._output_device_id

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def channels(self) -> int:
        return self._channels

    @property
    def error(self) -> Optional[str]:
        return self._error

    async def open(self) -> None:
        """Open the audio session — prepare for streaming."""
        async with self._lock:
            if self._state not in (AudioSessionState.CREATED, AudioSessionState.CLOSED):
                raise AudioSessionStateError(
                    f"Cannot open session in state: {self._state.value}"
                )

            self._state = AudioSessionState.OPENING
            self._error = None
            self._opened_at = time.monotonic()

            # Create recording session
            if self._recorder:
                self._recording_session = self._recorder.create_session(
                    self._input_device_id,
                    sample_rate=self._sample_rate,
                    channels=self._channels,
                    sample_width=self._sample_width,
                )

            # Create playback session
            if self._playback:
                self._playback_session = self._playback.create_session(
                    self._output_device_id,
                    sample_rate=self._sample_rate,
                    channels=self._channels,
                    sample_width=self._sample_width,
                )

            self._state = AudioSessionState.READY

    async def start_streaming(self) -> None:
        """Start audio streaming (recording + playback)."""
        async with self._lock:
            if self._state != AudioSessionState.READY:
                raise AudioSessionStateError(
                    f"Cannot start streaming in state: {self._state.value}"
                )

            self._state = AudioSessionState.STREAMING

            # Start recording
            if self._recorder and self._recording_session:
                await self._recorder.start(self._recording_session.id)

            # Start playback
            if self._playback and self._playback_session:
                await self._playback.start(self._playback_session.id)

    async def stop_streaming(self) -> None:
        """Stop audio streaming."""
        async with self._lock:
            if self._state != AudioSessionState.STREAMING:
                return

            # Stop recording
            if self._recorder and self._recording_session:
                await self._recorder.stop(self._recording_session.id)

            # Stop playback
            if self._playback and self._playback_session:
                await self._playback.stop(self._playback_session.id)

            self._state = AudioSessionState.READY

    async def pause(self) -> None:
        """Pause streaming."""
        async with self._lock:
            if self._state != AudioSessionState.STREAMING:
                raise AudioSessionStateError(
                    f"Cannot pause in state: {self._state.value}"
                )

            if self._recorder and self._recording_session:
                await self._recorder.pause(self._recording_session.id)

            if self._playback and self._playback_session:
                await self._playback.pause(self._playback_session.id)

            self._state = AudioSessionState.PAUSED

    async def resume(self) -> None:
        """Resume paused streaming."""
        async with self._lock:
            if self._state != AudioSessionState.PAUSED:
                raise AudioSessionStateError(
                    f"Cannot resume in state: {self._state.value}"
                )

            if self._recorder and self._recording_session:
                await self._recorder.resume(self._recording_session.id)

            if self._playback and self._playback_session:
                await self._playback.resume(self._playback_session.id)

            self._state = AudioSessionState.STREAMING

    async def close(self) -> None:
        """Close the audio session and free resources."""
        async with self._lock:
            if self._state in (AudioSessionState.CLOSED, AudioSessionState.CLOSING):
                return

            was_streaming = self._state == AudioSessionState.STREAMING
            self._state = AudioSessionState.CLOSING

            # Stop streaming if active
            if was_streaming:
                if self._recorder and self._recording_session:
                    await self._recorder.stop(self._recording_session.id)
                if self._playback and self._playback_session:
                    await self._playback.stop(self._playback_session.id)

            # Destroy sessions
            if self._recorder and self._recording_session:
                self._recorder.destroy_session(self._recording_session.id)

            if self._playback and self._playback_session:
                self._playback.destroy_session(self._playback_session.id)

            self._recording_session = None
            self._playback_session = None
            self._closed_at = time.monotonic()
            self._state = AudioSessionState.CLOSED

    def on_data(self, handler: Callable) -> None:
        """Register a handler for audio data events."""
        self._data_handlers.append(handler)

    def snapshot(self) -> AudioSessionSnapshot:
        """Take a snapshot of the current session state."""
        recording_bytes = 0
        if self._recording_session:
            recording_bytes = self._recording_session.bytes_recorded

        playback_bytes = 0
        if self._playback_session:
            playback_bytes = self._playback_session.bytes_played

        elapsed = 0.0
        if self._opened_at > 0:
            end = self._closed_at if self._closed_at > 0 else time.monotonic()
            elapsed = end - self._opened_at

        return AudioSessionSnapshot(
            session_id=self._session_id,
            state=self._state,
            input_device_id=self._input_device_id,
            output_device_id=self._output_device_id,
            sample_rate=self._sample_rate,
            channels=self._channels,
            sample_width=self._sample_width,
            is_streaming=self.is_streaming,
            recording_bytes=recording_bytes,
            playback_bytes=playback_bytes,
            duration_seconds=elapsed,
            error=self._error,
        )

    def to_dict(self) -> dict:
        """Serialize session state."""
        return self.snapshot().to_dict()
