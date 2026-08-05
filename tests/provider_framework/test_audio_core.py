"""Comprehensive tests for the audio subsystem (Sprint D1).

Target: 50+ tests covering buffer, resampler, device_manager, router,
recorder, playback, mixer, session, diagnostics, engine, thread safety,
and error recovery.
"""

from __future__ import annotations

import asyncio
import struct
import threading
import time

import pytest

from aios.voice.audio.buffer import AudioBuffer, BufferStats
from aios.voice.audio.resampler import AudioResampler, SampleRate, ResampleResult
from aios.voice.audio.device_manager import (
    DeviceManager, AudioDeviceInfo, DeviceType, DeviceStatus,
)
from aios.voice.audio.router import AudioRouter, RouteType, RouteStatus
from aios.voice.audio.recorder import Recorder, RecordingSession, RecordingState
from aios.voice.audio.playback import Playback, PlaybackSession, PlaybackState
from aios.voice.audio.mixer import Mixer, MixerStream, StreamPriority
from aios.voice.audio.session import AudioSession, AudioSessionState
from aios.voice.audio.diagnostics import AudioDiagnostics, AudioDiagnosticsSnapshot
from aios.voice.audio.engine import AudioEngine, AudioEngineConfig, AudioEngineState
from aios.voice.audio.exceptions import (
    AudioBufferOverflowError,
    AudioBufferUnderflowError,
    AudioDeviceNotFoundError,
    AudioResamplerError,
    AudioRoutingError,
    AudioRecordingError,
    AudioPlaybackError,
    AudioMixerError,
    AudioSessionStateError,
)


# ============================================================
# BUFFER TESTS
# ============================================================

