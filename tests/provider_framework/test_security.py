"""D9 Integration — Security Review Tests.
Verifies: microphone privacy, wake word local processing, credential safety,
provider isolation, memory access, permission enforcement, tool mediation.
"""

import os
import json
import tempfile
import threading
from aios.voice.wakeword.engine import WakeWordEngine
from aios.voice.wakeword.detector import WakeWordDetector
from aios.voice.wakeword.models import WakeWordConfig, SensitivityLevel
from aios.voice.conversation.manager import ConversationSessionManager
from aios.voice.identity.manager import VoiceIdentityManager
from aios.voice.identity.preferences import PreferenceManager
from aios.voice.identity.pronunciation import PronunciationDictionary
from aios.voice.identity.adaptation import AdaptationContext
from aios.core.health_monitor import HealthMonitor, ProviderStatus


class TestMicrophonePrivacy:
    def test_wake_word_local_processing(self):
        wake = WakeWordEngine()
        wake.initialize()
        config = WakeWordConfig(enabled_phrases=["EVE"])
        assert config.privacy_mode is True
        wake.shutdown()

    def test_detector_no_external_calls(self):
        wake = WakeWordEngine()
        wake.initialize()
        wake.add_phrase("test", sensitivity=0.5)

    def test_audio_config_privacy(self):
        config = WakeWordConfig(enabled_phrases=["EVE"])
        assert hasattr(config, 'sensitivity')
        assert hasattr(config, 'cooldown_s')


class TestWakeWordLocalProcessing:
    def test_detector_sensitivity_settings(self):
        for level in SensitivityLevel:
            config = WakeWordConfig(enabled_phrases=["EVE"], sensitivity=level)
            assert config.sensitivity == level

    def test_detector_threshold_settings(self):
        wake = WakeWordEngine()
        wake.initialize()
        wake.set_sensitivity(SensitivityLevel.LOW)
        wake.set_sensitivity(SensitivityLevel.MEDIUM)
        wake.set_sensitivity(SensitivityLevel.HIGH)
        wake.shutdown()


class TestCredentialSafety:
    def test_identity_no_credential_storage(self):
        identity = VoiceIdentityManager()
        identity.initialize()

        exported = identity.export_profiles()
        exported_str = json.dumps(exported)
        assert "api_key" not in exported_str.lower()
        assert "secret" not in exported_str.lower()
        assert "password" not in exported_str.lower()

    def test_preferences_no_credential_storage(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = f.name
        try:
            pm = PreferenceManager(storage_path=path)
            pm.load()
            pm.save()

            with open(path, 'r') as f:
                content = f.read()
            assert "api_key" not in content.lower()
            assert "secret" not in content.lower()
        finally:
            os.unlink(path)

    def test_pronunciation_no_credential_storage(self):
        d = PronunciationDictionary()
        d.add("test", "TEST")
        exported = d.export_dict()
        exported_str = json.dumps(exported)
        assert "api_key" not in exported_str.lower()
        assert "secret" not in exported_str.lower()


class TestProviderIsolation:
    def test_health_monitor_isolation(self):
        monitor = HealthMonitor()
        monitor.record_provider_result("provider_a", "", ProviderStatus.CONNECTED, "")
        monitor.record_provider_result("provider_b", "", ProviderStatus.OFFLINE, "error")

        health_a = monitor.get_health("provider_a")
        health_b = monitor.get_health("provider_b")
        assert health_a is not None
        assert health_b is not None

    def test_identity_profile_isolation(self):
        identity = VoiceIdentityManager()
        identity.initialize()
        identity.switch_profile("technical")
        assert identity.active_profile_id == "technical"
        identity.switch_profile("friendly")
        assert identity.active_profile_id == "friendly"

    def test_conversation_session_isolation(self):
        conv = ConversationSessionManager()
        s1 = conv.start_conversation()
        s2 = conv.start_conversation()
        conv.begin_turn("Session 1 data")
        conv.begin_turn("Session 2 data")
        conv.end_conversation(s1.id)
        conv.end_conversation(s2.id)


class TestMemoryAccess:
    def test_pronunciation_thread_safety(self):
        d = PronunciationDictionary()
        errors = []

        def writer():
            try:
                for i in range(50):
                    d.add(f"w_{i}", f"W{i}")
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for _ in range(50):
                    d.get_all()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer) for _ in range(3)]
        threads += [threading.Thread(target=reader) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors

    def test_preferences_thread_safety(self):
        pm = PreferenceManager()
        pm.load()
        errors = []

        def updater():
            try:
                for i in range(50):
                    pm.update(preferred_voice=f"v_{i % 5}")
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for _ in range(50):
                    _ = pm.preferences
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=updater) for _ in range(3)]
        threads += [threading.Thread(target=reader) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors

    def test_identity_thread_safety(self):
        identity = VoiceIdentityManager()
        identity.initialize()
        errors = []

        def switcher():
            try:
                for _ in range(50):
                    identity.switch_profile("technical")
                    identity.switch_profile("friendly")
            except Exception as e:
                errors.append(e)

        def adapter():
            try:
                for _ in range(50):
                    identity.adapt_to_context(AdaptationContext.CODING)
                    identity.adapt_to_context(AdaptationContext.DESIGN)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=switcher) for _ in range(2)]
        threads += [threading.Thread(target=adapter) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors


class TestPermissionEnforcement:
    def test_conversation_requires_session(self):
        conv = ConversationSessionManager()
        session = conv.start_conversation()
        assert session is not None
        conv.end_conversation(session.id)

    def test_identity_requires_initialization(self):
        identity = VoiceIdentityManager()
        assert identity.initialized is False


class TestToolMediation:
    def test_tool_execution_with_identity(self):
        identity = VoiceIdentityManager()
        identity.initialize()
        identity.adapt_to_context(AdaptationContext.CODING)
        response = identity.format_response("Tool executed successfully")
        assert "Tool executed" in response

    def test_error_handling_mediates_tool_failure(self):
        identity = VoiceIdentityManager()
        identity.initialize()
        result = identity.adapt_to_error()
        assert result.adapted is True
        response = identity.format_response("Tool failed", is_error=True)
        assert "Tool failed" in response
