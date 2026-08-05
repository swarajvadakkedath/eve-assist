"""Voice Identity Events — event types for identity system."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class IdentityEventType(Enum):
    """Events published by the identity system."""
    IDENTITY_LOADED = "identity_loaded"
    IDENTITY_CHANGED = "identity_changed"
    PROFILE_CHANGED = "profile_changed"
    PRONUNCIATION_UPDATED = "pronunciation_updated"
    PREFERENCES_CHANGED = "preferences_changed"
    VOICE_CHANGED = "voice_changed"
    SPEAKING_STYLE_CHANGED = "speaking_style_changed"
    ADAPTATION_TRIGGERED = "adaptation_triggered"


@dataclass
class IdentityEvent:
    """Event data for identity events."""
    event_type: IdentityEventType
    profile_id: str = ""
    context: str = ""
    previous_profile: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "profile_id": self.profile_id,
            "context": self.context,
            "previous_profile": self.previous_profile,
            "metadata": self.metadata,
        }