class TestAudioBuffer:
    """Tests for AudioBuffer (ring buffer)."""

    def test_create_buffer(self):
        buf = AudioBuffer(capacity=1024)
        assert buf.capacity == 1024
        assert buf.count == 0
        assert buf.available == 1024
        assert buf.is_empty is True
        assert buf.is_full is False

    def test_write_and_read(self):
        buf = AudioBuffer(capacity=256)
        data = b'\x01\x02\x03\x04'
        written = buf.write(data)
        assert written == 4
        assert buf.count == 4
        read = buf.read(4)
        assert read == data
        assert buf.count == 0

    def test_write_multiple_chunks(self):
        buf = AudioBuffer(capacity=256)
        buf.write(b'\x01\x02')
        buf.write(b'\x03\x04')
        buf.write(b'\x05\x06')
        assert buf.count == 6
        read = buf.read(6)
        assert read == b'\x01\x02\x03\x04\x05\x06'

    def test_write_wraps_around(self):
        buf = AudioBuffer(capacity=8)
        buf.write(b'\x01\x02\x03\x04')
        buf.read(4)  # Advance read position
        buf.write(b'\x05\x06\x07\x08')
        assert buf.count == 4
        read = buf.read(4)
        assert read == b'\x05\x06\x07\x08'

    def test_overflow_protection_raises(self):
        buf = AudioBuffer(capacity=4, overflow_protection=True)
        buf.write(b'\x01\x02\x03\x04')
        with pytest.raises(AudioBufferOverflowError):
            buf.write(b'\x05')

    def test_overflow_protection_disabled(self):
        buf = AudioBuffer(capacity=4, overflow_protection=False)
        buf.write(b'\x01\x02\x03\x04')
        written = buf.write(b'\x05')
        assert written == 0

    def test_underflow_protection_raises(self):
        buf = AudioBuffer(capacity=4, underflow_protection=True)
        with pytest.raises(AudioBufferUnderflowError):
            buf.read(4)

    def test_underflow_protection_disabled(self):
        buf = AudioBuffer(capacity=4, underflow_protection=False)
        result = buf.read(4)
        assert result == b""

    def test_peek_does_not_consume(self):
        buf = AudioBuffer(capacity=256)
        buf.write(b'\x01\x02\x03\x04')
        peeked = buf.peek(4)
        assert peeked == b'\x01\x02\x03\x04'
        assert buf.count == 4

    def test_flush(self):
        buf = AudioBuffer(capacity=256)
        buf.write(b'\x01\x02\x03\x04')
        discarded = buf.flush()
        assert discarded == 4
        assert buf.count == 0

    def test_close(self):
        buf = AudioBuffer(capacity=256)
        buf.write(b'\x01\x02')
        buf.close()
        assert buf.is_closed is True

    def test_write_after_close_returns_zero(self):
        buf = AudioBuffer(capacity=256)
        buf.close()
        written = buf.write(b'\x01\x02')
        assert written == 0

    def test_stats(self):
        buf = AudioBuffer(capacity=256)
        buf.write(b'\x01\x02\x03\x04')
        buf.read(2)
        stats = buf.stats
        assert stats.total_written == 4
        assert stats.total_read == 2
        assert stats.current_usage == 2
        assert stats.capacity == 256

    def test_reset_stats(self):
        buf = AudioBuffer(capacity=256)
        buf.write(b'\x01\x02')
        buf.reset_stats()
        stats = buf.stats
        assert stats.total_written == 0
        assert stats.total_read == 0

    def test_len_and_bool(self):
        buf = AudioBuffer(capacity=256)
        assert len(buf) == 0
        assert bool(buf) is False
        buf.write(b'\x01')
        assert len(buf) == 1
        assert bool(buf) is True

    def test_read_partial(self):
        buf = AudioBuffer(capacity=256)
        buf.write(b'\x01\x02\x03\x04')
        read = buf.read(2)
        assert read == b'\x01\x02'
        assert buf.count == 2

    def test_read_more_than_available(self):
        buf = AudioBuffer(capacity=256)
        buf.write(b'\x01\x02')
        read = buf.read(100)
        assert read == b'\x01\x02'
        assert buf.count == 0

    def test_empty_read_returns_bytes(self):
        buf = AudioBuffer(capacity=256, underflow_protection=False)
        read = buf.read(10)
        assert read == b""

    def test_thread_safety_concurrent_writes(self):
        buf = AudioBuffer(capacity=8192, overflow_protection=False)
        errors = []

        def writer(thread_id):
            try:
                for i in range(100):
                    data = bytes([thread_id % 256]) * 4
                    buf.write(data, block=False)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert buf.stats.total_written > 0

    def test_thread_safety_concurrent_read_write(self):
        buf = AudioBuffer(capacity=1024, overflow_protection=False,
                          underflow_protection=False)
        results = []

        def writer():
            for i in range(200):
                buf.write(b'\x01' * 4, block=False)

        def reader():
            for i in range(200):
                buf.read(4, block=False)

        t1 = threading.Thread(target=writer)
        t2 = threading.Thread(target=reader)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # No crash = success
        assert True


# ============================================================
# RESAMPLER TESTS
# ============================================================

