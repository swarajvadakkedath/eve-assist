"""Tests for Voice Conversation module (Sprint D6)."""

import time
import threading
import pytest
from unittest.mock import MagicMock

from aios.voice.conversation.events import (
    Turn, ConversationEvent, ConversationEventType
)
from aios.voice.conversation.state import (
    ConversationState, CONVERSATION_TRANSITIONS, can_transition
)
from aios.voice.conversation.session import (
    ConversationSession, ConversationSessionConfig,
    ConversationSessionStats, ConvEvent
)
from aios.voice.conversation.metrics import (
    ConversationMetrics, ConversationMetricsSnapshot
)
from aios.voice.conversation.manager import (
    ConversationSessionManager, TurnManager, ConversationManagerConfig,
    TurnState, TurnAction, ManagerEvent, TURN_TRANSITIONS
)


# === Events Tests ===

class TestTurn:
    def test_creation(self):
        t = Turn(turn_number=1, user_text="hello")
        assert t.turn_number == 1
        assert t.user_text == "hello"
        assert t.eve_response == ""
        assert t.confidence == 0.0
        assert t.is_follow_up is False
        assert t.is_interrupted is False

    def test_creation_with_params(self):
        t = Turn(turn_number=5, user_text="hi", eve_response="hey",
                 confidence=0.95, is_follow_up=True)
        assert t.turn_number == 5
        assert t.eve_response == "hey"
        assert t.confidence == 0.95
        assert t.is_follow_up is True

    def test_response_latency_no_end(self):
        t = Turn(turn_number=1, user_text="hi")
        assert t.response_latency_ms == 0.0

    def test_response_latency_with_end(self):
        t = Turn(turn_number=1, user_text="hi", start_time=100.0, end_time=100.5)
        assert t.duration_ms == 500.0

    def test_to_dict(self):
        t = Turn(turn_number=1, user_text="hi", eve_response="hey")
        d = t.to_dict()
        assert d["turn_number"] == 1
        assert d["user_text"] == "hi"
        assert d["eve_response"] == "hey"

    def test_thread_safe(self):
        t = Turn(turn_number=1, user_text="hi")
        errors = []

        def writer():
            for _ in range(100):
                t.eve_response = "response"
                t.is_interrupted = True

        def reader():
            for _ in range(100):
                _ = t.to_dict()

        threads = [threading.Thread(target=writer) for _ in range(3)]
        threads += [threading.Thread(target=reader) for _ in range(3)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()


class TestConversationEvent:
    def test_creation(self):
        e = ConversationEvent(event_type=ConversationEventType.CONVERSATION_STARTED)
        assert e.event_type == ConversationEventType.CONVERSATION_STARTED
        assert e.metadata == {}

    def test_all_event_types(self):
        for et in ConversationEventType:
            e = ConversationEvent(event_type=et)
            assert e.event_type == et

    def test_to_dict(self):
        e = ConversationEvent(event_type=ConversationEventType.TURN_STARTED,
                              session_id="s1", turn_number=3, text="hello")
        d = e.to_dict()
        assert d["session_id"] == "s1"
        assert d["turn_number"] == 3
        assert d["text"] == "hello"


# === State Tests ===

class TestConversationState:
    def test_all_states_exist(self):
        states = [
            "idle", "listening", "processing", "speaking",
            "waiting_for_follow_up", "paused", "timed_out", "ended"
        ]
        for s in states:
            assert ConversationState(s) is not None

    def test_valid_transitions(self):
        assert can_transition(ConversationState.IDLE, ConversationState.LISTENING)
        assert can_transition(ConversationState.LISTENING, ConversationState.PROCESSING)
        assert can_transition(ConversationState.PROCESSING, ConversationState.SPEAKING)
        assert can_transition(ConversationState.SPEAKING, ConversationState.WAITING_FOR_FOLLOW_UP)
        assert can_transition(ConversationState.WAITING_FOR_FOLLOW_UP, ConversationState.LISTENING)
        assert can_transition(ConversationState.WAITING_FOR_FOLLOW_UP, ConversationState.ENDED)
        assert can_transition(ConversationState.LISTENING, ConversationState.PAUSED)
        assert can_transition(ConversationState.LISTENING, ConversationState.TIMED_OUT)

    def test_invalid_transitions(self):
        assert not can_transition(ConversationState.IDLE, ConversationState.SPEAKING)
        assert not can_transition(ConversationState.IDLE, ConversationState.PROCESSING)
        assert not can_transition(ConversationState.ENDED, ConversationState.LISTENING)
        assert not can_transition(ConversationState.TIMED_OUT, ConversationState.LISTENING)

    def test_transition_table_complete(self):
        for state in ConversationState:
            assert state in CONVERSATION_TRANSITIONS

    def test_ended_is_terminal(self):
        for target in ConversationState:
            if target == ConversationState.ENDED:
                continue
            assert not can_transition(ConversationState.ENDED, target)


# === Session Tests ===

class TestConversationSessionConfig:
    def test_defaults(self):
        cfg = ConversationSessionConfig()
        assert cfg.silence_timeout_s == 1.5
        assert cfg.follow_up_timeout_s == 5.0
        assert cfg.conversation_timeout_s == 300.0
        assert cfg.max_turns == 100
        assert cfg.enable_barge_in is True
        assert cfg.enable_follow_ups is True


class TestConversationSession:
    def test_lifecycle(self):
        s = ConversationSession()
        assert s.state == ConversationState.IDLE
        s.start()
        assert s.state == ConversationState.LISTENING
        assert s.is_active

    def test_begin_turn(self):
        s = ConversationSession()
        s.start()
        turn = s.begin_turn("hello")
        assert s.state == ConversationState.PROCESSING
        assert turn.user_text == "hello"
        assert turn.turn_number == 1

    def test_complete_turn(self):
        s = ConversationSession()
        s.start()
        s.begin_turn("hello")
        turn = s.complete_turn("hi there")
        assert s.state == ConversationState.PROCESSING
        assert turn.eve_response == "hi there"

    def test_speaking_cycle(self):
        s = ConversationSession()
        s.start()
        s.begin_turn("hello")
        s.start_speaking()
        assert s.state == ConversationState.SPEAKING
        s.stop_speaking()
        assert s.state == ConversationState.WAITING_FOR_FOLLOW_UP

    def test_follow_up(self):
        s = ConversationSession()
        s.start()
        s.begin_turn("hello")
        s.start_speaking()
        s.stop_speaking()
        turn2 = s.begin_turn("another question")
        assert s.state == ConversationState.PROCESSING
        assert turn2.is_follow_up is True

    def test_interruption(self):
        s = ConversationSession()
        s.start()
        s.begin_turn("hello")
        s.start_speaking()
        s.interrupt()
        assert s.state == ConversationState.LISTENING
        assert s._interruption_count == 1

    def test_timeout(self):
        s = ConversationSession()
        s.start()
        s.begin_turn("hello")
        s.start_speaking()
        s.stop_speaking()
        s.timeout()
        assert s.state == ConversationState.TIMED_OUT
        assert not s.is_active

    def test_end(self):
        s = ConversationSession()
        s.start()
        s.end()
        assert s.state == ConversationState.ENDED
        assert not s.is_active

    def test_stats(self):
        s = ConversationSession()
        s.start()
        s.begin_turn("hello world")
        s.complete_turn("hi")
        snap = s.stats()
        assert snap.turn_count == 1
        assert snap.total_user_words == 2
        assert snap.total_eve_words == 1

    def test_context(self):
        s = ConversationSession()
        s.set_context("key", "value")
        assert s.get_context("key") == "value"
        assert s.get_context("missing", "default") == "default"
        s.clear_context()
        assert s.get_context("key") is None

    def test_uptime(self):
        s = ConversationSession()
        time.sleep(0.01)
        assert s.uptime > 0

    def test_events(self):
        s = ConversationSession()
        events = []
        s.on(ConvEvent.STATE_CHANGED, lambda e, d: events.append(("changed", d)))
        s.on(ConvEvent.TURN_STARTED, lambda e, d: events.append(("turn", d)))
        s.on(ConvEvent.TURN_COMPLETED, lambda e, d: events.append(("done", d)))
        assert ConvEvent.STATE_CHANGED in s._event_handlers
        assert len(s._event_handlers[ConvEvent.STATE_CHANGED]) == 1

    def test_thread_safety(self):
        s = ConversationSession()
        s.start()
        errors = []

        def writer():
            for i in range(50):
                try:
                    s.set_context(f"k{i}", i)
                except Exception as e:
                    errors.append(e)

        def reader():
            for _ in range(50):
                try:
                    s.stats()
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=writer) for _ in range(3)]
        threads += [threading.Thread(target=reader) for _ in range(3)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        assert not errors


# === Metrics Tests ===

class TestConversationMetrics:
    def test_basics(self):
        m = ConversationMetrics()
        m.record_conversation_start()
        assert m.uptime > 0

    def test_conversation_end(self):
        m = ConversationMetrics()
        m.record_conversation_start()
        m.record_conversation_end(10.0, 5)
        m.record_turn()
        snap = m.snapshot()
        assert snap.total_conversations == 1

    def test_turn_tracking(self):
        m = ConversationMetrics()
        m.record_turn()
        m.record_turn()
        snap = m.snapshot()
        assert snap.total_turns == 2

    def test_follow_ups(self):
        m = ConversationMetrics()
        m.record_follow_up()
        m.record_follow_up()
        snap = m.snapshot()
        assert snap.total_follow_ups == 2

    def test_interruptions(self):
        m = ConversationMetrics()
        m.record_interruption()
        snap = m.snapshot()
        assert snap.total_interruptions == 1

    def test_timeouts(self):
        m = ConversationMetrics()
        m.record_timeout()
        snap = m.snapshot()
        assert snap.total_timeouts == 1

    def test_snapshot(self):
        m = ConversationMetrics()
        m.record_conversation_start()
        m.record_conversation_end(10.0, 3)
        snap = m.snapshot(active_conversations=1)
        assert snap.active_conversations == 1
        d = snap.to_dict()
        assert isinstance(d, dict)

    def test_reset(self):
        m = ConversationMetrics()
        m.record_turn()
        m.reset()
        snap = m.snapshot()
        assert snap.total_turns == 0

    def test_latency_tracking(self):
        m = ConversationMetrics()
        m.record_turn(response_latency_ms=100.0)
        m.record_turn(response_latency_ms=200.0)
        snap = m.snapshot()
        assert snap.avg_response_latency_ms > 0

    def test_empty_snapshot(self):
        m = ConversationMetrics()
        snap = m.snapshot()
        assert snap.total_conversations == 0
        assert snap.avg_response_latency_ms == 0.0


# === TurnManager Tests ===

class TestTurnManager:
    def test_initial_state(self):
        tm = TurnManager()
        assert tm.state == TurnState.IDLE

    def test_start_listening(self):
        tm = TurnManager()
        assert tm.start_listening() is True
        assert tm.state == TurnState.LISTENING

    def test_user_speaking(self):
        tm = TurnManager()
        tm.start_listening()
        assert tm.user_started_speaking() is True
        assert tm.state == TurnState.PROCESSING

    def test_processing_complete(self):
        tm = TurnManager()
        tm.start_listening()
        tm.user_started_speaking()
        assert tm.processing_complete() is True
        assert tm.state == TurnState.SPEAKING

    def test_eve_done(self):
        tm = TurnManager()
        tm.start_listening()
        tm.user_started_speaking()
        tm.processing_complete()
        assert tm.eve_done_speaking() is True
        assert tm.state == TurnState.WAITING

    def test_invalid_transition(self):
        tm = TurnManager()
        assert tm.processing_complete() is False

    def test_barge_in(self):
        tm = TurnManager()
        tm.start_listening()
        tm.user_started_speaking()
        tm.processing_complete()
        assert tm.user_interrupt() is True
        assert tm.state == TurnState.LISTENING

    def test_follow_up_timeout(self):
        tm = TurnManager(follow_up_timeout=0.01)
        tm.start_listening()
        tm.user_started_speaking()
        tm.processing_complete()
        tm.eve_done_speaking()
        time.sleep(0.02)
        action = tm.check_timeouts()
        assert action == TurnAction.FOLLOW_UP_TIMEOUT

    def test_conversation_timeout(self):
        tm = TurnManager(conversation_timeout=0.01)
        tm.start_listening()
        time.sleep(0.02)
        action = tm.check_timeouts()
        assert action == TurnAction.CONVERSATION_TIMEOUT

    def test_no_timeout(self):
        tm = TurnManager(conversation_timeout=10.0)
        tm.start_listening()
        action = tm.check_timeouts()
        assert action is None

    def test_reset(self):
        tm = TurnManager()
        tm.start_listening()
        tm.reset()
        assert tm.state == TurnState.IDLE


# === ConversationSessionManager Tests ===

class TestConversationManagerConfig:
    def test_defaults(self):
        cfg = ConversationManagerConfig()
        assert cfg.default_silence_timeout_s == 1.5
        assert cfg.default_follow_up_timeout_s == 5.0
        assert cfg.default_conversation_timeout_s == 300.0
        assert cfg.enable_barge_in is True
        assert cfg.enable_follow_ups is True

    def test_to_dict(self):
        cfg = ConversationManagerConfig()
        d = cfg.to_dict()
        assert isinstance(d, dict)
        assert "default_silence_timeout_s" in d


class TestConversationSessionManager:
    def test_start_and_end(self):
        mgr = ConversationSessionManager()
        session = mgr.start_conversation("test-1")
        assert session is not None
        assert session.is_active
        assert mgr.active_session is session
        mgr.end_conversation("test-1")
        assert mgr.active_session is None

    def test_begin_complete_turn(self):
        mgr = ConversationSessionManager()
        mgr.start_conversation()
        turn = mgr.begin_turn("hello")
        assert turn is not None
        assert turn.user_text == "hello"
        turn = mgr.complete_turn("hi there")
        assert turn is not None
        assert turn.eve_response == "hi there"

    def test_start_stop_speaking(self):
        mgr = ConversationSessionManager()
        mgr.start_conversation()
        mgr.begin_turn("hello")
        mgr.start_speaking()
        assert mgr.active_session.state == ConversationState.SPEAKING
        mgr.stop_speaking()
        assert mgr.active_session.state == ConversationState.WAITING_FOR_FOLLOW_UP

    def test_resume_listening(self):
        mgr = ConversationSessionManager()
        mgr.start_conversation()
        mgr.resume_listening()
        assert mgr.active_session.state == ConversationState.LISTENING

    def test_interrupt(self):
        mgr = ConversationSessionManager()
        mgr.start_conversation()
        mgr.begin_turn("hello")
        mgr.start_speaking()
        mgr.interrupt()
        snap = mgr.metrics.snapshot()
        assert snap.total_interruptions == 1

    def test_barge_in_disabled(self):
        cfg = ConversationManagerConfig(enable_barge_in=False)
        mgr = ConversationSessionManager(config=cfg)
        mgr.start_conversation()
        mgr.begin_turn("hello")
        mgr.start_speaking()
        mgr.interrupt()
        snap = mgr.metrics.snapshot()
        assert snap.total_interruptions == 0

    def test_follow_up_timeout(self):
        cfg = ConversationManagerConfig(default_follow_up_timeout_s=0.01)
        mgr = ConversationSessionManager(config=cfg)
        session = mgr.start_conversation()
        mgr.begin_turn("hello")
        mgr.start_speaking()
        mgr.stop_speaking()
        time.sleep(0.02)
        mgr.check_timeouts()
        assert session.state == ConversationState.TIMED_OUT

    def test_conversation_timeout(self):
        cfg = ConversationManagerConfig(default_conversation_timeout_s=0.01)
        mgr = ConversationSessionManager(config=cfg)
        mgr.start_conversation()
        time.sleep(0.02)
        mgr.check_timeouts()
        assert mgr.active_session is None

    def test_set_get_context(self):
        mgr = ConversationSessionManager()
        mgr.start_conversation()
        mgr.set_context("topic", "python")
        assert mgr.get_context("topic") == "python"
        assert mgr.get_context("missing", "default") == "default"

    def test_snapshot(self):
        mgr = ConversationSessionManager()
        mgr.start_conversation()
        snap = mgr.snapshot()
        assert "config" in snap
        assert "session" in snap
        assert "metrics" in snap

    def test_event_handlers(self):
        mgr = ConversationSessionManager()
        events = []
        mgr.on(ManagerEvent.SESSION_STARTED, lambda e, d: events.append(("started", d)))
        mgr.on(ManagerEvent.TURN_STARTED, lambda e, d: events.append(("turn", d)))
        mgr.start_conversation()
        mgr.begin_turn("hello")
        assert len(events) == 2
        assert events[0][0] == "started"
        assert events[1][0] == "turn"

    def test_reset(self):
        mgr = ConversationSessionManager()
        mgr.start_conversation()
        mgr.begin_turn("hello")
        mgr.reset()
        snap = mgr.snapshot()
        assert snap["session"] is None

    def test_no_session_actions(self):
        mgr = ConversationSessionManager()
        assert mgr.begin_turn("hello") is None
        assert mgr.complete_turn("hi") is None
        mgr.start_speaking()
        mgr.stop_speaking()
        mgr.resume_listening()
        mgr.interrupt()
        mgr.check_timeouts()
        mgr.set_context("k", "v")
        assert mgr.get_context("k") is None

    def test_custom_timeouts(self):
        mgr = ConversationSessionManager()
        session = mgr.start_conversation(
            silence_timeout=2.0,
            follow_up_timeout=10.0,
            conversation_timeout=600.0,
        )
        assert session.config.silence_timeout_s == 2.0
        assert session.config.follow_up_timeout_s == 10.0
        assert session.config.conversation_timeout_s == 600.0

    def test_thread_safety(self):
        mgr = ConversationSessionManager()
        mgr.start_conversation()
        errors = []

        def writer():
            for i in range(20):
                try:
                    mgr.set_context(f"k{i}", i)
                except Exception as e:
                    errors.append(e)

        def reader():
            for _ in range(20):
                try:
                    mgr.snapshot()
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=writer) for _ in range(3)]
        threads += [threading.Thread(target=reader) for _ in range(3)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        assert not errors


# === Integration Tests ===

class TestConversationIntegration:
    def test_multi_turn_conversation(self):
        mgr = ConversationSessionManager()
        session = mgr.start_conversation()

        mgr.begin_turn("what is the weather?")
        mgr.start_speaking()
        mgr.stop_speaking()
        mgr.complete_turn("It is sunny today.")
        mgr.resume_listening()

        mgr.begin_turn("and tomorrow?")
        mgr.start_speaking()
        mgr.stop_speaking()
        mgr.complete_turn("Rain expected.")
        mgr.end_conversation()

        assert session.turn_count == 2
        assert session.stats().total_eve_words == 6

    def test_barge_in_conversation(self):
        mgr = ConversationSessionManager()
        mgr.start_conversation()

        mgr.begin_turn("tell me a story")
        mgr.start_speaking()
        mgr.interrupt()
        mgr.begin_turn("never mind, what time is it?")
        mgr.start_speaking()
        mgr.stop_speaking()
        mgr.complete_turn("It is 3 PM.")
        mgr.end_conversation()

        snap = mgr.metrics.snapshot()
        assert snap.total_interruptions == 1

    def test_conversation_with_context(self):
        mgr = ConversationSessionManager()
        mgr.start_conversation()
        mgr.set_context("language", "spanish")
        mgr.begin_turn("hola")
        assert mgr.get_context("language") == "spanish"
        mgr.end_conversation()

    def test_multiple_sessions(self):
        mgr = ConversationSessionManager()
        s1 = mgr.start_conversation("s1")
        s2 = mgr.start_conversation("s2")
        assert mgr.active_session is s2
        assert len(mgr._sessions) == 2
        mgr.end_conversation("s1")
        mgr.end_conversation("s2")
        assert len(mgr._sessions) == 0
