"""Tests for Wake Word Engine (Sprint D7)."""

import time
import struct
import threading
import pytest
from unittest.mock import MagicMock

from aios.voice.wakeword.models import (
    WakePhrase, WakeWordConfig, WakeWordState, DetectionResult,
    SensitivityLevel, SensitivityProfile, PowerMode, SENSITIVITY_PROFILES,
)
from aios.voice.wakeword.events import WakeWordEvent, WakeWordEventType
from aios.voice.wakeword.metrics import WakeWordMetrics, WakeWordMetricsSnapshot
from aios.voice.wakeword.detector import WakeWordDetector, AudioFrame, DetectorState
from aios.voice.wakeword.session import (
    WakeWordSession, WakeSessionState, WakeSessionStats, WakeSessionEvent,
)
from aios.voice.wakeword.engine import WakeWordEngine, WakeEngineState


# === Models Tests ===

class TestWakePhrase:
    def test_creation(self):
        p = WakePhrase(phrase="EVE")
        assert p.phrase == "EVE"
        assert p.enabled is True
        assert p.is_custom is False

    def test_custom_phrase(self):
        p = WakePhrase(phrase="Hello Computer", sensitivity=0.8, is_custom=True)
        assert p.is_custom is True
        assert p.sensitivity == 0.8

    def test_to_dict(self):
        p = WakePhrase(phrase="EVE")
        d = p.to_dict()
        assert d["phrase"] == "EVE"
        assert d["enabled"] is True


class TestWakeWordConfig:
    def test_defaults(self):
        cfg = WakeWordConfig()
        assert "EVE" in cfg.enabled_phrases
        assert "Hey EVE" in cfg.enabled_phrases
        assert cfg.sensitivity == SensitivityLevel.MEDIUM
        assert cfg.threshold == 0.5
        assert cfg.cooldown_s == 2.0
        assert cfg.privacy_mode is True
        assert cfg.power_mode == PowerMode.ACTIVE

    def test_to_dict(self):
        cfg = WakeWordConfig()
        d = cfg.to_dict()
        assert isinstance(d, dict)
        assert "enabled_phrases" in d
        assert "sensitivity" in d


class TestSensitivityProfiles:
    def test_all_levels_present(self):
        assert SensitivityLevel.LOW in SENSITIVITY_PROFILES
        assert SensitivityLevel.MEDIUM in SENSITIVITY_PROFILES
        assert SensitivityLevel.HIGH in SENSITIVITY_PROFILES

    def test_low_has_higher_threshold(self):
        low = SENSITIVITY_PROFILES[SensitivityLevel.LOW]
        high = SENSITIVITY_PROFILES[SensitivityLevel.HIGH]
        assert low.threshold > high.threshold

    def test_to_dict(self):
        for level, profile in SENSITIVITY_PROFILES.items():
            d = profile.to_dict()
            assert d["level"] == level.value


class TestDetectionResult:
    def test_creation(self):
        r = DetectionResult(detected=True, phrase="EVE", confidence=0.8, detection_latency_ms=15.0)
        assert r.detected is True
        assert r.phrase == "EVE"

    def test_defaults(self):
        r = DetectionResult(detected=False, phrase="", confidence=0.0, detection_latency_ms=0.0)
        assert r.is_false_positive is False
        assert r.rejected_reason == ""

    def test_to_dict(self):
        r = DetectionResult(detected=True, phrase="EVE", confidence=0.8, detection_latency_ms=15.0)
        d = r.to_dict()
        assert d["detected"] is True
        assert d["confidence"] == 0.8


# === Events Tests ===

class TestWakeWordEvent:
    def test_creation(self):
        e = WakeWordEvent(event_type=WakeWordEventType.WAKE_WORD_DETECTED)
        assert e.event_type == WakeWordEventType.WAKE_WORD_DETECTED
        assert e.phrase == ""

    def test_all_event_types(self):
        for et in WakeWordEventType:
            e = WakeWordEvent(event_type=et)
            assert e.event_type == et

    def test_to_dict(self):
        e = WakeWordEvent(event_type=WakeWordEventType.WAKE_WORD_DETECTED,
                          phrase="EVE", confidence=0.9)
        d = e.to_dict()
        assert d["phrase"] == "EVE"
        assert d["confidence"] == 0.9


# === Metrics Tests ===

