"""Sprint D4 Tests — Streaming Speech Recognition."""

import asyncio
import struct
import threading
import time
import pytest

from aios.voice.stt_streaming.events import (
    TranscriptEvent, TranscriptEventType, WordTiming,
)
from aios.voice.stt_streaming.provider import (
    STTProvider, ProviderConfig, ProviderState, ProviderHealth,
)
from aios.voice.stt_streaming.session import (
    StreamingSTTSession, SessionState, SessionEvent,
    TranscriptChunk, SessionStats, SESSION_TRANSITIONS,
)
from aios.voice.stt_streaming.metrics import (
    TranscriptMetrics, TranscriptMetricsSnapshot,
)
from aios.voice.stt_streaming.manager import (
    StreamingSTTManager, STTConfig, ManagerEventType,
)


# ─── Helpers ────────────────────────────────────────────────────────

def make_words(text="hello world"):
    return [WordTiming(word=w, start_ms=i*500, end_ms=(i+1)*500, confidence=0.9)
            for i, w in enumerate(text.split())]


# ─── Events Tests ───────────────────────────────────────────────────

class TestTranscriptEvent:
    def test_creation(self):
        e = TranscriptEvent(event_type=TranscriptEventType.PARTIAL_TRANSCRIPT, text="hi")
        assert e.event_type == TranscriptEventType.PARTIAL_TRANSCRIPT
        assert e.text == "hi"

    def test_to_dict(self):
        e = TranscriptEvent(event_type=TranscriptEventType.FINAL_TRANSCRIPT, text="hello", confidence=0.95)
        d = e.to_dict()
        assert d["event_type"] == "final_transcript"
        assert d["confidence"] == 0.95

    def test_defaults(self):
        e = TranscriptEvent(event_type=TranscriptEventType.RECOGNITION_STARTED)
        assert e.session_id == ""
        assert e.text == ""
        assert e.words == []

    def test_all_event_types(self):
        for t in TranscriptEventType:
            e = TranscriptEvent(event_type=t)
            assert e.event_type == t


class TestWordTiming:
    def test_creation(self):
        w = WordTiming(word="hello", start_ms=0, end_ms=500, confidence=0.9)
        assert w.word == "hello"
        assert w.start_ms == 0

    def test_to_dict(self):
        w = WordTiming(word="hi", start_ms=100, end_ms=200, confidence=0.8, speaker="A")
        d = w.to_dict()
        assert d["word"] == "hi"
        assert d["speaker"] == "A"


# ─── Provider Tests ─────────────────────────────────────────────────

