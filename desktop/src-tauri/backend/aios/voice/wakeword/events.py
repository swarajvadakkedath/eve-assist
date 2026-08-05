"""Wake Word Events — event types for wake word detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class WakeWordEventType(Enum):
    """Events published by the wake word engine."""
    WAKE_WORD_DETECTED = "wake_word_detected"
    WAKE_WORD_REJECTED = "wake_word_rejected"
    WAKE_WORD_TIMEOUT = "wake_word_timeout"
    WAKE_SESSION_STARTED = "wake_session_started"
    WAKE_SESSION_ENDED = "wake_session_ended"
    FALSE_POSITIVE_DETECTED = "false_positive_detected"
    SENSITIVITY_CHANGED = "sensitivity_changed"


@dataclass
class WakeWordEvent:
    """Event data for wake word events."""
    event_type: WakeWordEventType
    session_id: str = ""
    phrase: str = ""
    confidence: float = 0.0
    detection_latency_ms: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "session_id": self.session_id,
            "phrase": self.phrase,
            "confidence": round(self.confidence, 4),
            "detection_latency_ms": round(self.detection_latency_ms, 3),
            "metadata": self.metadata,
        }
