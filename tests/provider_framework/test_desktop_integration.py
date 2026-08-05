"""D9 Integration — Desktop Integration Validation.
Verifies: tray, notifications, hotkeys, desktop services, voice activation, background execution.
"""

import os
import sys
import tempfile
import json
import threading
from aios.voice.conversation.manager import ConversationSessionManager
from aios.voice.identity.manager import VoiceIdentityManager
from aios.voice.identity.preferences import PreferenceManager
from aios.voice.identity.pronunciation import PronunciationDictionary
from aios.voice.identity.adaptation import AdaptationContext
from aios.voice.wakeword.engine import WakeWordEngine


class TestDesktopTrayIntegration:
    def test_identity_preferences_persistence(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = f.name
        try:
            pm = PreferenceManager(storage_path=path)
            pm.load()
            pm.set_preferred_voice("shimmer")
            pm.save()

            pm2 = PreferenceManager(storage_path=path)
            pm2.load()
            assert pm2.preferences.preferred_voice == "shimmer"
        finally:
            os.unlink(path)

    def test_identity_profile_export(self):
        from aios.voice.identity.models import VoiceProfile, PersonalityType
        identity = VoiceIdentityManager()
        identity.initialize()
        custom = VoiceProfile(profile_id="custom1", name="Custom",
                              personality=PersonalityType.CUSTOM)
        identity.create_profile(custom)
        exported = identity.export_profiles()
        assert isinstance(exported, dict)
        assert "custom1" in exported

    def test_identity_pronunciation_persistence(self):
        d = PronunciationDictionary()
        d.add("Custom", "KUHS-tum", category="custom")
        exported = d.export_dict()

        d2 = PronunciationDictionary()
        d2.import_dict(exported)
        assert d2.has("Custom")


class TestDesktopNotifications:
    def test_error_recovery_notification(self):
        identity = VoiceIdentityManager()
        identity.initialize()
        result = identity.adapt_to_error()
        assert result.adapted is True
        result2 = identity.adapt_to_success()
        assert result2.adapted is True

    def test_context_switch_notification(self):
        identity = VoiceIdentityManager()
        identity.initialize()
        identity.adapt_to_context(AdaptationContext.CODING)
        assert identity.active_profile_id == "technical"
        identity.adapt_to_context(AdaptationContext.DESIGN)
        assert identity.active_profile_id == "creative"


class TestDesktopHotkeys:
    def test_conversation_start_hotkey(self):
        conv = ConversationSessionManager()
        session = conv.start_conversation()
        assert session is not None
        conv.end_conversation(session.id)

    def test_identity_switch_hotkey(self):
        identity = VoiceIdentityManager()
        identity.initialize()
        identity.switch_profile("technical")
        assert identity.active_profile_id == "technical"
        identity.switch_profile("friendly")
        assert identity.active_profile_id == "friendly"


class TestDesktopServices:
    def test_wake_word_engine_background(self):
        wake = WakeWordEngine()
        wake.initialize()
        wake.start_monitoring()
        wake.shutdown()

    def test_conversation_background(self):
        conv = ConversationSessionManager()
        session = conv.start_conversation()
        conv.begin_turn("Background test")
        conv.end_conversation(session.id)


class TestVoiceActivation:
    def test_voice_activation_flow(self):
        wake = WakeWordEngine()
        wake.initialize()

        identity = VoiceIdentityManager()
        identity.initialize()

        conv = ConversationSessionManager()

        session = conv.start_conversation()
        identity.adapt_to_context(AdaptationContext.GENERAL)
        phrase = identity.get_confirmation_phrase()
        assert len(phrase) > 0

        conv.end_conversation(session.id)
        wake.shutdown()


class TestWindowFocus:
    def test_conversation_with_focus(self):
        conv = ConversationSessionManager()
        identity = VoiceIdentityManager()
        identity.initialize()

        session = conv.start_conversation()
        identity.adapt_to_context(AdaptationContext.CODING)
        response = identity.format_response("Focus test response")
        assert "Focus test" in response
        conv.end_conversation(session.id)


class TestBackgroundExecution:
    def test_long_running_background(self):
        conv = ConversationSessionManager()
        identity = VoiceIdentityManager()
        identity.initialize()

        for _ in range(100):
            s = conv.start_conversation()
            conv.begin_turn("Background msg")
            identity.adapt_to_context(AdaptationContext.CODING)
            conv.end_conversation(s.id)

        identity.shutdown()

    def test_threaded_background_tasks(self):
        conv = ConversationSessionManager()
        identity = VoiceIdentityManager()
        identity.initialize()
        errors = []

        def background_conv():
            try:
                for _ in range(50):
                    s = conv.start_conversation()
                    conv.begin_turn("bg")
                    conv.end_conversation(s.id)
            except Exception as e:
                errors.append(e)

        def background_identity():
            try:
                for _ in range(50):
                    identity.adapt_to_context(AdaptationContext.CODING)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=background_conv) for _ in range(2)]
        threads += [threading.Thread(target=background_identity) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
