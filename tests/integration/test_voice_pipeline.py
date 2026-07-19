"""Integration tests for the Voice Pipeline — end-to-end flow with mock components."""

import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock

from aios.voice.models import VoiceConfig, STTProvider, TTSProvider
from aios.voice.stt import STTEngine
from aios.voice.tts import TTSEngine
from aios.voice.session import VoiceSession
from aios.voice.pipeline import VoicePipeline
from aios.voice.events import VoiceEventPublisher
from aios.core.event_bus import EventBus


@pytest.fixture
async def event_bus():
    bus = EventBus()
    await bus.start()
    yield bus
    await bus.stop()


@pytest.fixture
async def integration_pipeline(event_bus):
    stt = STTEngine(provider=STTProvider.MOCK)
    tts = TTSEngine(provider=TTSProvider.MOCK)
    await stt.initialize()
    await tts.initialize()

    conv_service = AsyncMock()
    conv_service.create_conversation = AsyncMock(return_value=MagicMock(id="conv-int-1"))
    conv_service.send_message = AsyncMock(return_value=MagicMock(
        id="msg-int-1",
        conversation_id="conv-int-1",
        content="Integration test response from Eve.",
        role=MagicMock(value="assistant"),
    ))

    async def stream_mock(conv_id, content):
        yield {"type": "status", "data": {"status": "processing"}}
        yield {"type": "token", "data": {"text": "Integration"}}
        yield {"type": "token", "data": {"text": " test"}}
        yield {"type": "token", "data": {"text": " response"}}
        yield {"type": "final_response", "data": {"content": "Integration test response from Eve."}}
        yield {"type": "done", "data": {}}

    conv_service.stream_message = stream_mock

    events = VoiceEventPublisher(event_bus)
    config = VoiceConfig(stt_provider=STTProvider.MOCK, tts_provider=TTSProvider.MOCK)
    session = VoiceSession(stt, tts, conv_service, events, config)
    await session.start_session()

    pipeline = VoicePipeline(session, stt, tts, conv_service, events)
    yield pipeline

    await pipeline.cleanup()
    await stt.cleanup()
    await tts.cleanup()


@pytest.mark.asyncio
async def test_voice_session_full_lifecycle(integration_pipeline):
    pipeline = integration_pipeline
    session = pipeline._session

    assert session.state.session_id
    assert session.state.conversation_id

    await session.start_listening()
    assert session.is_listening

    text = await session.stop_listening()
    assert not session.is_listening


@pytest.mark.asyncio
async def test_voice_send_and_speak(integration_pipeline):
    pipeline = integration_pipeline
    session = pipeline._session

    result = await session.send_text_message("What can you do?")
    assert "error" not in result
    assert "Integration test response" in result.get("content", "")


@pytest.mark.asyncio
async def test_voice_barge_in_during_speech(integration_pipeline):
    pipeline = integration_pipeline
    session = pipeline._session

    await session.start_speaking("This is a long message that should be interrupted.")
    assert session.is_speaking

    await session.barge_in()
    assert not session.is_speaking
    assert session.state.state.value == "idle"


@pytest.mark.asyncio
async def test_voice_events_published(event_bus, integration_pipeline):
    received_events = []

    async def collector(event):
        received_events.append(event.type)

    await event_bus.subscribe("voice:listening:start", collector)
    await event_bus.subscribe("voice:listening:stop", collector)
    await event_bus.subscribe("voice:speaking:start", collector)
    await event_bus.subscribe("voice:speaking:stop", collector)
    await event_bus.subscribe("voice:state:change", collector)
    await event_bus.subscribe("voice:error", collector)

    session = integration_pipeline._session
    await session.start_listening()
    await session.stop_listening()
    await session.start_speaking("Hi")
    await asyncio.sleep(0.5)
    await session.stop_speaking()

    await asyncio.sleep(0.5)

    assert "voice:listening:start" in received_events
    assert "voice:listening:stop" in received_events
    assert "voice:speaking:start" in received_events
    assert "voice:speaking:stop" in received_events


@pytest.mark.asyncio
async def test_voice_event_bus_integration(event_bus):
    events = VoiceEventPublisher(event_bus)
    received = []

    async def collector(event):
        received.append(event.type)

    await event_bus.subscribe("voice:listening:start", collector)
    await event_bus.subscribe("voice:listening:stop", collector)
    await event_bus.subscribe("voice:transcript:partial", collector)
    await event_bus.subscribe("voice:transcript:final", collector)

    await events.publish_listening_start("test-session", "mic-1")
    await events.publish_listening_stop("test-session", "timeout")
    await events.publish_transcript_partial("test-session", "hello", 0.8)
    await events.publish_transcript_final("test-session", "hello world", 0.9)

    await asyncio.sleep(0.3)

    assert "voice:listening:start" in received
    assert "voice:listening:stop" in received
    assert "voice:transcript:partial" in received
    assert "voice:transcript:final" in received


@pytest.mark.asyncio
async def test_voice_streaming_transcript(integration_pipeline):
    session = integration_pipeline._session

    events = []
    async for e in session.process_transcript("Hello"):
        events.append(e)

    assert len(events) > 0


@pytest.mark.asyncio
async def test_voice_conversation_synchronization(integration_pipeline):
    pipeline = integration_pipeline
    session = pipeline._session

    session.set_conversation("custom-conv-id")
    assert session.conversation_id == "custom-conv-id"

    result = await session.send_text_message("Sync test")
    assert result.get("conversation_id") == "conv-int-1"