class TestWakeWordMetrics:
    def test_basics(self):
        m = WakeWordMetrics()
        assert m.uptime > 0

    def test_detection_recording(self):
        m = WakeWordMetrics()
        m.record_detection(50.0, 0.8, success=True)
        m.record_detection(60.0, 0.7, success=False)
        snap = m.snapshot()
        assert snap.total_detections == 2
        assert snap.successful_detections == 1

    def test_false_positives(self):
        m = WakeWordMetrics()
        m.record_false_positive()
        m.record_false_positive()
        snap = m.snapshot()
        assert snap.false_positives == 2

    def test_rejections(self):
        m = WakeWordMetrics()
        m.record_rejection()
        snap = m.snapshot()
        assert snap.rejected_detections == 1

    def test_timeouts(self):
        m = WakeWordMetrics()
        m.record_timeout()
        snap = m.snapshot()
        assert snap.timeouts == 1

    def test_sessions(self):
        m = WakeWordMetrics()
        m.record_session_start()
        m.record_session_end()
        snap = m.snapshot()
        assert snap.sessions_started == 1
        assert snap.sessions_ended == 1

    def test_activation_counting(self):
        m = WakeWordMetrics()
        m.record_activation()
        m.record_activation()
        snap = m.snapshot()
        assert snap.activations_today == 2

    def test_activation_daily_reset(self):
        m = WakeWordMetrics()
        m.record_activation()
        snap = m.snapshot()
        assert snap.activations_today == 1

    def test_latency_tracking(self):
        m = WakeWordMetrics()
        m.record_detection(10.0, 0.9)
        m.record_detection(20.0, 0.8)
        snap = m.snapshot()
        assert snap.avg_detection_latency_ms == 15.0
        assert snap.p95_detection_latency_ms >= 10.0

    def test_confidence_tracking(self):
        m = WakeWordMetrics()
        m.record_detection(10.0, 0.9)
        m.record_detection(20.0, 0.7)
        snap = m.snapshot()
        assert abs(snap.avg_confidence - 0.8) < 0.01

    def test_snapshot_with_params(self):
        m = WakeWordMetrics()
        snap = m.snapshot(current_threshold=0.6, current_sensitivity="high")
        assert snap.current_threshold == 0.6
        assert snap.current_sensitivity == "high"

    def test_to_dict(self):
        m = WakeWordMetrics()
        snap = m.snapshot()
        d = snap.to_dict()
        assert isinstance(d, dict)
        assert "total_detections" in d

    def test_reset(self):
        m = WakeWordMetrics()
        m.record_detection(10.0, 0.9)
        m.record_false_positive()
        m.reset()
        snap = m.snapshot()
        assert snap.total_detections == 0
        assert snap.false_positives == 0

    def test_empty_snapshot(self):
        m = WakeWordMetrics()
        snap = m.snapshot()
        assert snap.avg_detection_latency_ms == 0.0
        assert snap.avg_confidence == 0.0


# === Detector Tests ===

class TestAudioFrame:
    def test_creation(self):
        f = AudioFrame(data=b"\x00\x00" * 100)
        assert len(f.data) == 200
        assert f.sample_rate == 16000

    def test_duration_ms(self):
        f = AudioFrame(data=b"\x00\x00" * 160, sample_rate=16000)
        assert f.duration_ms == 10.0

    def test_with_energy(self):
        f = AudioFrame(data=b"", rms=0.1, peak=0.2)
        assert f.rms == 0.1
        assert f.peak == 0.2


