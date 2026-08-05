"""Context Adaptation — automatic voice style adaptation based on session context."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .models import (
    AdaptationContext, PersonalityType, SpeakingStyleConfig,
    CONTEXT_TO_PROFILE_MAP, VoiceProfile,
)


class AdaptationReason(Enum):
    """Why adaptation occurred."""
    CONTEXT_CHANGE = "context_change"
    ERROR_RECOVERY = "error_recovery"
    SUCCESS = "success"
    USER_OVERRIDE = "user_override"
    MANUAL = "manual"


@dataclass
class AdaptationResult:
    """Result of an adaptation attempt."""
    adapted: bool
    new_profile: str
    reason: AdaptationReason
    context: AdaptationContext
    latency_ms: float = 0.0
    previous_profile: str = ""

    def to_dict(self) -> dict:
        return {
            "adapted": self.adapted,
            "new_profile": self.new_profile,
            "reason": self.reason.value,
            "context": self.context.value,
            "latency_ms": round(self.latency_ms, 3),
            "previous_profile": self.previous_profile,
        }


class ContextAdapter:
    """Adapts voice profile based on operating context.

    Maintains a mapping from context types to personality profiles.
    Automatically switches profiles when context changes.
    """

    def __init__(self):
        self._context_map: dict[AdaptationContext, PersonalityType] = dict(CONTEXT_TO_PROFILE_MAP)
        self._current_context: AdaptationContext = AdaptationContext.GENERAL
        self._current_profile_id: str = "friendly"
        self._history: list[AdaptationResult] = []
        self._max_history: int = 100
        self._custom_mappings: dict[AdaptationContext, str] = {}
        self._enabled: bool = True

    @property
    def current_context(self) -> AdaptationContext:
        return self._current_context

    @property
    def current_profile_id(self) -> str:
        return self._current_profile_id

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool):
        self._enabled = enabled

    def set_profile_for_context(self, context: AdaptationContext, profile_id: str):
        self._custom_mappings[context] = profile_id

    def get_profile_for_context(self, context: AdaptationContext) -> str:
        if context in self._custom_mappings:
            return self._custom_mappings[context]
        ptype = self._context_map.get(context, PersonalityType.FRIENDLY)
        return ptype.value

    def adapt(self, context: AdaptationContext, *,
              reason: AdaptationReason = AdaptationReason.CONTEXT_CHANGE,
              force: bool = False) -> AdaptationResult:
        start = time.monotonic()

        if not self._enabled and not force:
            return AdaptationResult(adapted=False, new_profile=self._current_profile_id,
                                    reason=reason, context=context,
                                    previous_profile=self._current_profile_id)

        if context == self._current_context and not force:
            return AdaptationResult(adapted=False, new_profile=self._current_profile_id,
                                    reason=reason, context=context,
                                    previous_profile=self._current_profile_id)

        new_profile = self.get_profile_for_context(context)
        previous = self._current_profile_id

        self._current_context = context
        self._current_profile_id = new_profile

        latency = (time.monotonic() - start) * 1000
        result = AdaptationResult(adapted=True, new_profile=new_profile, reason=reason,
                                  context=context, latency_ms=latency, previous_profile=previous)

        self._history.append(result)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        return result

    def adapt_to_error(self) -> AdaptationResult:
        return self.adapt(AdaptationContext.ERROR_RECOVERY, reason=AdaptationReason.ERROR_RECOVERY)

    def adapt_to_success(self) -> AdaptationResult:
        return self.adapt(AdaptationContext.SUCCESS, reason=AdaptationReason.SUCCESS)

    def force_profile(self, profile_id: str) -> AdaptationResult:
        previous = self._current_profile_id
        self._current_profile_id = profile_id
        result = AdaptationResult(adapted=True, new_profile=profile_id,
                                  reason=AdaptationReason.USER_OVERRIDE,
                                  context=self._current_context,
                                  previous_profile=previous)
        self._history.append(result)
        return result

    def get_history(self) -> list[AdaptationResult]:
        return list(self._history)

    def clear_history(self):
        self._history.clear()

    def snapshot(self) -> dict:
        return {
            "enabled": self._enabled,
            "current_context": self._current_context.value,
            "current_profile": self._current_profile_id,
            "custom_mappings": {k.value: v for k, v in self._custom_mappings.items()},
            "history_count": len(self._history),
        }

    def reset(self):
        self._current_context = AdaptationContext.GENERAL
        self._current_profile_id = "friendly"
        self._history.clear()
        self._custom_mappings.clear()
        self._enabled = True
