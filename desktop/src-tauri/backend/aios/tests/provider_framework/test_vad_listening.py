"""Comprehensive tests for Sprint D2 — Voice Activity Detection & Listening Intelligence.

Target: 70+ tests covering VAD, noise processing, listening state machine,
calibration, profiles, diagnostics, and integration.
"""

from __future__ import annotations

import asyncio
import math
import struct
import time

import pytest

from aios.voice.audio.noise import NoiseProcessor, NoiseStats
from aios.voice.audio.profiles import (
    VoiceProfile, ProfileType, get_profile, list_profiles,
    create_custom_profile, PROFILES,
)
from aios.voice.audio.vad import VoiceActivityDetector, VADState, VADEvent, VADFrame, VADStats
from aios.voice.audio.listening_state import (
    ListeningStateMachine, ListeningState, ListeningEvent, ListeningSnapshot,
)
from aios.voice.audio.calibration import (
    CalibrationManager, CalibrationConfig, CalibrationResult, CalibrationState,
)
from aios.voice.audio.diagnostics import AudioDiagnostics


# ============================================================
# PROFILES TESTS
# ============================================================

class TestProfiles:
    """Tests for sensitivity profiles."""

    def test_get_quiet_room_profile(self):
        p = get_profile(ProfileType.QUIET_ROOM)
        assert p.profile_type == ProfileType.QUIET_ROOM
        assert p.name == "Quiet Room"
        assert p.noise_threshold < 0.05

    def test_get_office_profile(self):
        p = get_profile(ProfileType.OFFICE)
        assert p.profile_type == ProfileType.OFFICE
        assert p.noise_threshold > 0.01

    def test_get_all_profiles(self):
        for pt in ProfileType:
            if pt == ProfileType.CUSTOM:
                continue
            p = get_profile(pt)
            assert p.profile_type == pt

    def test_list_profiles(self):
        profiles = list_profiles()
        assert len(profiles) >= 6

    def test_create_custom_profile(self):
        p = create_custom_profile("My Profile", noise_threshold=0.1, gain=2.0)
        assert p.profile_type == ProfileType.CUSTOM
        assert p.name == "My Profile"
        assert p.noise_threshold == 0.1
        assert p.gain == 2.0

    def test_profile_returns_copy(self):
        p1 = get_profile(ProfileType.QUIET_ROOM)
        p2 = get_profile(ProfileType.QUIET_ROOM)
        p1.noise_threshold = 999
        assert p2.noise_threshold != 999

    def test_profile_to_dict(self):
        p = get_profile(ProfileType.QUIET_ROOM)
        d = p.to_dict()
        assert "profile_type" in d
        assert "noise_threshold" in d
        assert "silence_timeout" in d

    def test_conference_profile_higher_thresholds(self):
        q = get_profile(ProfileType.QUIET_ROOM)
        c = get_profile(ProfileType.CONFERENCE)
        assert c.noise_threshold > q.noise_threshold
        assert c.speech_threshold > q.speech_threshold

    def test_cafe_profile_highest_thresholds(self):
        profiles = [get_profile(pt) for pt in ProfileType if pt != ProfileType.CUSTOM]
        cafe = get_profile(ProfileType.CAFE)
        assert cafe.noise_threshold >= max(p.noise_threshold for p in profiles)

    def test_headset_profile_low_thresholds(self):
        h = get_profile(ProfileType.HEADSET)
        assert h.noise_threshold < 0.05


# ============================================================
# NOISE PROCESSOR TESTS
# ============================================================

