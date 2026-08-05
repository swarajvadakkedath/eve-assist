"""Sensitivity profiles for voice activity detection.

Each profile defines thresholds and timeouts optimized for a specific
environment. Profiles are applied automatically or selected by the user.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ProfileType(Enum):
    """Built-in sensitivity profiles."""
    QUIET_ROOM = "quiet_room"
    OFFICE = "office"
    CONFERENCE = "conference"
    CAFE = "cafe"
    HEADSET = "headset"
    EXTERNAL_MIC = "external_mic"
    CUSTOM = "custom"


@dataclass
class VoiceProfile:
    """Configuration profile for VAD sensitivity.

    Attributes:
        profile_type: Profile identifier
        name: Human-readable name
        noise_threshold: RMS amplitude below which audio is considered silence (0.0-1.0)
        speech_threshold: RMS amplitude above which audio is considered speech (0.0-1.0)
        silence_timeout: Seconds of silence before speech end is triggered
        short_pause_timeout: Seconds of silence before a short pause is detected
        long_pause_timeout: Seconds of silence before a long pause is detected
        speech_min_duration: Minimum speech duration to be considered valid (seconds)
        speech_max_duration: Maximum speech duration before forced end (seconds)
        confidence_threshold: Minimum speech confidence to trigger speech start (0.0-1.0)
        gain: Automatic gain multiplier (1.0 = no gain)
        energy_window_ms: Window size for energy calculation (milliseconds)
        hangover_ms: Keep speech state for this many ms after energy drops (prevents choppiness)
        frame_duration_ms: Duration of each audio frame for analysis (milliseconds)
    """
    profile_type: ProfileType = ProfileType.QUIET_ROOM
    name: str = "Quiet Room"
    noise_threshold: float = 0.01
    speech_threshold: float = 0.05
    silence_timeout: float = 1.5
    short_pause_timeout: float = 0.5
    long_pause_timeout: float = 5.0
    speech_min_duration: float = 0.1
    speech_max_duration: float = 30.0
    confidence_threshold: float = 0.6
    gain: float = 1.0
    energy_window_ms: int = 30
    hangover_ms: int = 300
    frame_duration_ms: int = 30

    def to_dict(self) -> dict:
        return {
            "profile_type": self.profile_type.value,
            "name": self.name,
            "noise_threshold": self.noise_threshold,
            "speech_threshold": self.speech_threshold,
            "silence_timeout": self.silence_timeout,
            "short_pause_timeout": self.short_pause_timeout,
            "long_pause_timeout": self.long_pause_timeout,
            "speech_min_duration": self.speech_min_duration,
            "speech_max_duration": self.speech_max_duration,
            "confidence_threshold": self.confidence_threshold,
            "gain": self.gain,
            "energy_window_ms": self.energy_window_ms,
            "hangover_ms": self.hangover_ms,
            "frame_duration_ms": self.frame_duration_ms,
        }


# Built-in profiles
PROFILES: dict[ProfileType, VoiceProfile] = {
    ProfileType.QUIET_ROOM: VoiceProfile(
        profile_type=ProfileType.QUIET_ROOM,
        name="Quiet Room",
        noise_threshold=0.01,
        speech_threshold=0.05,
        silence_timeout=1.5,
        short_pause_timeout=0.5,
        long_pause_timeout=5.0,
        speech_min_duration=0.1,
        speech_max_duration=30.0,
        confidence_threshold=0.6,
        gain=1.0,
        energy_window_ms=30,
        hangover_ms=300,
    ),
    ProfileType.OFFICE: VoiceProfile(
        profile_type=ProfileType.OFFICE,
        name="Office",
        noise_threshold=0.03,
        speech_threshold=0.08,
        silence_timeout=1.2,
        short_pause_timeout=0.4,
        long_pause_timeout=4.0,
        speech_min_duration=0.1,
        speech_max_duration=30.0,
        confidence_threshold=0.65,
        gain=1.2,
        energy_window_ms=30,
        hangover_ms=250,
    ),
    ProfileType.CONFERENCE: VoiceProfile(
        profile_type=ProfileType.CONFERENCE,
        name="Conference Room",
        noise_threshold=0.05,
        speech_threshold=0.12,
        silence_timeout=2.0,
        short_pause_timeout=0.8,
        long_pause_timeout=6.0,
        speech_min_duration=0.15,
        speech_max_duration=60.0,
        confidence_threshold=0.7,
        gain=1.5,
        energy_window_ms=40,
        hangover_ms=400,
    ),
    ProfileType.CAFE: VoiceProfile(
        profile_type=ProfileType.CAFE,
        name="Cafe",
        noise_threshold=0.08,
        speech_threshold=0.15,
        silence_timeout=1.0,
        short_pause_timeout=0.3,
        long_pause_timeout=3.0,
        speech_min_duration=0.15,
        speech_max_duration=30.0,
        confidence_threshold=0.75,
        gain=1.8,
        energy_window_ms=50,
        hangover_ms=350,
    ),
    ProfileType.HEADSET: VoiceProfile(
        profile_type=ProfileType.HEADSET,
        name="Headset",
        noise_threshold=0.02,
        speech_threshold=0.06,
        silence_timeout=1.5,
        short_pause_timeout=0.5,
        long_pause_timeout=5.0,
        speech_min_duration=0.1,
        speech_max_duration=30.0,
        confidence_threshold=0.55,
        gain=1.0,
        energy_window_ms=25,
        hangover_ms=200,
    ),
    ProfileType.EXTERNAL_MIC: VoiceProfile(
        profile_type=ProfileType.EXTERNAL_MIC,
        name="External Microphone",
        noise_threshold=0.025,
        speech_threshold=0.07,
        silence_timeout=1.5,
        short_pause_timeout=0.5,
        long_pause_timeout=5.0,
        speech_min_duration=0.1,
        speech_max_duration=30.0,
        confidence_threshold=0.6,
        gain=1.1,
        energy_window_ms=30,
        hangover_ms=280,
    ),
}


def get_profile(profile_type: ProfileType) -> VoiceProfile:
    """Get a built-in profile by type."""
    if profile_type in PROFILES:
        # Return a copy to prevent mutation
        import copy
        return copy.deepcopy(PROFILES[profile_type])
    raise ValueError(f"Unknown profile type: {profile_type}")


def list_profiles() -> list[VoiceProfile]:
    """List all built-in profiles."""
    import copy
    return [copy.deepcopy(p) for p in PROFILES.values()]


def create_custom_profile(name: str, **kwargs) -> VoiceProfile:
    """Create a custom profile with overrides.

    Any unspecified fields use Quiet Room defaults.
    """
    base = get_profile(ProfileType.QUIET_ROOM)
    base.profile_type = ProfileType.CUSTOM
    base.name = name
    for key, value in kwargs.items():
        if hasattr(base, key):
            setattr(base, key, value)
    return base
