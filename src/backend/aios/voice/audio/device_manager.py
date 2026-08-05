"""Audio device discovery and management."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from .exceptions import AudioDeviceError, AudioDeviceNotFoundError, AudioDeviceBusyError


class DeviceType(Enum):
    """Audio device type."""
    INPUT = "input"
    OUTPUT = "output"
    BOTH = "both"


class DeviceStatus(Enum):
    """Audio device status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    READY = "ready"
    ACTIVE = "active"
    ERROR = "error"


@dataclass
class AudioDeviceInfo:
    """Information about an audio device."""
    id: str
    name: str
    device_type: DeviceType
    channels: int = 1
    sample_rate: int = 16000
    sample_width: int = 2
    status: DeviceStatus = DeviceStatus.DISCONNECTED
    is_default: bool = False
    is_builtin: bool = False
    latency_ms: float = 0.0
    max_input_channels: int = 0
    max_output_channels: int = 0
    host_api: str = ""
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "device_type": self.device_type.value,
            "channels": self.channels,
            "sample_rate": self.sample_rate,
            "sample_width": self.sample_width,
            "status": self.status.value,
            "is_default": self.is_default,
            "is_builtin": self.is_builtin,
            "latency_ms": self.latency_ms,
            "max_input_channels": self.max_input_channels,
            "max_output_channels": self.max_output_channels,
            "host_api": self.host_api,
        }


