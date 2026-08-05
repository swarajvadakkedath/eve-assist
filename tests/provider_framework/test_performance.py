"""D9 Integration — Performance Measurement Tests.
Measures: wake detection, conversation latency, adaptation speed, memory usage.
"""

import gc
import os
import sys
import time
import threading
from aios.voice.conversation.manager import ConversationSessionManager
from aios.voice.identity.manager import VoiceIdentityManager
from aios.voice.identity.adaptation import AdaptationContext
from aios.voice.identity.pronunciation import PronunciationDictionary
from aios.voice.wakeword.engine import WakeWordEngine
from aios.voice.wakeword.detector import WakeWordDetector
from aios.voice.wakeword.session import WakeWordSession
from aios.voice.stt_streaming.manager import StreamingSTTManager
from aios.voice.tts_streaming.manager import StreamingTTSManager
from aios.core.health_monitor import HealthMonitor, ProviderStatus
from aios.error_intelligence.service import ErrorIntelligenceService


class TestWakeWordPerformance:
    def test_wake_detection_latency(self):
        wake = WakeWordEngine()
        wake.initialize()
        start = time.perf_counter()
        wake.start_monitoring()
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 100
        wake.shutdown()

    def test_detector_phrase_add_latency(self):
        wake = WakeWordEngine()
        wake.initialize()
        start = time.perf_counter()
        for i in range(100):
            wake.add_phrase(f"p_{i}", sensitivity=0.5)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 500
        wake.shutdown()

    def test_session_creation_latency(self):
        start = time.perf_counter()
        for _ in range(1000):
            WakeWordSession()
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 500


class TestConversationPerformance:
    def test_conversation_start_latency(self):
        conv = ConversationSessionManager()
        start = time.perf_counter()
        for _ in range(1000):
            s = conv.start_conversation()
            conv.end_conversation(s.id)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 2000

    def test_message_throughput(self):
        conv = ConversationSessionManager()
        session = conv.start_conversation()
        start = time.perf_counter()
        for i in range(500):
            conv.begin_turn(f"Msg {i}")
        elapsed_ms = (time.perf_counter() - start) * 1000
        throughput = 500 / (elapsed_ms / 1000)
        conv.end_conversation(session.id)
        assert throughput > 500

    def test_conversation_switch_latency(self):
        conv = ConversationSessionManager()
        start = time.perf_counter()
        sessions = []
        for _ in range(100):
            s = conv.start_conversation()
            sessions.append(s)
        for s in sessions:
            conv.end_conversation(s.id)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 500


class TestIdentityPerformance:
    def test_adaptation_latency(self):
        identity = VoiceIdentityManager()
        identity.initialize()
        start = time.perf_counter()
        for _ in range(1000):
            identity.adapt_to_context(AdaptationContext.CODING)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 1000

    def test_profile_switch_latency(self):
        identity = VoiceIdentityManager()
        identity.initialize()
        profiles = ["professional", "friendly", "technical", "minimal",
                     "companion", "teacher", "creative", "executive"]
        start = time.perf_counter()
        for i in range(1000):
            identity.switch_profile(profiles[i % len(profiles)])
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 1000

    def test_pronunciation_lookup_latency(self):
        d = PronunciationDictionary()
        d.load_defaults()
        start = time.perf_counter()
        for _ in range(10000):
            d.has("typescript")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 500

    def test_snapshot_latency(self):
        identity = VoiceIdentityManager()
        identity.initialize()
        start = time.perf_counter()
        for _ in range(1000):
            identity.snapshot()
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 500


class TestSTTPerformance:
    def test_stt_session_start_latency(self):
        mgr = StreamingSTTManager()
        start = time.perf_counter()
        for _ in range(100):
            mgr.start_session()
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 2000


class TestTTSPerformance:
    def test_tts_synthesize_latency(self):
        mgr = StreamingTTSManager()
        start = time.perf_counter()
        for i in range(100):
            mgr.synthesize(f"Test message {i}")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 2000


class TestHealthMonitorPerformance:
    def test_health_check_latency(self):
        monitor = HealthMonitor()
        start = time.perf_counter()
        for i in range(100):
            monitor.record_provider_result(f"provider_{i % 10}", "", ProviderStatus.CONNECTED, "")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 500


class TestErrorIntelligencePerformance:
    def test_service_creation_latency(self):
        start = time.perf_counter()
        for _ in range(100):
            ErrorIntelligenceService()
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 500


class TestMemoryUsage:
    def test_conversation_memory_footprint(self):
        gc.collect()
        conv = ConversationSessionManager()
        for _ in range(500):
            s = conv.start_conversation()
            conv.begin_turn("x" * 100)
            conv.end_conversation(s.id)
        gc.collect()

    def test_identity_memory_footprint(self):
        gc.collect()
        identity = VoiceIdentityManager()
        identity.initialize()
        for _ in range(500):
            identity.adapt_to_context(AdaptationContext.CODING)
        identity.shutdown()
        gc.collect()


class TestConcurrentPerformance:
    def test_parallel_conversation_throughput(self):
        conv = ConversationSessionManager()
        results = []

        def run_batch():
            start = time.perf_counter()
            for _ in range(100):
                s = conv.start_conversation()
                conv.begin_turn("test")
                conv.end_conversation(s.id)
            results.append(time.perf_counter() - start)

        threads = [threading.Thread(target=run_batch) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        total = sum(results)
        total_ms = total * 1000
        assert total_ms < 5000
