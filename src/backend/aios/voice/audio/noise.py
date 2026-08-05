"""Noise processing — cleans audio before VAD analysis.

Provides noise suppression, floor estimation, gain control,
peak detection, and silence calibration.
"""

from __future__ import annotations

import math
import struct
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NoiseStats:
    """Current noise processing statistics."""
    noise_floor: float = 0.0
    peak_level: float = 0.0
    rms_level: float = 0.0
    estimated_snr: float = 0.0
    frames_processed: int = 0
    noise_frames: int = 0
    speech_frames: int = 0
    gain_applied: float = 1.0

    def to_dict(self) -> dict:
        return {
            "noise_floor": round(self.noise_floor, 6),
            "peak_level": round(self.peak_level, 6),
            "rms_level": round(self.rms_level, 6),
            "estimated_snr": round(self.estimated_snr, 2),
            "frames_processed": self.frames_processed,
            "noise_frames": self.noise_frames,
            "speech_frames": self.speech_frames,
            "gain_applied": round(self.gain_applied, 2),
        }


class NoiseProcessor:
    """Processes raw audio to clean it before VAD analysis.

    Pipeline:
        Raw audio → Gain → Noise gate → Floor estimation → Clean audio

    Supports:
        - Automatic gain control (AGC) hooks
        - Noise floor estimation (exponential moving average)
        - Noise gate (suppress below threshold)
        - Peak detection and clipping
        - Silence calibration
    """

    def __init__(self, *, sample_rate: int = 16000, channels: int = 1,
                 sample_width: int = 2, noise_threshold: float = 0.01,
                 gain: float = 1.0, enable_noise_gate: bool = True,
                 enable_agc: bool = False, agc_target: float = 0.1):
        self._sample_rate = sample_rate
        self._channels = channels
        self._sample_width = sample_width
        self._noise_threshold = noise_threshold
        self._gain = gain
        self._enable_noise_gate = enable_noise_gate
        self._enable_agc = enable_agc
        self._agc_target = agc_target

        # State
        self._noise_floor = 0.0
        self._peak_level = 0.0
        self._rms_level = 0.0
        self._estimated_snr = 0.0
        self._frames_processed = 0
        self._noise_frames = 0
        self._speech_frames = 0
        self._noise_floor_ema = 0.0
        self._ema_alpha = 0.05  # Smoothing factor for noise floor EMA
        self._peak_decay = 0.999  # Peak hold decay
        self._created_at = time.monotonic()

    @property
    def noise_floor(self) -> float:
        return self._noise_floor

    @property
    def peak_level(self) -> float:
        return self._peak_level

    @property
    def rms_level(self) -> float:
        return self._rms_level

    @property
    def estimated_snr(self) -> float:
        return self._estimated_snr

    @property
    def gain(self) -> float:
        return self._gain

    @gain.setter
    def gain(self, value: float) -> None:
        self._gain = max(0.1, min(10.0, value))

    @property
    def noise_threshold(self) -> float:
        return self._noise_threshold

    @noise_threshold.setter
    def noise_threshold(self, value: float) -> None:
        self._noise_threshold = max(0.0, min(1.0, value))

    def process(self, data: bytes) -> bytes:
        """Process a chunk of raw PCM audio.

        Applies gain, noise gate, and updates statistics.
        Returns processed audio bytes.
        """
        if len(data) < self._sample_width:
            return data

        # Unpack samples
        samples = self._unpack_samples(data)

        if not samples:
            return data

        # Apply gain
        if self._gain != 1.0:
            samples = [max(-32768, min(32767, int(s * self._gain))) for s in samples]

        # Calculate RMS
        rms = self._calculate_rms(samples)
        self._rms_level = rms

        # Update peak (with decay)
        peak = max(abs(s) for s in samples) / 32768.0
        if peak > self._peak_level:
            self._peak_level = peak
        else:
            self._peak_level *= self._peak_decay

        # Update noise floor estimate
        self._update_noise_floor(rms)

        # Estimate SNR
        if self._noise_floor > 0:
            self._estimated_snr = 20 * math.log10(rms / self._noise_floor) if rms > 0 else 0
        else:
            self._estimated_snr = 0.0

        # Classify frame
        self._frames_processed += 1
        if rms < self._noise_threshold:
            self._noise_frames += 1
        else:
            self._speech_frames += 1

        # Apply noise gate
        if self._enable_noise_gate and rms < self._noise_threshold:
            # Gate open but below threshold — attenuate
            attenuation = min(1.0, rms / self._noise_threshold) if self._noise_threshold > 0 else 0
            samples = [int(s * attenuation) for s in samples]

        return self._pack_samples(samples)

    def _unpack_samples(self, data: bytes) -> list[int]:
        """Unpack raw PCM bytes into integer samples."""
        if self._sample_width == 2:
            count = len(data) // 2
            return list(struct.unpack(f"<{count}h", data[:count * 2]))
        elif self._sample_width == 1:
            return [b - 128 for b in data]  # unsigned 8-bit to signed
        elif self._sample_width == 4:
            count = len(data) // 4
            return list(struct.unpack(f"<{count}i", data[:count * 4]))
        return []

    def _pack_samples(self, samples: list[int]) -> bytes:
        """Pack integer samples back into raw PCM bytes."""
        if self._sample_width == 2:
            clamped = [max(-32768, min(32767, s)) for s in samples]
            return struct.pack(f"<{len(clamped)}h", *clamped)
        elif self._sample_width == 1:
            return bytes([max(0, min(255, s + 128)) for s in samples])
        elif self._sample_width == 4:
            clamped = [max(-2147483648, min(2147483647, s)) for s in samples]
            return struct.pack(f"<{len(clamped)}i", *clamped)
        return b""

    def _calculate_rms(self, samples: list[int]) -> float:
        """Calculate RMS amplitude (normalized to 0.0-1.0)."""
        if not samples:
            return 0.0
        sum_sq = sum(s * s for s in samples)
        rms = math.sqrt(sum_sq / len(samples))
        return rms / 32768.0 if self._sample_width == 2 else rms / 128.0

    def _update_noise_floor(self, rms: float) -> None:
        """Update noise floor estimate using exponential moving average."""
        if self._noise_floor_ema == 0.0:
            self._noise_floor_ema = rms
        else:
            self._noise_floor_ema = self._ema_alpha * rms + (1 - self._ema_alpha) * self._noise_floor_ema

        # Only update noise floor when in noise (below threshold)
        if rms < self._noise_threshold * 2:
            self._noise_floor = self._noise_floor_ema

    def calibrate(self, data: bytes, duration_ms: int = 2000) -> dict:
        """Calibrate noise floor from a sample of ambient audio.

        Returns calibration results including recommended threshold.
        """
        samples = self._unpack_samples(data)
        if not samples:
            return {"noise_floor": 0.0, "recommended_threshold": 0.05, "status": "error"}

        rms = self._calculate_rms(samples)
        peak = max(abs(s) for s in samples) / 32768.0

        # Recommended threshold: noise floor * 3 (3x headroom)
        recommended = max(0.01, min(0.5, rms * 3))

        return {
            "noise_floor": round(rms, 6),
            "peak_level": round(peak, 6),
            "recommended_threshold": round(recommended, 6),
            "duration_ms": duration_ms,
            "samples_analyzed": len(samples),
            "status": "ok",
        }

    def reset(self) -> None:
        """Reset all statistics."""
        self._noise_floor = 0.0
        self._peak_level = 0.0
        self._rms_level = 0.0
        self._estimated_snr = 0.0
        self._frames_processed = 0
        self._noise_frames = 0
        self._speech_frames = 0
        self._noise_floor_ema = 0.0

    def stats(self) -> NoiseStats:
        """Get current noise statistics."""
        return NoiseStats(
            noise_floor=self._noise_floor,
            peak_level=self._peak_level,
            rms_level=self._rms_level,
            estimated_snr=self._estimated_snr,
            frames_processed=self._frames_processed,
            noise_frames=self._noise_frames,
            speech_frames=self._speech_frames,
            gain_applied=self._gain,
        )

    def to_dict(self) -> dict:
        """Serialize noise processor state."""
        return {
            "sample_rate": self._sample_rate,
            "noise_threshold": self._noise_threshold,
            "gain": self._gain,
            "noise_gate_enabled": self._enable_noise_gate,
            "agc_enabled": self._enable_agc,
            "stats": self.stats().to_dict(),
        }