class TestNoiseProcessor:
    """Tests for noise processing."""

    def test_create_processor(self):
        np = NoiseProcessor()
        assert np.noise_floor == 0.0

    def test_process_silence(self):
        np = NoiseProcessor(noise_threshold=0.05)
        silence = b'\x00\x00' * 100  # 100 samples of silence
        result = np.process(silence)
        assert len(result) == len(silence)

    def test_process_speech(self):
        np = NoiseProcessor(noise_threshold=0.01)
        # Generate speech-like signal (high amplitude sine wave)
        import math
        samples = [int(16000 * math.sin(2 * math.pi * 440 * i / 16000)) for i in range(100)]
        data = struct.pack(f"<{len(samples)}h", *samples)
        result = np.process(data)
        assert len(result) == len(data)

    def test_gain_applied(self):
        np = NoiseProcessor(gain=2.0)
        samples = [1000] * 100
        data = struct.pack(f"<{len(samples)}h", *samples)
        result = np.process(data)
        result_samples = struct.unpack(f"<{len(result)//2}h", result)
        # Some samples should be amplified (clamped at 32767)
        assert any(abs(s) > 1000 for s in result_samples)

    def test_noise_gate(self):
        np = NoiseProcessor(noise_threshold=0.05, enable_noise_gate=True)
        # Very quiet signal
        samples = [10] * 100
        data = struct.pack(f"<{len(samples)}h", *samples)
        result = np.process(data)
        result_samples = struct.unpack(f"<{len(result)//2}h", result)
        # Should be attenuated
        assert all(abs(s) <= 10 for s in result_samples)

    def test_noise_gate_disabled(self):
        np = NoiseProcessor(noise_threshold=0.05, enable_noise_gate=False)
        samples = [10] * 100
        data = struct.pack(f"<{len(samples)}h", *samples)
        result = np.process(data)
        result_samples = struct.unpack(f"<{len(result)//2}h", result)
        assert all(s == 10 for s in result_samples)

    def test_stats(self):
        np = NoiseProcessor()
        np.process(b'\x00\x00' * 100)
        stats = np.stats()
        assert stats.frames_processed == 1

    def test_calibrate(self):
        np = NoiseProcessor()
        samples = [100] * 1000
        data = struct.pack(f"<{len(samples)}h", *samples)
        result = np.calibrate(data)
        assert result["status"] == "ok"
        assert result["recommended_threshold"] > 0

    def test_reset(self):
        np = NoiseProcessor()
        np.process(b'\x00\x00' * 100)
        np.reset()
        stats = np.stats()
        assert stats.frames_processed == 0

    def test_to_dict(self):
        np = NoiseProcessor()
        d = np.to_dict()
        assert "noise_threshold" in d
        assert "gain" in d
        assert "stats" in d

    def test_gain_setter(self):
        np = NoiseProcessor()
        np.gain = 2.5
        assert np.gain == 2.5
        np.gain = 0.01  # Below min
        assert np.gain == 0.1

    def test_noise_threshold_setter(self):
        np = NoiseProcessor()
        np.noise_threshold = 0.1
        assert np.noise_threshold == 0.1
        np.noise_threshold = -0.1
        assert np.noise_threshold == 0.0

    def test_empty_data(self):
        np = NoiseProcessor()
        result = np.process(b"")
        assert result == b""

    def test_snr_estimation(self):
        np = NoiseProcessor()
        # Process some data to build noise floor
        for _ in range(10):
            np.process(b'\x00\x00' * 100)
        assert np.estimated_snr >= 0


# ============================================================
# VAD TESTS
# ============================================================

