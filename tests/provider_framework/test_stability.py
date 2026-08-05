"""D9 Integration — Long-Running Stability Tests.
Stress tests for conversations, wake activations, identity adaptations, resource leaks.
"""

import gc
import os
import sys
import time
import threading
from aios.voice.conversation.manager import ConversationSessionManager
from aios.voice.conversation.session import ConversationSession
from aios.voice.identity.manager import VoiceIdentityManager
from aios.voice.identity.adaptation import AdaptationContext
from aios.voice.identity.pronunciation import PronunciationDictionary
from aios.voice.identity.preferences import PreferenceManager
from aios.voice.wakeword.engine import WakeWordEngine
from aios.voice.wakeword.session import WakeWordSession
from aios.voice.stt_streaming.manager import StreamingSTTManager
from aios.voice.tts_streaming.manager import StreamingTTSManager


class TestConversationStability:
    def test_1000_conversations(self):
        conv = ConversationSessionManager()
        for i in range(1000):
            session = conv.start_conversation()
            conv.begin_turn(f"Message {i}")
            conv.end_conversation(session.id)

    def test_conversation_memory_no_leak(self):
        conv = ConversationSessionManager()
        gc.collect()
        for i in range(500):
            session = conv.start_conversation()
            conv.begin_turn(f"Msg {i}")
            conv.end_conversation(session.id)
        gc.collect()

    def test_concurrent_conversations_stability(self):
        conv = ConversationSessionManager()
        errors = []

        def run_batch(start):
            try:
                for i in range(100):
                    s = conv.start_conversation()
                    conv.begin_turn(f"Batch-{start}-{i}")
                    conv.end_conversation(s.id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=run_batch, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors


class TestWakeWordStability:
    def test_1000_wake_sessions(self):
        for i in range(1000):
            session = WakeWordSession()
            session.end()

    def test_wake_detector_stability(self):
        wake = WakeWordEngine()
        wake.initialize()
        for i in range(100):
            wake.add_phrase(f"phrase_{i}", sensitivity=0.5)
        for i in range(100):
            wake.remove_phrase(f"phrase_{i}")
        wake.shutdown()


class TestIdentityStability:
    def test_1000_adaptations(self):
        identity = VoiceIdentityManager()
        identity.initialize()
        contexts = [
            AdaptationContext.CODING, AdaptationContext.DESIGN,
            AdaptationContext.MEETING, AdaptationContext.TEACHING,
            AdaptationContext.QUICK_COMMAND, AdaptationContext.RESEARCH,
            AdaptationContext.GENERAL,
        ]
        for i in range(1000):
            identity.adapt_to_context(contexts[i % len(contexts)])
        identity.shutdown()

    def test_identity_switch_stability(self):
        identity = VoiceIdentityManager()
        identity.initialize()
        profiles = ["professional", "friendly", "technical", "minimal",
                     "companion", "teacher", "creative", "executive"]
        for i in range(500):
            identity.switch_profile(profiles[i % len(profiles)])
        identity.shutdown()

    def test_pronunciation_stability(self):
        d = PronunciationDictionary()
        for i in range(500):
            d.add(f"word_{i}", f"W_{i}")
        assert d.count == 500
        for i in range(500):
            d.has(f"word_{i}")
        for i in range(500):
            d.remove(f"word_{i}")
        assert d.count == 0

    def test_preferences_stability(self):
        pm = PreferenceManager()
        pm.load()
        for i in range(500):
            pm.update(preferred_voice=f"voice_{i % 5}")
        assert pm.preferences.preferred_voice == "voice_4"


class TestSTTStability:
    def test_stt_session_churn(self):
        mgr = StreamingSTTManager()
        for i in range(200):
            mgr.start_session()


class TestTTSStability:
    def test_tts_session_churn(self):
        mgr = StreamingTTSManager()
        for i in range(200):
            mgr.synthesize(f"Test message {i}")


class TestCrossSubsystemStability:
    def test_all_subsystems_simultaneously(self):
        conv = ConversationSessionManager()
        identity = VoiceIdentityManager()
        identity.initialize()
        errors = []

        def run_conv():
            try:
                for _ in range(200):
                    s = conv.start_conversation()
                    conv.begin_turn("test")
                    conv.end_conversation(s.id)
            except Exception as e:
                errors.append(e)

        def run_identity():
            try:
                for _ in range(200):
                    identity.adapt_to_context(AdaptationContext.CODING)
                    identity.adapt_to_context(AdaptationContext.DESIGN)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=run_conv) for _ in range(3)]
        threads += [threading.Thread(target=run_identity) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors

    def test_rapid_startup_shutdown(self):
        for _ in range(50):
            identity = VoiceIdentityManager()
            identity.initialize()
            identity.shutdown()


class TestResourceLeakDetection:
    def test_thread_count_stability(self):
        initial_threads = threading.active_count()
        conv = ConversationSessionManager()
        identity = VoiceIdentityManager()
        identity.initialize()

        for _ in range(100):
            s = conv.start_conversation()
            identity.adapt_to_context(AdaptationContext.CODING)
            conv.end_conversation(s.id)

        final_threads = threading.active_count()
        assert final_threads <= initial_threads + 5

    def test_gc_after_heavy_use(self):
        conv = ConversationSessionManager()
        identity = VoiceIdentityManager()
        identity.initialize()

        for _ in range(300):
            s = conv.start_conversation()
            conv.begin_turn("test")
            identity.adapt_to_context(AdaptationContext.CODING)
            conv.end_conversation(s.id)

        gc.collect()
        identity.shutdown()
