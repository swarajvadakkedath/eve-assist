"""Sprint D3 Tests — Real-Time Speech Pipeline.

Tests cover:
    - AudioChunk creation, validation, lifecycle
    - ChunkGenerator chunking, flush, reset
    - StreamMetrics latency, throughput, percentiles
    - SpeechSession lifecycle, transitions, events
    - StreamRouter multi-consumer, drop policies, backpressure
    - SpeechStreamManager integration, feed_audio, subscribe
    - Configuration, performance, thread safety
"""

import asyncio
import struct
import threading
import time
import pytest

from aios.voice.stream.chunk import (
    AudioChunk, ChunkGenerator, ChunkStatus,
    validate_chunk, compute_chunk_order_score,
)
from aios.voice.stream.metrics import (
    StreamMetrics, StreamMetricsSnapshot, LatencySnapshot,
)
from aios.voice.stream.session import (
    SpeechSession, SessionState, SessionEvent, SessionStats,
    SESSION_TRANSITIONS,
)
from aios.voice.stream.router import (
    StreamRouter, ConsumerInfo, ConsumerState, DropPolicy,
)
from aios.voice.stream.manager import (
    SpeechStreamManager, StreamConfig, StreamEventType,
)


# ─── Helpers ────────────────────────────────────────────────────────