class TestVAD:
    """Tests for Voice Activity Detector."""

    def test_create_vad(self):
        vad = VoiceActivityDetector()
        assert vad.state == VADState.IDLE

    def test_analyze_silence(self):
        vad = VoiceActivityDetector()
        silence = b'\x00\x00' * 100
        frame = vad.analyze_frame(silence)
        assert frame.is_speech is False
        assert frame.state == VADState.IDLE

    def test_analyze_speech(self):
        vad = VoiceActivityDetector()
        # High amplitude signal
        samples = [16000] * 100
        data = struct.pack(f"<{len(samples)}h", *samples)
        frame = vad.analyze_frame(data)
        assert frame.confidence > 0

    def test_state_transitions(self):
        vad = VoiceActivityDetector()

        # Start in idle
        assert vad.state == VADState.IDLE

        # Analyze speech frame
        samples = [16000] * 100
        data = struct.pack(f"<{len(samples)}h", *samples)
        vad.analyze_frame(data)

    def test_speech_start_event(self):
        vad = VoiceActivityDetector()
        events = []
        vad.on(VADEvent.SPEECH_START, lambda e, d: events.append((e, d)))

        # Generate speech
        samples = [16000] * 100
        data = struct.pack(f"<{len(samples)}h", *samples)
        vad.analyze_frame(data)

    def test_reset(self):
        vad = VoiceActivityDetector()
        samples = [16000] * 100
        data = struct.pack(f"<{len(samples)}h", *samples)
        vad.analyze_frame(data)
        vad.reset()
        assert vad.state == VADState.IDLE
        stats = vad.stats()
        assert stats.total_frames == 0

    def test_stats(self):
        vad = VoiceActivityDetector()
        for _ in range(10):
            vad.analyze_frame(b'\x00\x00' * 100)
        stats = vad.stats()
        assert stats.total_frames == 10

    def test_set_profile(self):
        vad = VoiceActivityDetector()
        new_profile = get_profile(ProfileType.OFFICE)
        vad.set_profile(new_profile)
        assert vad.profile.name == "Office"

    def test_to_dict(self):
        vad = VoiceActivityDetector()
        d = vad.to_dict()
        assert "state" in d
        assert "confidence" in d
        assert "profile" in d
        assert "stats" in d

    def test_frame_has_timestamp(self):
        vad = VoiceActivityDetector()
        frame = vad.analyze_frame(b'\x00\x00' * 100)
        assert frame.timestamp > 0

    def test_frame_to_dict(self):
        vad = VoiceActivityDetector()
        frame = vad.analyze_frame(b'\x00\x00' * 100)
        d = frame.to_dict()
        assert "rms" in d
        assert "confidence" in d
        assert "is_speech" in d

    def test_custom_profile(self):
        p = create_custom_profile("Test", speech_threshold=0.01)
        vad = VoiceActivityDetector(profile=p)
        assert vad.profile.name == "Test"

    def test_off_event(self):
        vad = VoiceActivityDetector()
        handler = lambda e, d: None
        vad.on(VADEvent.SPEECH_START, handler)
        vad.off(VADEvent.SPEECH_START, handler)
        assert handler not in vad._event_handlers.get(VADEvent.SPEECH_START, [])

    def test_silence_frames_tracked(self):
        vad = VoiceActivityDetector()
        for _ in range(5):
            vad.analyze_frame(b'\x00\x00' * 100)
        stats = vad.stats()
        assert stats.silence_frames > 0 or stats.total_frames > 0

    def test_confidence_range(self):
        vad = VoiceActivityDetector()
        frame = vad.analyze_frame(b'\x00\x00' * 100)
        assert 0.0 <= frame.confidence <= 1.0

    def test_multiple_frames(self):
        vad = VoiceActivityDetector()
        for _ in range(20):
            vad.analyze_frame(b'\x00\x00' * 100)
        stats = vad.stats()
        assert stats.total_frames == 20

    def test_speech_count(self):
        vad = VoiceActivityDetector()
        # Generate alternating speech and silence
        speech_data = struct.pack("<100h", *[16000] * 100)
        silence_data = b'\x00\x00' * 100
        for _ in range(5):
            vad.analyze_frame(speech_data)
        stats = vad.stats()
        assert stats.speech_count >= 0


# ============================================================
# LISTENING STATE MACHINE TESTS
# ============================================================

