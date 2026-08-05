"""Audio mixer — combines multiple streams into a single output."""

from __future__ import annotations

import asyncio
import struct
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from .buffer import AudioBuffer
from .exceptions import AudioMixerError


class StreamPriority(Enum):
    """Priority levels for audio streams."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3  # TTS, notifications — never drop these


@dataclass
class MixerStream:
    """An audio stream registered with the mixer."""
    id: str
    name: str
    sample_rate: int = 16000
    channels: int = 1
    sample_width: int = 2
    volume: float = 1.0
    is_muted: bool = False
    priority: StreamPriority = StreamPriority.NORMAL
    buffer: Optional[AudioBuffer] = None
    is_active: bool = True
    created_at: float = field(default_factory=time.monotonic)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "volume": self.volume,
            "is_muted": self.is_muted,
            "priority": self.priority.value,
            "is_active": self.is_active,
            "buffer_usage": self.buffer.count if self.buffer else 0,
        }


class Mixer:
    """Audio mixer — combines multiple input streams into one output.

    Supports per-stream volume control, muting, priority-based mixing,
    and real-time stream addition/removal. Designed for future TTS,
    notifications, and background audio mixing.
    """

    def __init__(self, *, output_buffer: Optional[AudioBuffer] = None,
                 sample_rate: int = 16000, channels: int = 1,
                 sample_width: int = 2):
        self._output_buffer = output_buffer or AudioBuffer(capacity=32768)
        self._sample_rate = sample_rate
        self._channels = channels
        self._sample_width = sample_width
        self._streams: dict[str, MixerStream] = {}
        self._mix_task: Optional[asyncio.Task] = None
        self._is_mixing = False
        self._created_at = time.monotonic()

    @property
    def streams(self) -> dict[str, MixerStream]:
        return dict(self._streams)

    @property
    def active_streams(self) -> list[MixerStream]:
        return [s for s in self._streams.values() if s.is_active and not s.is_muted]

    @property
    def output_buffer(self) -> AudioBuffer:
        return self._output_buffer

    def add_stream(self, stream_id: str, name: str, *,
                   sample_rate: int = 16000, channels: int = 1,
                   sample_width: int = 2, volume: float = 1.0,
                   priority: StreamPriority = StreamPriority.NORMAL,
                   buffer_size: int = 8192) -> MixerStream:
        """Add a stream to the mixer."""
        if stream_id in self._streams:
            raise AudioMixerError(f"Stream already exists: {stream_id}")

        stream = MixerStream(
            id=stream_id,
            name=name,
            sample_rate=sample_rate,
            channels=channels,
            sample_width=sample_width,
            volume=volume,
            priority=priority,
            buffer=AudioBuffer(capacity=buffer_size),
        )
        self._streams[stream_id] = stream
        return stream

    def remove_stream(self, stream_id: str) -> None:
        """Remove a stream from the mixer."""
        if stream_id not in self._streams:
            raise AudioMixerError(f"Stream not found: {stream_id}")

        stream = self._streams.pop(stream_id)
        if stream.buffer:
            stream.buffer.close()

    def set_volume(self, stream_id: str, volume: float) -> None:
        """Set stream volume (0.0 to 1.0)."""
        if stream_id not in self._streams:
            raise AudioMixerError(f"Stream not found: {stream_id}")
        self._streams[stream_id].volume = max(0.0, min(1.0, volume))

    def mute(self, stream_id: str) -> None:
        """Mute a stream."""
        if stream_id not in self._streams:
            raise AudioMixerError(f"Stream not found: {stream_id}")
        self._streams[stream_id].is_muted = True

    def unmute(self, stream_id: str) -> None:
        """Unmute a stream."""
        if stream_id not in self._streams:
            raise AudioMixerError(f"Stream not found: {stream_id}")
        self._streams[stream_id].is_muted = False

    def set_priority(self, stream_id: str, priority: StreamPriority) -> None:
        """Set stream priority."""
        if stream_id not in self._streams:
            raise AudioMixerError(f"Stream not found: {stream_id}")
        self._streams[stream_id].priority = priority

    def write_to_stream(self, stream_id: str, data: bytes) -> int:
        """Write audio data to a stream's buffer."""
        if stream_id not in self._streams:
            raise AudioMixerError(f"Stream not found: {stream_id}")

        stream = self._streams[stream_id]
        if stream.buffer is None:
            return 0
        return stream.buffer.write(data, block=False)

    async def start_mixing(self) -> None:
        """Start the mix loop that combines all active streams."""
        if self._is_mixing:
            return
        self._is_mixing = True
        self._mix_task = asyncio.create_task(self._mix_loop())

    async def stop_mixing(self) -> None:
        """Stop the mix loop."""
        self._is_mixing = False
        if self._mix_task:
            self._mix_task.cancel()
            try:
                await self._mix_task
            except asyncio.CancelledError:
                pass
            self._mix_task = None

    async def _mix_loop(self) -> None:
        """Mix all active streams into the output buffer."""
        try:
            chunk_size = self._sample_rate * self._channels * self._sample_width // 10  # 100ms

            while self._is_mixing:
                # Collect audio from all active streams
                mixed_samples = None
                max_samples = 0

                active = sorted(
                    [s for s in self._streams.values()
                     if s.is_active and s.buffer and not s.is_muted],
                    key=lambda s: s.priority.value,
                    reverse=True,
                )

                for stream in active:
                    data = stream.buffer.read(chunk_size, block=False)
                    if not data:
                        continue

                    # Convert to samples for mixing
                    if self._sample_width == 2:
                        samples = list(struct.unpack(f"<{len(data)//2}h", data))
                    else:
                        samples = list(data)

                    # Apply per-stream volume
                    if stream.volume < 1.0:
                        samples = [int(s * stream.volume) for s in samples]

                    # Mix into combined buffer
                    if mixed_samples is None:
                        mixed_samples = samples
                    else:
                        # Pad shorter stream with zeros
                        if len(samples) < len(mixed_samples):
                            samples.extend([0] * (len(mixed_samples) - len(samples)))
                        elif len(samples) > len(mixed_samples):
                            mixed_samples.extend([0] * (len(samples) - len(mixed_samples)))

                        mixed_samples = [
                            max(-32768, min(32767, mixed_samples[i] + samples[i]))
                            for i in range(len(mixed_samples))
                        ]

                    max_samples = max(max_samples, len(samples))

                if mixed_samples and max_samples > 0:
                    output = struct.pack(f"<{len(mixed_samples)}h", *mixed_samples)
                    self._output_buffer.write(output, block=False)

                await asyncio.sleep(0.01)  # 10ms mix interval

        except asyncio.CancelledError:
            return

    def to_dict(self) -> dict:
        """Serialize mixer state."""
        return {
            "stream_count": len(self._streams),
            "active_count": len(self.active_streams),
            "sample_rate": self._sample_rate,
            "channels": self._channels,
            "streams": {k: v.to_dict() for k, v in self._streams.items()},
        }
