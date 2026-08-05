"""AudioEngine — single entry point for all audio operations.

No module may access microphones or speakers directly.
All audio flows through AudioEngine.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from .buffer import AudioBuffer
from .device_manager import DeviceManager, AudioDeviceInfo
from .diagnostics import AudioDiagnostics
from .exceptions import AudioError, AudioDeviceNotFoundError, AudioSessionError
from .mixer import Mixer
from .playback import Playback, PlaybackSession
from .recorder import Recorder, RecordingSession
from .resampler import AudioResampler
from .router import AudioRouter, RouteType
from .session import AudioSession, AudioSessionState


class AudioEngineState(Enum):
    """Audio engine lifecycle state."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    SHUTTING_DOWN = "shutting_down"
    SHUTDOWN = "shutdown"
    ERROR = "error"


@dataclass
class AudioEngineConfig:
    """Configuration for the AudioEngine."""
    sample_rate: int = 16000
    channels: int = 1
    sample_width: int = 2
    buffer_size: int = 8192
    enable_monitoring: bool = True
    enable_diagnostics: bool = True


class AudioEngine:
    """Central audio engine — the single entry point for all audio operations.

    Responsibilities:
    - Initialize audio subsystem
    - Enumerate and manage devices
    - Create and manage audio sessions
    - Route audio streams
    - Manage buffers
    - Publish audio events
    - Provide diagnostics

    No module may access microphones or speakers directly.
    Everything goes through AudioEngine.
    """

    def __init__(self, config: Optional[AudioEngineConfig] = None, *,
                 event_bus: Optional[object] = None):
        self._config = config or AudioEngineConfig()
        self._event_bus = event_bus
        self._state = AudioEngineState.UNINITIALIZED

        # Core components
        self._device_manager = DeviceManager(event_bus=event_bus)
        self._router = AudioRouter(event_bus=event_bus)
        self._recorder = Recorder(event_bus=event_bus, device_manager=self._device_manager)
        self._playback = Playback(event_bus=event_bus, device_manager=self._device_manager)
        self._mixer = Mixer(
            sample_rate=self._config.sample_rate,
            channels=self._config.channels,
            sample_width=self._config.sample_width,
        )
        self._diagnostics = AudioDiagnostics(
            sample_rate=self._config.sample_rate,
            channels=self._config.channels,
            sample_width=self._config.sample_width,
        )

        # Session management
        self._sessions: dict[str, AudioSession] = {}
        self._resamplers: dict[str, AudioResampler] = {}

        # Event publishing
        self._event_handlers: dict[str, list[Callable]] = {}

        # Lifecycle
        self._created_at = time.monotonic()
        self._initialized_at: float = 0.0

    @property
    def state(self) -> AudioEngineState:
        return self._state

    @property
    def is_ready(self) -> bool:
        return self._state == AudioEngineState.READY

    @property
    def device_manager(self) -> DeviceManager:
        return self._device_manager

    @property
    def router(self) -> AudioRouter:
        return self._router

    @property
    def recorder(self) -> Recorder:
        return self._recorder

    @property
    def playback(self) -> Playback:
        return self._playback

    @property
    def mixer(self) -> Mixer:
        return self._mixer

    @property
    def diagnostics(self) -> AudioDiagnostics:
        return self._diagnostics

    @property
    def sessions(self) -> dict[str, AudioSession]:
        return dict(self._sessions)

    @property
    def config(self) -> AudioEngineConfig:
        return self._config

    async def initialize(self) -> None:
        """Initialize the audio subsystem.

        Discovers devices, sets up default routing, prepares diagnostics.
        Must be called before any other operation.
        """
        if self._state != AudioEngineState.UNINITIALIZED:
            return

        self._state = AudioEngineState.INITIALIZING

        try:
            # Discover devices
            await self._device_manager.initialize()

            # Start device monitoring
            if self._config.enable_monitoring:
                await self._device_manager.start_monitoring()

            # Set up default devices in diagnostics
            default_in = self._device_manager.default_input
            default_out = self._device_manager.default_output
            if default_in and default_out:
                self._diagnostics.set_devices(default_in.name, default_out.name)

            self._initialized_at = time.monotonic()
            self._state = AudioEngineState.READY
            await self._publish_event("audio:engine:ready", {})

        except Exception as e:
            self._state = AudioEngineState.ERROR
            await self._publish_event("audio:engine:error", {"error": str(e)})
            raise AudioError(f"Failed to initialize audio engine: {e}") from e

    async def shutdown(self) -> None:
        """Shut down the audio subsystem.

        Closes all sessions, stops monitoring, releases resources.
        """
        if self._state in (AudioEngineState.SHUTDOWN, AudioEngineState.SHUTTING_DOWN):
            return

        self._state = AudioEngineState.SHUTTING_DOWN

        # Close all sessions
        for session_id in list(self._sessions.keys()):
            try:
                await self._sessions[session_id].close()
            except Exception:
                pass
        self._sessions.clear()

        # Stop mixer
        await self._mixer.stop_mixing()

        # Stop device monitoring
        await self._device_manager.stop_monitoring()

        self._state = AudioEngineState.SHUTDOWN
        await self._publish_event("audio:engine:shutdown", {})

    async def create_session(self, *,
                              input_device_id: Optional[str] = None,
                              output_device_id: Optional[str] = None,
                              sample_rate: Optional[int] = None,
                              channels: Optional[int] = None) -> AudioSession:
        """Create a new audio session."""
        if self._state != AudioEngineState.READY:
            raise AudioSessionError("Audio engine not ready")

        # Resolve devices
        in_device = self._device_manager.get_input_device(input_device_id)
        out_device = self._device_manager.get_output_device(output_device_id)

        session = AudioSession(
            recorder=self._recorder,
            playback=self._playback,
            input_device_id=in_device.id,
            output_device_id=out_device.id,
            sample_rate=sample_rate or self._config.sample_rate,
            channels=channels or self._config.channels,
            sample_width=self._config.sample_width,
        )

        self._sessions[session.session_id] = session
        self._diagnostics.update_session_count(
            len(self._sessions),
            sum(1 for s in self._sessions.values() if s.is_streaming),
        )

        await self._publish_event("audio:session:created", {
            "session_id": session.session_id,
        })

        return session

    async def close_session(self, session_id: str) -> None:
        """Close and remove an audio session."""
        session = self._sessions.pop(session_id, None)
        if session:
            await session.close()
            self._diagnostics.update_session_count(
                len(self._sessions),
                sum(1 for s in self._sessions.values() if s.is_streaming),
            )
            await self._publish_event("audio:session:closed", {
                "session_id": session_id,
            })

    def get_session(self, session_id: str) -> Optional[AudioSession]:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def create_resampler(self, source_rate: int, target_rate: int,
                          resampler_id: Optional[str] = None) -> AudioResampler:
        """Create and register a resampler."""
        resampler = AudioResampler(source_rate, target_rate,
                                   self._config.channels, self._config.sample_width)
        rid = resampler_id or f"resample_{source_rate}_{target_rate}"
        self._resamplers[rid] = resampler
        return resampler

    def get_resampler(self, resampler_id: str) -> Optional[AudioResampler]:
        """Get a resampler by ID."""
        return self._resamplers.get(resampler_id)

    def on_event(self, event_type: str, handler: Callable) -> None:
        """Subscribe to audio engine events."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def off_event(self, event_type: str, handler: Callable) -> None:
        """Unsubscribe from audio engine events."""
        if event_type in self._event_handlers:
            self._event_handlers[event_type] = [
                h for h in self._event_handlers[event_type] if h != handler
            ]

    async def _publish_event(self, event_type: str, data: dict) -> None:
        """Publish an audio event."""
        # Notify local handlers
        for handler in self._event_handlers.get(event_type, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_type, data)
                else:
                    handler(event_type, data)
            except Exception:
                pass

        # Publish to EventBus if available
        if self._event_bus:
            try:
                if hasattr(self._event_bus, 'publish'):
                    await self._event_bus.publish(event_type, data, source="audio")
            except Exception:
                pass

    def diagnostics_snapshot(self) -> dict:
        """Get a full diagnostics snapshot for the AI Operations Center."""
        self._diagnostics.update_session_count(
            len(self._sessions),
            sum(1 for s in self._sessions.values() if s.is_streaming),
        )

        snap = self._diagnostics.snapshot()
        result = snap.to_dict()
        result["engine_state"] = self._state.value
        result["session_ids"] = list(self._sessions.keys())
        result["resampler_count"] = len(self._resamplers)
        result["route_count"] = len(self._router.routes)
        return result

    def to_dict(self) -> dict:
        """Serialize engine state."""
        return {
            "state": self._state.value,
            "config": {
                "sample_rate": self._config.sample_rate,
                "channels": self._config.channels,
                "sample_width": self._config.sample_width,
                "buffer_size": self._config.buffer_size,
            },
            "session_count": len(self._sessions),
            "device_manager": self._device_manager.to_dict(),
            "router": self._router.to_dict(),
            "recorder": self._recorder.to_dict(),
            "playback": self._playback.to_dict(),
            "mixer": self._mixer.to_dict(),
            "diagnostics": self.diagnostics_snapshot(),
        }