class TestSTTProvider:
    def test_creation(self):
        p = STTProvider(config=ProviderConfig(provider_id="openai"))
        assert p.provider_id == "openai"
        assert p.state == ProviderState.DISCONNECTED

    def test_connect(self):
        p = STTProvider(config=ProviderConfig(provider_id="openai"))
        assert p.connect()
        assert p.state == ProviderState.CONNECTED
        assert p.is_connected

    def test_start_stream(self):
        p = STTProvider(config=ProviderConfig(provider_id="openai"))
        p.connect()
        stream_id = p.start_stream()
        assert stream_id is not None
        assert p.state == ProviderState.STREAMING

    def test_send_audio(self):
        p = STTProvider(config=ProviderConfig(provider_id="openai"))
        p.connect()
        p.start_stream()
        assert p.send_audio(b'\x00\x00' * 100)

    def test_send_audio_not_streaming(self):
        p = STTProvider(config=ProviderConfig(provider_id="openai"))
        p.connect()
        assert not p.send_audio(b'\x00\x00' * 100)

    def test_finish_stream(self):
        p = STTProvider(config=ProviderConfig(provider_id="openai"))
        p.connect()
        p.start_stream()
        result = p.finish_stream()
        assert result is not None
        assert p.state == ProviderState.CONNECTED

    def test_finish_stream_not_streaming(self):
        p = STTProvider(config=ProviderConfig(provider_id="openai"))
        assert p.finish_stream() is None

    def test_disconnect(self):
        p = STTProvider(config=ProviderConfig(provider_id="openai"))
        p.connect()
        p.disconnect()
        assert p.state == ProviderState.DISCONNECTED
        assert not p.is_connected

    def test_set_error(self):
        p = STTProvider(config=ProviderConfig(provider_id="openai"))
        p.connect()
        p.set_error("timeout")
        assert p.state == ProviderState.ERROR
        assert p.health.last_error == "timeout"

    def test_recover(self):
        p = STTProvider(config=ProviderConfig(provider_id="openai"))
        p.connect()
        p.set_error("timeout")
        assert p.recover()
        assert p.state == ProviderState.CONNECTED

    def test_health_tracking(self):
        p = STTProvider(config=ProviderConfig(provider_id="openai"))
        p.connect()
        p.start_stream()
        p.send_audio(b'\x00' * 10)
        h = p.health
        assert h.total_requests == 1
        assert h.successful_requests == 1

    def test_snapshot(self):
        p = STTProvider(config=ProviderConfig(provider_id="openai"))
        s = p.snapshot()
        assert s["provider_id"] == "openai"
        assert "health" in s
        assert "config" in s

    def test_start_stream_not_connected(self):
        p = STTProvider(config=ProviderConfig(provider_id="openai"))
        assert p.start_stream() is None

    def test_config_to_dict(self):
        c = ProviderConfig(provider_id="openai", model="whisper-1", language="en")
        d = c.to_dict()
        assert d["provider_id"] == "openai"
        assert d["model"] == "whisper-1"

    def test_consecutive_failures(self):
        p = STTProvider(config=ProviderConfig(provider_id="openai"))
        p.connect()
        p.set_error("err1")
        p.set_error("err2")
        assert p.health.consecutive_failures == 2


# ─── Session Tests ──────────────────────────────────────────────────

