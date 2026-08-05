"""Audio resampling for cross-device compatibility."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .exceptions import AudioResamplerError


class SampleRate(Enum):
    """Standard audio sample rates."""
    RATE_8000 = 8000
    RATE_16000 = 16000
    RATE_22050 = 22050
    RATE_24000 = 24000
    RATE_44100 = 44100
    RATE_48000 = 48000


@dataclass
class ResampleResult:
    """Result of a resampling operation."""
    data: bytes
    source_rate: int
    target_rate: int
    source_samples: int
    target_samples: int

    def to_dict(self) -> dict:
        return {
            "source_rate": self.source_rate,
            "target_rate": self.target_rate,
            "source_samples": self.source_samples,
            "target_samples": self.target_samples,
            "output_bytes": len(self.data),
        }


class AudioResampler:
    """Converts audio between different sample rates.

    Uses linear interpolation for speed. Accepts 16-bit PCM (2 bytes per sample).
    """

    def __init__(self, source_rate: int = 16000, target_rate: int = 16000,
                 channels: int = 1, sample_width: int = 2):
        if source_rate <= 0 or target_rate <= 0:
            raise AudioResamplerError("Sample rates must be positive")
        if channels <= 0:
            raise AudioResamplerError("Channels must be positive")
        if sample_width not in (1, 2, 4):
            raise AudioResamplerError("Sample width must be 1, 2, or 4 bytes")

        self._source_rate = source_rate
        self._target_rate = target_rate
        self._channels = channels
        self._sample_width = sample_width
        self._ratio = target_rate / source_rate if source_rate != target_rate else 1.0
        self._is_passthrough = (source_rate == target_rate)

    @property
    def source_rate(self) -> int:
        return self._source_rate

    @property
    def target_rate(self) -> int:
        return self._target_rate

    @property
    def ratio(self) -> float:
        return self._ratio

    @property
    def is_passthrough(self) -> bool:
        return self._is_passthrough

    def resample(self, data: bytes) -> ResampleResult:
        """Resample audio data from source_rate to target_rate.

        If rates match, data is returned unchanged (passthrough).
        Input format: raw PCM bytes (default 16-bit signed LE, mono).
        """
        if self._is_passthrough:
            samples = len(data) // self._sample_width
            return ResampleResult(
                data=data,
                source_rate=self._source_rate,
                target_rate=self._target_rate,
                source_samples=samples,
                target_samples=samples,
            )

        if len(data) < self._sample_width:
            return ResampleResult(
                data=b"",
                source_rate=self._source_rate,
                target_rate=self._target_rate,
                source_samples=0,
                target_samples=0,
            )

        if self._sample_width == 2:
            return self._resample_16bit(data)
        elif self._sample_width == 1:
            return self._resample_8bit(data)
        else:
            return self._resample_32bit(data)

    def _resample_16bit(self, data: bytes) -> ResampleResult:
        """Resample 16-bit signed PCM using linear interpolation."""
        import struct

        num_source_samples = len(data) // 2
        num_target_samples = max(1, int(num_source_samples * self._ratio))

        # Unpack source samples
        source = struct.unpack(f"<{num_source_samples}h", data)
        target = []

        for i in range(num_target_samples):
            src_pos = i / self._ratio
            src_idx = int(src_pos)
            frac = src_pos - src_idx

            if src_idx >= num_source_samples - 1:
                sample = source[-1]
            else:
                s0 = source[src_idx]
                s1 = source[src_idx + 1]
                sample = int(s0 + frac * (s1 - s0))

            sample = max(-32768, min(32767, sample))
            target.append(sample)

        output = struct.pack(f"<{len(target)}h", *target)
        return ResampleResult(
            data=output,
            source_rate=self._source_rate,
            target_rate=self._target_rate,
            source_samples=num_source_samples,
            target_samples=num_target_samples,
        )

    def _resample_8bit(self, data: bytes) -> ResampleResult:
        """Resample 8-bit unsigned PCM using linear interpolation."""
        num_source_samples = len(data)
        num_target_samples = max(1, int(num_source_samples * self._ratio))

        target = []
        for i in range(num_target_samples):
            src_pos = i / self._ratio
            src_idx = int(src_pos)
            frac = src_pos - src_idx

            if src_idx >= num_source_samples - 1:
                sample = data[-1]
            else:
                s0 = data[src_idx]
                s1 = data[src_idx + 1]
                sample = int(s0 + frac * (s1 - s0))

            sample = max(0, min(255, sample))
            target.append(sample)

        output = bytes(target)
        return ResampleResult(
            data=output,
            source_rate=self._source_rate,
            target_rate=self._target_rate,
            source_samples=num_source_samples,
            target_samples=num_target_samples,
        )

    def _resample_32bit(self, data: bytes) -> ResampleResult:
        """Resample 32-bit signed PCM using linear interpolation."""
        import struct

        num_source_samples = len(data) // 4
        num_target_samples = max(1, int(num_source_samples * self._ratio))

        source = struct.unpack(f"<{num_source_samples}i", data)
        target = []

        for i in range(num_target_samples):
            src_pos = i / self._ratio
            src_idx = int(src_pos)
            frac = src_pos - src_idx

            if src_idx >= num_source_samples - 1:
                sample = source[-1]
            else:
                s0 = source[src_idx]
                s1 = source[src_idx + 1]
                sample = int(s0 + frac * (s1 - s0))

            sample = max(-2147483648, min(2147483647, sample))
            target.append(sample)

        output = struct.pack(f"<{len(target)}i", *target)
        return ResampleResult(
            data=output,
            source_rate=self._source_rate,
            target_rate=self._target_rate,
            source_samples=num_source_samples,
            target_samples=num_target_samples,
        )

    def update_rates(self, source_rate: int, target_rate: int) -> None:
        """Update source/target rates dynamically."""
        if source_rate <= 0 or target_rate <= 0:
            raise AudioResamplerError("Sample rates must be positive")
        self._source_rate = source_rate
        self._target_rate = target_rate
        self._ratio = target_rate / source_rate
        self._is_passthrough = (source_rate == target_rate)