class TestWakeWordDetector:
    def test_creation(self):
        d = WakeWordDetector()
        assert d.state == DetectorState.IDLE
        assert len(d.get_phrases()) == 3

    def test_creation_with_config(self):
        cfg = WakeWordConfig(enabled_phrases=["COMPUTER"])
        d = WakeWordDetector(config=cfg)
        assert len(d.get_phrases()) == 1

    def test_start_stop(self):
        d = WakeWordDetector()
        d.start()
        assert d.state == DetectorState.MONITORING
        d.stop()
        assert d.state == DetectorState.IDLE

    def test_add_phrase(self):
        d = WakeWordDetector()
        p = d.add_phrase("COMPUTER")
        assert p.phrase == "COMPUTER"
        assert p.is_custom is True
        assert len(d.get_phrases()) == 4

    def test_remove_phrase(self):
        d = WakeWordDetector()
        d.add_phrase("TEST")
        assert d.remove_phrase("TEST") is True
        assert len(d.get_phrases()) == 3

    def test_remove_builtin_phrase(self):
        d = WakeWordDetector()
        assert d.remove_phrase("EVE") is False

    def test_enable_disable_phrase(self):
        d = WakeWordDetector()
        d.disable_phrase("EVE")
        phrases = d.get_phrases()
        eve = [p for p in phrases if p.phrase == "EVE"][0]
        assert eve.enabled is False
        d.enable_phrase("EVE")
        phrases = d.get_phrases()
        eve = [p for p in phrases if p.phrase == "EVE"][0]
        assert eve.enabled is True

    def test_disable_nonexistent(self):
        d = WakeWordDetector()
        assert d.disable_phrase("NONEXISTENT") is False

    def test_set_sensitivity(self):
        d = WakeWordDetector()
        d.set_sensitivity(SensitivityLevel.HIGH)
        assert d.config.sensitivity == SensitivityLevel.HIGH
        assert d.adaptive_threshold == SENSITIVITY_PROFILES[SensitivityLevel.HIGH].threshold

    def test_set_threshold(self):
        d = WakeWordDetector()
        d.set_threshold(0.8)
        assert d.adaptive_threshold == 0.8

    def test_set_threshold_clamped(self):
        d = WakeWordDetector()
        d.set_threshold(1.5)
        assert d.adaptive_threshold == 1.0
        d.set_threshold(-0.5)
        assert d.adaptive_threshold == 0.0

    def test_process_frame_when_idle(self):
        d = WakeWordDetector()
        f = AudioFrame(data=b"\x00\x00" * 100)
        result = d.process_frame(f)
        assert result is None

    def test_process_frame_low_energy(self):
        d = WakeWordDetector()
        d.start()
        f = AudioFrame(data=b"\x01\x00" * 10, rms=0.001, peak=0.002)
        result = d.process_frame(f)
        assert result is not None
        assert result.detected is False

    def test_process_frame_high_energy(self):
        d = WakeWordDetector()
        d.start()
        f = AudioFrame(data=b"\x00\x80" * 100, rms=0.8, peak=0.9)
        result = d.process_frame(f)
        assert result is not None

    def test_cooldown_prevents_detection(self):
        cfg = WakeWordConfig(cooldown_s=10.0)
        d = WakeWordDetector(config=cfg)
        d.start()
        f1 = AudioFrame(data=b"\x00\x80" * 100, rms=0.9, peak=0.95)
        r1 = d.process_frame(f1)
        if r1 and r1.detected:
            f2 = AudioFrame(data=b"\x00\x80" * 100, rms=0.9, peak=0.95)
            r2 = d.process_frame(f2)
            assert r2.detected is False
            assert r2.rejected_reason == "cooldown"

    def test_false_positive_rate_limit(self):
        cfg = WakeWordConfig(max_false_positives=2, false_positive_window_s=60.0)
        d = WakeWordDetector(config=cfg)
        d._false_positive_times = [time.monotonic(), time.monotonic()]
        d.start()
        f = AudioFrame(data=b"\x00\x80" * 100, rms=0.9, peak=0.95)
        result = d.process_frame(f)
        if result:
            assert result.is_false_positive is True

    def test_event_handler(self):
        d = WakeWordDetector()
        events = []
        d.on("wake_word_detected", lambda data: events.append(data))
        d._emit("wake_word_detected", {"phrase": "EVE"})
        assert len(events) == 1
        assert events[0]["phrase"] == "EVE"

    def test_snapshot(self):
        d = WakeWordDetector()
        snap = d.snapshot()
        assert snap["state"] == "idle"
        assert "adaptive_threshold" in snap
        assert "phrase_count" in snap

    def test_reset(self):
        d = WakeWordDetector()
        d.start()
        d._frame_count = 100
        d.reset()
        assert d._frame_count == 0
        assert d.state == DetectorState.IDLE

    def test_rms_computation(self):
        d = WakeWordDetector()
        samples = struct.pack('<h', 10000) + struct.pack('<h', -10000)
        f = AudioFrame(data=samples)
        rms = d._compute_rms(f)
        assert rms > 0

    def test_peak_computation(self):
        d = WakeWordDetector()
        samples = struct.pack('<h', 10000) + struct.pack('<h', -20000)
        f = AudioFrame(data=samples)
        peak = d._compute_peak(f)
        assert peak > 0

    def test_empty_frame(self):
        d = WakeWordDetector()
        f = AudioFrame(data=b"")
        assert d._compute_rms(f) == 0.0
        assert d._compute_peak(f) == 0.0

    def test_noise_floor_adaptation(self):
        d = WakeWordDetector()
        d._update_noise_floor(0.005)
        assert d.noise_floor < 0.02
        d._update_noise_floor(0.5)
        assert d.noise_floor < 0.5

    def test_adaptive_threshold_increases(self):
        d = WakeWordDetector()
        old = d.adaptive_threshold
        d._adapt_threshold(old + 0.3)
        assert d.adaptive_threshold >= old

    def test_adaptive_threshold_decreases(self):
        d = WakeWordDetector()
        old = d.adaptive_threshold
        d._adapt_threshold(old * 0.3)
        assert d.adaptive_threshold <= old

    def test_adaptive_threshold_disabled(self):
        cfg = WakeWordConfig(adaptive_threshold_enabled=False)
        d = WakeWordDetector(config=cfg)
        old = d.adaptive_threshold
        d._adapt_threshold(0.99)
        assert d.adaptive_threshold == old


