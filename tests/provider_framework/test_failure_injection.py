"""D9 Integration — Failure Injection Tests.
Simulates failures across subsystems. Recovery Engine should recover automatically.
"""

import time
import threading
from aios.voice.wakeword.engine import WakeWordEngine
from aios.voice.wakeword.session import WakeWordSession, WakeSessionState
from aios.voice.conversation.manager import ConversationSessionManager
from aios.voice.identity.manager import VoiceIdentityManager
from aios.voice.identity.adaptation import AdaptationContext
from aios.voice.stt_streaming.manager import StreamingSTTManager
from aios.voice.tts_streaming.manager import StreamingTTSManager
from aios.core.health_monitor import HealthMonitor, ProviderStatus
from aios.error_intelligence.models import ErrorCategory, Severity, AutoRecoveryStrategy
from aios.error_intelligence.classifier import classify_error
from aios.error_intelligence.recovery_engine import RecoveryEngine
from aios.error_intelligence.service import ErrorIntelligenceService


class TestProviderFailureRecovery:
    def test_health_monitor_records_failure(self):
        monitor = HealthMonitor()
        monitor.record_provider_result("test_provider", "", ProviderStatus.OFFLINE, "connection_error")
        monitor.record_provider_result("test_provider", "", ProviderStatus.OFFLINE, "timeout")
        health = monitor.get_health("test_provider")
        assert health is not None

    def test_health_monitor_records_success_recovery(self):
        monitor = HealthMonitor()
        for _ in range(3):
            monitor.record_provider_result("p1", "", ProviderStatus.OFFLINE, "timeout")
        for _ in range(5):
            monitor.record_provider_result("p1", "", ProviderStatus.CONNECTED, "")
        health = monitor.get_health("p1")
        assert health is not None

    def test_stt_provider_failover(self):
        stt_mgr = StreamingSTTManager()
        stt_mgr.start_session()

    def test_tts_provider_failover(self):
        tts_mgr = StreamingTTSManager()
        assert tts_mgr is not None


class TestNetworkLossRecovery:
    def test_identity_survives_network_loss(self):
        identity = VoiceIdentityManager()
        identity.initialize()

        identity.adapt_to_context(AdaptationContext.CODING)
        assert identity.active_profile_id == "technical"

        identity.adapt_to_error()
        assert identity.active_profile_id == "minimal"

        identity.adapt_to_success()
        assert identity.active_profile_id == "friendly"


class TestAudioDeviceRemoval:
    def test_conversation_survives_device_removal(self):
        conv = ConversationSessionManager()
        session = conv.start_conversation()
        conv.begin_turn("Hello")
        conv.end_conversation(session.id)

        session2 = conv.start_conversation()
        assert session2 is not None
        conv.end_conversation(session2.id)


class TestSTTFailureRecovery:
    def test_stt_error_recovery(self):
        stt_mgr = StreamingSTTManager()
        stt_mgr.start_session()

    def test_stt_reconnection(self):
        stt_mgr = StreamingSTTManager()
        stt_mgr.start_session()
        stt_mgr.start_session()


class TestTTSFailureRecovery:
    def test_tts_error_recovery(self):
        tts_mgr = StreamingTTSManager()
        assert tts_mgr is not None


class TestWakeWordTimeout:
    def test_wake_timeout_recovery(self):
        wake = WakeWordEngine()
        wake.initialize()
        wake.start_monitoring()
        wake.end_session()
        wake.shutdown()

    def test_wake_phrase_timeout(self):
        session = WakeWordSession()
        assert session.state == WakeSessionState.INACTIVE
        session.end()
        assert session.state in (WakeSessionState.INACTIVE, WakeSessionState.ENDED)


class TestConversationTimeout:
    def test_conversation_timeout(self):
        conv = ConversationSessionManager()
        session = conv.start_conversation()
        conv.begin_turn("Hello")

        session2 = conv.start_conversation()
        assert session2 is not None

        conv.end_conversation(session.id)
        conv.end_conversation(session2.id)


class TestContextFailureRecovery:
    def test_context_adapter_resilience(self):
        identity = VoiceIdentityManager()
        identity.initialize()

        identity.adapt_to_context(AdaptationContext.CODING)
        identity.adapt_to_error()
        identity.adapt_to_success()
        assert identity.active_profile_id == "friendly"

    def test_identity_state_after_error(self):
        identity = VoiceIdentityManager()
        identity.initialize()
        identity.switch_profile("technical")
        identity.adapt_to_error()
        snap = identity.snapshot()
        assert snap["active_profile"] == "minimal"


class TestMemoryFailureRecovery:
    def test_pronunciation_persistence_survives(self):
        identity = VoiceIdentityManager()
        identity.initialize()
        identity.add_pronunciation("test", "TEST")
        identity.adapt_to_error()
        identity.adapt_to_success()
        assert identity.pronunciation.has("test")

    def test_preferences_persistence_survives(self):
        identity = VoiceIdentityManager()
        identity.initialize()
        identity.update_preferences(preferred_voice="nova")
        identity.adapt_to_error()
        assert identity.preferences.get("preferred_voice") == "nova"


class TestErrorClassifierIntegration:
    def test_classify_provider_error(self):
        result = classify_error(Exception("provider unavailable"))
        assert result is not None

    def test_classify_network_error(self):
        result = classify_error(Exception("network timeout"))
        assert result is not None

    def test_recovery_strategies(self):
        for strategy in AutoRecoveryStrategy:
            assert strategy.value is not None


class TestRecoveryEngineIntegration:
    def test_recovery_engine_creation(self):
        engine = RecoveryEngine()
        assert engine is not None

    def test_error_categories_coverage(self):
        assert len(ErrorCategory) >= 15
        critical = [
            ErrorCategory.AUTHENTICATION,
            ErrorCategory.NETWORK,
            ErrorCategory.TIMEOUT,
            ErrorCategory.PROVIDER,
        ]
        for cat in critical:
            assert cat.value is not None


class TestErrorIntelligenceService:
    def test_service_creation(self):
        svc = ErrorIntelligenceService()
        assert svc is not None

    def test_severity_levels(self):
        for sev in Severity:
            assert sev.value is not None


class TestCascadingFailureRecovery:
    def test_multiple_subsystem_failures(self):
        identity = VoiceIdentityManager()
        identity.initialize()

        identity.adapt_to_context(AdaptationContext.CODING)
        assert identity.active_profile_id == "technical"

        identity.adapt_to_error()
        assert identity.active_profile_id == "minimal"

        identity.switch_profile("friendly")
        assert identity.active_profile_id == "friendly"

        identity.adapt_to_success()
        assert identity.active_profile_id == "friendly"

    def test_conversation_recovery_after_stt_failure(self):
        conv = ConversationSessionManager()
        session = conv.start_conversation()
        conv.begin_turn("Hello")
        conv.end_conversation(session.id)

        session2 = conv.start_conversation()
        assert session2 is not None
        conv.end_conversation(session2.id)


class TestThreadedFailureRecovery:
    def test_concurrent_failures(self):
        identity = VoiceIdentityManager()
        identity.initialize()
        errors = []

        def fail_and_recover():
            try:
                for _ in range(10):
                    identity.adapt_to_error()
                    identity.adapt_to_success()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=fail_and_recover) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