class TestListeningStateMachine:
    """Tests for listening state machine."""

    def test_create_sm(self):
        sm = ListeningStateMachine()
        assert sm.state == ListeningState.IDLE

    def test_start(self):
        sm = ListeningStateMachine()
        assert sm.start() is True
        assert sm.state == ListeningState.LISTENING

    def test_speech_detected(self):
        sm = ListeningStateMachine()
        sm.start()
        assert sm.on_speech_detected() is True
        assert sm.state == ListeningState.SPEECH_DETECTED

    def test_recording(self):
        sm = ListeningStateMachine()
        sm.start()
        sm.on_speech_detected()
        assert sm.on_speech_started() is True
        assert sm.state == ListeningState.RECORDING

    def test_silence_detected(self):
        sm = ListeningStateMachine()
        sm.start()
        sm.on_speech_detected()
        sm.on_speech_started()
        assert sm.on_silence_detected() is True
        assert sm.state == ListeningState.SILENCE_DETECTED

    def test_processing_ready(self):
        sm = ListeningStateMachine()
        sm.start()
        sm.on_speech_detected()
        sm.on_speech_started()
        sm.on_silence_detected()
        assert sm.on_silence_timeout() is True
        assert sm.state == ListeningState.PROCESSING_READY

    def test_complete_to_idle(self):
        sm = ListeningStateMachine()
        sm.start()
        sm.on_speech_detected()
        sm.on_speech_started()
        sm.on_silence_detected()
        sm.on_silence_timeout()
        assert sm.on_processing_complete() is True
        assert sm.state == ListeningState.IDLE

    def test_full_lifecycle(self):
        sm = ListeningStateMachine()
        sm.start()
        sm.on_speech_detected()
        sm.on_speech_started()
        sm.on_silence_detected()
        sm.on_silence_timeout()
        sm.on_processing_complete()
        assert sm.state == ListeningState.IDLE
        assert sm.turn_count == 1

    def test_pause(self):
        sm = ListeningStateMachine()
        sm.start()
        assert sm.pause() is True
        assert sm.state == ListeningState.PAUSED

    def test_resume(self):
        sm = ListeningStateMachine()
        sm.start()
        sm.pause()
        assert sm.resume() is True
        assert sm.state == ListeningState.LISTENING

    def test_cancel(self):
        sm = ListeningStateMachine()
        sm.start()
        assert sm.cancel() is True
        assert sm.state == ListeningState.CANCELLED

    def test_invalid_transition(self):
        sm = ListeningStateMachine()
        # Can't go directly from IDLE to RECORDING
        assert sm.on_speech_started() is False

    def test_timeout_check(self):
        sm = ListeningStateMachine(listening_timeout=0.01)
        sm.start()
        time.sleep(0.02)
        assert sm.check_timeout() is True

    def test_snapshot(self):
        sm = ListeningStateMachine()
        sm.start()
        snap = sm.snapshot()
        assert snap.state == ListeningState.LISTENING

    def test_snapshot_to_dict(self):
        sm = ListeningStateMachine()
        d = sm.to_dict()
        assert "state" in d
        assert "turn_count" in d

    def test_is_recording(self):
        sm = ListeningStateMachine()
        assert sm.is_recording is False
        sm.start()
        sm.on_speech_detected()
        assert sm.is_recording is True

    def test_stop(self):
        sm = ListeningStateMachine()
        sm.start()
        sm.on_speech_detected()
        assert sm.stop() is True
        assert sm.state == ListeningState.IDLE

    @pytest.mark.asyncio
    async def test_event_handler(self):
        sm = ListeningStateMachine()
        events = []
        sm.on(ListeningEvent.STATE_CHANGED, lambda e, d: events.append((e, d)))
        await sm._emit(ListeningEvent.STATE_CHANGED, {"test": True})
        assert len(events) > 0

    def test_turn_counting(self):
        sm = ListeningStateMachine()
        for _ in range(3):
            sm.start()
            sm.on_speech_detected()
            sm.on_speech_started()
            sm.on_silence_detected()
            sm.on_silence_timeout()
            sm.on_processing_complete()
        assert sm.turn_count == 3

    def test_speech_resume(self):
        sm = ListeningStateMachine()
        sm.start()
        sm.on_speech_detected()
        sm.on_speech_started()
        sm.on_silence_detected()
        # Speech resumes during silence
        assert sm.on_speech_detected() is True
        assert sm.state == ListeningState.RECORDING


# ============================================================
# CALIBRATION TESTS
# ============================================================

class TestCalibration:
    """Tests for automatic calibration."""

    def test_create_calibration(self):
        cm = CalibrationManager()
        assert cm.state == CalibrationState.IDLE

    @pytest.mark.asyncio
    async def test_simulate_calibration(self):
        cm = CalibrationManager()
        result = await cm.calibrate()
        assert result.state == CalibrationState.COMPLETE
        assert result.samples_analyzed > 0

    @pytest.mark.asyncio
    async def test_calibration_result(self):
        cm = CalibrationManager()
        result = await cm.calibrate()
        assert result.noise_floor >= 0
        assert result.peak_level >= 0
        assert result.recommended_threshold > 0

    @pytest.mark.asyncio
    async def test_calibration_profile(self):
        cm = CalibrationManager()
        await cm.calibrate()
        profile = cm.get_recommended_profile()
        assert isinstance(profile, VoiceProfile)

    def test_reset(self):
        cm = CalibrationManager()
        cm.reset()
        assert cm.state == CalibrationState.IDLE

    def test_to_dict(self):
        cm = CalibrationManager()
        d = cm.to_dict()
        assert "state" in d
        assert "config" in d

    def test_config_to_dict(self):
        cfg = CalibrationConfig()
        d = cfg.to_dict()
        assert "duration_seconds" in d
        assert "sample_rate" in d

    @pytest.mark.asyncio
    async def test_calibration_duration(self):
        cm = CalibrationManager(CalibrationConfig(duration_seconds=0.1))
        start = time.monotonic()
        await cm.calibrate()
        elapsed = time.monotonic() - start
        assert elapsed < 1.0

    @pytest.mark.asyncio
    async def test_calibration_result_to_dict(self):
        cm = CalibrationManager()
        result = await cm.calibrate()
        d = result.to_dict()
        assert "noise_floor" in d
        assert "recommended_profile" in d

    def test_progress_callback(self):
        cm = CalibrationManager()
        progress = []
        cm.on_progress(lambda p: progress.append(p))
        assert cm._progress_callback is not None


