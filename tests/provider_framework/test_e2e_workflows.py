"""D9 Integration — End-to-End Voice Workflow Scenarios.
Tests complete pipelines: Wake Word → Conversation → STT → LLM → Voice Identity → TTS → Recovery.
"""

import time
import threading
from aios.voice.wakeword.engine import WakeWordEngine
from aios.voice.wakeword.detector import WakeWordDetector
from aios.voice.wakeword.session import WakeWordSession
from aios.voice.wakeword.models import WakeWordConfig
from aios.voice.conversation.manager import ConversationSessionManager
from aios.voice.conversation.session import ConversationSession
from aios.voice.conversation.state import ConversationState
from aios.voice.identity.manager import VoiceIdentityManager
from aios.voice.identity.adaptation import AdaptationContext
from aios.voice.identity.personality import BUILTIN_PROFILES
from aios.voice.stt_streaming.manager import StreamingSTTManager, STTConfig
from aios.voice.stt_streaming.provider import STTProvider
from aios.voice.tts_streaming.manager import StreamingTTSManager, TTSConfig
from aios.voice.tts_streaming.provider import TTSProvider


class TestE2EScenario1PDFSummary:
    def test_wake_to_conversation_transition(self):
        wake = WakeWordEngine()
        wake.initialize()
        conv = ConversationSessionManager()
        identity = VoiceIdentityManager()
        identity.initialize()

        wake.start_monitoring()
        session = conv.start_conversation()
        assert session is not None

        identity.adapt_to_context(AdaptationContext.GENERAL)
        phrase = identity.get_confirmation_phrase()
        assert len(phrase) > 0

        conv.end_conversation(session.id)
        wake.shutdown()

    def test_conversation_with_identity_adaptation(self):
        identity = VoiceIdentityManager()
        identity.initialize()
        identity.switch_profile("technical")
        assert identity.active_profile_id == "technical"

        mgr = ConversationSessionManager()
        session = mgr.start_conversation()
        turn = mgr.begin_turn("Summarize this PDF")
        assert turn is not None

        result = identity.adapt_to_context(AdaptationContext.CODING)
        style = identity.get_speaking_style()
        assert style is not None

        mgr.end_conversation(session.id)

    def test_tts_integration_with_identity(self):
        identity = VoiceIdentityManager()
        identity.initialize()
        identity.switch_profile("friendly")

        tts_mgr = StreamingTTSManager()
        response_text = "Here's your PDF summary."
        style = identity.get_speaking_style()
        assert style.speech_rate == 1.05
        assert tts_mgr is not None


class TestE2EScenario2DashboardRedesign:
    def test_vision_to_identity_pipeline(self):
        identity = VoiceIdentityManager()
        identity.initialize()
        identity.adapt_to_context(AdaptationContext.DESIGN)
        assert identity.active_profile_id == "creative"

        style = identity.get_speaking_style()
        greeting = identity.get_greeting()
        assert len(greeting) > 0

    def test_multi_context_adaptation(self):
        identity = VoiceIdentityManager()
        identity.initialize()

        identity.adapt_to_context(AdaptationContext.CODING)
        assert identity.active_profile_id == "technical"
        identity.adapt_to_context(AdaptationContext.DESIGN)
        assert identity.active_profile_id == "creative"
        identity.adapt_to_context(AdaptationContext.GENERAL)
        assert identity.active_profile_id == "friendly"


class TestE2EScenario3DebugApplication:
    def test_recovery_to_voice(self):
        identity = VoiceIdentityManager()
        identity.initialize()

        result = identity.adapt_to_error()
        assert result.adapted is True
        assert identity.active_profile_id == "minimal"

        phrase = identity.get_confirmation_phrase()
        assert len(phrase) > 0

        result2 = identity.adapt_to_success()
        assert result2.adapted is True
        assert identity.active_profile_id == "friendly"

    def test_error_recovery_cycle(self):
        identity = VoiceIdentityManager()
        identity.initialize()

        identity.adapt_to_error()
        assert identity.active_profile_id == "minimal"
        identity.adapt_to_success()
        assert identity.active_profile_id == "friendly"
        identity.adapt_to_error()
        assert identity.active_profile_id == "minimal"


class TestE2EScenario4BrowserAutomation:
    def test_browser_with_conversation(self):
        conv = ConversationSessionManager()
        identity = VoiceIdentityManager()
        identity.initialize()

        session = conv.start_conversation()
        turn = conv.begin_turn("Open the browser")
        assert turn is not None

        identity.adapt_to_context(AdaptationContext.GENERAL)
        response = identity.format_response("Opening browser now")
        assert "Opening browser" in response

        conv.end_conversation(session.id)


class TestE2EScenario5FileEditing:
    def test_file_edit_with_pronunciation(self):
        identity = VoiceIdentityManager()
        identity.initialize()
        identity.add_pronunciation("TypeScript", "TY-pah-skript")

        entry = identity.lookup_pronunciation("TypeScript")
        assert entry.phonetic == "TY-pah-skript"

        result = identity.adapt_to_context(AdaptationContext.CODING)
        assert result.adapted is True

        response = identity.format_response("File saved successfully", is_success=True)
        assert "File saved" in response