# === Session Tests ===

class TestWakeWordSession:
    def test_creation(self):
        s = WakeWordSession()
        assert s.state == WakeSessionState.INACTIVE
        assert s.is_active is False

    def test_lifecycle(self):
        s = WakeWordSession()
        s.start_monitoring()
        assert s.state == WakeSessionState.MONITORING
        assert s.is_active is True

    def test_detection(self):
        s = WakeWordSession()
        s.start_monitoring()
        s.record_detection("EVE", 0.9, 15.0)
        assert s.state == WakeSessionState.DETECTED
        assert s.phrase == "EVE"
        assert s.confidence == 0.9

    def test_activation(self):
        s = WakeWordSession()
        s.start_monitoring()
        s.record_detection("EVE", 0.9, 15.0)
        s.activate()
        assert s.state == WakeSessionState.ACTIVATED

    def test_timeout(self):
        s = WakeWordSession(timeout_s=0.01)
        s.start_monitoring()
        time.sleep(0.02)
        assert s.check_timeout() is True
        assert s.state == WakeSessionState.TIMEOUT

    def test_end(self):
        s = WakeWordSession()
        s.start_monitoring()
        s.end()
        assert s.state == WakeSessionState.ENDED
        assert s.is_active is False

    def test_reset(self):
        s = WakeWordSession()
        s.start_monitoring()
        s.record_detection("EVE", 0.9, 15.0)
        s.reset()
        assert s.state == WakeSessionState.INACTIVE
        assert s.phrase == ""

    def test_false_positive_counting(self):
        s = WakeWordSession()
        s.start_monitoring()
        s.record_false_positive()
        s.record_false_positive()
        stats = s.stats()
        assert stats.false_positives == 2

    def test_activation_counting(self):
        s = WakeWordSession()
        s.start_monitoring()
        s.record_detection("EVE", 0.9, 15.0)
        s.activate()
        stats = s.stats()
        assert stats.activations == 1
        s.reset()
        assert s.stats().activations == 0
        s.start_monitoring()
        s.record_detection("EVE", 0.9, 15.0)
        s.activate()
        stats = s.stats()
        assert stats.activations == 1

    def test_uptime(self):
        s = WakeWordSession()
        time.sleep(0.01)
        assert s.uptime > 0

    def test_elapsed(self):
        s = WakeWordSession()
        s.start_monitoring()
        time.sleep(0.01)
        assert s.elapsed > 0

    def test_stats(self):
        s = WakeWordSession()
        s.start_monitoring()
        s.record_detection("EVE", 0.9, 15.0)
        stats = s.stats()
        assert stats.session_id == s.id
        assert stats.phrase == "EVE"
        assert stats.to_dict()["state"] == "detected"

    def test_event_handler(self):
        s = WakeWordSession()
        events = []
        s.on(WakeSessionEvent.STATE_CHANGED, lambda e, d: events.append(("changed", d)))
        s.start_monitoring()
        assert len(events) == 1

    def test_invalid_transition(self):
        s = WakeWordSession()
        assert s.activate() is False

    def test_custom_id(self):
        s = WakeWordSession(session_id="custom-123")
        assert s.id == "custom-123"

    def test_check_timeout_not_active(self):
        s = WakeWordSession(timeout_s=0.01)
        assert s.check_timeout() is False

    def test_thread_safety(self):
        s = WakeWordSession()
        s.start_monitoring()
        errors = []

        def writer():
            for _ in range(20):
                try:
                    s.record_false_positive()
                except Exception as e:
                    errors.append(e)

        def reader():
            for _ in range(20):
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


