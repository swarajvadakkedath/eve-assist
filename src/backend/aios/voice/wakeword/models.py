"""Wake Word models — data structures for wake word detection."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class WakeWordState(Enum):
    """Wake word engine state."""
    IDLE = "idle"
    MONITORING = "monitoring"
    DETECTING = "detecting"
    ACTIVATED = "activated"
    COOLDOWN = "cooldown"
    DISABLED = "disabled"


class SensitivityLevel(Enum):
    """Wake word sensitivity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CUSTOM = "custom"


class PowerMode(Enum):
    """Power management modes."""
    ACTIVE = "active"
    LOW_POWER = "low_power"
    IDLE = "idle"
    BATTERY_SAVER = "battery_saver"


@dataclass
class WakePhrase:
    """A wake phrase configuration."""
    phrase: str
    enabled: bool = True
    sensitivity: float = 0.5
    is_custom: bool = False
    created_at: float = field(default_factory=time.monotonic)

    def to_dict(self) -> dict:
        return {
            "phrase": self.phrase,
            "enabled": self.enabled,
            "sensitivity": round(self.sensitivity, 4),
            "is_custom": self.is_custom,
            "created_at": self.created_at,
        }


@dataclass
class SensitivityProfile:
    """Sensitivity configuration profile."""
    level: SensitivityLevel
    threshold: float
    cooldown_s: float
    max_confidence_drop: float
    false_positive_window_s: float

    def to_dict(self) -> dict:
        return {
            "level": self.level.value,
            "threshold": self.threshold,
            "cooldown_s": self.cooldown_s,
            "max_confidence_drop": self.max_confidence_drop,
            "false_positive_window_s": self.false_positive_window_s,
        }


@dataclass
class DetectionResult:
    """Result of a wake word detection attempt."""
    detected: bool
    phrase: str
    confidence: float
    detection_latency_ms: float
    timestamp: float = field(default_factory=time.monotonic)
    is_false_positive: bool = False
    rejected_reason: str = ""
    energy_level: float = 0.0
    signal_quality: float = 0.0

    def to_dict(self) -> dict:
        return {
            "detected": self.detected,
            "phrase": self.phrase,
            "confidence": round(self.confidence, 4),
            "detection_latency_ms": round(self.detection_latency_ms, 3),
            "timestamp": self.timestamp,
            "is_false_positive": self.is_false_positive,
            "rejected_reason": self.rejected_reason,
            "energy_level": round(self.energy_level, 4),
            "signal_quality": round(self.signal_quality, 4),
        }


@dataclass
class WakeWordConfig:
    """Configuration for the wake word engine."""
    enabled_phrases: list[str] = field(default_factory=lambda: ["EVE", "Hey EVE", "Okay EVE"])
    sensitivity: SensitivityLevel = SensitivityLevel.MEDIUM
    threshold: float = 0.5
    cooldown_s: float = 2.0
    false_positive_window_s: float = 30.0
    max_false_positives: int = 3
    adaptive_threshold_enabled: bool = True
    power_mode: PowerMode = PowerMode.ACTIVE
    monitoring_interval_ms: int = 100
    max_detection_latency_ms: float = 100.0
    privacy_mode: bool = True
    cpu_throttle_percent: float = 0.01
    battery_threshold_percent: float = 20.0

    def to_dict(self) -> dict:
        return {
            "enabled_phrases": list(self.enabled_phrases),
            "sensitivity": self.sensitivity.value,
            "threshold": self.threshold,
            "cooldown_s": self.cooldown_s,
            "false_positive_window_s": self.false_positive_window_s,
            "max_false_positives": self.max_false_positives,
            "adaptive_threshold_enabled": self.adaptive_threshold_enabled,
            "power_mode": self.power_mode.value,
            "monitoring_interval_ms": self.monitoring_interval_ms,
            "max_detection_latency_ms": self.max_detection_latency_ms,
            "privacy_mode": self.privacy_mode,
            "cpu_throttle_percent": self.cpu_throttle_percent,
            "battery_threshold_percent": self.battery_threshold_percent,
        }


SENSITIVITY_PROFILES = {
    SensitivityLevel.LOW: SensitivityProfile(
        level=SensitivityLevel.LOW, threshold=0.7, cooldown_s=3.0,
        max_confidence_drop=0.3, false_positive_window_s=60.0),
    SensitivityLevel.MEDIUM: SensitivityProfile(
        level=SensitivityLevel.MEDIUM, threshold=0.5, cooldown_s=2.0,
        max_confidence_drop=0.2, false_positive_window_s=30.0),
    SensitivityLevel.HIGH: SensitivityProfile(
        level=SensitivityLevel.HIGH, threshold=0.3, cooldown_s=1.0,
        max_confidence_drop=0.1, false_positive_window_s=15.0),
}