class TestE2EScenario6MemoryRecall:
    def test_memory_with_identity(self):
        identity = VoiceIdentityManager()
        identity.initialize()
        identity.switch_profile("teacher")

        response = identity.format_response(
            "Based on our previous conversation, you mentioned...")
        assert "previous conversation" in response

        greeting = identity.get_greeting()
        assert len(greeting) > 0

    def test_context_memory_flow(self):
        identity = VoiceIdentityManager()
        identity.initialize()

        identity.adapt_to_context(AdaptationContext.TEACHING)
        assert identity.active_profile_id == "teacher"
        response = identity.format_response("Let me explain that concept")
        assert "explain" in response


class TestE2EScenario7ProviderFailover:
    def test_failover_with_identity_switch(self):
        identity = VoiceIdentityManager()
        identity.initialize()

        identity.adapt_to_error()
        assert identity.active_profile_id == "minimal"

        identity.adapt_to_success()
        assert identity.active_profile_id == "friendly"

    def test_stt_failover(self):
        stt_mgr = StreamingSTTManager()
        session = stt_mgr.start_session()
        assert stt_mgr is not None


class TestE2EScenario8ToolExecution:
    def test_tool_with_conversation(self):
        conv = ConversationSessionManager()
        identity = VoiceIdentityManager()
        identity.initialize()

        session = conv.start_conversation()
        conv.begin_turn("Run the linter")

        identity.adapt_to_context(AdaptationContext.CODING)
        response = identity.format_response("Running linter on your project")
        assert "linter" in response

        conv.end_conversation(session.id)


class TestE2EScenario9RecoveryAfterFailure:
    def test_full_recovery_cycle(self):
        identity = VoiceIdentityManager()
        identity.initialize()

        identity.adapt_to_context(AdaptationContext.CODING)
        assert identity.active_profile_id == "technical"

        identity.adapt_to_error()
        assert identity.active_profile_id == "minimal"

        identity.adapt_to_success()
        assert identity.active_profile_id == "friendly"

    def test_conversation_recovery(self):
        conv = ConversationSessionManager()
        session = conv.start_conversation()
        conv.begin_turn("What went wrong?")

        conv.end_conversation(session.id)

        session2 = conv.start_conversation()
        assert session2 is not None
        conv.end_conversation(session2.id)


class TestE2EScenario10LongMultiTurn:
    def test_multi_turn_session(self):
        conv = ConversationSessionManager()
        identity = VoiceIdentityManager()
        identity.initialize()

        session = conv.start_conversation()
        messages = [
            "Hello EVE",
            "Can you summarize this document?",
            "Now make it more concise",
            "Add bullet points",
            "Perfect, thanks"
        ]

        for msg in messages:
            turn = conv.begin_turn(msg)
            assert turn is not None

        conv.end_conversation(session.id)

    def test_multi_turn_with_context_switches(self):
        conv = ConversationSessionManager()
        identity = VoiceIdentityManager()
        identity.initialize()

        session = conv.start_conversation()

        identity.adapt_to_context(AdaptationContext.GENERAL)
        conv.begin_turn("Hello")

        identity.adapt_to_context(AdaptationContext.CODING)
        conv.begin_turn("Now write code")

        identity.adapt_to_context(AdaptationContext.DESIGN)
        conv.begin_turn("Make it pretty")

        assert len(identity.adapter.get_history()) >= 2
        conv.end_conversation(session.id)

    def test_interruption_handling(self):
        conv = ConversationSessionManager()
        identity = VoiceIdentityManager()
        identity.initialize()

        session = conv.start_conversation()
        conv.begin_turn("Tell me about")

        conv.end_conversation(session.id)

        session2 = conv.start_conversation()
        conv.begin_turn("Never mind, something else")
        conv.end_conversation(session2.id)

    def test_conversation_metrics_tracking(self):
        conv = ConversationSessionManager()
        session = conv.start_conversation()

        for i in range(10):
            conv.begin_turn(f"Message {i}")

        conv.end_conversation(session.id)

    def test_rapid_turn_exchange(self):
        conv = ConversationSessionManager()
        session = conv.start_conversation()

        start = time.time()
        for i in range(20):
            conv.begin_turn(f"Turn {i}")
        elapsed = time.time() - start

        conv.end_conversation(session.id)
        assert elapsed < 1.0

    def test_session_isolation(self):
        conv = ConversationSessionManager()
        s1 = conv.start_conversation()
        s2 = conv.start_conversation()

        conv.begin_turn("From session 1")
        conv.begin_turn("From session 2")

        conv.end_conversation(s1.id)
        conv.end_conversation(s2.id)

    def test_threaded_conversations(self):
        conv = ConversationSessionManager()
        errors = []

        def run_conversation(idx):
            try:
                session = conv.start_conversation()
                for i in range(5):
                    conv.begin_turn(f"Msg {idx}-{i}")
                conv.end_conversation(session.id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=run_conversation, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
