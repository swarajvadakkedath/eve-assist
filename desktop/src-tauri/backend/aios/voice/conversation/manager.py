"""Conversation Manager — orchestrates continuous conversations."""

from __future__ import annotations

import asyncio
import time
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .events import Turn
from .state import ConversationState
from .session import ConversationSession, ConversationSessionConfig, ConvEvent
from .metrics import ConversationMetrics


class TurnState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    WAITING = "waiting"


class TurnAction(Enum):
    FOLLOW_UP_TIMEOUT = "follow_up_timeout"
    CONVERSATION_TIMEOUT = "conversation_timeout"


TURN_TRANSITIONS = {
    TurnState.IDLE: {TurnState.LISTENING},
    TurnState.LISTENING: {TurnState.PROCESSING, TurnState.WAITING},
    TurnState.PROCESSING: {TurnState.SPEAKING, TurnState.LISTENING},
    TurnState.SPEAKING: {TurnState.LISTENING, TurnState.WAITING, TurnState.IDLE},
    TurnState.WAITING: {TurnState.LISTENING, TurnState.IDLE},
}


class ManagerEvent(Enum):
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    TURN_STARTED = "turn_started"
    TURN_COMPLETED = "turn_completed"
    BARGE_IN = "barge_in"
    LISTENING_RESUMED = "listening_resumed"


@dataclass
class ConversationManagerConfig:
    default_silence_timeout_s: float = 1.5
    default_follow_up_timeout_s: float = 5.0
    default_conversation_timeout_s: float = 300.0
    enable_barge_in: bool = True
    enable_follow_ups: bool = True

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


class TurnManager:
    def __init__(self, *, silence_timeout: float = 1.5, follow_up_timeout: float = 5.0,
                 conversation_timeout: float = 300.0):
        self._silence_timeout = silence_timeout
        self._follow_up_timeout = follow_up_timeout
        self._conversation_timeout = conversation_timeout
        self._state = TurnState.IDLE
        self._last_activity_time: float = 0.0
        self._turn_start_time: float = 0.0

    @property
    def state(self): return self._state

    def _transition(self, new_state):
        valid = TURN_TRANSITIONS.get(self._state, set())
        if new_state not in valid: return False
        self._state = new_state
        self._last_activity_time = time.monotonic()
        if new_state == TurnState.LISTENING:
            self._turn_start_time = time.monotonic()
        return True

    def user_started_speaking(self): return self._transition(TurnState.PROCESSING)
    def processing_complete(self): return self._transition(TurnState.SPEAKING)
    def eve_started_speaking(self): return self._transition(TurnState.SPEAKING)
    def eve_done_speaking(self): return self._transition(TurnState.WAITING)
    def user_interrupt(self): return self._transition(TurnState.LISTENING)
    def start_listening(self): return self._transition(TurnState.LISTENING)

    def check_timeouts(self):
        now = time.monotonic()
        if self._state == TurnState.WAITING:
            if now - self._last_activity_time >= self._follow_up_timeout:
                return TurnAction.FOLLOW_UP_TIMEOUT
        if self._state in (TurnState.LISTENING, TurnState.WAITING):
            if now - self._turn_start_time >= self._conversation_timeout:
                return TurnAction.CONVERSATION_TIMEOUT
        return None

    def reset(self):
        self._state = TurnState.IDLE
        self._last_activity_time = 0.0
        self._turn_start_time = 0.0


