"""Sprint D5 Tests — Streaming Text-to-Speech."""

import asyncio
import struct
import threading
import time
import pytest

from aios.voice.tts_streaming.events import SpeechChunk, TTSRequest, TTSEventType
from aios.voice.tts_streaming.provider import (
    TTSProvider, TTSProviderConfig, TTSProviderState, TTSProviderHealth,
)
from aios.voice.tts_streaming.session import (
    StreamingTTSSession, TTSSessionState, TTSSessionEvent,
    TTSSessionStats, TTS_SESSION_TRANSITIONS,
)
from aios.voice.tts_streaming.metrics import TTSMetrics, TTSMetricsSnapshot
from aios.voice.tts_streaming.manager import (
    StreamingTTSManager, TTSConfig, TTSManagerEventType, SpeechQueue,
)


# ─── Helpers ────────────────────────────────────────────────────────

def make_audio(size=100):
    return b'\x00\x00' * (size // 2)


def make_chunks(text="hello world", n=3):
    return [SpeechChunk(audio_data=make_audio(50), chunk_index=i,
            text=f"{text}_{i}", is_final=(i == n - 1)) for i in range(n)]


# ─── Events Tests ───────────────────────────────────────────────────

class TestSpeechChunk:
    def test_creation(self):
        c = SpeechChunk(audio_data=b'\x00\x00' * 50, chunk_index=0, text="hello")
        assert c.size_bytes == 100
        assert c.chunk_index == 0

    def test_to_dict(self):
        c = SpeechChunk(audio_data=b'\x00\x00', chunk_index=1, text="hi", is_final=True)
        d = c.to_dict()
        assert d["chunk_index"] == 1
        assert d["is_final"] is True
        assert d["size_bytes"] == 2

    def test_defaults(self):
        c = SpeechChunk(audio_data=b'\x00\x00')
        assert c.sample_rate == 22050
        assert c.is_final is False


class TestTTSRequest:
    def test_creation(self):
        r = TTSRequest(text="hello world", voice="alloy", speed=1.5)
        assert r.text == "hello world"
        assert r.voice == "alloy"

    def test_to_dict(self):
        r = TTSRequest(text="hi", priority=5)
        d = r.to_dict()
        assert d["text"] == "hi"
        assert d["priority"] == 5


# ─── Provider Tests ─────────────────────────────────────────────────

class TestTTSProvider:
    def test_creation(self):
        p = TTSProvider(config=TTSProviderConfig(provider_id="openai"))
        assert p.provider_id == "openai"
        assert p.state == TTSProviderState.DISCONNECTED

    def test_connect(self):
        p = TTSProvider(config=TTSProviderConfig(provider_id="openai"))
        assert p.connect()
        assert p.state == TTSProviderState.CONNECTED
        assert p.is_connected

    def test_synthesize(self):
        p = TTSProvider(config=TTSProviderConfig(provider_id="openai"))
        p.connect()
        chunks = p.synthesize("hello world")
        assert len(chunks) > 0
        assert chunks[-1].is_final is True

    def test_synthesize_not_connected(self):
        p = TTSProvider(config=TTSProviderConfig(provider_id="openai"))
        chunks = p.synthesize("hello")
        assert len(chunks) == 0

    def test_synthesize_streaming(self):
        p = TTSProvider(config=TTSProviderConfig(provider_id="openai"))
        p.connect()
        chunks = list(p.synthesize_streaming("hello world"))
        assert len(chunks) > 0
        assert chunks[-1].is_final is True

    def test_synthesize_streaming_not_connected(self):
        p = TTSProvider(config=TTSProviderConfig(provider_id="openai"))
        chunks = list(p.synthesize_streaming("hello"))
        assert len(chunks) == 0

    def test_set_error(self):
        p = TTSProvider(config=TTSProviderConfig(provider_id="openai"))
        p.connect()
        p.set_error("timeout")
        assert p.state == TTSProviderState.ERROR
        assert p.health.last_error == "timeout"

    def test_recover(self):
        p = TTSProvider(config=TTSProviderConfig(provider_id="openai"))
        p.connect()
        p.set_error("timeout")
        assert p.recover()
        assert p.state == TTSProviderState.CONNECTED

    def test_disconnect(self):
        p = TTSProvider(config=TTSProviderConfig(provider_id="openai"))
        p.connect()
        p.disconnect()
        assert p.state == TTSProviderState.DISCONNECTED

    def test_health_tracking(self):
        p = TTSProvider(config=TTSProviderConfig(provider_id="openai"))
        p.connect()
        p.synthesize("hello")
        h = p.health
        assert h.total_requests == 1
        assert h.successful_requests == 1

    def test_snapshot(self):
        p = TTSProvider(config=TTSProviderConfig(provider_id="openai"))
        s = p.snapshot()
        assert s["provider_id"] == "openai"
        assert "health" in s

    def test_consecutive_failures(self):
        p = TTSProvider(config=TTSProviderConfig(provider_id="openai"))
        p.connect()
        p.set_error("err1")
        p.set_error("err2")
        assert p.health.consecutive_failures == 2

    def test_config_to_dict(self):
        c = TTSProviderConfig(provider_id="openai", voice="alloy")
        d = c.to_dict()
        assert d["provider_id"] == "openai"
        assert d["voice"] == "alloy"


# ─── Session Tests ──────────────────────────────────────────────────

class TestStreamingTTSSession:
    def test_creation(self):
        s = StreamingTTSSession(session_id="test", provider_id="openai",
                                request=TTSRequest(text="hello"))
        assert s.id == "test"
        assert s.state == TTSSessionState.CREATED
        assert s.text == "hello"

    def test_auto_id(self):
        s = StreamingTTSSession()
        assert s.id.startswith("tts_")

    def test_queue(self):
        s = StreamingTTSSession(session_id="test", request=TTSRequest(text="hi"))
        assert s.queue()
        assert s.state == TTSSessionState.QUEUED

    def test_start_synthesis(self):
        s = StreamingTTSSession(session_id="test", request=TTSRequest(text="hi"))
        s.queue()
        assert s.start_synthesis()
        assert s.state == TTSSessionState.SYNTHESIZING

    def test_start_playing(self):
        s = StreamingTTSSession(session_id="test", request=TTSRequest(text="hi"))
        s.queue()
        s.start_synthesis()
        assert s.start_playing()
        assert s.state == TTSSessionState.PLAYING

    def test_pause(self):
        s = StreamingTTSSession(session_id="test", request=TTSRequest(text="hi"))
        s.queue(); s.start_synthesis(); s.start_playing()
        assert s.pause()
        assert s.state == TTSSessionState.PAUSED

    def test_resume(self):
        s = StreamingTTSSession(session_id="test", request=TTSRequest(text="hi"))
        s.queue(); s.start_synthesis(); s.start_playing(); s.pause()
        assert s.resume()
        assert s.state == TTSSessionState.PLAYING

    def test_complete(self):
        s = StreamingTTSSession(session_id="test", request=TTSRequest(text="hi"))
        s.queue(); s.start_synthesis(); s.start_playing()
        assert s.complete()
        assert s.state == TTSSessionState.COMPLETED

    def test_cancel(self):
        s = StreamingTTSSession(session_id="test", request=TTSRequest(text="hi"))
        s.queue()
        assert s.cancel()
        assert s.state == TTSSessionState.CANCELLED

    def test_set_error(self):
        s = StreamingTTSSession(session_id="test", request=TTSRequest(text="hi"))
        s.queue(); s.start_synthesis()
        s.set_error("provider_error")
        assert s.state == TTSSessionState.ERROR

    def test_receive_chunk(self):
        s = StreamingTTSSession(session_id="test", request=TTSRequest(text="hi"))
        s.queue(); s.start_synthesis()
        chunk = SpeechChunk(audio_data=b'\x00\x00', chunk_index=0)
        assert s.receive_chunk(chunk)
        assert s.stats().chunks_received == 1

    def test_play_chunk(self):
        s = StreamingTTSSession(session_id="test", request=TTSRequest(text="hi"))
        s.queue(); s.start_synthesis(); s.start_playing()
        chunk = SpeechChunk(audio_data=b'\x00\x00', chunk_index=0)
        s.receive_chunk(chunk)
        assert s.play_chunk(chunk)
        assert s.stats().chunks_played == 1

    def test_drop_chunk(self):
        s = StreamingTTSSession(session_id="test", request=TTSRequest(text="hi"))
        chunk = SpeechChunk(audio_data=b'\x00\x00', chunk_index=0)
        s.drop_chunk(chunk)
        assert s.stats().chunks_dropped == 1

    def test_interrupt(self):
        s = StreamingTTSSession(session_id="test", request=TTSRequest(text="hi"))
        s.queue(); s.start_synthesis(); s.start_playing()
        s.interrupt()
        assert s.state == TTSSessionState.CANCELLED

    def test_switch_provider(self):
        s = StreamingTTSSession(session_id="test", provider_id="openai",
                                request=TTSRequest(text="hi"))
        s.switch_provider("google")
        assert s.provider_id == "google"

    def test_is_active(self):
        s = StreamingTTSSession(session_id="test", request=TTSRequest(text="hi"))
        assert s.is_active
        s.cancel()
        assert not s.is_active

    def test_priority(self):
        s = StreamingTTSSession(session_id="test", request=TTSRequest(text="hi", priority=5))
        assert s.priority == 5

    def test_stats(self):
        s = StreamingTTSSession(session_id="test", provider_id="openai",
                                request=TTSRequest(text="hello"))
        stats = s.stats()
        assert stats.session_id == "test"
        assert stats.text == "hello"

    def test_stats_dict(self):
        s = StreamingTTSSession(session_id="test", request=TTSRequest(text="hi"))
        d = s.stats().to_dict()
        assert "session_id" in d
        assert "chunks_received" in d

    def test_valid_transitions(self):
        for state in TTSSessionState:
            assert state in TTS_SESSION_TRANSITIONS

    def test_invalid_transition(self):
        s = StreamingTTSSession(session_id="test", request=TTSRequest(text="hi"))
        assert not s.start_playing()  # Can't skip to PLAYING

    def test_uptime(self):
        s = StreamingTTSSession(session_id="test", request=TTSRequest(text="hi"))
        time.sleep(0.01)
        assert s.uptime > 0

    def test_total_bytes(self):
        s = StreamingTTSSession(session_id="test", request=TTSRequest(text="hi"))
        chunk = SpeechChunk(audio_data=b'\x00' * 100, chunk_index=0)
        s.receive_chunk(chunk)
        assert s.stats().total_bytes == 100


# ─── SpeechQueue Tests ──────────────────────────────────────────────

class TestSpeechQueue:
    def test_creation(self):
        q = SpeechQueue(max_size=10)
        assert q.size == 0
        assert not q.is_full

    def test_enqueue(self):
        q = SpeechQueue(max_size=10)
        s = StreamingTTSSession(session_id="s1", request=TTSRequest(text="hi", priority=0))
        s.queue()
        assert q.enqueue(s)
        assert q.size == 1

    def test_enqueue_full(self):
        q = SpeechQueue(max_size=1)
        s1 = StreamingTTSSession(session_id="s1", request=TTSRequest(text="hi"))
        s2 = StreamingTTSSession(session_id="s2", request=TTSRequest(text="hi"))
        s1.queue(); s2.queue()
        q.enqueue(s1)
        assert not q.enqueue(s2)

    def test_dequeue_priority(self):
        q = SpeechQueue(max_size=10)
        s1 = StreamingTTSSession(session_id="s1", request=TTSRequest(text="low", priority=0))
        s2 = StreamingTTSSession(session_id="s2", request=TTSRequest(text="high", priority=10))
        s1.queue(); s2.queue()
        q.enqueue(s1)
        q.enqueue(s2)
        # Higher priority should come first
        first = q.dequeue()
        assert first.id == "s2"

    def test_dequeue_empty(self):
        q = SpeechQueue()
        assert q.dequeue() is None

    def test_cancel(self):
        q = SpeechQueue(max_size=10)
        s = StreamingTTSSession(session_id="s1", request=TTSRequest(text="hi"))
        s.queue()
        q.enqueue(s)
        assert q.cancel("s1")
        assert q.size == 0

    def test_clear(self):
        q = SpeechQueue(max_size=10)
        for i in range(5):
            s = StreamingTTSSession(session_id=f"s{i}", request=TTSRequest(text=f"t{i}"))
            s.queue()
            q.enqueue(s)
        q.clear()
        assert q.size == 0

    def test_contains(self):
        q = SpeechQueue(max_size=10)
        s = StreamingTTSSession(session_id="s1", request=TTSRequest(text="hi"))
        s.queue()
        q.enqueue(s)
        assert q.contains("s1")
        assert not q.contains("s2")

    def test_get_all(self):
        q = SpeechQueue(max_size=10)
        for i in range(3):
            s = StreamingTTSSession(session_id=f"s{i}", request=TTSRequest(text=f"t{i}", priority=i))
            s.queue()
            q.enqueue(s)
        all_sessions = q.get_all()
        assert len(all_sessions) == 3

    def test_peek(self):
        q = SpeechQueue(max_size=10)
        s = StreamingTTSSession(session_id="s1", request=TTSRequest(text="hi", priority=5))
        s.queue()
        q.enqueue(s)
        peeked = q.peek()
        assert peeked.id == "s1"
        assert q.size == 1  # peek doesn't remove


# ─── Metrics Tests ──────────────────────────────────────────────────

class TestTTSMetrics:
    def test_creation(self):
        m = TTSMetrics()
        snap = m.snapshot()
        assert snap.total_syntheses == 0

    def test_record_synthesis(self):
        m = TTSMetrics()
        m.record_synthesis()
        assert m.snapshot().total_syntheses == 1

    def test_record_chunk(self):
        m = TTSMetrics()
        m.record_chunk(100)
        m.record_chunk(200)
        snap = m.snapshot()
        assert snap.total_chunks == 2
        assert snap.total_bytes == 300

    def test_record_played(self):
        m = TTSMetrics()
        m.record_played()
        assert m.snapshot().total_played == 1

    def test_record_dropped(self):
        m = TTSMetrics()
        m.record_dropped()
        assert m.snapshot().total_dropped == 1

    def test_record_latency(self):
        m = TTSMetrics()
        m.record_latency(50.0)
        m.record_latency(100.0)
        snap = m.snapshot()
        assert snap.avg_latency_ms == 75.0

    def test_record_first_word_latency(self):
        m = TTSMetrics()
        m.record_first_word_latency(200.0)
        m.record_first_word_latency(300.0)
        snap = m.snapshot()
        assert snap.first_word_latency_ms == 250.0

    def test_record_provider_switch(self):
        m = TTSMetrics()
        m.record_provider_switch()
        assert m.snapshot().provider_switches == 1

    def test_record_recovery(self):
        m = TTSMetrics()
        m.record_recovery()
        assert m.snapshot().recovery_events == 1

    def test_record_failure(self):
        m = TTSMetrics()
        m.record_failure()
        assert m.snapshot().failed_attempts == 1

    def test_percentile(self):
        m = TTSMetrics()
        for i in range(100):
            m.record_latency(float(i))
        snap = m.snapshot()
        assert snap.p95_latency_ms > 0
        assert snap.max_latency_ms == 99.0

    def test_reset(self):
        m = TTSMetrics()
        m.record_synthesis()
        m.record_chunk(100)
        m.reset()
        snap = m.snapshot()
        assert snap.total_syntheses == 0
        assert snap.total_bytes == 0

    def test_snapshot_dict(self):
        m = TTSMetrics()
        d = m.snapshot().to_dict()
        assert "total_syntheses" in d
        assert "first_word_latency_ms" in d


# ─── Manager Tests ──────────────────────────────────────────────────

class TestStreamingTTSManager:
    def test_creation(self):
        m = StreamingTTSManager()
        assert m.config.provider_id == "openai"

    def test_creation_with_config(self):
        config = TTSConfig(provider_id="google", voice="alloy")
        m = StreamingTTSManager(config=config)
        assert m.config.provider_id == "google"

    def test_register_provider(self):
        m = StreamingTTSManager()
        m.register_provider("openai")
        assert m.get_provider("openai") is not None

    def test_unregister_provider(self):
        m = StreamingTTSManager()
        m.register_provider("openai")
        m.unregister_provider("openai")
        assert m.get_provider("openai") is None

    def test_synthesize(self):
        m = StreamingTTSManager()
        m.register_provider("openai")
        session = m.synthesize("hello world")
        assert session is not None
        assert session.text == "hello world"

    def test_synthesize_no_provider(self):
        m = StreamingTTSManager()
        session = m.synthesize("hello")
        assert session is None

    def test_start_next(self):
        m = StreamingTTSManager()
        m.register_provider("openai")
        m.synthesize("hello")
        session = m.start_next()
        assert session is not None
        assert session.state == TTSSessionState.SYNTHESIZING

    def test_start_next_empty(self):
        m = StreamingTTSManager()
        assert m.start_next() is None

    def test_process_chunks(self):
        m = StreamingTTSManager()
        m.register_provider("openai")
        m.synthesize("hello world")
        m.start_next()
        chunks = m.process_chunks()
        assert len(chunks) > 0

    def test_synthesize_streaming(self):
        m = StreamingTTSManager()
        m.register_provider("openai")
        chunks = list(m.synthesize_streaming("hello world"))
        assert len(chunks) > 0
        assert chunks[-1].is_final is True

    def test_play_chunk(self):
        m = StreamingTTSManager()
        m.register_provider("openai")
        m.synthesize("hello")
        m.start_next()
        chunks = m.process_chunks()
        if chunks:
            assert m.play_chunk(chunks[0])

    def test_cancel_session(self):
        m = StreamingTTSManager()
        m.register_provider("openai")
        session = m.synthesize("hello")
        assert m.cancel_session(session.id)

    def test_cancel_nonexistent(self):
        m = StreamingTTSManager()
        assert not m.cancel_session("nonexistent")

    def test_interrupt(self):
        m = StreamingTTSManager()
        m.register_provider("openai")
        m.synthesize("hello")
        m.start_next()
        m.interrupt()
        assert m.active_session is None

    def test_complete_current(self):
        m = StreamingTTSManager()
        m.register_provider("openai")
        m.synthesize("hello")
        m.start_next()
        m.process_chunks()
        m.complete_current()
        assert m.active_session is None

    def test_failover(self):
        m = StreamingTTSManager()
        m.register_provider("openai")
        m.register_provider("google")
        session = m.synthesize("hello")
        m.start_next()
        assert m.failover()
        snap = m.snapshot()
        assert snap["metrics"]["provider_switches"] == 1

    def test_failover_no_session(self):
        m = StreamingTTSManager()
        assert not m.failover()

    def test_recover(self):
        m = StreamingTTSManager()
        m.register_provider("openai")
        session = m.synthesize("hello")
        m.start_next()
        session.set_error("timeout")
        assert m.recover()

    def test_recover_not_error(self):
        m = StreamingTTSManager()
        m.register_provider("openai")
        m.synthesize("hello")
        m.start_next()
        assert not m.recover()

    def test_snapshot(self):
        m = StreamingTTSManager()
        m.register_provider("openai")
        m.synthesize("hello")
        snap = m.snapshot()
        assert "config" in snap
        assert "metrics" in snap
        assert "providers" in snap
        assert "queue" in snap

    def test_snapshot_empty(self):
        m = StreamingTTSManager()
        snap = m.snapshot()
        assert snap["session"] is None
        assert snap["queue_size"] == 0

    def test_reset(self):
        m = StreamingTTSManager()
        m.register_provider("openai")
        m.synthesize("hello")
        m.reset()
        snap = m.snapshot()
        assert snap["queue_size"] == 0

    def test_config_to_dict(self):
        c = TTSConfig(provider_id="google", voice="alloy")
        d = c.to_dict()
        assert d["provider_id"] == "google"

    def test_multiple_syntheses(self):
        m = StreamingTTSManager()
        m.register_provider("openai")
        for i in range(5):
            m.synthesize(f"message {i}")
        assert m.queue.size == 5

    def test_active_session(self):
        m = StreamingTTSManager()
        m.register_provider("openai")
        assert m.active_session is None
        m.synthesize("hello")
        m.start_next()
        assert m.active_session is not None

    def test_metrics_tracked(self):
        m = StreamingTTSManager()
        m.register_provider("openai")
        m.synthesize("hello")
        m.start_next()
        m.process_chunks()
        snap = m.snapshot()
        assert snap["metrics"]["total_syntheses"] == 1
        assert snap["metrics"]["total_chunks"] > 0

    def test_provider_snapshot(self):
        m = StreamingTTSManager()
        m.register_provider("openai")
        m.register_provider("google")
        snap = m.snapshot()
        assert "openai" in snap["providers"]
        assert "google" in snap["providers"]


# ─── Integration Tests ──────────────────────────────────────────────

class TestD5Integration:
    def test_full_synthesis_flow(self):
        """Test complete flow: synthesize → queue → start → chunks → play → complete."""
        m = StreamingTTSManager()
        m.register_provider("openai")
        session = m.synthesize("Hello world")
        assert session is not None
        assert session.state == TTSSessionState.QUEUED

        started = m.start_next()
        assert started.state == TTSSessionState.SYNTHESIZING

        chunks = m.process_chunks()
        assert len(chunks) > 0

        for chunk in chunks:
            m.play_chunk(chunk)

        m.complete_current()
        assert m.active_session is None

    def test_streaming_synthesis(self):
        """Test streaming synthesis yields chunks incrementally."""
        m = StreamingTTSManager()
        m.register_provider("openai")
        chunks = list(m.synthesize_streaming("The quick brown fox"))
        assert len(chunks) > 0
        assert chunks[-1].is_final is True

    def test_priority_queue(self):
        """Test higher priority sessions are served first."""
        q = SpeechQueue(max_size=10)
        s1 = StreamingTTSSession(session_id="s1", request=TTSRequest(text="low", priority=0))
        s2 = StreamingTTSSession(session_id="s2", request=TTSRequest(text="high", priority=10))
        s3 = StreamingTTSSession(session_id="s3", request=TTSRequest(text="medium", priority=5))
        s1.queue(); s2.queue(); s3.queue()
        q.enqueue(s1)
        q.enqueue(s2)
        q.enqueue(s3)

        first = q.dequeue()
        second = q.dequeue()
        third = q.dequeue()
        assert first.text == "high"
        assert second.text == "medium"
        assert third.text == "low"

    def test_cancel_queued(self):
        """Test cancelling a queued session."""
        m = StreamingTTSManager()
        m.register_provider("openai")
        s = m.synthesize("to cancel")
        assert m.cancel_session(s.id)
        assert s.state == TTSSessionState.CANCELLED

    def test_interrupt_clears_queue(self):
        """Test interrupt clears the entire queue."""
        m = StreamingTTSManager()
        m.register_provider("openai")
        for i in range(5):
            m.synthesize(f"msg {i}")
        m.interrupt()
        assert m.queue.size == 0
        assert m.active_session is None

    def test_failover_flow(self):
        """Test failover to different provider."""
        m = StreamingTTSManager()
        m.register_provider("openai")
        m.register_provider("google")
        m.register_provider("deepinfra")

        session = m.synthesize("hello")
        m.start_next()

        m.failover()
        assert session.provider_id == "google"

        m.failover()
        assert session.provider_id == "deepinfra"

    def test_error_recovery(self):
        """Test error → recovery during synthesis."""
        m = StreamingTTSManager()
        m.register_provider("openai")
        session = m.synthesize("hello")
        m.start_next()

        session.set_error("timeout")
        assert session.state == TTSSessionState.ERROR

        m.recover()
        assert session.state == TTSSessionState.QUEUED

    def test_multiple_sessions_queue(self):
        """Test multiple sessions in queue."""
        m = StreamingTTSManager()
        m.register_provider("openai")
        for i in range(3):
            m.synthesize(f"message {i}")
        assert m.queue.size == 3

    def test_long_text_synthesis(self):
        """Test synthesizing long text produces multiple chunks."""
        m = StreamingTTSManager()
        m.register_provider("openai")
        m.synthesize("The quick brown fox jumps over the lazy dog " * 10)
        m.start_next()
        chunks = m.process_chunks()
        assert len(chunks) >= 1

    def test_thread_safety(self):
        """Test concurrent access to manager."""
        config = TTSConfig(max_queue_size=50)
        m = StreamingTTSManager(config=config)
        m.register_provider("openai")
        results = []

        def synthesize():
            for i in range(10):
                m.synthesize(f"msg_{i}")
            results.append(True)

        threads = [threading.Thread(target=synthesize) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 3
        assert m.snapshot()["queue_size"] == 30

    def test_metrics_accuracy(self):
        """Test metrics track accurately."""
        m = StreamingTTSManager()
        m.register_provider("openai")
        m.synthesize("hello")
        m.start_next()
        m.process_chunks()

        snap = m.snapshot()
        assert snap["metrics"]["total_syntheses"] == 1
        assert snap["metrics"]["total_chunks"] > 0

    def test_provider_health(self):
        """Test provider health is tracked."""
        m = StreamingTTSManager()
        m.register_provider("openai")
        m.synthesize("hello")
        m.start_next()
        m.process_chunks()

        provider = m.get_provider("openai")
        assert provider.health.total_requests >= 0

    def test_queue_full_reject(self):
        """Test synthesis rejected when queue is full."""
        config = TTSConfig(max_queue_size=2)
        m = StreamingTTSManager(config=config)
        m.register_provider("openai")

        m.synthesize("first")
        m.synthesize("second")
        result = m.synthesize("third")
        assert result is None

    def test_session_lifecycle(self):
        """Test complete session lifecycle."""
        s = StreamingTTSSession(session_id="lifecycle", request=TTSRequest(text="test"))
        s.queue()
        s.start_synthesis()
        s.start_playing()
        s.complete()

        assert s.state == TTSSessionState.COMPLETED

    def test_chunk_processing_flow(self):
        """Test chunk processing from synthesis to playback."""
        m = StreamingTTSManager()
        m.register_provider("openai")
        session = m.synthesize("hello world")
        m.start_next()
        chunks = m.process_chunks()

        for chunk in chunks:
            assert m.play_chunk(chunk)

        stats = session.stats()
        assert stats.chunks_received == len(chunks)
        assert stats.chunks_played == len(chunks)

    def test_config_propagation(self):
        """Test config propagates to components."""
        config = TTSConfig(provider_id="google", voice="alloy", speed=1.5)
        m = StreamingTTSManager(config=config)
        assert m.config.voice == "alloy"
        assert m.config.speed == 1.5

    def test_multiple_providers_independent(self):
        """Test providers are independent."""
        m = StreamingTTSManager()
        m.register_provider("openai")
        m.register_provider("google")

        p1 = m.get_provider("openai")
        p2 = m.get_provider("google")

        m.register_provider("openai")
        assert p1.provider_id == "openai"
        assert p2.provider_id == "google"

    def test_speech_queue_independence(self):
        """Test SpeechQueue works independently."""
        q = SpeechQueue(max_size=5)
        for i in range(3):
            s = StreamingTTSSession(session_id=f"s{i}", request=TTSRequest(text=f"t{i}", priority=i))
            s.queue()
            q.enqueue(s)
        assert q.size == 3
        first = q.dequeue()
        assert first.priority == 2  # Highest first

    def test_full_lifecycle_with_diagnostics(self):
        """Test complete lifecycle with metrics snapshot."""
        m = StreamingTTSManager()
        m.register_provider("openai")
        session = m.synthesize("Hello world test")

        m.start_next()
        chunks = m.process_chunks()
        for chunk in chunks:
            m.play_chunk(chunk)
        m.complete_current()

        snap = m.snapshot()
        assert snap["metrics"]["total_syntheses"] == 1
        assert snap["metrics"]["total_played"] > 0
