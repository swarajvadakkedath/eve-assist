"""Automatic microphone calibration.

Measures ambient noise, input gain, and background level
to recommend optimal VAD thresholds. Completes in a few seconds.
"""

from __future__ import annotations

import asyncio
import math
import struct
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .profiles import VoiceProfile, ProfileType, get_profile


class CalibrationState(Enum):
    """Calibration lifecycle state."""
    IDLE = "idle"
    CALIBRATING = "calibrating"
    COMPLETE = "complete"
    FAILED = "error"


@dataclass
class CalibrationResult:
    """Results from automatic calibration."""
    state: CalibrationState
    noise_floor: float
    peak_level: float
    recommended_threshold: float
    recommended_profile: ProfileType
    recommended_gain: float
    duration_seconds: float
    samples_analyzed: int
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "state": self.state.value,
            "noise_floor": round(self.noise_floor, 6),
            "peak_level": round(self.peak_level, 6),
            "recommended_threshold": round(self.recommended_threshold, 6),
            "recommended_profile": self.recommended_profile.value,
            "recommended_gain": round(self.recommended_gain, 2),
            "duration_seconds": round(self.duration_seconds, 2),
            "samples_analyzed": self.samples_analyzed,
            "error": self.error,
        }


@dataclass
class CalibrationConfig:
    """Configuration for calibration."""
    duration_seconds: float = 3.0
    sample_rate: int = 16000
    channels: int = 1
    sample_width: int = 2
    min_samples: int = 100

    def to_dict(self) -> dict:
        return {
            "duration_seconds": self.duration_seconds,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "sample_width": self.sample_width,
        }


