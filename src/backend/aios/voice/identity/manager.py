"""Voice Identity Manager — single entry point for voice identity system.

Sits between Hermes and Streaming TTS. Controls HOW EVE speaks.
"""

from __future__ import annotations

import time
import threading
from typing import Callable, Optional

from .models import (
    VoiceProfile, PersonalityType, SpeakingStyle, SpeakingStyleConfig,
    AdaptationContext, IdentityPreferences, IdentitySnapshot, PronunciationEntry,
)
from .events import IdentityEvent, IdentityEventType
from .personality import BUILTIN_PROFILES, get_builtin_profile, list_builtin_profiles
from .adaptation import ContextAdapter, AdaptationResult, AdaptationReason
from .pronunciation import PronunciationDictionary
from .preferences import PreferenceManager
from .metrics import IdentityMetrics


class VoiceIdentityManager:
    """Single entry point for the voice identity system.

    Controls personality, speaking style, context adaptation,
    pronunciation, and preferences. Sits between Hermes and TTS.
    """

    def __init__(self, *, storage_path: Optional[str] = None):
        self._profiles: dict[str, VoiceProfile] = {}
        self._active_profile_id: str = "friendly"
        self._adapter = ContextAdapter()
        self._pronunciation = PronunciationDictionary()
        self._preferences = PreferenceManager(storage_path=storage_path)
        self._metrics = IdentityMetrics()
        self._event_handlers: dict[IdentityEventType, list[Callable]] = {}
        self._lock = threading.Lock()
        self._created_at = time.monotonic()
        self._initialized = False

        for pid, profile in BUILTIN_PROFILES.items():
            self._profiles[pid] = profile

    @property
    def active_profile(self) -> VoiceProfile:
        return self._profiles.get(self._active_profile_id, self._profiles["friendly"])

    @property
    def active_profile_id(self) -> str:
        return self._active_profile_id

    @property
    def adapter(self) -> ContextAdapter:
        return self._adapter

    @property
    def pronunciation(self) -> PronunciationDictionary:
        return self._pronunciation

    @property
    def preferences(self) -> PreferenceManager:
        return self._preferences

    @property
    def metrics(self) -> IdentityMetrics:
        return self._metrics

    @property
    def initialized(self) -> bool:
        return self._initialized

    def on(self, event_type: IdentityEventType, handler: Callable):
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def _emit(self, event_type: IdentityEventType, data: dict):
        event = IdentityEvent(event_type=event_type, metadata=data)
        for handler in self._event_handlers.get(event_type, []):
            try:
                handler(event)
            except Exception:
                pass

    def initialize(self):
        with self._lock:
            self._preferences.load()
            self._pronunciation.load_defaults()
            pref_profile = self._preferences.get("preferred_profile", "friendly")
            if pref_profile in self._profiles:
                self._active_profile_id = pref_profile
            self._initialized = True
            self._emit(IdentityEventType.IDENTITY_LOADED, {"profile": self._active_profile_id})

    def shutdown(self):
        with self._lock:
            self._preferences.save()
            self._initialized = False

    def get_profile(self, profile_id: str) -> Optional[VoiceProfile]:
        return self._profiles.get(profile_id)

    def list_profiles(self) -> list[VoiceProfile]:
        return list(self._profiles.values())

    def create_profile(self, profile: VoiceProfile) -> VoiceProfile:
        with self._lock:
            profile.is_builtin = False
            self._profiles[profile.profile_id] = profile
            return profile

    def update_profile(self, profile_id: str, **kwargs) -> Optional[VoiceProfile]:
        with self._lock:
            profile = self._profiles.get(profile_id)
            if not profile or profile.is_builtin:
                return None
            for key, value in kwargs.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            profile.updated_at = time.monotonic()
            return profile

    def delete_profile(self, profile_id: str) -> bool:
        with self._lock:
            profile = self._profiles.get(profile_id)
            if not profile or profile.is_builtin:
                return False
            if self._active_profile_id == profile_id:
                return False
            del self._profiles[profile_id]
            return True

    def duplicate_profile(self, source_id: str, new_id: str, new_name: str = "") -> Optional[VoiceProfile]:
        source = self._profiles.get(source_id)
        if not source:
            return None
        import copy
        new_profile = copy.deepcopy(source)
        new_profile.profile_id = new_id
        new_profile.name = new_name or f"{source.name} (Copy)"
        new_profile.is_builtin = False
        new_profile.created_at = time.monotonic()
        new_profile.updated_at = time.monotonic()
        with self._lock:
            self._profiles[new_id] = new_profile
        return new_profile

    def switch_profile(self, profile_id: str) -> bool:
        with self._lock:
            if profile_id not in self._profiles:
                return False
            previous = self._active_profile_id
            self._active_profile_id = profile_id
            self._metrics.record_profile_change()
            self._emit(IdentityEventType.PROFILE_CHANGED, {
                "profile_id": profile_id, "previous": previous})
            return True

    def adapt_to_context(self, context: AdaptationContext, *,
                         reason: AdaptationReason = AdaptationReason.CONTEXT_CHANGE,
                         force: bool = False) -> AdaptationResult:
        start = time.monotonic()
        result = self._adapter.adapt(context, reason=reason, force=force)
        if result.adapted:
            self.switch_profile(result.new_profile)
            latency = (time.monotonic() - start) * 1000
            self._metrics.record_adaptation(latency)
            self._metrics.record_context_switch()
            self._emit(IdentityEventType.ADAPTATION_TRIGGERED, result.to_dict())
        return result

    def adapt_to_error(self) -> AdaptationResult:
        return self.adapt_to_context(AdaptationContext.ERROR_RECOVERY,
                                     reason=AdaptationReason.ERROR_RECOVERY)

    def adapt_to_success(self) -> AdaptationResult:
        return self.adapt_to_context(AdaptationContext.SUCCESS,
                                     reason=AdaptationReason.SUCCESS)

    def set_speaking_style(self, style: SpeakingStyleConfig):
        with self._lock:
            profile = self._profiles.get(self._active_profile_id)
            if profile:
                profile.style = style
                self._emit(IdentityEventType.SPEAKING_STYLE_CHANGED,
                           {"profile_id": self._active_profile_id, "style": style.to_dict()})

    def get_speaking_style(self) -> SpeakingStyleConfig:
        return self.active_profile.style

    def lookup_pronunciation(self, word: str) -> Optional[PronunciationEntry]:
        self._metrics.record_pronunciation_lookup()
        return self._pronunciation.lookup(word)

    def add_pronunciation(self, word: str, phonetic: str, **kwargs) -> PronunciationEntry:
        entry = self._pronunciation.add(word, phonetic, **kwargs)
        self._emit(IdentityEventType.PRONUNCIATION_UPDATED, {"word": word, "phonetic": phonetic})
        return entry

    def update_preferences(self, **kwargs):
        self._preferences.update(**kwargs)
        self._metrics.record_preference_update()
        self._emit(IdentityEventType.PREFERENCES_CHANGED, kwargs)

    def get_confirmation_phrase(self) -> str:
        phrases = self.active_profile.confirmation_phrases
        if phrases:
            return phrases[int(time.monotonic() * 1000) % len(phrases)]
        return "Done."

    def get_greeting(self) -> str:
        return self.active_profile.greeting

    def get_farewell(self) -> str:
        return self.active_profile.farewell

    def format_response(self, text: str, *, is_error: bool = False,
                        is_success: bool = False) -> str:
        profile = self.active_profile
        if is_error and profile.error_prefix:
            return f"{profile.error_prefix} {text}"
        if is_success and profile.success_prefix:
            return f"{profile.success_prefix} {text}"
        return text

    def export_profiles(self) -> dict:
        return {pid: p.to_dict() for pid, p in self._profiles.items() if not p.is_builtin}

    def import_profiles(self, data: dict) -> int:
        count = 0
        for pid, pdata in data.items():
            profile = VoiceProfile(
                profile_id=pid,
                name=pdata.get("name", pid),
                personality=PersonalityType(pdata.get("personality", "custom")),
                style=SpeakingStyleConfig.from_dict(pdata.get("style", {})),
                confirmation_phrases=pdata.get("confirmation_phrases", []),
                filler_words=pdata.get("filler_words", []),
                greeting=pdata.get("greeting", ""),
                farewell=pdata.get("farewell", ""),
                error_prefix=pdata.get("error_prefix", ""),
                success_prefix=pdata.get("success_prefix", ""),
                verbosity=pdata.get("verbosity", 0.5),
                sentence_rhythm=pdata.get("sentence_rhythm", 1.0),
                is_builtin=False,
            )
            with self._lock:
                self._profiles[pid] = profile
            count += 1
        return count

    def snapshot(self) -> dict:
        return {
            "initialized": self._initialized,
            "active_profile": self._active_profile_id,
            "active_personality": self.active_profile.personality.value,
            "active_style": self.active_profile.style.to_dict(),
            "adapter": self._adapter.snapshot(),
            "pronunciation": self._pronunciation.snapshot(),
            "preferences": self._preferences.snapshot(),
            "metrics": self._metrics.snapshot(
                current_profile=self._active_profile_id,
                current_context=self._adapter.current_context.value).to_dict(),
            "profile_count": len(self._profiles),
            "builtin_profiles": [p for p, pr in self._profiles.items() if pr.is_builtin],
        }

    def reset(self):
        with self._lock:
            self._adapter.reset()
            self._pronunciation.reset()
            self._preferences.reset()
            self._metrics.reset()
            self._active_profile_id = "friendly"
            self._profiles = {k: v for k, v in self._profiles.items() if v.is_builtin}
            self._initialized = False