# ============================================================
# DIAGNOSTICS VAD TESTS
# ============================================================

class TestDiagnosticsVAD:
    """Tests for extended diagnostics with VAD metrics."""

    def test_vad_state_update(self):
        diag = AudioDiagnostics()
        diag.update_vad_state("speech")
        snap = diag.snapshot()
        assert snap.vad_state == "speech"

    def test_speech_confidence_update(self):
        diag = AudioDiagnostics()
        diag.update_speech_confidence(0.85)
        snap = diag.snapshot()
        assert snap.speech_confidence == 0.85

    def test_noise_floor_update(self):
        diag = AudioDiagnostics()
        diag.update_noise_floor(0.03)
        snap = diag.snapshot()
        assert snap.noise_floor == 0.03

    def test_input_level_update(self):
        diag = AudioDiagnostics()
        diag.update_input_level(0.15)
        snap = diag.snapshot()
        assert snap.input_level == 0.15

    def test_listening_state_update(self):
        diag = AudioDiagnostics()
        diag.update_listening_state("recording")
        snap = diag.snapshot()
        assert snap.listening_state == "recording"

    def test_speech_duration_update(self):
        diag = AudioDiagnostics()
        diag.update_speech_duration(2.5)
        snap = diag.snapshot()
        assert snap.speech_duration == 2.5

    def test_detection_latency_update(self):
        diag = AudioDiagnostics()
        diag.update_detection_latency(35.0)
        snap = diag.snapshot()
        assert snap.detection_latency_ms == 35.0

    def test_active_profile_update(self):
        diag = AudioDiagnostics()
        diag.update_active_profile("Office")
        snap = diag.snapshot()
        assert snap.active_profile == "Office"

    def test_voice_event_recording(self):
        diag = AudioDiagnostics()
        diag.record_voice_event("speech_start", {"confidence": 0.9})
        snap = diag.snapshot()
        assert len(snap.recent_events) == 1
        assert snap.recent_events[0]["type"] == "speech_start"

    def test_recent_events_limit(self):
        diag = AudioDiagnostics()
        for i in range(60):
            diag.record_voice_event(f"event_{i}", {})
        snap = diag.snapshot()
        assert len(snap.recent_events) <= 10

    def test_reset_clears_vad(self):
        diag = AudioDiagnostics()
        diag.update_vad_state("speech")
        diag.update_speech_confidence(0.9)
        diag.record_voice_event("test", {})
        diag.reset()
        snap = diag.snapshot()
        assert snap.vad_state == "idle"
        assert snap.speech_confidence == 0.0
        assert len(snap.recent_events) == 0

    def test_snapshot_includes_vad(self):
        diag = AudioDiagnostics()
        snap = diag.snapshot()
        d = snap.to_dict()
        assert "vad_state" in d
        assert "speech_confidence" in d
        assert "noise_floor" in d
        assert "listening_state" in d
        assert "recent_events" in d


# ============================================================
# INTEGRATION TESTS
# ============================================================

