"""Voice Personality Framework — EVE's voice persona and style.

Defines how EVE sounds and communicates through voice:
  - Voice persona (name, personality traits, communication style)
  - Tone profiles for different contexts (casual, professional, error, excited)
  - TTS formatting rules (remove markdown, expand abbreviations, etc.)
  - Response style guidelines (concise vs verbose, formal vs friendly)

The framework is configuration-driven — no hardcoded voice attributes.
Personality is applied AFTER the LLM generates text and BEFORE TTS.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from aios.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Tone profiles
# ---------------------------------------------------------------------------

class ToneProfile(str, Enum):
    """Pre-defined tone profiles for different contexts."""
    CASUAL = "casual"
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    TECHNICAL = "technical"
    ERROR = "error"
    EXCITED = "excited"
    CALM = "calm"
    APOLOGETIC = "apologetic"


@dataclass
class Tone:
    """A tone configuration for voice output."""
    profile: ToneProfile = ToneProfile.FRIENDLY
    formality: float = 0.5        # 0=casual, 1=formal
    enthusiasm: float = 0.5       # 0=calm, 1=excited
    verbosity: float = 0.5        # 0=concise, 1=verbose
    warmth: float = 0.7           # 0=cold, 1=warm
    confidence: float = 0.8       # 0=hesitant, 1=confident
    emoji_usage: bool = False     # whether to include emoji in TTS text
    pause_after_greeting: float = 0.3  # seconds pause after greeting


# Pre-defined tone profiles
TONE_PROFILES: dict[ToneProfile, Tone] = {
    ToneProfile.CASUAL: Tone(
        profile=ToneProfile.CASUAL,
        formality=0.2,
        enthusiasm=0.5,
        verbosity=0.3,
        warmth=0.8,
        confidence=0.7,
    ),
    ToneProfile.PROFESSIONAL: Tone(
        profile=ToneProfile.PROFESSIONAL,
        formality=0.8,
        enthusiasm=0.3,
        verbosity=0.5,
        warmth=0.5,
        confidence=0.9,
    ),
    ToneProfile.FRIENDLY: Tone(
        profile=ToneProfile.FRIENDLY,
        formality=0.3,
        enthusiasm=0.6,
        verbosity=0.4,
        warmth=0.9,
        confidence=0.8,
    ),
    ToneProfile.TECHNICAL: Tone(
        profile=ToneProfile.TECHNICAL,
        formality=0.7,
        enthusiasm=0.2,
        verbosity=0.6,
        warmth=0.3,
        confidence=0.95,
    ),
    ToneProfile.ERROR: Tone(
        profile=ToneProfile.ERROR,
        formality=0.4,
        enthusiasm=0.1,
        verbosity=0.3,
        warmth=0.6,
        confidence=0.5,
    ),
    ToneProfile.EXCITED: Tone(
        profile=ToneProfile.EXCITED,
        formality=0.2,
        enthusiasm=0.9,
        verbosity=0.5,
        warmth=0.8,
        confidence=0.9,
    ),
    ToneProfile.CALM: Tone(
        profile=ToneProfile.CALM,
        formality=0.5,
        enthusiasm=0.2,
        verbosity=0.3,
        warmth=0.7,
        confidence=0.7,
    ),
    ToneProfile.APOLOGETIC: Tone(
        profile=ToneProfile.APOLOGETIC,
        formality=0.5,
        enthusiasm=0.1,
        verbosity=0.4,
        warmth=0.8,
        confidence=0.4,
    ),
}


# ---------------------------------------------------------------------------
# Voice personality
# ---------------------------------------------------------------------------

@dataclass
class VoicePersonality:
    """EVE's voice personality configuration."""
    name: str = "EVE"
    tagline: str = "Your AI operating system"
    default_tone: ToneProfile = ToneProfile.FRIENDLY
    traits: list[str] = field(default_factory=lambda: [
        "helpful",
        "concise",
        "knowledgeable",
        "friendly",
        "reliable",
    ])
    greeting: str = "Hi, I'm EVE. How can I help?"
    farewell: str = "Goodbye! Let me know if you need anything."
    # TTS formatting
    remove_markdown: bool = True
    expand_abbreviations: bool = True
    spell_out_numbers: bool = False
    max_sentence_length: int = 25  # words — split longer sentences
    # Style guidelines
    use_contractions: bool = True
    avoid_jargon: bool = True
    max_response_length_words: int = 150  # for voice, keep responses short
    # Context-specific tones
    context_tones: dict[str, ToneProfile] = field(default_factory=lambda: {
        "error": ToneProfile.ERROR,
        "apology": ToneProfile.APOLOGETIC,
        "success": ToneProfile.EXCITED,
        "information": ToneProfile.PROFESSIONAL,
        "greeting": ToneProfile.FRIENDLY,
        "farewell": ToneProfile.FRIENDLY,
        "clarification": ToneProfile.CALM,
    })


# ---------------------------------------------------------------------------
# TTS text formatter
# ---------------------------------------------------------------------------

