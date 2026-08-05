"""Wake Word Session — manages a single wake word activation session."""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .events import WakeWordEvent, WakeWordEventType


class WakeSessionState(Enum):
    """Wake session lifecycle state."""
    INACTIVE = "inactive"
    MONITORING = "monitoring"
    DETECTED = "detected"
    ACTIVATED = "activated"
    TIMEOUT = "timeout"
    ENDED = "ended"


class WakeSessionEvent(Enum):
    """Events within a wake session."""
    STATE_CHANGED = "state_changed"
    DETECTION = "detection"
    ACTIVATION = "activation"
    TIMEOUT = "timeout"
    END = "end"


@dataclass
class WakeSessionStats:
    """Statistics for a wake session."""
    session_id: str
    state: str
    phrase: str
    confidence: float = 0.0
    detection_latency_ms: float = 0.0
    duration_s: float = 0.0
    false_positives: int = 0
    activations: int = 0

    def to_dict(self) -> dict:
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in self.__dict__.items()}


class WakeWordSession:
    """Manages a single wake word activation session.

    Tracks state from monitoring through detection to activation,
    with support for timeout and false positive tracking.
    """

    def __init__(self, *, session_id: str = "", timeout_s: float = 30.0):
        self._session_id = session_id or f"wake_{int(time.time() * 1000)}"
        self._state = WakeSessionState.INACTIVE
        self._timeout_s = timeout_s
        self._created_at = time.monotonic()
        self._state_entered_at = self._created_at
        self._phrase = ""
        self._confidence = 0.0
        self._detection_latency_ms = 0.0
        self._false_positives = 0
        self._activations = 0
        self._event_handlers: dict[WakeSessionEvent, list] = {}
        self._lock = threading.Lock()

    @property
    def id(self) -> str:
        return self._session_id

    @property
    def state(self) -> WakeSessionState:
        return self._state

    @property
    def phrase(self) -> str:
        return self._phrase

    @property
    def confidence(self) -> float:
        return self._confidence

    @property
    def is_active(self) -> bool:
        return self._state not in (WakeSessionState.INACTIVE, WakeSessionState.ENDED, WakeSessionState.TIMEOUT)

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self._state_entered_at

    @property
    def uptime(self) -> float:
        return time.monotonic() - self._created_at

    def on(self, event: WakeSessionEvent, handler):
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def _emit(self, event: WakeSessionEvent, data: dict):
        for handler in self._event_handlers.get(event, []):
            try:
                handler(event, data)
            except Exception:
                pass

    def _transition(self, new_state: WakeSessionState, reason: str = ""):
        VALID_TRANSITIONS = {
            WakeSessionState.INACTIVE: {WakeSessionState.MONITORING},
            WakeSessionState.MONITORING: {WakeSessionState.DETECTED, WakeSessionState.TIMEOUT, WakeSessionState.ENDED},
            WakeSessionState.DETECTED: {WakeSessionState.ACTIVATED, WakeSessionState.MONITORING, WakeSessionState.TIMEOUT, WakeSessionState.ENDED, WakeSessionState.INACTIVE},
            WakeSessionState.ACTIVATED: {WakeSessionState.MONITORING, WakeSessionState.ENDED, WakeSessionState.INACTIVE},
            WakeSessionState.TIMEOUT: {WakeSessionState.INACTIVE, WakeSessionState.MONITORING},
            WakeSessionState.ENDED: {WakeSessionState.INACTIVE},
        }
        valid = VALID_TRANSITIONS.get(self._state, set())
        if new_state not in valid:
            return False
        prev = self._state
        self._state = new_state
        self._state_entered_at = time.monotonic()
        self._emit(WakeSessionEvent.STATE_CHANGED, {"from": prev.value, "to": new_state.value, "reason": reason})
        return True

    def start_monitoring(self) -> bool:
        return self._transition(WakeSessionState.MONITORING, "start")

    def record_detection(self, phrase: str, confidence: float, latency_ms: float):
        with self._lock:
            self._phrase = phrase
            self._confidence = confidence
            self._detection_latency_ms = latency_ms
        self._transition(WakeSessionState.DETECTED, f"detected:{phrase}")
        self._emit(WakeSessionEvent.DETECTION, {
            "phrase": phrase, "confidence": confidence, "latency_ms": latency_ms})

    def activate(self) -> bool:
        with self._lock:
            self._activations += 1
        result = self._transition(WakeSessionState.ACTIVATED, "activate")
        if result:
            self._emit(WakeSessionEvent.ACTIVATION, {"phrase": self._phrase, "activations": self._activations})
        return result

    def record_false_positive(self):
        with self._lock:
            self._false_positives += 1

    def timeout(self) -> bool:
        result = self._transition(WakeSessionState.TIMEOUT, "timeout")
        if result:
            self._emit(WakeSessionEvent.TIMEOUT, {})
        return result

    def end(self) -> bool:
        result = self._transition(WakeSessionState.ENDED, "end")
        if result:
            self._emit(WakeSessionEvent.END, {"duration_s": self.uptime})
        return result

    def reset(self):
        self._transition(WakeSessionState.INACTIVE, "reset")
        with self._lock:
            self._phrase = ""
            self._confidence = 0.0
            self._detection_latency_ms = 0.0
            self._false_positives = 0
            self._activations = 0
            self._created_at = time.monotonic()
            self._state_entered_at = self._created_at

    def check_timeout(self) -> bool:
        if self._state in (WakeSessionState.MONITORING, WakeSessionState.ACTIVATED):
            if self.elapsed > self._timeout_s:
                self.timeout()
                return True
        return False

    def stats(self) -> WakeSessionStats:
        return WakeSessionStats(
            session_id=self._session_id, state=self._state.value,
            phrase=self._phrase, confidence=self._confidence,
            detection_latency_ms=self._detection_latency_ms,
            duration_s=self.uptime, false_positives=self._false_positives,
            activations=self._activations)
