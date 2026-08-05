"""Voice Identity Models — data structures for voice identity system."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PersonalityType(Enum):
    """Built-in personality profiles."""
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    TECHNICAL = "technical"
    MINIMAL = "minimal"
    COMPANION = "companion"
    TEACHER = "teacher"
    CREATIVE = "creative"
    EXECUTIVE = "executive"
    CUSTOM = "custom"


class SpeakingStyle(Enum):
    """Speaking style presets."""
    CONCISE = "concise"
    VERBOSE = "verbose"
    BALANCED = "balanced"
    TECHNICAL = "technical"
    CONVERSATIONAL = "conversational"
    FORMAL = "formal"
    CASUAL = "casual"
    CUSTOM = "custom"


class AdaptationContext(Enum):
    """Context types for automatic adaptation."""
    CODING = "coding"
    DESIGN = "design"
    RESEARCH = "research"
    MEETING = "meeting"
    TEACHING = "teaching"
    QUICK_COMMAND = "quick_command"
    GENERAL = "general"
    ERROR_RECOVERY = "error_recovery"
    SUCCESS = "success"
    CUSTOM = "custom"


@dataclass
class SpeakingStyleConfig:
    """Detailed speaking style configuration."""
    speech_rate: float = 1.0
    pause_duration_ms: float = 200.0
    sentence_pacing: float = 1.0
    emphasis_strength: float = 0.5
    response_length: str = "medium"
    confirmation_frequency: float = 0.3
    technical_wording: bool = False
    natural_wording: bool = True
    filler_usage: float = 0.1
    pitch_offset: float = 0.0

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, data: dict) -> "SpeakingStyleConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class VoiceProfile:
    """A complete voice identity profile."""
    profile_id: str
    name: str
    personality: PersonalityType
    style: SpeakingStyleConfig = field(default_factory=SpeakingStyleConfig)
    confirmation_phrases: list[str] = field(default_factory=list)
    filler_words: list[str] = field(default_factory=list)
    greeting: str = ""
    farewell: str = ""
    error_prefix: str = ""
    success_prefix: str = ""
    verbosity: float = 0.5
    sentence_rhythm: float = 1.0
    is_builtin: bool = False
    created_at: float = field(default_factory=time.monotonic)
    updated_at: float = field(default_factory=time.monotonic)

    def to_dict(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "personality": self.personality.value,
            "style": self.style.to_dict(),
            "confirmation_phrases": list(self.confirmation_phrases),
            "filler_words": list(self.filler_words),
            "greeting": self.greeting,
            "farewell": self.farewell,
            "error_prefix": self.error_prefix,
            "success_prefix": self.success_prefix,
            "verbosity": self.verbosity,
            "sentence_rhythm": self.sentence_rhythm,
            "is_builtin": self.is_builtin,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class PronunciationEntry:
    """A single pronunciation override."""
    word: str
    phonetic: str
    language: str = "en"
    category: str = "custom"
    notes: str = ""
    created_at: float = field(default_factory=time.monotonic)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class IdentityPreferences:
    """User voice preferences."""
    preferred_voice: str = "default"
    preferred_provider: str = ""
    speech_speed: float = 1.0
    pitch: float = 0.0
    verbosity: float = 0.5
    confirmation_style: str = "brief"
    preferred_profile: str = "friendly"
    preferred_pronunciation_lang: str = "en"
    address_user_as: str = ""
    created_at: float = field(default_factory=time.monotonic)
    updated_at: float = field(default_factory=time.monotonic)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, data: dict) -> "IdentityPreferences":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class IdentitySnapshot:
    """Snapshot of identity system state for diagnostics."""
    timestamp: float
    uptime_seconds: float
    active_profile: str
    active_personality: str
    active_style: str
    active_context: str
    profile_count: int
    pronunciation_count: int
    adaptations_today: int
    avg_adaptation_latency_ms: float
    preferences_loaded: bool
    memory_status: str

    def to_dict(self) -> dict:
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in self.__dict__.items()}


CONTEXT_TO_PROFILE_MAP = {
    AdaptationContext.CODING: PersonalityType.TECHNICAL,
    AdaptationContext.DESIGN: PersonalityType.CREATIVE,
    AdaptationContext.RESEARCH: PersonalityType.PROFESSIONAL,
    AdaptationContext.MEETING: PersonalityType.EXECUTIVE,
    AdaptationContext.TEACHING: PersonalityType.TEACHER,
    AdaptationContext.QUICK_COMMAND: PersonalityType.MINIMAL,
    AdaptationContext.GENERAL: PersonalityType.FRIENDLY,
    AdaptationContext.ERROR_RECOVERY: PersonalityType.MINIMAL,
    AdaptationContext.SUCCESS: PersonalityType.FRIENDLY,
}