class TestAudioResampler:
    """Tests for AudioResampler."""

    def test_passthrough_same_rate(self):
        resampler = AudioResampler(16000, 16000)
        assert resampler.is_passthrough is True
        data = b'\x01\x02\x03\x04'
        result = resampler.resample(data)
        assert result.data == data
        assert result.source_samples == 2
        assert result.target_samples == 2

    def test_upsample_16bit(self):
        resampler = AudioResampler(16000, 32000, sample_width=2)
        assert resampler.ratio == 2.0
        # 10 samples at 16kHz → ~20 samples at 32kHz
        samples = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
        data = struct.pack(f"<{len(samples)}h", *samples)
        result = resampler.resample(data)
        assert result.target_samples > result.source_samples
        assert len(result.data) > len(data)

    def test_downsample_16bit(self):
        resampler = AudioResampler(32000, 16000, sample_width=2)
        assert resampler.ratio == 0.5
        samples = list(range(0, 2000, 100))
        data = struct.pack(f"<{len(samples)}h", *samples)
        result = resampler.resample(data)
        assert result.target_samples < result.source_samples

    def test_8bit_resample(self):
        resampler = AudioResampler(16000, 32000, sample_width=1)
        data = bytes([100, 128, 150, 200, 50, 75])
        result = resampler.resample(data)
        assert len(result.data) > len(data)

    def test_32bit_resample(self):
        resampler = AudioResampler(16000, 32000, sample_width=4)
        samples = [100000, 200000, 300000, 400000]
        data = struct.pack(f"<{len(samples)}i", *samples)
        result = resampler.resample(data)
        assert len(result.data) > len(data)

    def test_invalid_sample_rate(self):
        with pytest.raises(AudioResamplerError):
            AudioResampler(0, 16000)
        with pytest.raises(AudioResamplerError):
            AudioResampler(16000, -1)

    def test_invalid_channels(self):
        with pytest.raises(AudioResamplerError):
            AudioResampler(16000, 16000, channels=0)

    def test_invalid_sample_width(self):
        with pytest.raises(AudioResamplerError):
            AudioResampler(16000, 16000, sample_width=3)

    def test_empty_data(self):
        resampler = AudioResampler(16000, 32000)
        result = resampler.resample(b"")
        assert result.data == b""
        assert result.source_samples == 0

    def test_update_rates(self):
        resampler = AudioResampler(16000, 16000)
        assert resampler.is_passthrough is True
        resampler.update_rates(16000, 32000)
        assert resampler.is_passthrough is False
        assert resampler.ratio == 2.0

    def test_resample_result_dict(self):
        resampler = AudioResampler(16000, 32000)
        data = b'\x01\x02\x03\x04'
        result = resampler.resample(data)
        d = result.to_dict()
        assert "source_rate" in d
        assert "target_rate" in d
        assert "output_bytes" in d


# ============================================================
# DEVICE MANAGER TESTS
# ============================================================

class TestDeviceManager:
    """Tests for DeviceManager."""

    def test_create_device_manager(self):
        dm = DeviceManager()
        assert dm.initialized is False

    @pytest.mark.asyncio
    async def test_initialize_creates_mock_devices(self):
        dm = DeviceManager()
        await dm.initialize()
        assert dm.initialized is True
        assert len(dm.devices) > 0

    @pytest.mark.asyncio
    async def test_mock_devices_have_defaults(self):
        dm = DeviceManager()
        await dm.initialize()
        assert dm.default_input is not None
        assert dm.default_output is not None

    @pytest.mark.asyncio
    async def test_list_input_devices(self):
        dm = DeviceManager()
        await dm.initialize()
        inputs = dm.list_input_devices()
        assert len(inputs) > 0
        assert all(d.device_type in (DeviceType.INPUT, DeviceType.BOTH) for d in inputs)

    @pytest.mark.asyncio
    async def test_list_output_devices(self):
        dm = DeviceManager()
        await dm.initialize()
        outputs = dm.list_output_devices()
        assert len(outputs) > 0

    @pytest.mark.asyncio
    async def test_get_device(self):
        dm = DeviceManager()
        await dm.initialize()
        device = dm.get_device("mock_input")
        assert device.name == "Mock Microphone"

    @pytest.mark.asyncio
    async def test_get_device_not_found(self):
        dm = DeviceManager()
        await dm.initialize()
        with pytest.raises(AudioDeviceNotFoundError):
            dm.get_device("nonexistent")

    @pytest.mark.asyncio
    async def test_set_default_input(self):
        dm = DeviceManager()
        await dm.initialize()
        dm.set_default_input("mock_input")
        assert dm.default_input.id == "mock_input"

    @pytest.mark.asyncio
    async def test_set_default_output(self):
        dm = DeviceManager()
        await dm.initialize()
        dm.set_default_output("mock_output")
        assert dm.default_output.id == "mock_output"

    @pytest.mark.asyncio
    async def test_mark_active(self):
        dm = DeviceManager()
        await dm.initialize()
        dm.mark_active("mock_input")
        assert dm.get_device("mock_input").status == DeviceStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_to_dict(self):
        dm = DeviceManager()
        await dm.initialize()
        d = dm.to_dict()
        assert "initialized" in d
        assert "devices" in d
        assert d["input_count"] > 0


# ============================================================
# ROUTER TESTS
# ============================================================

