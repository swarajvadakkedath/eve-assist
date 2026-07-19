"""Unit tests for voice data models."""

import pytest
from datetime import datetime

from aios.voice.models import (
    VoiceConfig,
    VoiceState,
    VoiceSessionState,
    STTProvider,
    TTSProvider,
    Transcript,
    TranscriptStatus,
    STTResult,
    TTSRequest,
    AudioDevice,
    VoiceEvent,
)


def test_stt_provider_enum():
    assert STTProvider.GOOGLE.value == "google"
    assert STTProvider.WHISPER.value == "whisper"
    assert STTProvider.SPHINX.value == "sphinx"
    assert STTProvider.AZURE.value == "azure"
    assert STTProvider.MOCK.value == "mock"


def test_tts_provider_enum():
    assert TTSProvider.PYTTSX3.value == "pyttsx3"
    assert TTSProvider.EDGE.value == "edge"
    assert TTSProvider.AZURE.value == "azure"
    assert TTSProvider.MOCK.value == "mock"


def test_voice_state_enum():
    assert VoiceState.IDLE.value == "idle"
    assert VoiceState.LISTENING.value == "listening"
    assert VoiceState.PROCESSING.value == "processing"
    assert VoiceState.SPEAKING.value == "speaking"
    assert VoiceState.ERROR.value == "error"


def test_transcript_creation():
    t = Transcript(text="hello", status=TranscriptStatus.PARTIAL, confidence=0.8)
    assert t.text == "hello"
    assert t.status == TranscriptStatus.PARTIAL
    assert t.confidence == 0.8
    assert not t.is_final
    assert t.timestamp is not None


def test_transcript_final():
    t = Transcript(text="hello", status=TranscriptStatus.FINAL)
    assert t.is_final


def test_transcript_defaults():
    t = Transcript()
    assert t.text == ""
    assert t.status == TranscriptStatus.PARTIAL
    assert not t.is_final


def test_voice_config_defaults():
    c = VoiceConfig()
    assert c.stt_provider == STTProvider.WHISPER
    assert c.tts_provider == TTSProvider.PYTTSX3
    assert c.language == "en-US"
    assert c.speaking_rate == 1.0
    assert c.pitch == 1.0
    assert c.push_to_talk_key == "v"
    assert not c.wake_word_enabled


def test_voice_config_custom():
    c = VoiceConfig(
        stt_provider=STTProvider.GOOGLE,
        tts_provider=TTSProvider.EDGE,
        language="fr-FR",
        speaking_rate=1.5,
        pitch=0.8,
    )
    assert c.stt_provider == STTProvider.GOOGLE
    assert c.tts_provider == TTSProvider.EDGE
    assert c.language == "fr-FR"
    assert c.speaking_rate == 1.5
    assert c.pitch == 0.8


def test_stt_result_defaults():
    r = STTResult()
    assert r.text == ""
    assert r.confidence == 0.0
    assert r.language == "en"
    assert not r.is_final
    assert r.error is None


def test_tts_request():
    r = TTSRequest(text="hello", voice_id="v1", rate=1.5, pitch=1.2)
    assert r.text == "hello"
    assert r.voice_id == "v1"
    assert r.rate == 1.5
    assert r.pitch == 1.2
    assert r.utterance_id


def test_audio_device():
    d = AudioDevice(id="mic1", name="Microphone Array", is_default=True)
    assert d.id == "mic1"
    assert d.name == "Microphone Array"
    assert d.is_default
    assert d.channels == 1
    assert d.sample_rate == 16000


def test_voice_event():
    e = VoiceEvent(event_type="test", session_id="s1", data={"key": "value"})
    assert e.event_type == "test"
    assert e.session_id == "s1"
    assert e.data == {"key": "value"}
    assert e.timestamp is not None


def test_voice_session_state_defaults():
    s = VoiceSessionState()
    assert s.session_id
    assert s.state == VoiceState.IDLE
    assert not s.is_listening
    assert not s.is_speaking
    assert s.audio_level == 0.0
    assert s.error is None
    assert s.started_at is not None


def test_voice_session_state_custom():
    s = VoiceSessionState(
        session_id="s1",
        conversation_id="c1",
        state=VoiceState.LISTENING,
        is_listening=True,
    )
    assert s.session_id == "s1"
    assert s.conversation_id == "c1"
    assert s.state == VoiceState.LISTENING
    assert s.is_listening


def test_transcript_status_enum():
    assert TranscriptStatus.PARTIAL.value == "partial"
    assert TranscriptStatus.FINAL.value == "final"


def test_voice_config_wake_word():
    c = VoiceConfig(wake_word_enabled=True, wake_word="hey eve")
    assert c.wake_word_enabled
    assert c.wake_word == "hey eve"


def test_stt_result_with_error():
    r = STTResult(text="", error="Could not understand audio", is_final=False)
    assert r.error == "Could not understand audio"
    assert not r.is_final
