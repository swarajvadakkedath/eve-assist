"""TTS Events — event types for the streaming TTS layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TTSEventType(Enum):
    SYNTHESIS_STARTED = "synthesis_started"
    SYNTHESIS_COMPLETED = "synthesis_completed"
    SYNTHESIS_FAILED = "synthesis_failed"
    CHUNK_READY = "chunk_ready"
    PLAYBACK_STARTED = "playback_started"
    PLAYBACK_PAUSED = "playback_paused"
    PLAYBACK_RESUMED = "playback_resumed"
    PLAYBACK_COMPLETED = "playback_completed"
    PLAYBACK_CANCELLED = "playback_cancelled"
    PROVIDER_SWITCHED = "provider_switched"
    QUEUE_CHANGED = "queue_changed"
    INTERRUPTED = "interrupted"


@dataclass
class SpeechChunk:
    """A chunk of synthesized audio ready for playback."""
    audio_data: bytes
    chunk_index: int = 0
    text: str = ""
    is_final: bool = False
    sample_rate: int = 22050
    channels: int = 1
    sample_width: int = 2
    duration_ms: float = 0.0
    timestamp: float = 0.0

    @property
    def size_bytes(self) -> int:
        return len(self.audio_data)

    def to_dict(self) -> dict:
        return {
            "chunk_index": self.chunk_index, "text": self.text, "is_final": self.is_final,
            "sample_rate": self.sample_rate, "channels": self.channels,
            "sample_width": self.sample_width, "duration_ms": round(self.duration_ms, 3),
            "size_bytes": self.size_bytes, "timestamp": self.timestamp,
        }


@dataclass
class TTSRequest:
    """A TTS synthesis request."""
    text: str
    voice: str = ""
    speed: float = 1.0
    priority: int = 0
    request_id: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"text": self.text, "voice": self.voice, "speed": self.speed,
                "priority": self.priority, "request_id": self.request_id}