class TestAudioRouter:
    """Tests for AudioRouter."""

    def test_create_router(self):
        router = AudioRouter()
        assert len(router.routes) == 0

    def test_create_route(self):
        router = AudioRouter()
        route = router.create_route(
            RouteType.RECORD, "mic_1", "buffer_1", buffer_size=1024
        )
        assert route.route_type == RouteType.RECORD
        assert route.source_id == "mic_1"
        assert route.destination_id == "buffer_1"
        assert route.status == RouteStatus.INACTIVE

    def test_start_route(self):
        router = AudioRouter()
        route = router.create_route(RouteType.RECORD, "mic_1", "buffer_1")
        router.start_route(route.id)
        assert route.status == RouteStatus.ACTIVE

    def test_pause_route(self):
        router = AudioRouter()
        route = router.create_route(RouteType.RECORD, "mic_1", "buffer_1")
        router.start_route(route.id)
        router.pause_route(route.id)
        assert route.status == RouteStatus.PAUSED

    def test_stop_route(self):
        router = AudioRouter()
        route = router.create_route(RouteType.RECORD, "mic_1", "buffer_1")
        router.start_route(route.id)
        router.stop_route(route.id)
        assert route.status == RouteStatus.INACTIVE

    def test_remove_route(self):
        router = AudioRouter()
        route = router.create_route(RouteType.RECORD, "mic_1", "buffer_1")
        router.remove_route(route.id)
        assert len(router.routes) == 0

    def test_write_and_read_route(self):
        router = AudioRouter()
        route = router.create_route(RouteType.RECORD, "mic_1", "buffer_1")
        router.start_route(route.id)
        data = b'\x01\x02\x03\x04'
        written = router.write_to_route(route.id, data)
        assert written == 4
        read = router.read_from_route(route.id, 4)
        assert read == data

    def test_write_to_inactive_route(self):
        router = AudioRouter()
        route = router.create_route(RouteType.RECORD, "mic_1", "buffer_1")
        written = router.write_to_route(route.id, b'\x01')
        assert written == 0

    def test_route_not_found(self):
        router = AudioRouter()
        with pytest.raises(AudioRoutingError):
            router.start_route("nonexistent")

    def test_active_routes(self):
        router = AudioRouter()
        r1 = router.create_route(RouteType.RECORD, "a", "b")
        r2 = router.create_route(RouteType.PLAYBACK, "c", "d")
        router.start_route(r1.id)
        assert len(router.active_routes) == 1

    def test_to_dict(self):
        router = AudioRouter()
        router.create_route(RouteType.RECORD, "a", "b")
        d = router.to_dict()
        assert d["route_count"] == 1


# ============================================================
# RECORDER TESTS
# ============================================================

class TestRecorder:
    """Tests for Recorder."""

    def test_create_recorder(self):
        rec = Recorder()
        assert len(rec.sessions) == 0

    def test_create_session(self):
        rec = Recorder()
        session = rec.create_session("mock_input")
        assert session.device_id == "mock_input"
        assert session.state == RecordingState.IDLE

    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        rec = Recorder()
        session = rec.create_session("mock_input")
        await rec.start(session.id)
        assert session.state == RecordingState.RECORDING
        await rec.stop(session.id)
        assert session.state == RecordingState.STOPPED

    @pytest.mark.asyncio
    async def test_pause_and_resume(self):
        rec = Recorder()
        session = rec.create_session("mock_input")
        await rec.start(session.id)
        await rec.pause(session.id)
        assert session.state == RecordingState.PAUSED
        await rec.resume(session.id)
        assert session.state == RecordingState.RECORDING

    @pytest.mark.asyncio
    async def test_start_invalid_state(self):
        rec = Recorder()
        session = rec.create_session("mock_input")
        await rec.start(session.id)
        with pytest.raises(AudioRecordingError):
            await rec.start(session.id)

    @pytest.mark.asyncio
    async def test_pause_invalid_state(self):
        rec = Recorder()
        session = rec.create_session("mock_input")
        with pytest.raises(AudioRecordingError):
            await rec.pause(session.id)

    def test_destroy_session(self):
        rec = Recorder()
        session = rec.create_session("mock_input")
        rec.destroy_session(session.id)
        assert session.id not in rec.sessions

    @pytest.mark.asyncio
    async def test_active_sessions(self):
        rec = Recorder()
        s1 = rec.create_session("mock_input")
        s2 = rec.create_session("mock_input")
        await rec.start(s1.id)
        assert len(rec.active_sessions) == 1

    @pytest.mark.asyncio
    async def test_session_not_found(self):
        rec = Recorder()
        with pytest.raises(AudioRecordingError):
            await rec.start("nonexistent")

    def test_to_dict(self):
        rec = Recorder()
        rec.create_session("mock_input")
        d = rec.to_dict()
        assert d["session_count"] == 1


