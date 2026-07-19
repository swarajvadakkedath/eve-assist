"""Unit tests for the Voice Session."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from aios.voice.session import VoiceSession
from aios.voice.models import VoiceConfig, STTProvider, TTSProvider
from aios.voice.stt import STTEngine
from aios.voice.tts import TTSEngine
from aios.voice.events import VoiceEventPublisher


@pytest.fixture
async def voice_session():
    stt = STTEngine(provider=STTProvider.MOCK)
    tts = TTSEngine(provider=TTSProvider.MOCK)
    await stt.initialize()
    await tts.initialize()

    conv_service = AsyncMock()
    conv_service.create_conversation = AsyncMock(return_value=MagicMock(id="conv-1"))
    conv_service.send_message = AsyncMock(return_value=MagicMock(
        id="msg-1",
        conversation_id="conv-1",
        content="Test response",
        role=MagicMock(value="assistant"),
    ))
    conv_service.stream_message = AsyncMock()

    event_bus = MagicMock()
    event_bus.publish = AsyncMock()
    events = VoiceEventPublisher(event_bus)

    config = VoiceConfig(stt_provider=STTProvider.MOCK, tts_provider=TTSProvider.MOCK)
    session = VoiceSession(stt, tts, conv_service, events, config)

    yield session

    await session.cleanup()


@pytest.mark.asyncio
async def test_session_start(voice_session):
    sid = await voice_session.start_session()
    assert sid
    assert voice_session.state.conversation_id


@pytest.mark.asyncio
async def test_session_start_listening(voice_session):
    await voice_session.start_session()
    assert not voice_session.is_listening
    await voice_session.start_listening()
    assert voice_session.is_listening
    assert voice_session.state.state.value == "listening"


@pytest.mark.asyncio
async def test_session_stop_listening(voice_session):
    await voice_session.start_session()
    await voice_session.start_listening()
    text = await voice_session.stop_listening()
    assert not voice_session.is_listening
    assert voice_session.state.state.value == "idle"


@pytest.mark.asyncio
async def test_session_speak(voice_session):
    await voice_session.start_session()
    uid = await voice_session.start_speaking("Hello world")
    assert uid
    assert voice_session.is_speaking
    await voice_session.stop_speaking()
    assert not voice_session.is_speaking


@pytest.mark.asyncio
async def test_session_barge_in(voice_session):
    await voice_session.start_session()
    await voice_session.start_speaking("Long text to speak")
    assert voice_session.is_speaking
    await voice_session.barge_in()
    assert not voice_session.is_speaking
    assert voice_session.state.state.value == "idle"


@pytest.mark.asyncio
async def test_session_send_text(voice_session):
    await voice_session.start_session()
    result = await voice_session.send_text_message("Hello")
    assert "error" not in result
    assert result.get("content") == "Test response"


@pytest.mark.asyncio
async def test_session_set_conversation(voice_session):
    await voice_session.start_session()
    voice_session.set_conversation("conv-2")
    assert voice_session.conversation_id == "conv-2"


@pytest.mark.asyncio
async def test_session_update_config(voice_session):
    await voice_session.start_session()
    new_config = VoiceConfig(
        stt_provider=STTProvider.MOCK,
        tts_provider=TTSProvider.MOCK,
        language="fr-FR",
        voice_id="new-voice",
    )
    voice_session.update_config(new_config)
    assert voice_session._config.language == "fr-FR"
    assert voice_session._config.voice_id == "new-voice"


@pytest.mark.asyncio
async def test_session_cleanup(voice_session):
    await voice_session.start_session()
    await voice_session.start_listening()
    await voice_session.start_speaking("Test")
    await voice_session.cleanup()
    assert not voice_session.is_listening
    assert not voice_session.is_speaking
    assert voice_session.state.state.value == "idle"
