"""Playback abstraction — outputs audio to speakers."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from .buffer import AudioBuffer
from .exceptions import AudioPlaybackError


class PlaybackState(Enum):
    """Playback lifecycle state."""
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class PlaybackSession:
    """An active playback session."""
    id: str
    device_id: str
    sample_rate: int = 16000
    channels: int = 1
    sample_width: int = 2
    state: PlaybackState = PlaybackState.IDLE
    buffer: Optional[AudioBuffer] = None
    volume: float = 1.0
    is_muted: bool = False
    started_at: float = 0.0
    paused_at: float = 0.0
    total_paused_duration: float = 0.0
    bytes_played: int = 0
    error: Optional[str] = None

    @property
    def elapsed_seconds(self) -> float:
        if self.state == PlaybackState.IDLE:
            return 0.0
        if self.state == PlaybackState.PAUSED:
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
            "volume": self.volume,
            "is_muted": self.is_muted,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "bytes_played": self.bytes_played,
            "error": self.error,
        }


class Playback:
    """Audio playback abstraction.

    Manages playback sessions to output devices. Supports start/stop/pause/resume,
    volume control, mute, device switching, and streaming from buffers.
    """

    def __init__(self, *, event_bus: Optional[object] = None,
                 device_manager: Optional[object] = None):
        self._event_bus = event_bus
        self._device_manager = device_manager
        self._sessions: dict[str, PlaybackSession] = {}
        self._playback_tasks: dict[str, asyncio.Task] = {}
        self._completion_handlers: dict[str, list[Callable]] = {}
        self._created_at = time.monotonic()

    @property
    def sessions(self) -> dict[str, PlaybackSession]:
        return dict(self._sessions)

    @property
    def active_sessions(self) -> list[PlaybackSession]:
        return [
            s for s in self._sessions.values()
            if s.state in (PlaybackState.PLAYING, PlaybackState.PAUSED)
        ]

    def create_session(self, device_id: str, *, sample_rate: int = 16000,
                       channels: int = 1, sample_width: int = 2,
                       buffer_size: int = 16384) -> PlaybackSession:
        """Create a new playback session."""
        session_id = f"play_{uuid.uuid4().hex[:12]}"
        session = PlaybackSession(
            id=session_id,
            device_id=device_id,
            sample_rate=sample_rate,
            channels=channels,
            sample_width=sample_width,
            buffer=AudioBuffer(capacity=buffer_size),
        )
        self._sessions[session_id] = session
        self._completion_handlers[session_id] = []
        return session

    async def start(self, session_id: str) -> None:
        """Start playback."""
        if session_id not in self._sessions:
            raise AudioPlaybackError(f"Session not found: {session_id}")

        session = self._sessions[session_id]
        if session.state not in (PlaybackState.IDLE, PlaybackState.STOPPED):
            raise AudioPlaybackError(
                f"Cannot start playback in state: {session.state.value}"
            )

        session.state = PlaybackState.PLAYING
        session.started_at = time.monotonic()
        session.bytes_played = 0
        session.error = None

        task = asyncio.create_task(self._playback_loop(session_id))
        self._playback_tasks[session_id] = task

    async def stop(self, session_id: str) -> None:
        """Stop playback."""
        if session_id not in self._sessions:
            raise AudioPlaybackError(f"Session not found: {session_id}")

        session = self._sessions[session_id]
        if session.state == PlaybackState.IDLE:
            return

        session.state = PlaybackState.STOPPED

        if session_id in self._playback_tasks:
            self._playback_tasks[session_id].cancel()
            try:
                await self._playback_tasks[session_id]
            except asyncio.CancelledError:
                pass
            del self._playback_tasks[session_id]

    async def pause(self, session_id: str) -> None:
        """Pause playback."""
        if session_id not in self._sessions:
            raise AudioPlaybackError(f"Session not found: {session_id}")

        session = self._sessions[session_id]
        if session.state != PlaybackState.PLAYING:
            raise AudioPlaybackError(
                f"Cannot pause playback in state: {session.state.value}"
            )

        session.state = PlaybackState.PAUSED
        session.paused_at = time.monotonic()

    async def resume(self, session_id: str) -> None:
        """Resume paused playback."""
        if session_id not in self._sessions:
            raise AudioPlaybackError(f"Session not found: {session_id}")

        session = self._sessions[session_id]
        if session.state != PlaybackState.PAUSED:
            raise AudioPlaybackError(
                f"Cannot resume playback in state: {session.state.value}"
            )

        if session.paused_at > 0:
            session.total_paused_duration += time.monotonic() - session.paused_at

        session.state = PlaybackState.PLAYING

    def set_volume(self, session_id: str, volume: float) -> None:
        """Set playback volume (0.0 to 1.0)."""
        if session_id not in self._sessions:
            raise AudioPlaybackError(f"Session not found: {session_id}")

        volume = max(0.0, min(1.0, volume))
        self._sessions[session_id].volume = volume

    def mute(self, session_id: str) -> None:
        """Mute playback."""
        if session_id not in self._sessions:
            raise AudioPlaybackError(f"Session not found: {session_id}")
        self._sessions[session_id].is_muted = True

    def unmute(self, session_id: str) -> None:
        """Unmute playback."""
        if session_id not in self._sessions:
            raise AudioPlaybackError(f"Session not found: {session_id}")
        self._sessions[session_id].is_muted = False

    def switch_device(self, session_id: str, new_device_id: str) -> None:
        """Switch output device during playback."""
        if session_id not in self._sessions:
            raise AudioPlaybackError(f"Session not found: {session_id}")
        self._sessions[session_id].device_id = new_device_id

    def write_data(self, session_id: str, data: bytes) -> int:
        """Write audio data to a playback session's buffer."""
        if session_id not in self._sessions:
            raise AudioPlaybackError(f"Session not found: {session_id}")

        session = self._sessions[session_id]
        if not session.buffer:
            return 0
        return session.buffer.write(data, block=False)

    def on_complete(self, session_id: str, handler: Callable) -> None:
        """Register a handler called when playback completes."""
        if session_id not in self._completion_handlers:
            self._completion_handlers[session_id] = []
        self._completion_handlers[session_id].append(handler)

    def destroy_session(self, session_id: str) -> None:
        """Destroy a playback session and free resources."""
        if session_id in self._playback_tasks:
            self._playback_tasks[session_id].cancel()
            del self._playback_tasks[session_id]

        session = self._sessions.pop(session_id, None)
        if session and session.buffer:
            session.buffer.close()

        self._completion_handlers.pop(session_id, None)

    async def _playback_loop(self, session_id: str) -> None:
        """Consume audio data from the session buffer and simulate playback."""
        try:
            session = self._sessions[session_id]
            chunk_size = session.sample_rate * session.channels * session.sample_width // 10

            while session.state == PlaybackState.PLAYING:
                if not session.buffer:
                    await asyncio.sleep(0.01)
                    continue

                data = session.buffer.read(chunk_size, block=False)
                if data:
                    # Apply volume (scale samples)
                    if session.volume < 1.0 and not session.is_muted:
                        effective_volume = session.volume
                    elif session.is_muted:
                        effective_volume = 0.0
                    else:
                        effective_volume = 1.0

                    if effective_volume < 1.0:
                        # Simple volume scaling for 16-bit PCM
                        import struct
                        samples = struct.unpack(f"<{len(data)//2}h", data)
                        scaled = struct.pack(
                            f"<{len(samples)}h",
                            *[max(-32768, min(32767, int(s * effective_volume)))
                              for s in samples]
                        )
                        data = scaled

                    session.bytes_played += len(data)
                else:
                    await asyncio.sleep(0.01)

            # Notify completion handlers
            for handler in self._completion_handlers.get(session_id, []):
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(session_id)
                    else:
                        handler(session_id)
                except Exception:
                    pass

        except asyncio.CancelledError:
            return
        except Exception as e:
            session.state = PlaybackState.ERROR
            session.error = str(e)

    def to_dict(self) -> dict:
        """Serialize playback state."""
        return {
            "session_count": len(self._sessions),
            "active_count": len(self.active_sessions),
            "sessions": {k: v.to_dict() for k, v in self._sessions.items()},
        }
