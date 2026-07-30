"""Data models for the voice interface."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class STTProvider(str, Enum):
    GOOGLE = "google"
    WHISPER = "whisper"
    SPHINX = "sphinx"
    AZURE = "azure"
    MOCK = "mock"


class TTSProvider(str, Enum):
    PYTTSX3 = "pyttsx3"
    EDGE = "edge"
    AZURE = "azure"
    MOCK = "mock"


class TranscriptStatus(str, Enum):
    PARTIAL = "partial"
    FINAL = "final"


class VoiceState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"


@dataclass
class Transcript:
    text: str = ""
    status: TranscriptStatus = TranscriptStatus.PARTIAL
    confidence: float = 0.0
    language: str = "en"
    timestamp: datetime | None = None
    is_final: bool = False

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc)
        if isinstance(self.status, str):
            self.status = TranscriptStatus(self.status)
        if self.status == TranscriptStatus.FINAL:
            self.is_final = True


@dataclass
class VoiceConfig:
    stt_provider: STTProvider = STTProvider.WHISPER
    tts_provider: TTSProvider = TTSProvider.PYTTSX3
    input_device: str | None = None
    output_device: str | None = None
    language: str = "en-US"
    voice_id: str = ""
    speaking_rate: float = 1.0
    pitch: float = 1.0
    push_to_talk_key: str = "v"
    wake_word_enabled: bool = False
    wake_word: str = "hey eve"
    continuous_listening: bool = False
    auto_detect_language: bool = False
    vad_enabled: bool = True
    vad_threshold: float = 0.5


@dataclass
class VoiceEvent:
    event_type: str = ""
    session_id: str = ""
    data: dict = field(default_factory=dict)
    timestamp: datetime | None = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class STTResult:
    text: str = ""
    confidence: float = 0.0
    language: str = "en"
    is_final: bool = False
    duration_ms: float = 0.0
    error: str | None = None


@dataclass
class TTSRequest:
    text: str = ""
    voice_id: str = ""
    rate: float = 1.0
    pitch: float = 1.0
    priority: int = 0
    utterance_id: str = ""

    def __post_init__(self):
        if not self.utterance_id:
            self.utterance_id = uuid4().hex


@dataclass
class AudioDevice:
    id: str = ""
    name: str = ""
    is_default: bool = False
    channels: int = 1
    sample_rate: int = 16000


@dataclass
class VoiceSessionState:
    session_id: str = ""
    conversation_id: str = ""
    state: VoiceState = VoiceState.IDLE
    is_listening: bool = False
    is_speaking: bool = False
    current_transcript: str = ""
    audio_level: float = 0.0
    error: str | None = None
    started_at: datetime | None = None

    def __post_init__(self):
        if not self.session_id:
            self.session_id = uuid4().hex
        if not self.started_at:
            self.started_at = datetime.now(timezone.utc)
        if isinstance(self.state, str):
            self.state = VoiceState(self.state)