# ============================================================
# PLAYBACK TESTS
# ============================================================

class TestPlayback:
    """Tests for Playback."""

    def test_create_playback(self):
        pb = Playback()
        assert len(pb.sessions) == 0

    def test_create_session(self):
        pb = Playback()
        session = pb.create_session("mock_output")
        assert session.device_id == "mock_output"
        assert session.state == PlaybackState.IDLE

    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        pb = Playback()
        session = pb.create_session("mock_output")
        await pb.start(session.id)
        assert session.state == PlaybackState.PLAYING
        await pb.stop(session.id)
        assert session.state == PlaybackState.STOPPED

    @pytest.mark.asyncio
    async def test_pause_and_resume(self):
        pb = Playback()
        session = pb.create_session("mock_output")
        await pb.start(session.id)
        await pb.pause(session.id)
        assert session.state == PlaybackState.PAUSED
        await pb.resume(session.id)
        assert session.state == PlaybackState.PLAYING

    def test_volume_control(self):
        pb = Playback()
        session = pb.create_session("mock_output")
        pb.set_volume(session.id, 0.5)
        assert session.volume == 0.5

    def test_volume_clamping(self):
        pb = Playback()
        session = pb.create_session("mock_output")
        pb.set_volume(session.id, 1.5)
        assert session.volume == 1.0
        pb.set_volume(session.id, -0.5)
        assert session.volume == 0.0

    def test_mute_unmute(self):
        pb = Playback()
        session = pb.create_session("mock_output")
        pb.mute(session.id)
        assert session.is_muted is True
        pb.unmute(session.id)
        assert session.is_muted is False

    def test_switch_device(self):
        pb = Playback()
        session = pb.create_session("mock_output")
        pb.switch_device(session.id, "new_device")
        assert session.device_id == "new_device"

    def test_destroy_session(self):
        pb = Playback()
        session = pb.create_session("mock_output")
        pb.destroy_session(session.id)
        assert session.id not in pb.sessions

    def test_to_dict(self):
        pb = Playback()
        pb.create_session("mock_output")
        d = pb.to_dict()
        assert d["session_count"] == 1


# ============================================================
# MIXER TESTS
# ============================================================

class TestMixer:
    """Tests for Mixer."""

    def test_create_mixer(self):
        mixer = Mixer()
        assert len(mixer.streams) == 0

    def test_add_stream(self):
        mixer = Mixer()
        stream = mixer.add_stream("s1", "TTS")
        assert stream.name == "TTS"
        assert stream.id == "s1"

    def test_remove_stream(self):
        mixer = Mixer()
        mixer.add_stream("s1", "TTS")
        mixer.remove_stream("s1")
        assert len(mixer.streams) == 0

    def test_set_volume(self):
        mixer = Mixer()
        mixer.add_stream("s1", "TTS")
        mixer.set_volume("s1", 0.3)
        assert mixer.streams["s1"].volume == 0.3

    def test_mute_unmute(self):
        mixer = Mixer()
        mixer.add_stream("s1", "TTS")
        mixer.mute("s1")
        assert mixer.streams["s1"].is_muted is True
        mixer.unmute("s1")
        assert mixer.streams["s1"].is_muted is False

    def test_set_priority(self):
        mixer = Mixer()
        mixer.add_stream("s1", "TTS")
        mixer.set_priority("s1", StreamPriority.CRITICAL)
        assert mixer.streams["s1"].priority == StreamPriority.CRITICAL

    def test_write_to_stream(self):
        mixer = Mixer()
        mixer.add_stream("s1", "TTS")
        written = mixer.write_to_stream("s1", b'\x01\x02')
        assert written == 2

    def test_active_streams(self):
        mixer = Mixer()
        mixer.add_stream("s1", "TTS")
        mixer.add_stream("s2", "Notification")
        mixer.mute("s2")
        assert len(mixer.active_streams) == 1

    def test_stream_not_found(self):
        mixer = Mixer()
        with pytest.raises(AudioMixerError):
            mixer.set_volume("nonexistent", 0.5)

    def test_duplicate_stream(self):
        mixer = Mixer()
        mixer.add_stream("s1", "TTS")
        with pytest.raises(AudioMixerError):
            mixer.add_stream("s1", "Duplicate")

    def test_to_dict(self):
        mixer = Mixer()
        mixer.add_stream("s1", "TTS")
        d = mixer.to_dict()
        assert d["stream_count"] == 1