class ConversationSessionManager:
    def __init__(self, *, config: Optional[ConversationManagerConfig] = None):
        self._config = config or ConversationManagerConfig()
        self._metrics = ConversationMetrics()
        self._sessions: dict[str, ConversationSession] = {}
        self._active_session: Optional[ConversationSession] = None
        self._turn_managers: dict[str, TurnManager] = {}
        self._event_handlers: dict[ManagerEvent, list] = {}
        self._lock = threading.Lock()

    @property
    def config(self): return self._config

    @property
    def metrics(self): return self._metrics

    @property
    def active_session(self): return self._active_session

    def on(self, event: ManagerEvent, handler):
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def _emit(self, event: ManagerEvent, data: dict):
        for handler in self._event_handlers.get(event, []):
            try:
                handler(event, data)
            except Exception:
                pass

    def start_conversation(self, session_id: str = "",
                           silence_timeout: float = None,
                           follow_up_timeout: float = None,
                           conversation_timeout: float = None) -> Optional[ConversationSession]:
        cfg = ConversationSessionConfig(
            silence_timeout_s=silence_timeout or self._config.default_silence_timeout_s,
            follow_up_timeout_s=follow_up_timeout or self._config.default_follow_up_timeout_s,
            conversation_timeout_s=conversation_timeout or self._config.default_conversation_timeout_s,
            enable_barge_in=self._config.enable_barge_in,
            enable_follow_ups=self._config.enable_follow_ups,
        )
        session = ConversationSession(session_id=session_id, config=cfg)
        session.start()

        tm = TurnManager(
            silence_timeout=cfg.silence_timeout_s,
            follow_up_timeout=cfg.follow_up_timeout_s,
            conversation_timeout=cfg.conversation_timeout_s,
        )
        tm.start_listening()

        with self._lock:
            self._sessions[session.id] = session
            self._turn_managers[session.id] = tm
            self._active_session = session

        self._metrics.record_conversation_start()
        self._emit(ManagerEvent.SESSION_STARTED, {"session_id": session.id})
        return session

    def end_conversation(self, session_id: str = None):
        with self._lock:
            sid = session_id or (self._active_session.id if self._active_session else None)
            if not sid:
                return
            session = self._sessions.get(sid)

        if session:
            session.end()
            duration = session.uptime
            turn_count = session.turn_count
            self._metrics.record_conversation_end(duration, turn_count)
            self._emit(ManagerEvent.SESSION_ENDED, {"session_id": sid})

        with self._lock:
            self._turn_managers.pop(sid, None)
            self._sessions.pop(sid, None)
            if self._active_session and self._active_session.id == sid:
                self._active_session = None

    def begin_turn(self, user_text: str, confidence: float = 0.0,
                   session_id: str = None) -> Optional[Turn]:
        with self._lock:
            session = self._active_session
            if session_id:
                session = self._sessions.get(session_id)
        if not session or not session.is_active:
            return None

        tm = self._turn_managers.get(session.id)
        if tm:
            tm.user_started_speaking()

        turn = session.begin_turn(user_text, confidence=confidence)
        self._metrics.record_turn()
        self._emit(ManagerEvent.TURN_STARTED, {
            "session_id": session.id,
            "turn_number": turn.turn_number,
            "text": user_text,
        })
        return turn

    def complete_turn(self, eve_response: str = "",
                      session_id: str = None) -> Optional[Turn]:
        with self._lock:
            session = self._active_session
            if session_id:
                session = self._sessions.get(session_id)
        if not session:
            return None

        turn = session.complete_turn(eve_response)
        if turn:
            self._emit(ManagerEvent.TURN_COMPLETED, {
                "session_id": session.id,
                "turn_number": turn.turn_number,
            })
        return turn

    def start_speaking(self, session_id: str = None):
        with self._lock:
            session = self._active_session
            if session_id:
                session = self._sessions.get(session_id)
        if session:
            session.start_speaking()
            tm = self._turn_managers.get(session.id)
            if tm:
                tm.eve_started_speaking()

    def stop_speaking(self, session_id: str = None):
        with self._lock:
            session = self._active_session
            if session_id:
                session = self._sessions.get(session_id)
        if session:
            session.stop_speaking()
            tm = self._turn_managers.get(session.id)
            if tm:
                tm.eve_done_speaking()

    def resume_listening(self, session_id: str = None):
        with self._lock:
            session = self._active_session
            if session_id:
                session = self._sessions.get(session_id)
        if session:
            session.resume_listening()
            tm = self._turn_managers.get(session.id)
            if tm:
                tm.start_listening()
            self._emit(ManagerEvent.LISTENING_RESUMED, {"session_id": session.id})

    def interrupt(self, session_id: str = None):
        with self._lock:
            session = self._active_session
            if session_id:
                session = self._sessions.get(session_id)
        if session and self._config.enable_barge_in:
            session.interrupt()
            tm = self._turn_managers.get(session.id)
            if tm:
                tm.user_interrupt()
            self._metrics.record_interruption()
            self._emit(ManagerEvent.BARGE_IN, {"session_id": session.id})

    def check_timeouts(self, session_id: str = None):
        with self._lock:
            session = self._active_session
            if session_id:
                session = self._sessions.get(session_id)
        if not session or not session.is_active:
            return

        tm = self._turn_managers.get(session.id)
        if not tm:
            return

        action = tm.check_timeouts()
        if action == TurnAction.FOLLOW_UP_TIMEOUT:
            session.timeout()
            self._metrics.record_timeout()
        elif action == TurnAction.CONVERSATION_TIMEOUT:
            session.timeout()
            self._metrics.record_timeout()
            self.end_conversation(session.id)

    def set_context(self, key: str, value, session_id: str = None):
        with self._lock:
            session = self._active_session
            if session_id:
                session = self._sessions.get(session_id)
        if session:
            session.set_context(key, value)

    def get_context(self, key: str, default=None, session_id: str = None):
        with self._lock:
            session = self._active_session
            if session_id:
                session = self._sessions.get(session_id)
        return session.get_context(key, default) if session else default

    def snapshot(self):
        metrics_snap = self._metrics.snapshot(
            active_conversations=len([s for s in self._sessions.values() if s.is_active]))
        session_snap = self._active_session.stats().to_dict() if self._active_session else None
        return {
            "config": self._config.to_dict(),
            "session": session_snap,
            "metrics": metrics_snap.to_dict(),
        }

    def reset(self):
        with self._lock:
            for sid in list(self._sessions.keys()):
                session = self._sessions[sid]
                if session.is_active:
                    session.end()
            self._sessions.clear()
            self._active_session = None
            self._turn_managers.clear()
            self._metrics.reset()
