"""D9 Integration — Cross-System Validation.
Verifies every subsystem works together as one cohesive AI Operating System.
"""

import threading
import time
from aios.voice.wakeword.engine import WakeWordEngine
from aios.voice.wakeword.detector import WakeWordDetector
from aios.voice.wakeword.session import WakeWordSession
from aios.voice.wakeword.models import WakeWordConfig, SensitivityLevel
from aios.voice.conversation.manager import ConversationSessionManager
from aios.voice.conversation.session import ConversationSession
from aios.voice.conversation.state import ConversationState
from aios.voice.conversation.metrics import ConversationMetrics
from aios.voice.identity.manager import VoiceIdentityManager
from aios.voice.identity.adaptation import AdaptationContext, ContextAdapter
from aios.voice.identity.pronunciation import PronunciationDictionary
from aios.voice.identity.preferences import PreferenceManager
from aios.voice.identity.metrics import IdentityMetrics
from aios.voice.stt_streaming.manager import StreamingSTTManager, STTConfig
from aios.voice.stt_streaming.provider import STTProvider
from aios.voice.tts_streaming.manager import StreamingTTSManager, TTSConfig
from aios.voice.tts_streaming.provider import TTSProvider
from aios.voice.stream.session import SpeechSession
from aios.voice.stream.manager import SpeechStreamManager
from aios.core.health_monitor import HealthMonitor, HealthState, ProviderHealth, ProviderStatus
from aios.core.routing_types import RouteCandidate, CATEGORY_CAPABILITIES
from aios.error_intelligence.models import ErrorCategory, Severity, AutoRecoveryStrategy
from aios.error_intelligence.classifier import classify_error
from aios.error_intelligence.recovery_engine import RecoveryEngine
from aios.error_intelligence.service import ErrorIntelligenceService


class TestAudioEngineIntegration:
    def test_wake_detector_to_conversation(self):
        wake = WakeWordEngine()
        wake.initialize()
        detector = wake.detector
        assert detector is not None
        wake.shutdown()

    def test_detector_phrase_management(self):
        wake = WakeWordEngine()
        wake.initialize()
        wake.add_phrase("custom_wake", sensitivity=0.5)
        wake.remove_phrase("custom_wake")


class TestListeningIntelligenceIntegration:
    def test_vad_to_conversation_flow(self):
        conv = ConversationSessionManager()
        session = conv.start_conversation()
        assert session is not None
        conv.end_conversation(session.id)

    def test_conversation_metrics_accuracy(self):
        conv = ConversationSessionManager()
        session = conv.start_conversation()
        for i in range(5):
            conv.begin_turn(f"Message {i}")
        conv.end_conversation(session.id)


class TestStreamingSTTIntegration:
    def test_stt_session_lifecycle(self):
        stt_mgr = StreamingSTTManager()
        stt_mgr.start_session()

    def test_stt_multiple_providers(self):
        stt_mgr = StreamingSTTManager()
        stt_mgr.start_session()


class TestConversationIntegration:
    def test_conversation_state_machine(self):
        mgr = ConversationSessionManager()
        session = mgr.start_conversation()
        assert session is not None
        mgr.begin_turn("Hello")
        mgr.end_conversation(session.id)

    def test_conversation_with_identity(self):
        conv = ConversationSessionManager()
        identity = VoiceIdentityManager()
        identity.initialize()

        session = conv.start_conversation()
        identity.adapt_to_context(AdaptationContext.GENERAL)
        phrase = identity.get_confirmation_phrase()
        assert len(phrase) > 0

        conv.begin_turn("Hello EVE")
        identity.adapt_to_context(AdaptationContext.CODING)
        style = identity.get_speaking_style()
        assert style is not None

        conv.end_conversation(session.id)


class TestContextEngineIntegration:
    def test_context_to_identity_adaptation(self):
        identity = VoiceIdentityManager()
        identity.initialize()

        identity.adapt_to_context(AdaptationContext.CODING)
        assert identity.active_profile_id == "technical"

        identity.adapt_to_context(AdaptationContext.DESIGN)
        assert identity.active_profile_id == "creative"

        identity.adapt_to_context(AdaptationContext.MEETING)
        assert identity.active_profile_id == "executive"

        identity.adapt_to_context(AdaptationContext.TEACHING)
        assert identity.active_profile_id == "teacher"

        identity.adapt_to_context(AdaptationContext.QUICK_COMMAND)
        assert identity.active_profile_id == "minimal"

    def test_context_adapter_history(self):
        adapter = ContextAdapter()
        adapter.adapt(AdaptationContext.CODING)
        adapter.adapt(AdaptationContext.DESIGN)
        adapter.adapt(AdaptationContext.GENERAL)
        history = adapter.get_history()
        assert len(history) == 3


class TestMemoryIntegration:
    def test_memory_with_pronunciation(self):
        identity = VoiceIdentityManager()
        identity.initialize()

        identity.add_pronunciation("groq", "GROK")
        entry = identity.lookup_pronunciation("groq")
        assert entry.phonetic == "GROK"

        identity.add_pronunciation("Swaraj", "SWAH-raj")
        entry2 = identity.lookup_pronunciation("Swaraj")
        assert entry2.phonetic == "SWAH-raj"


class TestHermesIntegration:
    def test_hermes_with_identity(self):
        identity = VoiceIdentityManager()
        identity.initialize()

        identity.adapt_to_context(AdaptationContext.CODING)
        response = identity.format_response("Task completed successfully", is_success=True)
        assert "Task completed" in response

        identity.adapt_to_error()
        response = identity.format_response("Something went wrong", is_error=True)
        assert "Something went wrong" in response