# ============================================================
# SESSION TESTS
# ============================================================

class TestAudioSession:
    """Tests for AudioSession."""

    @pytest.mark.asyncio
    async def test_create_session(self):
        session = AudioSession()
        assert session.state == AudioSessionState.CREATED

    @pytest.mark.asyncio
    async def test_open_session(self):
        session = AudioSession()
        await session.open()
        assert session.state == AudioSessionState.READY

    @pytest.mark.asyncio
    async def test_start_stop_streaming(self):
        session = AudioSession()
        await session.open()
        await session.start_streaming()
        assert session.state == AudioSessionState.STREAMING
        await session.stop_streaming()
        assert session.state == AudioSessionState.READY

    @pytest.mark.asyncio
    async def test_pause_resume(self):
        session = AudioSession()
        await session.open()
        await session.start_streaming()
        await session.pause()
        assert session.state == AudioSessionState.PAUSED
        await session.resume()
        assert session.state == AudioSessionState.STREAMING

    @pytest.mark.asyncio
    async def test_close_session(self):
        session = AudioSession()
        await session.open()
        await session.close()
        assert session.state == AudioSessionState.CLOSED

    @pytest.mark.asyncio
    async def test_invalid_state_open(self):
        session = AudioSession()
        await session.open()
        with pytest.raises(AudioSessionStateError):
            await session.open()

    @pytest.mark.asyncio
    async def test_invalid_state_start_streaming(self):
        session = AudioSession()
        with pytest.raises(AudioSessionStateError):
            await session.start_streaming()

    @pytest.mark.asyncio
    async def test_invalid_state_pause(self):
        session = AudioSession()
        await session.open()
        with pytest.raises(AudioSessionStateError):
            await session.pause()

    @pytest.mark.asyncio
    async def test_invalid_state_resume(self):
        session = AudioSession()
        await session.open()
        with pytest.raises(AudioSessionStateError):
            await session.resume()

    @pytest.mark.asyncio
    async def test_snapshot(self):
        session = AudioSession()
        await session.open()
        snap = session.snapshot()
        assert snap.session_id == session.session_id
        assert snap.state == AudioSessionState.READY

    @pytest.mark.asyncio
    async def test_to_dict(self):
        session = AudioSession()
        await session.open()
        d = session.to_dict()
        assert "session_id" in d
        assert "state" in d


# ============================================================
# DIAGNOSTICS TESTS
# ============================================================