class CalibrationManager:
    """Automatic microphone calibration.

    Records ambient audio for a few seconds, analyzes noise floor
    and peak levels, and recommends optimal VAD thresholds and
    sensitivity profiles.
    """

    def __init__(self, config: Optional[CalibrationConfig] = None):
        self._config = config or CalibrationConfig()
        self._state = CalibrationState.IDLE
        self._result: Optional[CalibrationResult] = None
        self._samples: list[int] = []
        self._started_at: float = 0.0
        self._progress_callback = None

    @property
    def state(self) -> CalibrationState:
        return self._state

    @property
    def result(self) -> Optional[CalibrationResult]:
        return self._result

    def on_progress(self, callback) -> None:
        """Register a progress callback (called with 0.0-1.0)."""
        self._progress_callback = callback

    async def calibrate(self, audio_source=None) -> CalibrationResult:
        """Run automatic calibration.

        If audio_source is None, uses simulated calibration.
        In production, audio_source would be an AudioSession or Recorder.
        """
        self._state = CalibrationState.CALIBRATING
        self._started_at = time.monotonic()
        self._samples.clear()

        try:
            if audio_source is not None:
                await self._calibrate_from_source(audio_source)
            else:
                await self._simulate_calibration()

            self._result = self._analyze()
            self._state = CalibrationState.COMPLETE
            return self._result

        except Exception as e:
            self._state = CalibrationState.FAILED
            self._result = CalibrationResult(
                state=CalibrationState.FAILED,
                noise_floor=0.0,
                peak_level=0.0,
                recommended_threshold=0.05,
                recommended_profile=ProfileType.QUIET_ROOM,
                recommended_gain=1.0,
                duration_seconds=time.monotonic() - self._started_at,
                samples_analyzed=0,
                error=str(e),
            )
            return self._result

    async def _calibrate_from_source(self, audio_source) -> None:
        """Calibrate by reading from an audio source."""
        duration = self._config.duration_seconds
        sample_rate = self._config.sample_rate
        chunk_size = sample_rate * self._config.sample_width // 10  # 100ms chunks
        start = time.monotonic()

        while time.monotonic() - start < duration:
            # Read audio from source
            if hasattr(audio_source, 'read'):
                data = audio_source.read(chunk_size)
            elif hasattr(audio_source, 'buffer') and audio_source.buffer:
                data = audio_source.buffer.read(chunk_size, block=False)
            else:
                break

            if data:
                samples = self._unpack_samples(data)
                self._samples.extend(samples)

            # Report progress
            elapsed = time.monotonic() - start
            if self._progress_callback:
                self._progress_callback(min(1.0, elapsed / duration))

            await asyncio.sleep(0.01)

    async def _simulate_calibration(self) -> None:
        """Simulate calibration with mock data."""
        duration = self._config.duration_seconds
        sample_rate = self._config.sample_rate
        samples_needed = int(sample_rate * duration)
        chunk_size = sample_rate // 10  # 100ms chunks

        for i in range(0, samples_needed, chunk_size):
            # Generate mock ambient noise (low-level random)
            import random
            mock_samples = [random.randint(-100, 100) for _ in range(min(chunk_size, samples_needed - i))]
            self._samples.extend(mock_samples)

            # Report progress
            progress = min(1.0, len(self._samples) / samples_needed)
            if self._progress_callback:
                self._progress_callback(progress)

            await asyncio.sleep(0.01)

    def _unpack_samples(self, data: bytes) -> list[int]:
        """Unpack raw PCM bytes into integer samples."""
        if self._config.sample_width == 2:
            count = len(data) // 2
            if count == 0:
                return []
            return list(struct.unpack(f"<{count}h", data[:count * 2]))
        elif self._config.sample_width == 1:
            return [b - 128 for b in data]
        elif self._config.sample_width == 4:
            count = len(data) // 4
            if count == 0:
                return []
            return list(struct.unpack(f"<{count}i", data[:count * 4]))
        return []

    def _analyze(self) -> CalibrationResult:
        """Analyze collected samples and recommend settings."""
        if not self._samples:
            return CalibrationResult(
                state=CalibrationState.FAILED,
                noise_floor=0.0,
                peak_level=0.0,
                recommended_threshold=0.05,
                recommended_profile=ProfileType.QUIET_ROOM,
                recommended_gain=1.0,
                duration_seconds=time.monotonic() - self._started_at,
                samples_analyzed=0,
                error="No samples collected",
            )

        # Calculate noise floor (RMS of all samples)
        sum_sq = sum(s * s for s in self._samples)
        rms = math.sqrt(sum_sq / len(self._samples))
        noise_floor = rms / 32768.0

        # Calculate peak
        peak = max(abs(s) for s in self._samples) / 32768.0

        # Recommended threshold: noise floor * 3 (3x headroom)
        recommended_threshold = max(0.01, min(0.5, noise_floor * 3))

        # Determine recommended profile based on noise level
        if noise_floor < 0.02:
            profile = ProfileType.QUIET_ROOM
            gain = 1.0
        elif noise_floor < 0.05:
            profile = ProfileType.HEADSET
            gain = 1.0
        elif noise_floor < 0.08:
            profile = ProfileType.OFFICE
            gain = 1.2
        elif noise_floor < 0.15:
            profile = ProfileType.CONFERENCE
            gain = 1.5
        else:
            profile = ProfileType.CAFE
            gain = 1.8

        # If peak is very low, increase gain
        if peak < 0.05:
            gain = min(3.0, gain * 2)

        return CalibrationResult(
            state=CalibrationState.COMPLETE,
            noise_floor=noise_floor,
            peak_level=peak,
            recommended_threshold=recommended_threshold,
            recommended_profile=profile,
            recommended_gain=gain,
            duration_seconds=time.monotonic() - self._started_at,
            samples_analyzed=len(self._samples),
        )

    def get_recommended_profile(self) -> VoiceProfile:
        """Get a VoiceProfile based on calibration results."""
        if self._result and self._result.state == CalibrationState.COMPLETE:
            profile = get_profile(self._result.recommended_profile)
            profile.noise_threshold = self._result.recommended_threshold
            profile.gain = self._result.recommended_gain
            return profile
        return get_profile(ProfileType.QUIET_ROOM)

    def reset(self) -> None:
        """Reset calibration state."""
        self._state = CalibrationState.IDLE
        self._result = None
        self._samples.clear()

    def to_dict(self) -> dict:
        """Serialize calibration state."""
        result = {
            "state": self._state.value,
            "config": self._config.to_dict(),
        }
        if self._result:
            result["result"] = self._result.to_dict()
        return result