# === Engine Tests ===

class TestWakeWordEngine:
    def test_creation(self):
        e = WakeWordEngine()
        assert e.state == WakeEngineState.UNINITIALIZED

    def test_initialize(self):
        e = WakeWordEngine()
        e.initialize()
        assert e.state == WakeEngineState.READY

    def test_start_stop_monitoring(self):
        e = WakeWordEngine()
        e.initialize()
        e.start_monitoring()
        assert e.state == WakeEngineState.MONITORING
        e.stop_monitoring()
        assert e.state == WakeEngineState.READY

    def test_shutdown(self):
        e = WakeWordEngine()
        e.initialize()
        e.shutdown()
        assert e.state == WakeEngineState.SHUTDOWN

    def test_process_frame_when_not_monitoring(self):
        e = WakeWordEngine()
        e.initialize()
        f = AudioFrame(data=b"\x00\x80" * 100, rms=0.9, peak=0.95)
        result = e.process_frame(f)
        assert result is None

    def test_process_frame_when_idle_power(self):
        e = WakeWordEngine()
        e.initialize()
        e.start_monitoring()
        e.set_power_mode(PowerMode.IDLE)
        f = AudioFrame(data=b"\x00\x80" * 100, rms=0.9, peak=0.95)
        result = e.process_frame(f)
        assert result is None

    def test_process_frame_monitoring(self):
        e = WakeWordEngine()
        e.initialize()
        e.start_monitoring()
        f = AudioFrame(data=b"\x01\x00" * 10, rms=0.001, peak=0.002)
        result = e.process_frame(f)
        assert result is not None

    def test_activation_callback(self):
        e = WakeWordEngine()
        e.initialize()
        activations = []
        e.set_activation_callback(lambda phrase, conf: activations.append((phrase, conf)))
        e._on_detection({"phrase": "EVE", "confidence": 0.9, "latency_ms": 10.0})
        assert len(activations) == 1
        assert activations[0] == ("EVE", 0.9)

    def test_phrase_management(self):
        e = WakeWordEngine()
        e.initialize()
        e.add_phrase("COMPUTER")
        phrases = e.detector.get_phrases()
        assert any(p.phrase == "COMPUTER" for p in phrases)
        e.remove_phrase("COMPUTER")
        phrases = e.detector.get_phrases()
        assert not any(p.phrase == "COMPUTER" for p in phrases)

    def test_enable_disable_phrase(self):
        e = WakeWordEngine()
        e.initialize()
        e.disable_phrase("EVE")
        phrases = e.detector.get_phrases()
        eve = [p for p in phrases if p.phrase == "EVE"][0]
        assert eve.enabled is False
        e.enable_phrase("EVE")
        phrases = e.detector.get_phrases()
        eve = [p for p in phrases if p.phrase == "EVE"][0]
        assert eve.enabled is True

    def test_set_sensitivity(self):
        e = WakeWordEngine()
        e.initialize()
        e.set_sensitivity(SensitivityLevel.HIGH)
        assert e.detector.config.sensitivity == SensitivityLevel.HIGH

    def test_set_power_mode(self):
        e = WakeWordEngine()
        e.set_power_mode(PowerMode.BATTERY_SAVER)
        assert e.power_mode == PowerMode.BATTERY_SAVER

    def test_set_privacy_mode(self):
        e = WakeWordEngine()
        e.set_privacy_mode(False)
        assert e.privacy_mode is False

    def test_end_session(self):
        e = WakeWordEngine()
        e.initialize()
        e._on_detection({"phrase": "EVE", "confidence": 0.9, "latency_ms": 10.0})
        assert e.active_session is not None
        e.end_session()
        assert e.active_session is None

    def test_end_session_by_id(self):
        e = WakeWordEngine()
        e.initialize()
        e._on_detection({"phrase": "EVE", "confidence": 0.9, "latency_ms": 10.0})
        sid = e.active_session.id
        e.end_session(sid)
        assert e.active_session is None

    def test_end_nonexistent_session(self):
        e = WakeWordEngine()
        e.end_session("nonexistent")

    def test_snapshot(self):
        e = WakeWordEngine()
        e.initialize()
        snap = e.snapshot()
        assert "state" in snap
        assert "detector" in snap
        assert "metrics" in snap

    def test_reset(self):
        e = WakeWordEngine()
        e.initialize()
        e.start_monitoring()
        e.reset()
        assert e.state == WakeEngineState.UNINITIALIZED

    def test_event_handlers(self):
        e = WakeWordEngine()
        events = []
        e.on(WakeWordEventType.WAKE_WORD_DETECTED, lambda ev: events.append(ev))
        e._emit_event(WakeWordEventType.WAKE_WORD_DETECTED, {"phrase": "EVE"})
        assert len(events) == 1

    def test_false_positive_event(self):
        e = WakeWordEngine()
        events = []
        e.on(WakeWordEventType.FALSE_POSITIVE_DETECTED, lambda ev: events.append(ev))
        e._on_false_positive({"phrase": "EVE"})
        assert len(events) == 1
        assert e.metrics.snapshot().false_positives == 1

    def test_sensitivity_changed_event(self):
        e = WakeWordEngine()
        events = []
        e.on(WakeWordEventType.SENSITIVITY_CHANGED, lambda ev: events.append(ev))
        e.set_sensitivity(SensitivityLevel.LOW)
        assert len(events) == 1

    def test_thread_safety(self):
        e = WakeWordEngine()
        e.initialize()
        e.start_monitoring()
        errors = []

        def processor():
            for _ in range(10):
                try:
                    f = AudioFrame(data=b"\x01\x00" * 10, rms=0.001, peak=0.002)
                    e.process_frame(f)
                except Exception as ex:
                    errors.append(ex)

        def snapshotter():
            for _ in range(10):
                try:
                    e.snapshot()
                except Exception as ex:
                    errors.append(ex)

        threads = [threading.Thread(target=processor) for _ in range(3)]
        threads += [threading.Thread(target=snapshotter) for _ in range(3)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        assert not errors


# === Integration Tests ===

class TestWakeWordIntegration:
    def test_full_activation_flow(self):
        e = WakeWordEngine()
        e.initialize()
        e.start_monitoring()

        activations = []
        e.set_activation_callback(lambda phrase, conf: activations.append((phrase, conf)))

        f = AudioFrame(data=b"\x00\x80" * 100, rms=0.9, peak=0.95)
        result = e.process_frame(f)

        if result and result.detected:
            assert len(activations) == 1
            assert e.active_session is not None
            assert e.active_session.state == WakeSessionState.ACTIVATED

    def test_multi_phrase_detection(self):
        e = WakeWordEngine()
        e.initialize()
        e.add_phrase("COMPUTER", sensitivity=0.8)
        phrases = e.detector.get_phrases()
        assert len(phrases) == 4

    def test_sensitivity_change_flow(self):
        e = WakeWordEngine()
        e.initialize()
        e.set_sensitivity(SensitivityLevel.HIGH)
        assert e.detector.adaptive_threshold == SENSITIVITY_PROFILES[SensitivityLevel.HIGH].threshold
        e.set_sensitivity(SensitivityLevel.LOW)
        assert e.detector.adaptive_threshold == SENSITIVITY_PROFILES[SensitivityLevel.LOW].threshold

    def test_session_lifecycle(self):
        e = WakeWordEngine()
        e.initialize()
        e._on_detection({"phrase": "EVE", "confidence": 0.9, "latency_ms": 10.0})
        session = e.active_session
        assert session is not None
        assert session.state == WakeSessionState.ACTIVATED
        e.end_session()
        assert e.active_session is None

    def test_privacy_mode_default(self):
        e = WakeWordEngine()
        assert e.privacy_mode is True

    def test_power_mode_affects_processing(self):
        e = WakeWordEngine()
        e.initialize()
        e.start_monitoring()
        e.set_power_mode(PowerMode.IDLE)
        f = AudioFrame(data=b"\x00\x80" * 100, rms=0.9, peak=0.95)
        result = e.process_frame(f)
        assert result is None
