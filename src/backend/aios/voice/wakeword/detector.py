"""Wake Word Detector — core detection engine with confidence scoring.

Provider-independent. Processes audio frames and detects wake phrases
using energy analysis and pattern matching. All processing is local.
"""

from __future__ import annotations

import math
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from .models import (
    WakePhrase, WakeWordConfig, WakeWordState, DetectionResult,
    SensitivityLevel, SensitivityProfile, SENSITIVITY_PROFILES,
)


class DetectorState(Enum):
    """Internal detector state."""
    IDLE = "idle"
    MONITORING = "monitoring"
    CANDIDATE = "candidate"
    COOLDOWN = "cooldown"


@dataclass
class AudioFrame:
    """A single audio frame for analysis."""
    data: bytes
    timestamp: float = field(default_factory=time.monotonic)
    sample_rate: int = 16000
    rms: float = 0.0
    peak: float = 0.0

    @property
    def duration_ms(self) -> float:
        return len(self.data) / (self.sample_rate * 2) * 1000


class WakeWordDetector:
    """Core wake word detection engine.

    Processes audio frames, computes energy metrics, and detects wake phrases.
    All processing is local — no audio data leaves the device.
    """

    def __init__(self, *, config: Optional[WakeWordConfig] = None):
        self._config = config or WakeWordConfig()
        self._state = DetectorState.IDLE
        self._phrases: dict[str, WakePhrase] = {}
        self._lock = threading.Lock()
        self._last_detection_time: float = 0.0
        self._false_positive_times: list[float] = []
        self._recent_energies: list[float] = []
        self._noise_floor: float = 0.01
        self._adaptive_threshold: float = self._config.threshold
        self._consecutive_energy_high: int = 0
        self._energy_high_threshold: int = 3
        self._detection_start_time: float = 0.0
        self._event_handlers: dict[str, list[Callable]] = {}
        self._frame_count: int = 0
        self._energy_window: int = 10

        for phrase_str in self._config.enabled_phrases:
            self._phrases[phrase_str] = WakePhrase(phrase=phrase_str, sensitivity=self._config.threshold)

        profile = SENSITIVITY_PROFILES.get(self._config.sensitivity)
        if profile:
            self._adaptive_threshold = profile.threshold

    @property
    def state(self) -> DetectorState:
        return self._state

    @property
    def config(self) -> WakeWordConfig:
        return self._config

    @property
    def adaptive_threshold(self) -> float:
        return self._adaptive_threshold

    @property
    def noise_floor(self) -> float:
        return self._noise_floor

    def on(self, event_name: str, handler: Callable):
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        self._event_handlers[event_name].append(handler)

    def _emit(self, event_name: str, data: dict):
        for handler in self._event_handlers.get(event_name, []):
            try:
                handler(data)
            except Exception:
                pass

    def add_phrase(self, phrase: str, *, sensitivity: float = 0.5,
                   enabled: bool = True) -> WakePhrase:
        with self._lock:
            wp = WakePhrase(phrase=phrase, sensitivity=sensitivity, enabled=enabled, is_custom=True)
            self._phrases[phrase] = wp
            return wp

    def remove_phrase(self, phrase: str) -> bool:
        with self._lock:
            if phrase in self._phrases and self._phrases[phrase].is_custom:
                del self._phrases[phrase]
                return True
            return False

    def enable_phrase(self, phrase: str) -> bool:
        with self._lock:
            if phrase in self._phrases:
                self._phrases[phrase].enabled = True
                return True
            return False

    def disable_phrase(self, phrase: str) -> bool:
        with self._lock:
            if phrase in self._phrases:
                self._phrases[phrase].enabled = False
                return True
            return False

    def get_phrases(self) -> list[WakePhrase]:
        with self._lock:
            return list(self._phrases.values())

    def set_sensitivity(self, level: SensitivityLevel):
        with self._lock:
            self._config.sensitivity = level
            profile = SENSITIVITY_PROFILES.get(level)
            if profile:
                self._adaptive_threshold = profile.threshold
                self._config.cooldown_s = profile.cooldown_s
                self._config.threshold = profile.threshold
            self._emit("sensitivity_changed", {"level": level.value, "threshold": self._adaptive_threshold})

    def set_threshold(self, threshold: float):
        with self._lock:
            self._adaptive_threshold = max(0.0, min(1.0, threshold))
            self._config.threshold = self._adaptive_threshold

    def start(self):
        with self._lock:
            if self._state == DetectorState.IDLE:
                self._state = DetectorState.MONITORING
                self._emit("monitoring_started", {})

    def stop(self):
        with self._lock:
            self._state = DetectorState.IDLE
            self._emit("monitoring_stopped", {})

    def _compute_rms(self, frame: AudioFrame) -> float:
        if frame.rms > 0:
            return frame.rms
        if not frame.data:
            return 0.0
        try:
            samples = []
            for i in range(0, len(frame.data) - 1, 2):
                sample = int.from_bytes(frame.data[i:i+2], byteorder='little', signed=True)
                samples.append(sample / 32768.0)
            if not samples:
                return 0.0
            return math.sqrt(sum(s * s for s in samples) / len(samples))
        except Exception:
            return 0.0

    def _compute_peak(self, frame: AudioFrame) -> float:
        if frame.peak > 0:
            return frame.peak
        if not frame.data:
            return 0.0
        try:
            max_val = 0
            for i in range(0, len(frame.data) - 1, 2):
                sample = abs(int.from_bytes(frame.data[i:i+2], byteorder='little', signed=True))
                max_val = max(max_val, sample)
            return max_val / 32768.0
        except Exception:
            return 0.0

    def _update_noise_floor(self, rms: float):
        if rms < self._noise_floor * 2:
            self._noise_floor = self._noise_floor * 0.95 + rms * 0.05
        self._recent_energies.append(rms)
        if len(self._recent_energies) > self._energy_window:
            self._recent_energies.pop(0)

    def _check_cooldown(self) -> bool:
        if self._last_detection_time == 0:
            return False
        elapsed = time.monotonic() - self._last_detection_time
        return elapsed < self._config.cooldown_s

    def _check_false_positive_rate(self) -> bool:
        now = time.monotonic()
        window = self._config.false_positive_window_s
        self._false_positive_times = [t for t in self._false_positive_times if now - t < window]
        return len(self._false_positive_times) >= self._config.max_false_positives

    def _adapt_threshold(self, confidence: float):
        if not self._config.adaptive_threshold_enabled:
            return
        if confidence > self._adaptive_threshold + 0.2:
            self._adaptive_threshold = min(0.9, self._adaptive_threshold + 0.01)
        elif confidence < self._adaptive_threshold - 0.1:
            self._adaptive_threshold = max(0.2, self._adaptive_threshold - 0.005)

    def _match_phrase(self, energy_level: float, signal_quality: float) -> tuple[str, float]:
        best_phrase = ""
        best_confidence = 0.0

        for phrase_str, phrase in self._phrases.items():
            if not phrase.enabled:
                continue
            base_confidence = min(energy_level * 2.0, 1.0)
            quality_bonus = signal_quality * 0.3
            sensitivity_factor = phrase.sensitivity
            confidence = (base_confidence + quality_bonus) * sensitivity_factor
            confidence = max(0.0, min(1.0, confidence))

            if confidence > best_confidence:
                best_confidence = confidence
                best_phrase = phrase_str

        return best_phrase, best_confidence

    def process_frame(self, frame: AudioFrame) -> Optional[DetectionResult]:
        start_time = time.monotonic()
        self._frame_count += 1

        with self._lock:
            if self._state == DetectorState.IDLE or self._state == DetectorState.COOLDOWN:
                return None

        rms = self._compute_rms(frame)
        peak = self._compute_peak(frame)
        self._update_noise_floor(rms)

        signal_quality = 1.0 - (self._noise_floor / max(rms, 0.001))
        signal_quality = max(0.0, min(1.0, signal_quality))

        energy_level = rms
        phrase, confidence = self._match_phrase(energy_level, signal_quality)

        detection_latency = (time.monotonic() - start_time) * 1000

        if confidence >= self._adaptive_threshold and phrase:
            if self._check_cooldown():
                return DetectionResult(
                    detected=False, phrase=phrase, confidence=confidence,
                    detection_latency_ms=detection_latency,
                    rejected_reason="cooldown",
                    energy_level=energy_level, signal_quality=signal_quality)

            if self._check_false_positive_rate():
                self._emit("false_positive_detected", {"phrase": phrase, "confidence": confidence})
                return DetectionResult(
                    detected=False, phrase=phrase, confidence=confidence,
                    detection_latency_ms=detection_latency, is_false_positive=True,
                    rejected_reason="high_false_positive_rate",
                    energy_level=energy_level, signal_quality=signal_quality)

            self._last_detection_time = time.monotonic()
            self._adapt_threshold(confidence)
            self._emit("wake_word_detected", {"phrase": phrase, "confidence": confidence,
                                                "latency_ms": detection_latency})
            return DetectionResult(
                detected=True, phrase=phrase, confidence=confidence,
                detection_latency_ms=detection_latency,
                energy_level=energy_level, signal_quality=signal_quality)
        else:
            if confidence > 0 and confidence < self._adaptive_threshold * 0.5:
                self._adapt_threshold(confidence)
            return DetectionResult(
                detected=False, phrase=phrase or "", confidence=confidence,
                detection_latency_ms=detection_latency, rejected_reason="below_threshold",
                energy_level=energy_level, signal_quality=signal_quality)

    def snapshot(self) -> dict:
        return {
            "state": self._state.value,
            "adaptive_threshold": round(self._adaptive_threshold, 4),
            "noise_floor": round(self._noise_floor, 6),
            "phrase_count": len(self._phrases),
            "enabled_phrases": [p for p, ph in self._phrases.items() if ph.enabled],
            "frame_count": self._frame_count,
            "config": self._config.to_dict(),
        }

    def reset(self):
        with self._lock:
            self._state = DetectorState.IDLE
            self._last_detection_time = 0.0
            self._false_positive_times.clear()
            self._recent_energies.clear()
            self._noise_floor = 0.01
            self._adaptive_threshold = self._config.threshold
            self._consecutive_energy_high = 0
            self._frame_count = 0
