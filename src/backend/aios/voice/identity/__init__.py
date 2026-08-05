"""Voice Identity — EVE's spoken identity system."""

from .models import (
    VoiceProfile, PersonalityType, SpeakingStyle, SpeakingStyleConfig,
    AdaptationContext, IdentityPreferences, IdentitySnapshot,
    PronunciationEntry, CONTEXT_TO_PROFILE_MAP,
)
from .events import IdentityEvent, IdentityEventType
from .personality import BUILTIN_PROFILES, get_builtin_profile, list_builtin_profiles
from .adaptation import ContextAdapter, AdaptationResult, AdaptationReason
from .pronunciation import PronunciationDictionary
from .preferences import PreferenceManager
from .metrics import IdentityMetrics, IdentityMetricsSnapshot
from .manager import VoiceIdentityManager

__all__ = [
    "VoiceProfile", "PersonalityType", "SpeakingStyle", "SpeakingStyleConfig",
    "AdaptationContext", "IdentityPreferences", "IdentitySnapshot",
    "PronunciationEntry", "CONTEXT_TO_PROFILE_MAP",
    "IdentityEvent", "IdentityEventType",
    "BUILTIN_PROFILES", "get_builtin_profile", "list_builtin_profiles",
    "ContextAdapter", "AdaptationResult", "AdaptationReason",
    "PronunciationDictionary", "PreferenceManager",
    "IdentityMetrics", "IdentityMetricsSnapshot",
    "VoiceIdentityManager",
]