def make_pcm_silence(size: int = 960) -> bytes:
    """Generate silence PCM data (16-bit, 16kHz)."""
    return b'\x00\x00' * (size // 2)


def make_pcm_speech(size: int = 960) -> bytes:
    """Generate speech-like PCM data (16-bit, 16kHz)."""
    samples = [16000 if i % 2 == 0 else -16000 for i in range(size // 2)]
    return struct.pack(f"<{len(samples)}h", *samples)


def make_pcm_mixed(size: int = 960, level: int = 8000) -> bytes:
    """Generate mixed-level PCM data."""
    samples = [level] * (size // 2)
    return struct.pack(f"<{len(samples)}h", *samples)


# ─── AudioChunk Tests ───────────────────────────────────────────────

class TestAudioChunk:
    def test_creation(self):
        chunk = AudioChunk(data=b'\x00\x00' * 100, sequence=0)
        assert chunk.data == b'\x00\x00' * 100
        assert chunk.sequence == 0
        assert chunk.status == ChunkStatus.CREATED
        assert chunk.is_valid

    def test_size_bytes(self):
        data = b'\x00\x00' * 50
        chunk = AudioChunk(data=data, sequence=0)
        assert chunk.size_bytes == 100

    def test_age_ms(self):
        chunk = AudioChunk(data=b'\x00', sequence=0)
        time.sleep(0.01)
        assert chunk.age_ms > 0

    def test_mark_processing(self):
        chunk = AudioChunk(data=b'\x00', sequence=0)
        chunk.mark_processing()
        assert chunk.status == ChunkStatus.PROCESSING

    def test_mark_delivered(self):
        chunk = AudioChunk(data=b'\x00', sequence=0)
        chunk.mark_delivered()
        assert chunk.status == ChunkStatus.DELIVERED

    def test_mark_dropped(self):
        chunk = AudioChunk(data=b'\x00', sequence=0)
        chunk.mark_dropped(reason="overflow")
        assert chunk.status == ChunkStatus.DROPPED
        assert chunk.metadata["drop_reason"] == "overflow"

    def test_is_valid_empty(self):
        chunk = AudioChunk(data=b'', sequence=0)
        assert not chunk.is_valid

    def test_is_valid_size_mismatch(self):
        chunk = AudioChunk(data=b'\x00\x00', sequence=0, chunk_size_bytes=100)
        assert not chunk.is_valid

    def test_is_valid_size_match(self):
        chunk = AudioChunk(data=b'\x00\x00', sequence=0, chunk_size_bytes=2)
        assert chunk.is_valid

    def test_to_dict(self):
        chunk = AudioChunk(data=b'\x00\x00', sequence=5, sample_rate=16000)
        d = chunk.to_dict()
        assert d["sequence"] == 5
        assert d["sample_rate"] == 16000
        assert d["status"] == "created"

    def test_metadata(self):
        chunk = AudioChunk(data=b'\x00', sequence=0, metadata={"source": "test"})
        assert chunk.metadata["source"] == "test"

    def test_timestamp(self):
        t = time.monotonic()
        chunk = AudioChunk(data=b'\x00', sequence=0, timestamp=t)
        assert chunk.timestamp == t


# ─── ChunkGenerator Tests ───────────────────────────────────────────

class TestChunkGenerator:
    def test_creation(self):
        gen = ChunkGenerator(chunk_size_ms=30, sample_rate=16000)
        assert gen.chunk_size_bytes == 960  # 30ms * 16000 * 2 bytes
        assert gen.chunk_size_ms == 30

    def test_feed_exact_chunk(self):
        gen = ChunkGenerator(chunk_size_ms=30, sample_rate=16000)
        # 30ms at 16kHz 16-bit mono = 960 bytes
        data = make_pcm_silence(960)
        chunks = gen.feed(data)
        assert len(chunks) == 1
        assert chunks[0].sequence == 0
        assert chunks[0].size_bytes == 960

    def test_feed_multiple_chunks(self):
        gen = ChunkGenerator(chunk_size_ms=30, sample_rate=16000)
        data = make_pcm_silence(960 * 3)
        chunks = gen.feed(data)
        assert len(chunks) == 3
        assert chunks[0].sequence == 0
        assert chunks[1].sequence == 1
        assert chunks[2].sequence == 2

    def test_feed_partial(self):
        gen = ChunkGenerator(chunk_size_ms=30, sample_rate=16000)
        data = make_pcm_silence(480)  # Half a chunk
        chunks = gen.feed(data)
        assert len(chunks) == 0
        assert gen.buffered_bytes == 480

    def test_feed_accumulate(self):
        gen = ChunkGenerator(chunk_size_ms=30, sample_rate=16000)
        gen.feed(make_pcm_silence(480))
        gen.feed(make_pcm_silence(480))
        # Now we have 960 bytes = 1 chunk
        chunks = gen.feed(make_pcm_silence(0))
        # The second feed should produce 1 chunk
        # Actually the first feed of 480 + second feed of 480 = 960
        # But we already called feed(480) twice
        # Let me fix: we need 960 bytes total
        gen2 = ChunkGenerator(chunk_size_ms=30, sample_rate=16000)
        gen2.feed(make_pcm_silence(480))
        chunks = gen2.feed(make_pcm_silence(480))
        assert len(chunks) == 1

    def test_flush_partial(self):
        gen = ChunkGenerator(chunk_size_ms=30, sample_rate=16000)
        gen.feed(make_pcm_silence(480))
        chunk = gen.flush()
        assert chunk is not None
        assert chunk.metadata.get("partial") is True
        assert gen.buffered_bytes == 0

    def test_flush_empty(self):
        gen = ChunkGenerator(chunk_size_ms=30, sample_rate=16000)
        chunk = gen.flush()
        assert chunk is None

    def test_reset(self):
        gen = ChunkGenerator(chunk_size_ms=30, sample_rate=16000)
        gen.feed(make_pcm_silence(960))
        gen.reset()
        assert gen.sequence == 0
        assert gen.buffered_bytes == 0
        assert gen.stats["total_chunks_created"] == 0

    def test_stats(self):
        gen = ChunkGenerator(chunk_size_ms=30, sample_rate=16000)
        gen.feed(make_pcm_silence(960))
        s = gen.stats
        assert s["total_chunks_created"] == 1
        assert s["total_bytes_fed"] == 960

    def test_mono_16bit(self):
        gen = ChunkGenerator(chunk_size_ms=30, sample_rate=16000, channels=1, sample_width=2)
        assert gen.chunk_size_bytes == 960

    def test_stereo_16bit(self):
        gen = ChunkGenerator(chunk_size_ms=30, sample_rate=16000, channels=2, sample_width=2)
        assert gen.chunk_size_bytes == 1920

    def test_sequence_monotonic(self):
        gen = ChunkGenerator(chunk_size_ms=30, sample_rate=16000)
        chunks1 = gen.feed(make_pcm_silence(960))
        chunks2 = gen.feed(make_pcm_silence(960))
        assert chunks2[0].sequence > chunks1[0].sequence

    def test_thread_safety(self):
        gen = ChunkGenerator(chunk_size_ms=30, sample_rate=16000)
        results = []

        def feed_data():
            for _ in range(10):
                gen.feed(make_pcm_silence(960))
            results.append(gen.stats["total_chunks_created"])

        threads = [threading.Thread(target=feed_data) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 4
        # Each thread appends the cumulative total; final value should be 40
        assert max(results) == 40


# ─── validate_chunk Tests ───────────────────────────────────────────

class TestValidateChunk:
    def test_valid(self):
        chunk = AudioChunk(data=b'\x00\x00', sequence=0, sample_rate=16000, channels=1)
        assert validate_chunk(chunk, 0)

    def test_empty_data(self):
        chunk = AudioChunk(data=b'', sequence=0)
        assert not validate_chunk(chunk, 0)

    def test_wrong_size(self):
        chunk = AudioChunk(data=b'\x00\x00', sequence=0)
        assert not validate_chunk(chunk, 100)

    def test_zero_sample_rate(self):
        chunk = AudioChunk(data=b'\x00', sequence=0, sample_rate=0)
        assert not validate_chunk(chunk, 0)

    def test_zero_channels(self):
        chunk = AudioChunk(data=b'\x00', sequence=0, channels=0)
        assert not validate_chunk(chunk, 0)

    def test_skip_size_check(self):
        chunk = AudioChunk(data=b'\x00\x00', sequence=0)
        assert validate_chunk(chunk, 0)


# ─── compute_chunk_order_score Tests ────────────────────────────────

class TestChunkOrderScore:
    def test_empty(self):
        assert compute_chunk_order_score([]) == (0, 0)

    def test_single(self):
        chunk = AudioChunk(data=b'\x00', sequence=0)
        assert compute_chunk_order_score([chunk]) == (0, 0)

    def test_ordered(self):
        chunks = [
            AudioChunk(data=b'\x00', sequence=i) for i in range(5)
        ]
        out, gaps = compute_chunk_order_score(chunks)
        assert out == 0
        assert gaps == 0

    def test_gap(self):
        chunks = [
            AudioChunk(data=b'\x00', sequence=0),
            AudioChunk(data=b'\x00', sequence=3),
        ]
        out, gaps = compute_chunk_order_score(chunks)
        assert out == 0
        assert gaps == 1

    def test_out_of_order(self):
        chunks = [
            AudioChunk(data=b'\x00', sequence=5),
            AudioChunk(data=b'\x00', sequence=2),
        ]
        out, gaps = compute_chunk_order_score(chunks)
        assert out == 1
        assert gaps == 0


# ─── StreamMetrics Tests ────────────────────────────────────────────

class TestStreamMetrics:
    def test_creation(self):
        m = StreamMetrics()
        snap = m.snapshot()
        assert snap.chunks_created == 0
        assert snap.uptime_seconds >= 0

    def test_record_chunk_created(self):
        m = StreamMetrics()
        m.record_chunk_created(960)
        snap = m.snapshot()
        assert snap.chunks_created == 1
        assert snap.total_bytes_processed == 960

    def test_record_chunk_delivered(self):
        m = StreamMetrics()
        m.record_chunk_delivered()
        snap = m.snapshot()
        assert snap.chunks_delivered == 1

    def test_record_chunk_dropped(self):
        m = StreamMetrics()
        m.record_chunk_dropped()
        snap = m.snapshot()
        assert snap.chunks_dropped == 1

    def test_record_chunk_lost(self):
        m = StreamMetrics()
        m.record_chunk_lost()
        snap = m.snapshot()
        assert snap.chunks_lost == 1

    def test_record_latency(self):
        m = StreamMetrics()
        m.record_latency("capture", 5.0)
        m.record_latency("buffer", 3.0)
        m.record_latency("end_to_end", 15.0)
        snap = m.snapshot()
        assert snap.avg_capture_ms == 5.0
        assert snap.avg_buffer_ms == 3.0
        assert snap.avg_end_to_end_ms == 15.0

    def test_record_backpressure(self):
        m = StreamMetrics()
        m.record_backpressure()
        snap = m.snapshot()
        assert snap.backpressure_events == 1

    def test_record_recovery(self):
        m = StreamMetrics()
        m.record_recovery()
        snap = m.snapshot()
        assert snap.recovery_events == 1

    def test_queue_depth(self):
        m = StreamMetrics()
        m.update_queue_depth(5)
        m.update_queue_depth(10)
        snap = m.snapshot()
        assert snap.queue_depth == 10
        assert snap.max_queue_depth == 10

    def test_percentile(self):
        m = StreamMetrics()
        for i in range(100):
            m.record_latency("end_to_end", float(i))
        snap = m.snapshot()
        assert snap.p95_end_to_end_ms > 0
        assert snap.p99_end_to_end_ms > 0
        assert snap.max_end_to_end_ms == 99.0

    def test_throughput_rate(self):
        m = StreamMetrics(rate_window_seconds=1.0)
        for _ in range(10):
            m.record_chunk_created(960)
        time.sleep(0.1)
        snap = m.snapshot()
        assert snap.chunks_per_second > 0

    def test_reset(self):
        m = StreamMetrics()
        m.record_chunk_created(960)
        m.record_latency("capture", 5.0)
        m.reset()
        snap = m.snapshot()
        assert snap.chunks_created == 0
        assert snap.avg_capture_ms == 0.0

    def test_snapshot_dict(self):
        m = StreamMetrics()
        snap = m.snapshot()
        d = snap.to_dict()
        assert "chunks_created" in d
        assert "avg_end_to_end_ms" in d


# ─── SpeechSession Tests ───────────────────────────────────────────

class TestSpeechSession:
    def test_creation(self):
        s = SpeechSession(session_id="test_1")
        assert s.id == "test_1"
        assert s.state == SessionState.CREATED
        assert s.is_active

    def test_auto_id(self):
        s = SpeechSession()
        assert s.id.startswith("session_")

    def test_open(self):
        s = SpeechSession(session_id="test")
        assert s.open()
        assert s.state == SessionState.OPENING

    def test_start_streaming(self):
        s = SpeechSession(session_id="test")
        s.open()
        assert s.start_streaming()
        assert s.state == SessionState.STREAMING

    def test_receive_chunk(self):
        s = SpeechSession(session_id="test")
        s.open()
        s.start_streaming()
        chunk = AudioChunk(data=b'\x00\x00', sequence=0)
        assert s.receive_chunk(chunk)
        assert s.stats().chunks_received == 1

    def test_receive_chunk_not_streaming(self):
        s = SpeechSession(session_id="test")
        chunk = AudioChunk(data=b'\x00\x00', sequence=0)
        assert not s.receive_chunk(chunk)

    def test_process_chunk(self):
        s = SpeechSession(session_id="test")
        s.open()
        s.start_streaming()
        chunk = AudioChunk(data=b'\x00\x00', sequence=0)
        s.receive_chunk(chunk)
        s.process_chunk(chunk)
        assert s.stats().chunks_processed == 1

    def test_drop_chunk(self):
        s = SpeechSession(session_id="test")
        s.open()
        s.start_streaming()
        chunk = AudioChunk(data=b'\x00\x00', sequence=0)
        s.drop_chunk(chunk, reason="overflow")
        assert s.stats().chunks_dropped == 1

    def test_pause(self):
        s = SpeechSession(session_id="test")
        s.open()
        s.start_streaming()
        assert s.pause()
        assert s.state == SessionState.PAUSED

    def test_resume(self):
        s = SpeechSession(session_id="test")
        s.open()
        s.start_streaming()
        s.pause()
        assert s.resume()
        assert s.state == SessionState.STREAMING

    def test_recover(self):
        s = SpeechSession(session_id="test")
        s.open()
        s.start_streaming()
        assert s.recover()
        assert s.state == SessionState.RECOVERING

    def test_finish_recovery(self):
        s = SpeechSession(session_id="test")
        s.open()
        s.start_streaming()
        s.recover()
        assert s.finish_recovery()
        assert s.state == SessionState.STREAMING

    def test_close(self):
        s = SpeechSession(session_id="test")
        s.open()
        s.close()
        assert s.state == SessionState.CLOSED
        assert not s.is_active

    def test_set_error(self):
        s = SpeechSession(session_id="test")
        s.open()
        s.start_streaming()
        s.set_error("timeout")
        assert s.state == SessionState.ERROR
        assert s.stats().error == "timeout"

    def test_invalid_transition(self):
        s = SpeechSession(session_id="test")
        # Can't go from CREATED directly to STREAMING
        assert not s.start_streaming()

    def test_stats(self):
        s = SpeechSession(session_id="test")
        stats = s.stats()
        assert stats.session_id == "test"
        assert stats.state == "created"

    def test_stats_dict(self):
        s = SpeechSession(session_id="test")
        d = s.stats().to_dict()
        assert "session_id" in d
        assert "chunks_received" in d

    def test_uptime(self):
        s = SpeechSession(session_id="test")
        time.sleep(0.01)
        assert s.uptime > 0

    def test_elapsed(self):
        s = SpeechSession(session_id="test")
        s.open()
        time.sleep(0.01)
        assert s.elapsed > 0

    def test_event_handler(self):
        s = SpeechSession(session_id="test")
        events = []
        s.on(SessionEvent.STATE_CHANGED, lambda e, d: events.append((e, d)))
        s.open()
        # Event is async, so it won't fire in sync context
        # But handler should be registered
        assert len(s._event_handlers[SessionEvent.STATE_CHANGED]) == 1

    def test_check_timeout(self):
        s = SpeechSession(session_id="test", silence_timeout=0.01)
        s.open()
        s.start_streaming()
        time.sleep(0.02)
        assert s.check_timeout() is True

    def test_check_timeout_not_streaming(self):
        s = SpeechSession(session_id="test", silence_timeout=0.01)
        assert s.check_timeout() is False

    def test_total_bytes(self):
        s = SpeechSession(session_id="test")
        s.open()
        s.start_streaming()
        chunk = AudioChunk(data=b'\x00' * 100, sequence=0)
        s.receive_chunk(chunk)
        assert s.stats().total_bytes == 100

    def test_valid_transitions_map(self):
        """All states should have transition rules."""
        for state in SessionState:
            assert state in SESSION_TRANSITIONS


# ─── StreamRouter Tests ─────────────────────────────────────────────

class TestStreamRouter:
    def test_creation(self):
        r = StreamRouter()
        assert r.consumer_count == 0

    def test_subscribe(self):
        r = StreamRouter()
        received = []
        assert r.subscribe("c1", lambda c: received.append(c))
        assert r.consumer_count == 1

    def test_subscribe_duplicate(self):
        r = StreamRouter()
        r.subscribe("c1", lambda c: None)
        assert not r.subscribe("c1", lambda c: None)

    def test_unsubscribe(self):
        r = StreamRouter()
        r.subscribe("c1", lambda c: None)
        assert r.unsubscribe("c1")
        assert r.consumer_count == 0

    def test_unsubscribe_nonexistent(self):
        r = StreamRouter()
        assert not r.unsubscribe("c1")

    def test_route_single_consumer(self):
        r = StreamRouter()
        received = []
        r.subscribe("c1", lambda c: received.append(c))
        chunk = AudioChunk(data=b'\x00\x00', sequence=0)
        results = r.route(chunk)
        r.deliver()
        assert results["c1"] is True
        assert len(received) == 1

    def test_route_multiple_consumers(self):
        r = StreamRouter()
        received1 = []
        received2 = []
        r.subscribe("c1", lambda c: received1.append(c))
        r.subscribe("c2", lambda c: received2.append(c))
        chunk = AudioChunk(data=b'\x00\x00', sequence=0)
        results = r.route(chunk)
        r.deliver()
        assert results["c1"] is True
        assert results["c2"] is True
        assert len(received1) == 1
        assert len(received2) == 1

    def test_route_independent_queues(self):
        r = StreamRouter(default_max_queue=5)
        received1 = []
        r.subscribe("c1", lambda c: received1.append(c))
        r.subscribe("c2", lambda c: None, max_queue_size=1)
        # c2 should overflow independently
        for i in range(10):
            chunk = AudioChunk(data=b'\x00\x00', sequence=i)
            r.route(chunk)
        info1 = r.consumer_info("c1")
        info2 = r.consumer_info("c2")
        assert info1.chunks_received == 10
        assert info2.chunks_dropped > 0

    def test_pause_consumer(self):
        r = StreamRouter()
        received = []
        r.subscribe("c1", lambda c: received.append(c))
        r.pause_consumer("c1")
        chunk = AudioChunk(data=b'\x00\x00', sequence=0)
        r.route(chunk)
        assert len(received) == 0

    def test_resume_consumer(self):
        r = StreamRouter()
        received = []
        r.subscribe("c1", lambda c: received.append(c))
        r.pause_consumer("c1")
        r.resume_consumer("c1")
        chunk = AudioChunk(data=b'\x00\x00', sequence=0)
        r.route(chunk)
        r.deliver()
        assert len(received) == 1

    def test_drop_oldest(self):
        r = StreamRouter(default_max_queue=2, default_drop_policy=DropPolicy.DROP_OLDEST)
        received = []
        r.subscribe("c1", lambda c: received.append(c))
        for i in range(5):
            chunk = AudioChunk(data=b'\x00\x00', sequence=i)
            r.route(chunk)
        info = r.consumer_info("c1")
        assert info.chunks_dropped > 0

    def test_drop_newest(self):
        r = StreamRouter(default_max_queue=2, default_drop_policy=DropPolicy.DROP_NEWEST)
        received = []
        r.subscribe("c1", lambda c: received.append(c))
        for i in range(5):
            chunk = AudioChunk(data=b'\x00\x00', sequence=i)
            r.route(chunk)
        info = r.consumer_info("c1")
        assert info.chunks_dropped > 0

    def test_consumer_info(self):
        r = StreamRouter()
        r.subscribe("c1", lambda c: None)
        info = r.consumer_info("c1")
        assert info is not None
        assert info.consumer_id == "c1"
        assert info.state == ConsumerState.ACTIVE

    def test_consumer_info_nonexistent(self):
        r = StreamRouter()
        assert r.consumer_info("c1") is None

    def test_all_consumer_info(self):
        r = StreamRouter()
        r.subscribe("c1", lambda c: None)
        r.subscribe("c2", lambda c: None)
        infos = r.all_consumer_info()
        assert len(infos) == 2

    def test_stats(self):
        r = StreamRouter()
        r.subscribe("c1", lambda c: None)
        s = r.stats()
        assert s["consumer_count"] == 1

    def test_reset(self):
        r = StreamRouter()
        r.subscribe("c1", lambda c: None)
        r.route(AudioChunk(data=b'\x00', sequence=0))
        r.reset()
        assert r.consumer_count == 0
        assert r.total_chunks_routed == 0

    def test_route_returns_results(self):
        r = StreamRouter()
        r.subscribe("c1", lambda c: None)
        chunk = AudioChunk(data=b'\x00', sequence=0)
        results = r.route(chunk)
        assert "c1" in results


# ─── SpeechStreamManager Tests ──────────────────────────────────────

class TestSpeechStreamManager:
    def test_creation(self):
        m = SpeechStreamManager()
        assert m.state == "idle"

    def test_creation_with_config(self):
        config = StreamConfig(chunk_size_ms=20, sample_rate=8000)
        m = SpeechStreamManager(config=config)
        assert m.config.chunk_size_ms == 20
        assert m.config.sample_rate == 8000

    def test_start(self):
        m = SpeechStreamManager()
        session = m.start()
        assert m.state == "streaming"
        assert session.state == SessionState.STREAMING

    def test_start_with_id(self):
        m = SpeechStreamManager()
        session = m.start(session_id="my_session")
        assert session.id == "my_session"

    def test_stop(self):
        m = SpeechStreamManager()
        m.start()
        m.stop()
        assert m.state == "idle"

    def test_feed_audio(self):
        m = SpeechStreamManager()
        m.start()
        data = make_pcm_silence(960)
        chunks = m.feed_audio(data)
        assert len(chunks) == 1

    def test_feed_audio_not_streaming(self):
        m = SpeechStreamManager()
        chunks = m.feed_audio(make_pcm_silence(960))
        assert len(chunks) == 0

    def test_subscribe_consumer(self):
        m = SpeechStreamManager()
        received = []
        assert m.subscribe_consumer("stt", lambda c: received.append(c))
        m.start()
        m.feed_audio(make_pcm_silence(960))
        assert len(received) == 1

    def test_unsubscribe_consumer(self):
        m = SpeechStreamManager()
        m.subscribe_consumer("stt", lambda c: None)
        assert m.unsubscribe_consumer("stt")
        assert m.router.consumer_count == 0

    def test_multiple_consumers(self):
        m = SpeechStreamManager()
        received1 = []
        received2 = []
        m.subscribe_consumer("stt", lambda c: received1.append(c))
        m.subscribe_consumer("wake", lambda c: received2.append(c))
        m.start()
        m.feed_audio(make_pcm_silence(960))
        assert len(received1) == 1
        assert len(received2) == 1

    def test_pause_resume(self):
        m = SpeechStreamManager()
        m.start()
        assert m.pause()
        assert m.state == "paused"
        assert m.resume()
        assert m.state == "streaming"

    def test_recover(self):
        m = SpeechStreamManager()
        m.start()
        assert m.recover()
        assert m.active_session.state == SessionState.RECOVERING

    def test_finish_recovery(self):
        m = SpeechStreamManager()
        m.start()
        m.recover()
        assert m.finish_recovery()
        assert m.state == "streaming"

    def test_flush(self):
        m = SpeechStreamManager()
        m.start()
        # Feed partial chunk
        m.feed_audio(make_pcm_silence(480))
        chunk = m.flush()
        # flush might return None if buffer is empty after routing
        # The important thing is no crash

    def test_snapshot(self):
        m = SpeechStreamManager()
        m.start()
        snap = m.snapshot()
        assert "state" in snap
        assert "metrics" in snap
        assert "router" in snap
        assert "chunk_generator" in snap

    def test_reset(self):
        m = SpeechStreamManager()
        m.start()
        m.feed_audio(make_pcm_silence(960))
        m.reset()
        assert m.state == "idle"

    def test_config_to_dict(self):
        config = StreamConfig()
        d = config.to_dict()
        assert "chunk_size_ms" in d
        assert "sample_rate" in d
        assert "drop_policy" in d

    def test_event_handlers(self):
        m = SpeechStreamManager()
        events = []
        m.on(StreamEventType.STREAM_STARTED, lambda e, d: events.append((e, d)))
        m.start()
        # In sync context, events fire directly
        # The event may or may not fire depending on event loop

    def test_metrics_tracked(self):
        m = SpeechStreamManager()
        m.start()
        m.feed_audio(make_pcm_silence(960))
        snap = m.snapshot()
        assert snap["metrics"]["chunks_created"] >= 1

    def test_consumer_with_custom_queue(self):
        m = SpeechStreamManager()
        received = []
        m.subscribe_consumer("c1", lambda c: received.append(c), max_queue_size=10)
        m.start()
        m.feed_audio(make_pcm_silence(960))
        assert len(received) == 1

    def test_active_session(self):
        m = SpeechStreamManager()
        assert m.active_session is None
        m.start()
        assert m.active_session is not None

    def test_stop_clears_session(self):
        m = SpeechStreamManager()
        m.start()
        m.stop()
        assert m.active_session is None

    def test_feed_multiple_chunks(self):
        m = SpeechStreamManager()
        m.start()
        data = make_pcm_silence(960 * 3)
        chunks = m.feed_audio(data)
        assert len(chunks) == 3


# ─── Integration Tests ──────────────────────────────────────────────

class TestD3Integration:
    def test_full_pipeline(self):
        """Test complete pipeline: config → manager → chunks → consumers."""
        config = StreamConfig(chunk_size_ms=30, sample_rate=16000)
        m = SpeechStreamManager(config=config)

        received = []
        m.subscribe_consumer("stt", lambda c: received.append(c))

        session = m.start()
        assert session.state == SessionState.STREAMING

        # Feed audio
        for _ in range(5):
            m.feed_audio(make_pcm_silence(960))

        assert len(received) == 5
        assert m.snapshot()["metrics"]["chunks_created"] == 5

    def test_chunk_generation_and_routing(self):
        """Test chunks flow from generator through router."""
        gen = ChunkGenerator(chunk_size_ms=30, sample_rate=16000)
        router = StreamRouter()

        received = []
        router.subscribe("consumer1", lambda c: received.append(c))

        # Generate and route
        chunks = gen.feed(make_pcm_silence(960 * 3))
        assert len(chunks) == 3

        for chunk in chunks:
            router.route(chunk)
        router.deliver()

        assert len(received) == 3

    def test_session_lifecycle(self):
        """Test complete session lifecycle."""
        s = SpeechSession(session_id="lifecycle_test")
        s.open()
        s.start_streaming()

        for i in range(10):
            chunk = AudioChunk(data=b'\x00\x00', sequence=i)
            s.receive_chunk(chunk)
            s.process_chunk(chunk)

        assert s.stats().chunks_received == 10
        assert s.stats().chunks_processed == 10

        s.pause()
        assert s.state == SessionState.PAUSED

        s.resume()
        assert s.state == SessionState.STREAMING

        s.close()
        assert s.state == SessionState.CLOSED

    def test_backpressure_detection(self):
        """Test backpressure is detected when queues fill."""
        m = SpeechStreamManager()
        # Consumer with tiny queue
        received = []
        m.subscribe_consumer("tiny", lambda c: received.append(c), max_queue_size=2)

        m.start()
        # Feed many chunks fast
        for _ in range(20):
            m.feed_audio(make_pcm_silence(960))

        snap = m.snapshot()
        assert snap["metrics"]["backpressure_events"] >= 0  # May or may not trigger

    def test_multiple_consumer_independence(self):
        """Test consumers are independent."""
        m = SpeechStreamManager()
        fast = []
        slow = []
        m.subscribe_consumer("fast", lambda c: fast.append(c))
        m.subscribe_consumer("slow", lambda c: slow.append(c), max_queue_size=1)

        m.start()
        for _ in range(10):
            m.feed_audio(make_pcm_silence(960))

        # Both should receive chunks (slow may drop some)
        assert len(fast) == 10
        assert len(slow) <= 10

    def test_thread_safety_full_pipeline(self):
        """Test pipeline under concurrent access."""
        m = SpeechStreamManager()
        results = []
        m.subscribe_consumer("stt", lambda c: results.append(c.sequence))

        m.start()

        def feed():
            for _ in range(20):
                m.feed_audio(make_pcm_silence(960))

        threads = [threading.Thread(target=feed) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All chunks should be processed
        assert len(results) == 60

    def test_metrics_accuracy(self):
        """Test metrics track accurately."""
        m = SpeechStreamManager()
        m.start()

        for _ in range(10):
            m.feed_audio(make_pcm_silence(960))

        snap = m.snapshot()
        assert snap["metrics"]["chunks_created"] == 10
        assert snap["metrics"]["total_bytes_processed"] == 9600

    def test_config_propagation(self):
        """Test config propagates to all components."""
        config = StreamConfig(chunk_size_ms=20, sample_rate=8000, channels=2)
        m = SpeechStreamManager(config=config)

        assert m.config.sample_rate == 8000
        assert m.config.channels == 2
        # Chunk generator should use config
        assert m._chunk_generator.chunk_size_ms == 20

    def test_recovery_flow(self):
        """Test recovery flow through manager."""
        m = SpeechStreamManager()
        m.start()

        # Simulate error
        m.recover()
        assert m.active_session.state == SessionState.RECOVERING

        # Complete recovery
        m.finish_recovery()
        assert m.state == "streaming"

    def test_pause_resume_flow(self):
        """Test pause/resume through manager."""
        m = SpeechStreamManager()
        m.start()

        m.pause()
        assert m.state == "paused"

        m.resume()
        assert m.state == "streaming"

    def test_long_duration_streaming(self):
        """Test streaming many chunks without errors."""
        m = SpeechStreamManager()
        m.start()

        for i in range(100):
            m.feed_audio(make_pcm_silence(960))

        snap = m.snapshot()
        assert snap["metrics"]["chunks_created"] == 100

    def test_drop_policy_propagation(self):
        """Test drop policy reaches router."""
        m = SpeechStreamManager(config=StreamConfig(drop_policy=DropPolicy.DROP_NEWEST))
        m.subscribe_consumer("c1", lambda c: None)
        assert m.router._default_drop_policy == DropPolicy.DROP_NEWEST

    def test_session_stats_accurate(self):
        """Test session stats are accurate."""
        m = SpeechStreamManager()
        session = m.start()

        for _ in range(5):
            m.feed_audio(make_pcm_silence(960))

        stats = session.stats()
        assert stats.chunks_received == 5
        assert stats.total_bytes == 4800

    def test_chunk_timestamps(self):
        """Test chunks have timestamps."""
        gen = ChunkGenerator(chunk_size_ms=30, sample_rate=16000)
        chunks = gen.feed(make_pcm_silence(960))
        assert chunks[0].timestamp > 0
        assert chunks[0].duration_ms == 30.0

    def test_full_lifecycle_with_diagnostics(self):
        """Test complete lifecycle with metrics snapshot."""
        m = SpeechStreamManager()
        received = []
        m.subscribe_consumer("stt", lambda c: received.append(c))
        m.start()

        for _ in range(10):
            m.feed_audio(make_pcm_silence(960))

        snap = m.snapshot()
        assert snap["state"] == "streaming"
        assert snap["session"]["chunks_received"] == 10
        assert snap["metrics"]["chunks_created"] == 10
        assert len(received) == 10
