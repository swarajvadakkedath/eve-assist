"""Conversation Session — manages a single conversation lifecycle."""

from __future__ import annotations

import asyncio
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from .events import Turn
from .state import ConversationState, can_transition


class ConvEvent(Enum):
    STATE_CHANGED = "state_changed"
    TURN_STARTED = "turn_started"
    TURN_COMPLETED = "turn_completed"
    FOLLOW_UP_DETECTED = "follow_up_detected"
    CONVERSATION_RESUMED = "conversation_resumed"
    CONVERSATION_TIMED_OUT = "conversation_timed_out"
    USER_INTERRUPTED = "user_interrupted"
    BARGE_IN = "barge_in"
    RESPONSE_READY = "response_ready"
    LISTENING_RESUMED = "listening_resumed"


@dataclass
class ConversationSessionConfig:
    silence_timeout_s: float = 1.5
    follow_up_timeout_s: float = 5.0
    conversation_timeout_s: float = 300.0
    max_turns: int = 100
    enable_barge_in: bool = True
    enable_follow_ups: bool = True


@dataclass
class ConversationSessionStats:
    session_id: str
    state: str
    turn_count: int = 0
    follow_up_count: int = 0
    interruption_count: int = 0
    total_user_words: int = 0
    total_eve_words: int = 0
    avg_response_latency_ms: float = 0.0
    uptime_seconds: float = 0.0
    last_turn_text: str = ""

    def to_dict(self) -> dict:
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in self.__dict__.items()}


class ConversationSession:
    def __init__(self, *, session_id: str = "", config: Optional[ConversationSessionConfig] = None):
        self._session_id = session_id or f"conv_{int(time.time() * 1000)}"
        self._config = config or ConversationSessionConfig()
        self._state = ConversationState.IDLE
        self._created_at = time.monotonic()
        self._state_entered_at = self._created_at
        self._turns: list[Turn] = []
        self._current_turn: Optional[Turn] = None
        self._context: dict = {}
        self._last_user_text = ""
        self._last_eve_response = ""
        self._follow_up_count = 0
        self._interruption_count = 0
        self._event_handlers = {}
        self._lock = threading.Lock()

    @property
    def id(self): return self._session_id
    @property
    def state(self): return self._state
    @property
    def config(self): return self._config
    @property
    def turns(self): return list(self._turns)
    @property
    def turn_count(self): return len(self._turns)
    @property
    def context(self): return dict(self._context)
    @property
    def last_user_text(self): return self._last_user_text
    @property
    def last_eve_response(self): return self._last_eve_response
    @property
    def interruption_count(self): return self._interruption_count
    @property
    def is_active(self): return self._state not in (ConversationState.ENDED, ConversationState.TIMED_OUT)
    @property
    def elapsed(self): return time.monotonic() - self._state_entered_at
    @property
    def uptime(self): return time.monotonic() - self._created_at

    def on(self, event, handler):
        if event not in self._event_handlers: self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def _transition(self, new_state, reason=""):
        if not can_transition(self._state, new_state): return False
        prev = self._state
        self._state = new_state
        self._state_entered_at = time.monotonic()
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._emit(ConvEvent.STATE_CHANGED, {
                "from": prev.value, "to": new_state.value, "reason": reason}))
        except RuntimeError: pass
        return True

    async def _emit(self, event, data):
        for handler in self._event_handlers.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler): await handler(event, data)
                else: handler(event, data)
            except Exception: pass

    def start(self): return self._transition(ConversationState.LISTENING, "start")
    def end(self): return self._transition(ConversationState.ENDED, "end")

    def begin_turn(self, user_text: str, confidence: float = 0.0) -> Turn:
        with self._lock:
            turn_num = len(self._turns) + 1
            turn = Turn(turn_number=turn_num, user_text=user_text, confidence=confidence,
                        start_time=time.monotonic())
            self._current_turn = turn
            self._last_user_text = user_text

        if self._state == ConversationState.WAITING_FOR_FOLLOW_UP:
            self._follow_up_count += 1
            turn.is_follow_up = True
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._emit(ConvEvent.FOLLOW_UP_DETECTED, {
                    "session_id": self._session_id, "text": user_text}))
            except RuntimeError: pass

        self._transition(ConversationState.PROCESSING, "turn_begin")
        return turn

    def complete_turn(self, eve_response: str = "") -> Optional[Turn]:
        with self._lock:
            if not self._current_turn: return None
            turn = self._current_turn
            turn.eve_response = eve_response
            turn.end_time = time.monotonic()
            self._turns.append(turn)
            self._current_turn = None
            self._last_eve_response = eve_response

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._emit(ConvEvent.TURN_COMPLETED, {
                "session_id": self._session_id, "turn_number": turn.turn_number}))
        except RuntimeError: pass
        return turn

    def start_speaking(self): return self._transition(ConversationState.SPEAKING, "speak")
    def stop_speaking(self): return self._transition(ConversationState.WAITING_FOR_FOLLOW_UP, "done_speaking")
    def resume_listening(self): return self._transition(ConversationState.LISTENING, "resume_listen")

    def interrupt(self):
        with self._lock: self._interruption_count += 1
        if self._current_turn:
            with self._lock: self._current_turn.is_interrupted = True
        self._transition(ConversationState.LISTENING, "interrupt")
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._emit(ConvEvent.USER_INTERRUPTED, {"session_id": self._session_id}))
        except RuntimeError: pass

    def timeout(self):
        self._transition(ConversationState.TIMED_OUT, "timeout")
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._emit(ConvEvent.CONVERSATION_TIMED_OUT, {"session_id": self._session_id}))
        except RuntimeError: pass

    def set_context(self, key: str, value):
        with self._lock: self._context[key] = value

    def get_context(self, key: str, default=None):
        with self._lock: return self._context.get(key, default)

    def clear_context(self):
        with self._lock: self._context.clear()

    def stats(self):
        with self._lock:
            tc = len(self._turns)
            total_lat = sum(t.response_latency_ms for t in self._turns)
            avg_lat = total_lat / tc if tc > 0 else 0.0
            uw = sum(len(t.user_text.split()) for t in self._turns)
            ew = sum(len(t.eve_response.split()) for t in self._turns)
            return ConversationSessionStats(
                session_id=self._session_id, state=self._state.value, turn_count=tc,
                follow_up_count=self._follow_up_count, interruption_count=self._interruption_count,
                total_user_words=uw, total_eve_words=ew, avg_response_latency_ms=avg_lat,
                uptime_seconds=self.uptime, last_turn_text=self._last_user_text)