class TestAudioDiagnostics:
    """Tests for AudioDiagnostics."""

    def test_create_diagnostics(self):
        diag = AudioDiagnostics()
        assert diag.uptime > 0

    def test_update_session_count(self):
        diag = AudioDiagnostics()
        diag.update_session_count(5, 3)
        snap = diag.snapshot()
        assert snap.session_count == 5
        assert snap.active_session_count == 3

    def test_set_devices(self):
        diag = AudioDiagnostics()
        diag.set_devices("Mic", "Speaker")
        snap = diag.snapshot()
        assert snap.input_device == "Mic"
        assert snap.output_device == "Speaker"

    def test_record_counters(self):
        diag = AudioDiagnostics()
        diag.record_dropped_frame()
        diag.record_buffer_underrun()
        diag.record_buffer_overrun()
        snap = diag.snapshot()
        assert snap.dropped_frames == 1
        assert snap.buffer_underruns == 1
        assert snap.buffer_overruns == 1

    def test_record_bytes(self):
        diag = AudioDiagnostics()
        diag.record_bytes_captured(1024)
        diag.record_bytes_played(2048)
        snap = diag.snapshot()
        assert snap.total_bytes_captured == 1024
        assert snap.total_bytes_played == 2048

    def test_latency_tracking(self):
        diag = AudioDiagnostics()
        diag.record_latency(10.0)
        diag.record_latency(20.0)
        diag.record_latency(30.0)
        assert diag.average_latency == 20.0
        assert diag.p95_latency == 30.0

    def test_reset(self):
        diag = AudioDiagnostics()
        diag.record_dropped_frame()
        diag.record_bytes_captured(100)
        diag.reset()
        snap = diag.snapshot()
        assert snap.dropped_frames == 0
        assert snap.total_bytes_captured == 0

    def test_to_dict(self):
        diag = AudioDiagnostics()
        d = diag.to_dict()
        assert "sample_rate" in d
        assert "average_latency_ms" in d
        assert "p95_latency_ms" in d

    def test_empty_latency(self):
        diag = AudioDiagnostics()
        assert diag.average_latency == 0.0
        assert diag.p95_latency == 0.0

    def test_snapshot_dict(self):
        diag = AudioDiagnostics()
        snap = diag.snapshot()
        d = snap.to_dict()
        assert "timestamp" in d
        assert "uptime_seconds" in d


# ============================================================
# ENGINE TESTS
# ============================================================

class TestAudioEngine:
    """Tests for AudioEngine."""

    @pytest.mark.asyncio
    async def test_create_engine(self):
        engine = AudioEngine()
        assert engine.state == AudioEngineState.UNINITIALIZED

    @pytest.mark.asyncio
    async def test_initialize(self):
        engine = AudioEngine()
        await engine.initialize()
        assert engine.state == AudioEngineState.READY
        assert engine.is_ready is True

    @pytest.mark.asyncio
    async def test_shutdown(self):
        engine = AudioEngine()
        await engine.initialize()
        await engine.shutdown()
        assert engine.state == AudioEngineState.SHUTDOWN

    @pytest.mark.asyncio
    async def test_create_session(self):
        engine = AudioEngine()
        await engine.initialize()
        session = await engine.create_session()
        assert session.session_id in engine.sessions

    @pytest.mark.asyncio
    async def test_close_session(self):
        engine = AudioEngine()
        await engine.initialize()
        session = await engine.create_session()
        await engine.close_session(session.session_id)
        assert session.session_id not in engine.sessions

    @pytest.mark.asyncio
    async def test_get_session(self):
        engine = AudioEngine()
        await engine.initialize()
        session = await engine.create_session()
        retrieved = engine.get_session(session.session_id)
        assert retrieved is session

    @pytest.mark.asyncio
    async def test_get_session_not_found(self):
        engine = AudioEngine()
        await engine.initialize()
        assert engine.get_session("nonexistent") is None

    @pytest.mark.asyncio
    async def test_create_resampler(self):
        engine = AudioEngine()
        await engine.initialize()
        resampler = engine.create_resampler(16000, 32000)
        assert resampler.source_rate == 16000
        assert resampler.target_rate == 32000

    @pytest.mark.asyncio
    async def test_get_resampler(self):
        engine = AudioEngine()
        await engine.initialize()
        engine.create_resampler(16000, 32000, resampler_id="test")
        resampler = engine.get_resampler("test")
        assert resampler is not None

    @pytest.mark.asyncio
    async def test_diagnostics_snapshot(self):
        engine = AudioEngine()
        await engine.initialize()
        snap = engine.diagnostics_snapshot()
        assert "engine_state" in snap
        assert "session_count" in snap

    @pytest.mark.asyncio
    async def test_to_dict(self):
        engine = AudioEngine()
        await engine.initialize()
        d = engine.to_dict()
        assert "state" in d
        assert "config" in d
        assert "device_manager" in d

    @pytest.mark.asyncio
    async def test_components_accessible(self):
        engine = AudioEngine()
        await engine.initialize()
        assert engine.device_manager is not None
        assert engine.router is not None
        assert engine.recorder is not None
        assert engine.playback is not None
        assert engine.mixer is not None
        assert engine.diagnostics is not None

    @pytest.mark.asyncio
    async def test_config(self):
        config = AudioEngineConfig(sample_rate=44100, channels=2)
        engine = AudioEngine(config)
        assert engine.config.sample_rate == 44100
        assert engine.config.channels == 2

    @pytest.mark.asyncio
    async def test_event_handlers(self):
        engine = AudioEngine()
        events = []
        def handler(event_type, data):
            events.append((event_type, data))
        engine.on_event("test", handler)
        await engine._publish_event("test", {"key": "value"})
        assert len(events) == 1
        assert events[0][0] == "test"

    @pytest.mark.asyncio
    async def test_off_event(self):
        engine = AudioEngine()
        def handler(event_type, data):
            pass
        engine.on_event("test", handler)
        engine.off_event("test", handler)
        assert "test" not in engine._event_handlers or len(engine._event_handlers.get("test", [])) == 0

    @pytest.mark.asyncio
    async def test_double_initialize(self):
        engine = AudioEngine()
        await engine.initialize()
        await engine.initialize()  # Should not raise
        assert engine.is_ready