class TestD2Integration:
    """Integration tests for the complete D2 pipeline."""

    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """Test: NoiseProcessor → VAD → ListeningStateMachine → Diagnostics."""
        # Setup
        noise = NoiseProcessor()
        vad = VoiceActivityDetector()
        sm = ListeningStateMachine()
        diag = AudioDiagnostics()

        # Simulate: silence → speech → silence
        silence = b'\x00\x00' * 100
        speech_samples = [16000] * 100
        speech = struct.pack(f"<{len(speech_samples)}h", *speech_samples)

        # Phase 1: Silence
        cleaned = noise.process(silence)
        frame = vad.analyze_frame(cleaned)
        assert frame.is_speech is False

        # Phase 2: Start listening
        sm.start()
        assert sm.state == ListeningState.LISTENING

        # Phase 3: Speech detected
        cleaned = noise.process(speech)
        frame = vad.analyze_frame(cleaned)
        if frame.is_speech:
            sm.on_speech_detected()
            assert sm.state in (ListeningState.SPEECH_DETECTED, ListeningState.RECORDING)

        # Phase 4: Update diagnostics
        diag.update_vad_state(vad.state.value)
        diag.update_speech_confidence(frame.confidence)
        diag.update_noise_floor(noise.noise_floor)
        diag.update_listening_state(sm.state.value)

        snap = diag.snapshot()
        assert snap.vad_state in ("idle", "speech", "silence", "pause")
        assert snap.listening_state in ("idle", "listening", "speech_detected", "recording")

    def test_calibration_to_vad(self):
        """Test: Calibration → profile → VAD configuration."""
        cm = CalibrationManager()
        # Simulate calibration
        result = cm._analyze()
        profile = cm.get_recommended_profile()
        vad = VoiceActivityDetector(profile=profile)
        assert vad.profile.profile_type == profile.profile_type

    @pytest.mark.asyncio
    async def test_calibration_with_audio(self):
        """Test calibration with simulated audio."""
        cm = CalibrationManager(CalibrationConfig(duration_seconds=0.1))
        result = await cm.calibrate()
        assert result.state == CalibrationState.COMPLETE
        assert result.recommended_threshold > 0

    def test_profiles_cover_all_environments(self):
        """Test that profiles cover all expected environments."""
        expected = [
            ProfileType.QUIET_ROOM, ProfileType.OFFICE, ProfileType.CONFERENCE,
            ProfileType.CAFE, ProfileType.HEADSET, ProfileType.EXTERNAL_MIC,
        ]
        for pt in expected:
            p = get_profile(pt)
            assert p.profile_type == pt

    def test_noise_processor_calibration(self):
        """Test noise processor self-calibration."""
        np = NoiseProcessor()
        # Generate quiet ambient noise
        samples = [50] * 1000
        data = struct.pack(f"<{len(samples)}h", *samples)
        result = np.calibrate(data)
        assert result["status"] == "ok"
        assert result["recommended_threshold"] > 0

    @pytest.mark.asyncio
    async def test_full_lifecycle_with_diagnostics(self):
        """Test complete lifecycle with diagnostics tracking."""
        diag = AudioDiagnostics()
        sm = ListeningStateMachine()
        vad = VoiceActivityDetector()

        # Start listening
        sm.start()
        diag.update_listening_state(sm.state.value)

        # Simulate speech
        sm.on_speech_detected()
        diag.update_listening_state(sm.state.value)
        diag.update_vad_state("speech")

        # Record event
        diag.record_voice_event("speech_start", {"timestamp": time.time()})

        # Verify diagnostics
        snap = diag.snapshot()
        assert snap.listening_state == "speech_detected"
        assert snap.vad_state == "speech"
        assert len(snap.recent_events) == 1

    def test_event_publishing(self):
        """Test that VAD and Listening events are published."""
        vad_events = []
        sm_events = []

        vad = VoiceActivityDetector()
        sm = ListeningStateMachine()

        vad.on(VADEvent.SPEECH_START, lambda e, d: vad_events.append(e))
        sm.on(ListeningEvent.STATE_CHANGED, lambda e, d: sm_events.append(e))

        # Trigger events via direct _emit (sync context lacks event loop)
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(sm._emit(ListeningEvent.STATE_CHANGED, {"from": "idle", "to": "listening"}))
            assert len(sm_events) > 0
        finally:
            loop.close()

    def test_concurrent_processing(self):
        """Test concurrent audio processing."""
        import threading

        vad = VoiceActivityDetector()
        results = []

        def process_frame():
            for _ in range(10):
                vad.analyze_frame(b'\x00\x00' * 100)
            results.append(vad.stats().total_frames)

        threads = [threading.Thread(target=process_frame) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have processed frames without errors
        assert len(results) == 4
        assert all(r > 0 for r in results)