class DeviceManager:
    """Manages audio input and output devices.

    Handles device discovery, hot-plug detection, default switching,
    and capability detection. No direct hardware access — wraps
    the underlying audio library abstraction.
    """

    def __init__(self, *, event_bus: Optional[object] = None):
        self._event_bus = event_bus
        self._devices: dict[str, AudioDeviceInfo] = {}
        self._input_devices: dict[str, AudioDeviceInfo] = {}
        self._output_devices: dict[str, AudioDeviceInfo] = {}
        self._default_input: Optional[str] = None
        self._default_output: Optional[str] = None
        self._active_devices: dict[str, object] = {}
        self._change_callbacks: list[Callable] = []
        self._initialized = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._created_at = time.monotonic()

    @property
    def initialized(self) -> bool:
        return self._initialized

    @property
    def devices(self) -> dict[str, AudioDeviceInfo]:
        return dict(self._devices)

    @property
    def input_devices(self) -> dict[str, AudioDeviceInfo]:
        return dict(self._input_devices)

    @property
    def output_devices(self) -> dict[str, AudioDeviceInfo]:
        return dict(self._output_devices)

    @property
    def default_input(self) -> Optional[AudioDeviceInfo]:
        if self._default_input and self._default_input in self._devices:
            return self._devices[self._default_input]
        return None

    @property
    def default_output(self) -> Optional[AudioDeviceInfo]:
        if self._default_output and self._default_output in self._devices:
            return self._devices[self._default_output]
        return None

    async def initialize(self) -> None:
        """Discover and enumerate all available audio devices."""
        if self._initialized:
            return

        try:
            await self._discover_devices()
        except Exception:
            # Graceful fallback: create mock devices for testing
            self._create_mock_devices()

        self._initialized = True

    async def _discover_devices(self) -> None:
        """Discover devices via the underlying audio library."""
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            for i, dev in enumerate(devices):
                device_type = DeviceType.BOTH
                if dev["max_input_channels"] > 0 and dev["max_output_channels"] == 0:
                    device_type = DeviceType.INPUT
                elif dev["max_output_channels"] > 0 and dev["max_input_channels"] == 0:
                    device_type = DeviceType.OUTPUT

                is_default = (
                    i == sd.default.device[0] or i == sd.default.device[1]
                )

                info = AudioDeviceInfo(
                    id=str(i),
                    name=dev["name"],
                    device_type=device_type,
                    channels=max(dev["max_input_channels"], dev["max_output_channels"]),
                    sample_rate=int(dev["default_samplerate"]),
                    is_default=is_default,
                    is_builtin="builtin" in dev["name"].lower(),
                    latency_ms=dev.get("latency", [0, 0])[0] * 1000,
                    max_input_channels=dev["max_input_channels"],
                    max_output_channels=dev["max_output_channels"],
                    host_api=sd.hostapis[dev["hostapi"]]["name"],
                )
                self._register_device(info)

        except ImportError:
            # sounddevice not installed — use mock devices
            self._create_mock_devices()

    def _create_mock_devices(self) -> None:
        """Create mock devices for testing and graceful fallback."""
        mock_input = AudioDeviceInfo(
            id="mock_input",
            name="Mock Microphone",
            device_type=DeviceType.INPUT,
            channels=1,
            sample_rate=16000,
            sample_width=2,
            is_default=True,
            is_builtin=True,
            max_input_channels=1,
            host_api="mock",
        )
        mock_output = AudioDeviceInfo(
            id="mock_output",
            name="Mock Speaker",
            device_type=DeviceType.OUTPUT,
            channels=1,
            sample_rate=16000,
            sample_width=2,
            is_default=True,
            is_builtin=True,
            max_output_channels=1,
            host_api="mock",
        )
        self._register_device(mock_input)
        self._register_device(mock_output)
        self._default_input = "mock_input"
        self._default_output = "mock_output"

    def _register_device(self, info: AudioDeviceInfo) -> None:
        """Register a device in the internal registry."""
        self._devices[info.id] = info
        if info.device_type in (DeviceType.INPUT, DeviceType.BOTH):
            self._input_devices[info.id] = info
        if info.device_type in (DeviceType.OUTPUT, DeviceType.BOTH):
            self._output_devices[info.id] = info
        if info.is_default:
            if info.device_type in (DeviceType.INPUT, DeviceType.BOTH):
                self._default_input = info.id
            if info.device_type in (DeviceType.OUTPUT, DeviceType.BOTH):
                self._default_output = info.id

    def get_device(self, device_id: str) -> AudioDeviceInfo:
        """Get device info by ID."""
        if device_id not in self._devices:
            raise AudioDeviceNotFoundError(f"Device not found: {device_id}")
        return self._devices[device_id]

    def get_input_device(self, device_id: Optional[str] = None) -> AudioDeviceInfo:
        """Get input device, defaulting to default input."""
        if device_id:
            return self.get_device(device_id)
        if self._default_input:
            return self._devices[self._default_input]
        raise AudioDeviceNotFoundError("No input devices available")

    def get_output_device(self, device_id: Optional[str] = None) -> AudioDeviceInfo:
        """Get output device, defaulting to default output."""
        if device_id:
            return self.get_device(device_id)
        if self._default_output:
            return self._devices[self._default_output]
        raise AudioDeviceNotFoundError("No output devices available")

    def set_default_input(self, device_id: str) -> None:
        """Set the default input device."""
        if device_id not in self._input_devices:
            raise AudioDeviceNotFoundError(f"Input device not found: {device_id}")
        self._default_input = device_id
        self._devices[device_id].is_default = True

    def set_default_output(self, device_id: str) -> None:
        """Set the default output device."""
        if device_id not in self._output_devices:
            raise AudioDeviceNotFoundError(f"Output device not found: {device_id}")
        self._default_output = device_id
        self._devices[device_id].is_default = True

    def mark_active(self, device_id: str) -> None:
        """Mark a device as active (in use)."""
        if device_id in self._devices:
            self._devices[device_id].status = DeviceStatus.ACTIVE

    def mark_ready(self, device_id: str) -> None:
        """Mark a device as ready."""
        if device_id in self._devices:
            self._devices[device_id].status = DeviceStatus.READY

    def mark_disconnected(self, device_id: str) -> None:
        """Mark a device as disconnected."""
        if device_id in self._devices:
            self._devices[device_id].status = DeviceStatus.DISCONNECTED

    def on_device_change(self, callback: Callable) -> None:
        """Register a callback for device changes."""
        self._change_callbacks.append(callback)

    async def _notify_device_change(self, device_id: str, event: str) -> None:
        """Notify callbacks of device changes."""
        for cb in self._change_callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(device_id, event)
                else:
                    cb(device_id, event)
            except Exception:
                pass

    async def start_monitoring(self) -> None:
        """Start monitoring for device changes (hot-plug)."""
        if self._monitor_task is not None:
            return
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop_monitoring(self) -> None:
        """Stop monitoring for device changes."""
        if self._monitor_task is not None:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

    async def _monitor_loop(self) -> None:
        """Poll for device changes periodically."""
        try:
            while True:
                await asyncio.sleep(2.0)
                previous_ids = set(self._devices.keys())
                await self._discover_devices()
                current_ids = set(self._devices.keys())

                for new_id in current_ids - previous_ids:
                    await self._notify_device_change(new_id, "connected")
                for removed_id in previous_ids - current_ids:
                    await self._notify_device_change(removed_id, "disconnected")
        except asyncio.CancelledError:
            return

    def enumerate_devices(self) -> list[AudioDeviceInfo]:
        """Return all discovered devices."""
        return list(self._devices.values())

    def list_input_devices(self) -> list[AudioDeviceInfo]:
        """Return all input devices."""
        return list(self._input_devices.values())

    def list_output_devices(self) -> list[AudioDeviceInfo]:
        """Return all output devices."""
        return list(self._output_devices.values())

    def to_dict(self) -> dict:
        """Serialize device manager state."""
        return {
            "initialized": self._initialized,
            "default_input": self._default_input,
            "default_output": self._default_output,
            "input_count": len(self._input_devices),
            "output_count": len(self._output_devices),
            "devices": {k: v.to_dict() for k, v in self._devices.items()},
        }