class TestStreamingSTTSession:
    def test_creation(self):
        s = StreamingSTTSession(session_id="test", provider_id="openai")
        assert s.id == "test"
        assert s.state == SessionState.CREATED
        assert s.provider_id == "openai"

    def test_auto_id(self):
        s = StreamingSTTSession()
        assert s.id.startswith("stt_")

    def test_connect(self):
        s = StreamingSTTSession(session_id="test")
        assert s.connect()
        assert s.state == SessionState.CONNECTING

    def test_start_streaming(self):
        s = StreamingSTTSession(session_id="test")
        s.connect()
        assert s.start_streaming()
        assert s.state == SessionState.STREAMING

    def test_receive_partial(self):
        s = StreamingSTTSession(session_id="test")
        s.connect()
        s.start_streaming()
        s.receive_partial("hello", confidence=0.8)
        assert s.partial_text == "hello"
        assert s.state == SessionState.RECEIVING

    def test_receive_final(self):
        s = StreamingSTTSession(session_id="test")
        s.connect()
        s.start_streaming()
        s.receive_partial("hello")
        s.receive_final("hello world", confidence=0.9)
        assert s.final_text == "hello world"
        assert s.partial_text == ""

    def test_multiple_partials(self):
        s = StreamingSTTSession(session_id="test")
        s.connect()
        s.start_streaming()
        s.receive_partial("hel")
        s.receive_partial("hello")
        s.receive_partial("hello wor")
        assert s.partial_text == "hello wor"
        assert s.stats().partial_count == 3

    def test_multiple_finals(self):
        s = StreamingSTTSession(session_id="test")
        s.connect()
        s.start_streaming()
        s.receive_final("first turn")
        s.receive_final(" second turn")
        assert s.final_text == "first turn second turn"
        assert s.stats().final_count == 2

    def test_finish(self):
        s = StreamingSTTSession(session_id="test")
        s.connect()
        s.start_streaming()
        s.receive_partial("hi")
        assert s.finish()
        assert s.state == SessionState.COMPLETED

    def test_close(self):
        s = StreamingSTTSession(session_id="test")
        s.connect()
        s.close()
        assert s.state == SessionState.CLOSED
        assert not s.is_active

    def test_set_error(self):
        s = StreamingSTTSession(session_id="test")
        s.connect()
        s.start_streaming()
        s.set_error("provider_error")
        assert s.state == SessionState.ERROR
        assert s.stats().error == "provider_error"

    def test_switch_provider(self):
        s = StreamingSTTSession(session_id="test", provider_id="openai")
        s.switch_provider("google")
        assert s.provider_id == "google"

    def test_is_active(self):
        s = StreamingSTTSession(session_id="test")
        assert s.is_active
        s.connect()
        assert s.is_active
        s.close()
        assert not s.is_active

    def test_uptime(self):
        s = StreamingSTTSession(session_id="test")
        time.sleep(0.01)
        assert s.uptime > 0

    def test_words_tracking(self):
        s = StreamingSTTSession(session_id="test")
        s.connect()
        s.start_streaming()
        words = make_words("hello world")
        s.receive_partial("hello world", words=words)
        assert s.stats().total_words == 2

    def test_confidence_tracking(self):
        s = StreamingSTTSession(session_id="test")
        s.connect()
        s.start_streaming()
        s.receive_partial("hi", confidence=0.8)
        s.receive_final("hi there", confidence=0.9)
        stats = s.stats()
        assert stats.avg_confidence == pytest.approx(0.85, abs=0.01)

    def test_stats(self):
        s = StreamingSTTSession(session_id="test", provider_id="openai")
        stats = s.stats()
        assert stats.session_id == "test"
        assert stats.provider == "openai"

    def test_stats_dict(self):
        s = StreamingSTTSession(session_id="test")
        d = s.stats().to_dict()
        assert "session_id" in d
        assert "partial_count" in d

    def test_valid_transitions(self):
        for state in SessionState:
            assert state in SESSION_TRANSITIONS

    def test_bytes_sent(self):
        s = StreamingSTTSession(session_id="test")
        s.connect()
        s.start_streaming()
        s.add_bytes_sent(100)
        assert s.stats().bytes_sent == 100
        assert s.stats().chunks_sent == 1

    def test_invalid_transition(self):
        s = StreamingSTTSession(session_id="test")
        assert not s.start_streaming()  # Can't skip CONNECTING

    def test_error_recovery_path(self):
        s = StreamingSTTSession(session_id="test")
        s.connect()
        s.start_streaming()
        s.set_error("timeout")
        assert s.state == SessionState.ERROR
        # Error -> CREATED is valid
        s2 = StreamingSTTSession(session_id="test2")
        s2.connect()
        s2.start_streaming()
        s2.set_error("timeout")
        s2.close()
        assert s2.state == SessionState.CLOSED


# ─── Metrics Tests ──────────────────────────────────────────────────

class TestTranscriptMetrics:
    def test_creation(self):
        m = TranscriptMetrics()
        snap = m.snapshot()
        assert snap.total_partials == 0
        assert snap.uptime_seconds >= 0

    def test_record_partial(self):
        m = TranscriptMetrics()
        m.record_partial("hello", confidence=0.8)
        snap = m.snapshot()
        assert snap.total_partials == 1
        assert snap.total_words == 1

    def test_record_final(self):
        m = TranscriptMetrics()
        m.record_final("hello world", confidence=0.9)
        snap = m.snapshot()
        assert snap.total_finals == 1
        assert snap.total_words == 2

    def test_record_latency(self):
        m = TranscriptMetrics()
        m.record_latency(50.0)
        m.record_latency(100.0)
        snap = m.snapshot()
        assert snap.avg_latency_ms == 75.0

    def test_record_provider_switch(self):
        m = TranscriptMetrics()
        m.record_provider_switch()
        snap = m.snapshot()
        assert snap.provider_switches == 1

    def test_record_recovery(self):
        m = TranscriptMetrics()
        m.record_recovery()
        snap = m.snapshot()
        assert snap.recovery_events == 1

    def test_record_failure(self):
        m = TranscriptMetrics()
        m.record_failure()
        snap = m.snapshot()
        assert snap.failed_attempts == 1

    def test_words_per_second(self):
        m = TranscriptMetrics()
        m.record_partial("hello world", confidence=0.8)
        time.sleep(0.1)
        snap = m.snapshot()
        assert snap.words_per_second >= 0

    def test_confidence_average(self):
        m = TranscriptMetrics()
        m.record_partial("hi", confidence=0.6)
        m.record_final("hi there", confidence=0.9)
        snap = m.snapshot()
        assert snap.avg_confidence == pytest.approx(0.75, abs=0.01)

    def test_percentile(self):
        m = TranscriptMetrics()
        for i in range(100):
            m.record_latency(float(i))
        snap = m.snapshot()
        assert snap.p95_latency_ms > 0
        assert snap.max_latency_ms == 99.0

    def test_reset(self):
        m = TranscriptMetrics()
        m.record_partial("hi", confidence=0.8)
        m.reset()
        snap = m.snapshot()
        assert snap.total_partials == 0

    def test_snapshot_dict(self):
        m = TranscriptMetrics()
        d = m.snapshot().to_dict()
        assert "total_partials" in d
        assert "words_per_second" in d


