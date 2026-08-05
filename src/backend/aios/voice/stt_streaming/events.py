"""Speech Recognition Events — event types for the streaming STT layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TranscriptEventType(Enum):
    PARTIAL_TRANSCRIPT = "partial_transcript"
    FINAL_TRANSCRIPT = "final_transcript"
    PROVIDER_CONNECTED = "provider_connected"
    PROVIDER_DISCONNECTED = "provider_disconnected"
    PROVIDER_SWITCHED = "provider_switched"
    RECOGNITION_STARTED = "recognition_started"
    RECOGNITION_STOPPED = "recognition_stopped"
    RECOGNITION_RECOVERED = "recognition_recovered"
    RECOGNITION_FAILED = "recognition_failed"


@dataclass
class TranscriptEvent:
    event_type: TranscriptEventType
    session_id: str = ""
    text: str = ""
    confidence: float = 0.0
    words: list = field(default_factory=list)
    provider: str = ""
    timestamp: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value, "session_id": self.session_id,
            "text": self.text, "confidence": round(self.confidence, 4),
            "words": self.words, "provider": self.provider,
            "timestamp": self.timestamp, "metadata": self.metadata,
        }


@dataclass
class WordTiming:
    word: str
    start_ms: float
    end_ms: float
    confidence: float = 0.0
    speaker: str = ""

    def to_dict(self) -> dict:
        return {"word": self.word, "start_ms": round(self.start_ms, 2),
                "end_ms": round(self.end_ms, 2), "confidence": round(self.confidence, 4),
                "speaker": self.speaker}