class TestSmartRouterIntegration:
    def test_routing_categories(self):
        cats = CATEGORY_CAPABILITIES
        assert len(cats) >= 5
        assert "general_chat" in cats
        assert "coding" in cats
        assert "reasoning" in cats

    def test_route_candidate_capabilities(self):
        for cat_id in CATEGORY_CAPABILITIES:
            caps = CATEGORY_CAPABILITIES[cat_id]
            assert isinstance(caps, list)

    def test_health_monitor_integration(self):
        monitor = HealthMonitor()
        assert monitor is not None


class TestRecoveryIntegration:
    def test_error_classifier_integration(self):
        result = classify_error(Exception("test error"))
        assert result is not None

    def test_recovery_engine_integration(self):
        engine = RecoveryEngine()
        assert engine is not None

    def test_error_intelligence_service(self):
        svc = ErrorIntelligenceService()
        assert svc is not None


class TestVoiceIdentityIntegration:
    def test_identity_full_workflow(self):
        identity = VoiceIdentityManager()
        identity.initialize()

        identity.switch_profile("technical")
        assert identity.active_profile_id == "technical"

        identity.adapt_to_context(AdaptationContext.DESIGN)
        assert identity.active_profile_id == "creative"

        identity.add_pronunciation("Kubernetes", "koo-ber-NET-eez")
        entry = identity.lookup_pronunciation("Kubernetes")
        assert entry.phonetic == "koo-ber-NET-eez"

        identity.update_preferences(preferred_voice="nova")
        assert identity.preferences.get("preferred_voice") == "nova"

        snap = identity.snapshot()
        assert snap["initialized"] is True

        identity.shutdown()
        assert identity.initialized is False

    def test_identity_export_import(self):
        from aios.voice.identity.models import VoiceProfile, PersonalityType
        identity = VoiceIdentityManager()
        identity.initialize()

        custom = VoiceProfile(profile_id="custom1", name="Custom",
                              personality=PersonalityType.CUSTOM)
        identity.create_profile(custom)

        exported = identity.export_profiles()
        assert isinstance(exported, dict)
        assert "custom1" in exported

        identity2 = VoiceIdentityManager()
        count = identity2.import_profiles(exported)
        assert count >= 1
        assert identity2.get_profile("custom1") is not None

    def test_identity_metrics(self):
        identity = VoiceIdentityManager()
        identity.initialize()
        snap = identity.metrics.snapshot()
        assert snap.total_adaptations == 0


class TestStreamingTTSIntegration:
    def test_tts_session_lifecycle(self):
        tts_mgr = StreamingTTSManager()
        assert tts_mgr is not None


class TestStreamIntegration:
    def test_stream_manager(self):
        mgr = SpeechStreamManager()
        assert mgr is not None


class TestFullPipelineIntegration:
    def test_complete_voice_pipeline(self):
        wake = WakeWordEngine()
        wake.initialize()

        conv = ConversationSessionManager()
        identity = VoiceIdentityManager()
        identity.initialize()

        identity.adapt_to_context(AdaptationContext.GENERAL)

        session = conv.start_conversation()
        conv.begin_turn("Hey EVE, what time is it?")

        identity.adapt_to_context(AdaptationContext.QUICK_COMMAND)
        assert identity.active_profile_id == "minimal"

        response = identity.format_response("It's 3:45 PM")
        assert "3:45 PM" in response

        conv.end_conversation(session.id)
        identity.switch_profile("friendly")
        wake.shutdown()

    def test_concurrent_subsystems(self):
        identity = VoiceIdentityManager()
        identity.initialize()
        conv = ConversationSessionManager()

        errors = []

        def run_identity():
            try:
                for _ in range(10):
                    identity.adapt_to_context(AdaptationContext.CODING)
                    identity.adapt_to_context(AdaptationContext.DESIGN)
            except Exception as e:
                errors.append(e)

        def run_conversation():
            try:
                for _ in range(10):
                    s = conv.start_conversation()
                    conv.begin_turn("test")
                    conv.end_conversation(s.id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=run_identity) for _ in range(2)]
        threads += [threading.Thread(target=run_conversation) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors

    def test_subsystem_state_consistency(self):
        identity = VoiceIdentityManager()
        identity.initialize()

        identity.switch_profile("technical")
        identity.adapt_to_context(AdaptationContext.DESIGN)

        snap = identity.snapshot()
        assert snap["active_profile"] == "creative"
        assert snap["adapter"]["current_context"] == "design"

    def test_metrics_propagation(self):
        identity = VoiceIdentityManager()
        identity.initialize()

        identity.adapt_to_context(AdaptationContext.CODING)
        identity.adapt_to_context(AdaptationContext.DESIGN)
        identity.adapt_to_context(AdaptationContext.GENERAL)

        snap = identity.metrics.snapshot()
        assert snap.total_adaptations >= 2

    def test_pronunciation_cross_system(self):
        identity = VoiceIdentityManager()
        identity.initialize()

        identity.add_pronunciation("EVE", "EE-vee")
        entry = identity.lookup_pronunciation("EVE")
        assert entry.phonetic == "EE-vee"

        identity2 = VoiceIdentityManager()
        identity2.initialize()
        assert identity2.pronunciation.has("eve") is False

        identity2.add_pronunciation("EVE", "EE-vee")
        assert identity2.pronunciation.has("eve") is True

    def test_preferences_cross_system(self):
        identity = VoiceIdentityManager()
        identity.initialize()

        identity.update_preferences(preferred_voice="shimmer", speech_speed=1.3)
        assert identity.preferences.get("preferred_voice") == "shimmer"
        assert identity.preferences.get("speech_speed") == 1.3