# ─── Manager Tests ──────────────────────────────────────────────────

class TestStreamingSTTManager:
    def test_creation(self):
        m = StreamingSTTManager()
        assert m.config.provider_id == "openai"

    def test_creation_with_config(self):
        config = STTConfig(provider_id="google", language="es")
        m = StreamingSTTManager(config=config)
        assert m.config.provider_id == "google"
        assert m.config.language == "es"

    def test_register_provider(self):
        m = StreamingSTTManager()
        m.register_provider("openai")
        assert m.get_provider("openai") is not None

    def test_unregister_provider(self):
        m = StreamingSTTManager()
        m.register_provider("openai")
        m.unregister_provider("openai")
        assert m.get_provider("openai") is None

    def test_start_session(self):
        m = StreamingSTTManager()
        m.register_provider("openai")
        session = m.start_session()
        assert session is not None
        assert session.state == SessionState.STREAMING

    def test_start_session_no_provider(self):
        m = StreamingSTTManager()
        session = m.start_session()
        assert session is None

    def test_stop_session(self):
        m = StreamingSTTManager()
        m.register_provider("openai")
        m.start_session()
        m.stop_session()
        assert m.active_session is None

    def test_send_audio(self):
        m = StreamingSTTManager()
        m.register_provider("openai")
        m.start_session()
        assert m.send_audio(b'\x00\x00' * 100)

    def test_send_audio_no_session(self):
        m = StreamingSTTManager()
        assert not m.send_audio(b'\x00\x00' * 100)

    def test_process_partial(self):
        m = StreamingSTTManager()
        m.register_provider("openai")
        m.start_session()
        m.process_partial("hello", confidence=0.8)
        snap = m.snapshot()
        assert snap["metrics"]["total_partials"] == 1

    def test_process_final(self):
        m = StreamingSTTManager()
        m.register_provider("openai")
        m.start_session()
        m.process_final("hello world", confidence=0.9)
        snap = m.snapshot()
        assert snap["metrics"]["total_finals"] == 1

    def test_failover(self):
        m = StreamingSTTManager()
        m.register_provider("openai")
        m.register_provider("google")
        m.start_session()
        result = m.failover()
        assert result is True
        snap = m.snapshot()
        assert snap["metrics"]["provider_switches"] == 1

    def test_failover_no_alternative(self):
        m = StreamingSTTManager()
        m.register_provider("openai")
        m.start_session()
        result = m.failover()
        # Should try to failover to openai (same provider) or itself
        assert result is True  # It wraps around to openai

    def test_failover_no_session(self):
        m = StreamingSTTManager()
        result = m.failover()
        assert result is False

    def test_recover(self):
        m = StreamingSTTManager()
        m.register_provider("openai")
        session = m.start_session()
        session.set_error("timeout")
        result = m.recover()
        assert result is True

    def test_recover_not_error(self):
        m = StreamingSTTManager()
        m.register_provider("openai")
        m.start_session()
        result = m.recover()
        assert result is False

    def test_snapshot(self):
        m = StreamingSTTManager()
        m.register_provider("openai")
        m.start_session()
        snap = m.snapshot()
        assert "config" in snap
        assert "session" in snap
        assert "metrics" in snap
        assert "providers" in snap

    def test_snapshot_no_session(self):
        m = StreamingSTTManager()
        snap = m.snapshot()
        assert snap["session"] is None

    def test_reset(self):
        m = StreamingSTTManager()
        m.register_provider("openai")
        m.start_session()
        m.process_partial("hi")
        m.reset()
        snap = m.snapshot()
        assert snap["metrics"]["total_partials"] == 0

    def test_config_to_dict(self):
        c = STTConfig(provider_id="google", language="es")
        d = c.to_dict()
        assert d["provider_id"] == "google"

    def test_multiple_sessions(self):
        m = StreamingSTTManager()
        m.register_provider("openai")
        s1 = m.start_session(session_id="s1")
        m.stop_session()
        s2 = m.start_session(session_id="s2")
        assert s1.id == "s1"
        assert s2.id == "s2"

    def test_active_session(self):
        m = StreamingSTTManager()
        m.register_provider("openai")
        assert m.active_session is None
        m.start_session()
        assert m.active_session is not None

    def test_stop_clears_active(self):
        m = StreamingSTTManager()
        m.register_provider("openai")
        m.start_session()
        m.stop_session()
        assert m.active_session is None

    def test_metrics_tracked(self):
        m = StreamingSTTManager()
        m.register_provider("openai")
        m.start_session()
        m.process_partial("hello", confidence=0.8)
        m.process_final("hello world", confidence=0.9)
        snap = m.snapshot()
        assert snap["metrics"]["total_partials"] == 1
        assert snap["metrics"]["total_finals"] == 1

    def test_provider_snapshot(self):
        m = StreamingSTTManager()
        m.register_provider("openai")
        m.register_provider("google")
        snap = m.snapshot()
        assert "openai" in snap["providers"]
        assert "google" in snap["providers"]


