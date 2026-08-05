"""Audio diagnostics — collects metrics for the AI Operations Center."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from .buffer import AudioBuffer, BufferStats


@dataclass
class AudioDiagnosticsSnapshot:
    """Snapshot of all audio diagnostics at a point in time."""
    timestamp: float
    sample_rate: int
    channels: int
    sample_width: int
    session_count: int
    active_session_count: int
    input_device: str
    output_device: str
    cpu_percent: float
    buffer_stats: dict
    dropped_frames: int
    buffer_underruns: int
    buffer_overruns: int
    total_bytes_captured: int
    total_bytes_played: int
    uptime_seconds: float
    # VAD metrics
    vad_state: str = "idle"
    speech_confidence: float = 0.0
    noise_floor: float = 0.0
    input_level: float = 0.0
    listening_state: str = "idle"
    speech_duration: float = 0.0
    silence_duration: float = 0.0
    detection_latency_ms: float = 0.0
    active_profile: str = "Quiet Room"
    recent_events: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "sample_width": self.sample_width,
            "session_count": self.session_count,
            "active_session_count": self.active_session_count,
            "input_device": self.input_device,
            "output_device": self.output_device,
            "cpu_percent": round(self.cpu_percent, 2),
            "buffer_stats": self.buffer_stats,
            "dropped_frames": self.dropped_frames,
            "buffer_underruns": self.buffer_underruns,
            "buffer_overruns": self.buffer_overruns,
            "total_bytes_captured": self.total_bytes_captured,
            "total_bytes_played": self.total_bytes_played,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "vad_state": self.vad_state,
            "speech_confidence": round(self.speech_confidence, 4),
            "noise_floor": round(self.noise_floor, 6),
            "input_level": round(self.input_level, 6),
            "listening_state": self.listening_state,
            "speech_duration": round(self.speech_duration, 3),
            "silence_duration": round(self.silence_duration, 3),
            "detection_latency_ms": round(self.detection_latency_ms, 2),
            "active_profile": self.active_profile,
            "recent_events": self.recent_events,
        }


class AudioDiagnostics:
    """Collects and reports audio subsystem diagnostics.

    Tracks CPU usage, latency, dropped frames, buffer stats,
    device info, and session metrics. Designed for AI Operations
    Center integration.
    """

    def __init__(self, *, sample_rate: int = 16000, channels: int = 1,
                 sample_width: int = 2):
        self._sample_rate = sample_rate
        self._channels = channels
        self._sample_width = sample_width
        self._session_count = 0
        self._active_session_count = 0
        self._input_device = "unknown"
        self._output_device = "unknown"
        self._cpu_percent = 0.0
        self._dropped_frames = 0
        self._buffer_underruns = 0
        self._buffer_overruns = 0
        self._total_bytes_captured = 0
        self._total_bytes_played = 0
        self._buffer_stats: dict = {}
        self._latency_readings: list[float] = []
        self._created_at = time.monotonic()
        # VAD metrics
        self._vad_state = "idle"
        self._speech_confidence = 0.0
        self._noise_floor = 0.0
        self._input_level = 0.0
        self._listening_state = "idle"
        self._speech_duration = 0.0
        self._silence_duration = 0.0
        self._detection_latency_ms = 0.0
        self._active_profile = "Quiet Room"
        self._recent_events: list[dict] = []
        self._max_recent_events = 50

    @property
    def uptime(self) -> float:
        return time.monotonic() - self._created_at

    def update_session_count(self, total: int, active: int) -> None:
        """Update session counts."""
        self._session_count = total
        self._active_session_count = active

    def set_devices(self, input_device: str, output_device: str) -> None:
        """Update current device names."""
        self._input_device = input_device
        self._output_device = output_device

    def record_dropped_frame(self) -> None:
        """Record a dropped frame."""
        self._dropped_frames += 1

    def record_buffer_underrun(self) -> None:
        """Record a buffer underrun."""
        self._buffer_underruns += 1

    def record_buffer_overrun(self) -> None:
        """Record a buffer overrun."""
        self._buffer_overruns += 1

    def record_bytes_captured(self, count: int) -> None:
        """Record bytes captured from microphone."""
        self._total_bytes_captured += count

    def record_bytes_played(self, count: int) -> None:
        """Record bytes played to speaker."""
        self._total_bytes_played += count

    def record_latency(self, latency_ms: float) -> None:
        """Record a latency measurement."""
        self._latency_readings.append(latency_ms)
        # Keep last 1000 readings
        if len(self._latency_readings) > 1000:
            self._latency_readings = self._latency_readings[-1000:]

    def update_buffer_stats(self, buffer_id: str, stats: BufferStats) -> None:
        """Update buffer statistics for a specific buffer."""
        self._buffer_stats[buffer_id] = stats.to_dict()

    def update_cpu(self, percent: float) -> None:
        """Update CPU usage measurement."""
        self._cpu_percent = percent

    # ---- VAD metrics ----

    def update_vad_state(self, state: str) -> None:
        """Update VAD detection state."""
        self._vad_state = state

    def update_speech_confidence(self, confidence: float) -> None:
        """Update current speech confidence."""
        self._speech_confidence = confidence

    def update_noise_floor(self, level: float) -> None:
        """Update noise floor estimate."""
        self._noise_floor = level

    def update_input_level(self, level: float) -> None:
        """Update current input audio level."""
        self._input_level = level

    def update_listening_state(self, state: str) -> None:
        """Update listening state machine state."""
        self._listening_state = state

    def update_speech_duration(self, duration: float) -> None:
        """Update current speech duration."""
        self._speech_duration = duration

    def update_silence_duration(self, duration: float) -> None:
        """Update current silence duration."""
        self._silence_duration = duration

    def update_detection_latency(self, latency_ms: float) -> None:
        """Update VAD detection latency."""
        self._detection_latency_ms = latency_ms

    def update_active_profile(self, profile_name: str) -> None:
        """Update active sensitivity profile name."""
        self._active_profile = profile_name

    def record_voice_event(self, event_type: str, data: dict) -> None:
        """Record a recent voice event for the diagnostics panel."""
        import time as _time
        event = {
            "type": event_type,
            "timestamp": _time.time(),
            "data": data,
        }
        self._recent_events.append(event)
        if len(self._recent_events) > self._max_recent_events:
            self._recent_events = self._recent_events[-self._max_recent_events:]

    def snapshot(self) -> AudioDiagnosticsSnapshot:
        """Take a snapshot of all diagnostic metrics."""
        return AudioDiagnosticsSnapshot(
            timestamp=time.time(),
            sample_rate=self._sample_rate,
            channels=self._channels,
            sample_width=self._sample_width,
            session_count=self._session_count,
            active_session_count=self._active_session_count,
            input_device=self._input_device,
            output_device=self._output_device,
            cpu_percent=self._cpu_percent,
            buffer_stats=dict(self._buffer_stats),
            dropped_frames=self._dropped_frames,
            buffer_underruns=self._buffer_underruns,
            buffer_overruns=self._buffer_overruns,
            total_bytes_captured=self._total_bytes_captured,
            total_bytes_played=self._total_bytes_played,
            uptime_seconds=self.uptime,
            vad_state=self._vad_state,
            speech_confidence=self._speech_confidence,
            noise_floor=self._noise_floor,
            input_level=self._input_level,
            listening_state=self._listening_state,
            speech_duration=self._speech_duration,
            silence_duration=self._silence_duration,
            detection_latency_ms=self._detection_latency_ms,
            active_profile=self._active_profile,
            recent_events=list(self._recent_events[-10:]),
        )

    def reset(self) -> None:
        """Reset all diagnostic counters."""
        self._dropped_frames = 0
        self._buffer_underruns = 0
        self._buffer_overruns = 0
        self._total_bytes_captured = 0
        self._total_bytes_played = 0
        self._latency_readings.clear()
        self._buffer_stats.clear()
        self._cpu_percent = 0.0
        self._created_at = time.monotonic()
        self._vad_state = "idle"
        self._speech_confidence = 0.0
        self._noise_floor = 0.0
        self._input_level = 0.0
        self._listening_state = "idle"
        self._speech_duration = 0.0
        self._silence_duration = 0.0
        self._detection_latency_ms = 0.0
        self._active_profile = "Quiet Room"
        self._recent_events.clear()

    @property
    def average_latency(self) -> float:
        """Average latency across all readings."""
        if not self._latency_readings:
            return 0.0
        return sum(self._latency_readings) / len(self._latency_readings)

    @property
    def p95_latency(self) -> float:
        """95th percentile latency."""
        if not self._latency_readings:
            return 0.0
        sorted_readings = sorted(self._latency_readings)
        idx = int(len(sorted_readings) * 0.95)
        return sorted_readings[min(idx, len(sorted_readings) - 1)]

    def to_dict(self) -> dict:
        """Serialize diagnostics state."""
        snap = self.snapshot()
        result = snap.to_dict()
        result["average_latency_ms"] = round(self.average_latency, 2)
        result["p95_latency_ms"] = round(self.p95_latency, 2)
        return result