# Common abbreviations to expand for TTS
_ABBREVIATIONS: dict[str, str] = {
    "API": "A P I",
    "URL": "U R L",
    "HTTP": "H T T P",
    "HTTPS": "H T T P S",
    "JSON": "J-S-O-N",
    "SQL": "S-Q-L",
    "UI": "user interface",
    "UX": "user experience",
    "OS": "operating system",
    "AI": "A I",
    "ML": "machine learning",
    "CPU": "C P U",
    "GPU": "G P U",
    "RAM": "RAM",
    "SSD": "S S D",
    "PC": "P C",
    "DIY": "do it yourself",
    "FAQ": "frequently asked questions",
    "PTT": "push to talk",
    "VAD": "voice activity detection",
    "TTS": "text to speech",
    "STT": "speech to text",
}


def format_for_tts(text: str, personality: VoicePersonality | None = None) -> str:
    """Format text for TTS output.

    Applies personality-driven formatting rules:
      1. Remove markdown formatting
      2. Expand abbreviations
      3. Split long sentences
      4. Remove emoji
      5. Clean up punctuation for natural speech
    """
    if not text:
        return text

    result = text

    # Remove markdown
    if personality is None or personality.remove_markdown:
        result = _remove_markdown(result)

    # Remove emoji
    result = _remove_emoji(result)

    # Expand abbreviations
    if personality is None or personality.expand_abbreviations:
        result = _expand_abbreviations(result)

    # Clean up punctuation
    result = _clean_punctuation(result)

    return result.strip()


def _remove_markdown(text: str) -> str:
    """Remove markdown formatting for TTS."""
    import re
    # Remove code blocks
    text = re.sub(r"```[\s\S]*?```", "code block omitted", text)
    # Remove inline code
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Remove bold/italic
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
    # Remove headings
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove links
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove images
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    # Remove horizontal rules
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    # Remove blockquotes
    text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)
    # Remove list markers
    text = re.sub(r"^[\s]*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[\s]*\d+\.\s+", "", text, flags=re.MULTILINE)
    return text


def _remove_emoji(text: str) -> str:
    """Remove emoji characters from text."""
    import re
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001f926-\U0001f937"
        "\U00010000-\U0010ffff"
        "\u200d"
        "\u2640-\u2642"
        "\ufe0f"
        "\u2600-\u2B55"
        "\u23cf"
        "\u23e9"
        "\u231a"
        "\u3030"
        "\u2934"
        "\u2935"
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub("", text)


def _expand_abbreviations(text: str) -> str:
    """Expand abbreviations for natural TTS pronunciation."""
    import re
    result = text
    for abbr, expansion in _ABBREVIATIONS.items():
        # Match whole-word abbreviations
        result = re.sub(rf"\b{re.escape(abbr)}\b", expansion, result)
    return result


def _clean_punctuation(text: str) -> str:
    """Clean up punctuation for natural speech flow."""
    import re
    # Replace multiple punctuation with single
    text = re.sub(r"[.]{2,}", ".", text)
    text = re.sub(r"[!]{2,}", "!", text)
    text = re.sub(r"[?]{2,}", "?", text)
    # Remove ellipsis (replace with pause indication)
    text = re.sub(r"\.{3,}", "...", text)
    # Clean up commas
    text = re.sub(r",{2,}", ",", text)
    return text


# ---------------------------------------------------------------------------
# Voice personality manager
# ---------------------------------------------------------------------------

class VoicePersonalityManager:
    """Manages EVE's voice personality and applies it to responses."""

    def __init__(self, personality: VoicePersonality | None = None):
        self._personality = personality or VoicePersonality()
        self._current_tone = TONE_PROFILES[self._personality.default_tone]

    @property
    def personality(self) -> VoicePersonality:
        return self._personality

    @property
    def current_tone(self) -> Tone:
        return self._current_tone

    def set_tone(self, profile: ToneProfile) -> None:
        """Switch the active tone profile."""
        self._current_tone = TONE_PROFILES.get(profile, self._current_tone)
        logger.info("voice_personality.tone_changed", profile=profile.value)

    def set_context_tone(self, context: str) -> None:
        """Set tone based on context (error, success, greeting, etc.)."""
        profile = self._personality.context_tones.get(context)
        if profile:
            self.set_tone(profile)

    def format_response(self, text: str, context: str | None = None) -> str:
        """Apply voice personality to a response.

        This is the main entry point — call after LLM generates text,
        before sending to TTS.
        """
        if context:
            self.set_context_tone(context)
        return format_for_tts(text, self._personality)

    def get_greeting(self) -> str:
        """Return the personality's greeting."""
        return self._personality.greeting

    def get_farewell(self) -> str:
        """Return the personality's farewell."""
        return self._personality.farewell

    def to_dict(self) -> dict:
        """Export personality configuration."""
        return {
            "name": self._personality.name,
            "tagline": self._personality.tagline,
            "default_tone": self._personality.default_tone.value,
            "traits": self._personality.traits,
            "greeting": self._personality.greeting,
            "farewell": self._personality.farewell,
            "current_tone": self._current_tone.profile.value,
            "tone_config": {
                "formality": self._current_tone.formality,
                "enthusiasm": self._current_tone.enthusiasm,
                "verbosity": self._current_tone.verbosity,
                "warmth": self._current_tone.warmth,
                "confidence": self._current_tone.confidence,
            },
        }