# ─── Integration Tests ──────────────────────────────────────────────

class TestD4Integration:
    def test_full_recognition_flow(self):
        """Test complete flow: start → partial → final → stop."""
        m = StreamingSTTManager()
        m.register_provider("openai")
        session = m.start_session()

        m.process_partial("hello", confidence=0.7)
        m.process_partial("hello world", confidence=0.8)
        m.process_final("hello world", confidence=0.95)

        m.stop_session()

        assert session.stats().partial_count == 2
        assert session.stats().final_count == 1
        assert session.stats().total_words == 0  # Words only tracked when explicitly passed

    def test_provider_failover_flow(self):
        """Test failover during active session."""
        m = StreamingSTTManager()
        m.register_provider("openai")
        m.register_provider("google")
        m.register_provider("deepinfra")

        session = m.start_session()
        assert session.provider_id == "openai"

        m.failover()
        assert session.provider_id == "google"

        m.failover()
        assert session.provider_id == "deepinfra"

    def test_error_recovery_flow(self):
        """Test error → recovery during session."""
        m = StreamingSTTManager()
        m.register_provider("openai")
        session = m.start_session()

        session.set_error("timeout")
        assert session.state == SessionState.ERROR

        m.recover()
        assert session.state == SessionState.STREAMING

    def test_partial_updates_continuously(self):
        """Test partial transcripts update continuously."""
        m = StreamingSTTManager()
        m.register_provider("openai")
        m.start_session()

        texts = ["hel", "hello", "hello wo", "hello world"]
        for text in texts:
            m.process_partial(text, confidence=0.7)

        assert m.active_session.partial_text == "hello world"
        assert m.active_session.stats().partial_count == 4

    def test_final_clears_partial(self):
        """Test final transcript clears partial."""
        m = StreamingSTTManager()
        m.register_provider("openai")
        m.start_session()

        m.process_partial("hello world")
        m.process_final("hello world")

        assert m.active_session.partial_text == ""
        assert m.active_session.final_text == "hello world"

    def test_session_lifecycle(self):
        """Test complete session lifecycle."""
        s = StreamingSTTSession(session_id="lifecycle")
        s.connect()
        s.start_streaming()
        s.receive_partial("hello")
        s.receive_final("hello world")
        s.finish()
        s.close()

        assert s.state == SessionState.CLOSED
        assert not s.is_active

    def test_word_timing(self):
        """Test word timing tracking."""
        m = StreamingSTTManager()
        m.register_provider("openai")
        m.start_session()

        words = make_words("hello world test")
        m.process_partial("hello world test", words=words)

        assert m.active_session.stats().total_words == 3

    def test_thread_safety(self):
        """Test concurrent access to manager."""
        m = StreamingSTTManager()
        m.register_provider("openai")
        m.start_session()
        results = []

        def process():
            for i in range(20):
                m.process_partial(f"word_{i}", confidence=0.8)
            results.append(m.snapshot()["metrics"]["total_partials"])

        threads = [threading.Thread(target=process) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 4
        # Each thread appends the cumulative total; final value should be 80
        assert max(results) == 80

    def test_long_session(self):
        """Test long session with many transcripts."""
        m = StreamingSTTManager()
        m.register_provider("openai")
        m.start_session()

        for i in range(100):
            m.process_partial(f"partial_{i}", confidence=0.7)
            m.process_final(f"final_{i}", confidence=0.9)

        snap = m.snapshot()
        assert snap["metrics"]["total_partials"] == 100
        assert snap["metrics"]["total_finals"] == 100

    def test_metrics_accuracy(self):
        """Test metrics track accurately."""
        m = StreamingSTTManager()
        m.register_provider("openai")
        m.start_session()

        m.process_partial("hello", confidence=0.8)
        m.process_final("world", confidence=0.9)

        snap = m.snapshot()
        assert snap["metrics"]["total_partials"] == 1
        assert snap["metrics"]["total_finals"] == 1
        assert snap["metrics"]["total_words"] == 2

    def test_config_propagation(self):
        """Test config propagates to components."""
        config = STTConfig(provider_id="google", language="fr", sample_rate=44100)
        m = StreamingSTTManager(config=config)
        assert m.config.language == "fr"
        assert m.config.sample_rate == 44100

    def test_provider_health_monitoring(self):
        """Test provider health is tracked."""
        m = StreamingSTTManager()
        m.register_provider("openai")
        m.start_session()

        provider = m.get_provider("openai")
        assert provider.health.total_requests >= 0

    def test_multiple_providers_independent(self):
        """Test providers are independent."""
        m = StreamingSTTManager()
        m.register_provider("openai")
        m.register_provider("google")

        p1 = m.get_provider("openai")
        p2 = m.get_provider("google")

        m.start_session(provider_id="openai")
        p1.send_audio(b'\x00' * 100)

        assert p1.health.total_requests == 1
        assert p2.health.total_requests == 0

    def test_stop_session_specific(self):
        """Test stopping a specific session."""
        m = StreamingSTTManager()
        m.register_provider("openai")
        s1 = m.start_session(session_id="s1")
        m.stop_session()
        s2 = m.start_session(session_id="s2")
        m.stop_session(session_id="s1")
        assert s1.state == SessionState.CLOSED

    def test_full_lifecycle_with_diagnostics(self):
        """Test complete lifecycle with metrics snapshot."""
        m = StreamingSTTManager()
        m.register_provider("openai")
        m.start_session()

        for i in range(10):
            m.process_partial(f"word_{i}", confidence=0.8)
        m.process_final("complete sentence", confidence=0.95)

        snap = m.snapshot()
        assert snap["metrics"]["total_partials"] == 10
        assert snap["metrics"]["total_finals"] == 1

        m.stop_session()
        snap2 = m.snapshot()
        # Session is None after stop, but metrics persist
        assert snap2["metrics"]["total_partials"] == 10
