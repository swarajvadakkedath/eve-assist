"""Unit tests for the Voice Pipeline."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from aios.voice.pipeline import VoicePipeline
from aios.voice.session import VoiceSession
from aios.voice.models import VoiceConfig, STTProvider, TTSProvider
from aios.voice.stt import STTEngine
from aios.voice.tts import TTSEngine
from aios.voice.events import VoiceEventPublisher


@pytest.fixture
async def pipeline():
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
    await session.start_session()

    pipe = VoicePipeline(session, stt, tts, conv_service, events)
    yield pipe

    await pipe.cleanup()


@pytest.mark.asyncio
async def test_pipeline_process_voice_input_empty(pipeline):
    events = []
    async for e in pipeline.process_voice_input(""):
        events.append(e)
    assert len(events) == 0


@pytest.mark.asyncio
async def test_pipeline_process_and_speak(pipeline):
    result = await pipeline.process_and_speak("Hello")
    assert "error" not in result
    assert result.get("content") == "Test response"


@pytest.mark.asyncio
async def test_pipeline_process_and_speak_empty(pipeline):
    result = await pipeline.process_and_speak("")
    assert "error" in result


@pytest.mark.asyncio
async def test_pipeline_cleanup(pipeline):
    await pipeline.cleanup()
    # Should not throw
    assert True
