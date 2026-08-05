"""Wake Word Engine — orchestrates wake word detection, sessions, and activation.

Integrates with Audio Engine for frame input and ConversationSessionManager
for conversation activation. All processing is local (privacy mode).
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from .models import (
    WakeWordConfig, WakeWordState, DetectionResult,
    SensitivityLevel, PowerMode, SENSITIVITY_PROFILES,
)
from .events import WakeWordEvent, WakeWordEventType
from .metrics import WakeWordMetrics
from .detector import WakeWordDetector, AudioFrame
from .session import WakeWordSession, WakeSessionState


class WakeEngineState(Enum):
    """Engine lifecycle state."""
    UNINITIALIZED = "uninitialized"
    READY = "ready"
    MONITORING = "monitoring"
    SHUTDOWN = "shutdown"
    ERROR = "error"


class WakeWordEngine:
    """High-level wake word engine.

    Orchestrates detection, session management, power management,
    and conversation activation. Publishes events for all state changes.
    """

    def __init__(self, *, config: Optional[WakeWordConfig] = None):
        self._config = config or WakeWordConfig()
        self._state = WakeEngineState.UNINITIALIZED
        self._detector = WakeWordDetector(config=self._config)
        self._metrics = WakeWordMetrics()
        self._sessions: dict[str, WakeWordSession] = {}
        self._active_session: Optional[WakeWordSession] = None
        self._event_handlers: dict[WakeWordEventType, list[Callable]] = {}
        self._lock = threading.Lock()
        self._power_mode = self._config.power_mode
        self._monitoring_start_time: float = 0.0
        self._total_frames_processed: int = 0
        self._activation_callback: Optional[Callable] = None
        self._privacy_mode = self._config.privacy_mode

        self._detector.on("wake_word_detected", self._on_detection)
        self._detector.on("false_positive_detected", self._on_false_positive)
        self._detector.on("sensitivity_changed", self._on_sensitivity_changed)

    @property
    def state(self) -> WakeEngineState:
        return self._state

    @property
    def detector(self) -> WakeWordDetector:
        return self._detector

    @property
    def metrics(self) -> WakeWordMetrics:
        return self._metrics

    @property
    def active_session(self) -> Optional[WakeWordSession]:
        return self._active_session

    @property
    def power_mode(self) -> PowerMode:
        return self._power_mode

    @property
    def privacy_mode(self) -> bool:
        return self._privacy_mode

    def on(self, event_type: WakeWordEventType, handler: Callable):
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def _emit_event(self, event_type: WakeWordEventType, data: dict):
        event = WakeWordEvent(event_type=event_type, metadata=data)
        for handler in self._event_handlers.get(event_type, []):
            try:
                handler(event)
            except Exception:
                pass

    def _on_detection(self, data: dict):
        phrase = data.get("phrase", "")
        confidence = data.get("confidence", 0.0)
        latency_ms = data.get("latency_ms", 0.0)

        self._metrics.record_detection(latency_ms, confidence, success=True)
        self._metrics.record_activation()

        session = self._start_session()
        if session:
            session.record_detection(phrase, confidence, latency_ms)
            session.activate()

        self._emit_event(WakeWordEventType.WAKE_WORD_DETECTED, {
            "phrase": phrase, "confidence": confidence,
            "detection_latency_ms": latency_ms, "session_id": session.id if session else ""})

        if self._activation_callback:
            try:
                self._activation_callback(phrase, confidence)
            except Exception:
                pass

    def _on_false_positive(self, data: dict):
        self._metrics.record_false_positive()
        if self._active_session:
            self._active_session.record_false_positive()
        self._emit_event(WakeWordEventType.FALSE_POSITIVE_DETECTED, data)

    def _on_sensitivity_changed(self, data: dict):
        self._emit_event(WakeWordEventType.SENSITIVITY_CHANGED, data)

    def initialize(self):
        with self._lock:
            self._state = WakeEngineState.READY
            self._detector.start()

    def shutdown(self):
        with self._lock:
            self._state = WakeEngineState.SHUTDOWN
            self._detector.stop()
            for session in self._sessions.values():
                if session.is_active:
                    session.end()
            self._sessions.clear()
            self._active_session = None

    def start_monitoring(self):
        with self._lock:
            if self._state == WakeEngineState.READY:
                self._state = WakeEngineState.MONITORING
                self._monitoring_start_time = time.monotonic()
                self._detector.start()

    def stop_monitoring(self):
        with self._lock:
            if self._state == WakeEngineState.MONITORING:
                self._state = WakeEngineState.READY
                self._detector.stop()

    def process_frame(self, frame: AudioFrame) -> Optional[DetectionResult]:
        if self._state != WakeEngineState.MONITORING:
            return None
        if self._power_mode == PowerMode.IDLE:
            return None

        self._total_frames_processed += 1
        result = self._detector.process_frame(frame)
        if result and not result.detected:
            self._metrics.record_detection(result.detection_latency_ms, result.confidence, success=False)
        return result

    def set_activation_callback(self, callback: Callable[[str, float], None]):
        self._activation_callback = callback

    def _start_session(self) -> WakeWordSession:
        session = WakeWordSession(timeout_s=30.0)
        session.start_monitoring()
        with self._lock:
            self._sessions[session.id] = session
            self._active_session = session
        self._metrics.record_session_start()
        return session

    def end_session(self, session_id: str = None):
        with self._lock:
            sid = session_id or (self._active_session.id if self._active_session else None)
            if not sid:
                return
            session = self._sessions.get(sid)
        if session:
            session.end()
            self._metrics.record_session_end()
        with self._lock:
            self._sessions.pop(sid, None)
            if self._active_session and self._active_session.id == sid:
                self._active_session = None

    def add_phrase(self, phrase: str, *, sensitivity: float = 0.5, enabled: bool = True):
        return self._detector.add_phrase(phrase, sensitivity=sensitivity, enabled=enabled)

    def remove_phrase(self, phrase: str) -> bool:
        return self._detector.remove_phrase(phrase)

    def enable_phrase(self, phrase: str) -> bool:
        return self._detector.enable_phrase(phrase)

    def disable_phrase(self, phrase: str) -> bool:
        return self._detector.disable_phrase(phrase)

    def set_sensitivity(self, level: SensitivityLevel):
        self._detector.set_sensitivity(level)

    def set_power_mode(self, mode: PowerMode):
        with self._lock:
            self._power_mode = mode
            self._config.power_mode = mode

    def set_privacy_mode(self, enabled: bool):
        with self._lock:
            self._privacy_mode = enabled
            self._config.privacy_mode = enabled

    def snapshot(self) -> dict:
        return {
            "state": self._state.value,
            "power_mode": self._power_mode.value,
            "privacy_mode": self._privacy_mode,
            "detector": self._detector.snapshot(),
            "metrics": self._metrics.snapshot(
                current_threshold=self._detector.adaptive_threshold,
                current_sensitivity=self._config.sensitivity.value).to_dict(),
            "active_session": self._active_session.stats().to_dict() if self._active_session else None,
            "total_sessions": len(self._sessions),
            "total_frames_processed": self._total_frames_processed,
        }

    def reset(self):
        with self._lock:
            self._detector.reset()
            self._metrics.reset()
            for session in self._sessions.values():
                if session.is_active:
                    session.end()
            self._sessions.clear()
            self._active_session = None
            self._total_frames_processed = 0
            self._state = WakeEngineState.UNINITIALIZED