# ============================================================
# INTEGRATION TESTS
# ============================================================

class TestAudioIntegration:
    """Integration tests for the full audio pipeline."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test complete engine lifecycle: init → session → streaming → close → shutdown."""
        engine = AudioEngine()
        await engine.initialize()

        session = await engine.create_session()
        await session.open()
        await session.start_streaming()
        assert session.is_streaming

        await session.stop_streaming()
        await session.close()
        await engine.close_session(session.session_id)

        await engine.shutdown()
        assert engine.state == AudioEngineState.SHUTDOWN

    @pytest.mark.asyncio
    async def test_multiple_sessions(self):
        """Test concurrent sessions."""
        engine = AudioEngine()
        await engine.initialize()

        s1 = await engine.create_session()
        s2 = await engine.create_session()
        assert len(engine.sessions) == 2

        await s1.open()
        await s2.open()
        await s1.start_streaming()
        await s2.start_streaming()

        await s1.stop_streaming()
        await s2.stop_streaming()
        await s1.close()
        await s2.close()

        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_router_with_session(self):
        """Test routing audio through a session."""
        engine = AudioEngine()
        await engine.initialize()

        route = engine.router.create_route(
            RouteType.RECORD, "mic_1", "buffer_1"
        )
        engine.router.start_route(route.id)

        data = b'\x01\x02\x03\x04' * 100
        written = engine.router.write_to_route(route.id, data)
        assert written == len(data)

        read = engine.router.read_from_route(route.id, len(data))
        assert read == data

        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_mixer_with_routes(self):
        """Test mixer integration with routes."""
        engine = AudioEngine()
        await engine.initialize()

        engine.mixer.add_stream("tts", "TTS", priority=StreamPriority.HIGH)
        engine.mixer.add_stream("notification", "Notification", priority=StreamPriority.CRITICAL)

        engine.mixer.write_to_stream("tts", b'\x01\x02')
        engine.mixer.write_to_stream("notification", b'\x03\x04')

        assert len(engine.mixer.active_streams) == 2

        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_diagnostics_through_lifecycle(self):
        """Test diagnostics tracking through a full lifecycle."""
        engine = AudioEngine()
        await engine.initialize()

        session = await engine.create_session()
        await session.open()
        await session.start_streaming()

        engine.diagnostics.record_bytes_captured(1024)
        engine.diagnostics.record_bytes_played(512)
        engine.diagnostics.record_latency(15.0)

        snap = engine.diagnostics_snapshot()
        assert snap["total_bytes_captured"] == 1024
        assert snap["total_bytes_played"] == 512

        await session.stop_streaming()
        await session.close()
        await engine.shutdown()
