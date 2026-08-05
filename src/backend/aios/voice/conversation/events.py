"""Conversation Events — event types for continuous conversation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ConversationEventType(Enum):
    CONVERSATION_STARTED = "conversation_started"
    CONVERSATION_ENDED = "conversation_ended"
    TURN_STARTED = "turn_started"
    TURN_COMPLETED = "turn_completed"
    FOLLOW_UP_DETECTED = "follow_up_detected"
    CONVERSATION_RESUMED = "conversation_resumed"
    CONVERSATION_TIMED_OUT = "conversation_timed_out"
    USER_INTERRUPTED = "user_interrupted"
    BARGE_IN = "barge_in"
    PAUSE_DETECTED = "pause_detected"
    RESPONSE_READY = "response_ready"
    LISTENING_RESUMED = "listening_resumed"


@dataclass
class Turn:
    """A single turn in the conversation."""
    turn_number: int
    user_text: str = ""
    eve_response: str = ""
    is_follow_up: bool = False
    is_interrupted: bool = False
    confidence: float = 0.0
    start_time: float = 0.0
    end_time: float = 0.0
    response_latency_ms: float = 0.0

    @property
    def duration_ms(self) -> float:
        if self.end_time > 0 and self.start_time > 0:
            return (self.end_time - self.start_time) * 1000
        return 0.0

    def to_dict(self) -> dict:
        return {
            "turn_number": self.turn_number, "user_text": self.user_text,
            "eve_response": self.eve_response, "is_follow_up": self.is_follow_up,
            "is_interrupted": self.is_interrupted, "confidence": round(self.confidence, 4),
            "start_time": self.start_time, "end_time": self.end_time,
            "duration_ms": round(self.duration_ms, 3),
            "response_latency_ms": round(self.response_latency_ms, 3),
        }


@dataclass
class ConversationEvent:
    """Event data for conversation events."""
    event_type: ConversationEventType
    session_id: str = ""
    turn_number: int = 0
    text: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"event_type": self.event_type.value, "session_id": self.session_id,
                "turn_number": self.turn_number, "text": self.text, "metadata": self.metadata}
