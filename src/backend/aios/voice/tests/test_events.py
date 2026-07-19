"""Unit tests for the Voice Event Publisher."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from aios.voice.events import VoiceEventPublisher
from aios.voice.models import VoiceEvent


@pytest.fixture
def event_bus():
    bus = MagicMock()
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def publisher(event_bus):
    return VoiceEventPublisher(event_bus)


@pytest.mark.asyncio
async def test_publish_listening_start(publisher, event_bus):
    await publisher.publish_listening_start("session-1", "mic-1")
    event_bus.publish.assert_called_once()
    args = event_bus.publish.call_args
    assert args[0][0] == "voice:listening:start"


@pytest.mark.asyncio
async def test_publish_listening_stop(publisher, event_bus):
    await publisher.publish_listening_stop("session-1")
    event_bus.publish.assert_called_once_with(
        "voice:listening:stop",
        {"session_id": "session-1", "reason": "manual"},
        source="voice",
    )


@pytest.mark.asyncio
async def test_publish_transcript_partial(publisher, event_bus):
    await publisher.publish_transcript_partial("session-1", "hello world", 0.8)
    event_bus.publish.assert_called_once_with(
        "voice:transcript:partial",
        {"session_id": "session-1", "text": "hello world", "confidence": 0.8},
        source="voice",
    )


@pytest.mark.asyncio
async def test_publish_transcript_final(publisher, event_bus):
    await publisher.publish_transcript_final("session-1", "hello world", 0.9)
    event_bus.publish.assert_called_once_with(
        "voice:transcript:final",
        {"session_id": "session-1", "text": "hello world", "confidence": 0.9},
        source="voice",
    )


@pytest.mark.asyncio
async def test_publish_speaking_start(publisher, event_bus):
    await publisher.publish_speaking_start("session-1", "utt-1")
    event_bus.publish.assert_called_once_with(
        "voice:speaking:start",
        {"session_id": "session-1", "utterance_id": "utt-1"},
        source="voice",
    )


@pytest.mark.asyncio
async def test_publish_speaking_stop(publisher, event_bus):
    await publisher.publish_speaking_stop("session-1", "utt-1", "completed")
    event_bus.publish.assert_called_once_with(
        "voice:speaking:stop",
        {"session_id": "session-1", "utterance_id": "utt-1", "reason": "completed"},
        source="voice",
    )


@pytest.mark.asyncio
async def test_publish_error(publisher, event_bus):
    await publisher.publish_error("session-1", "test error")
    event_bus.publish.assert_called_once_with(
        "voice:error",
        {"session_id": "session-1", "error": "test error"},
        source="voice",
    )


@pytest.mark.asyncio
async def test_publish_state_change(publisher, event_bus):
    await publisher.publish_state_change("session-1", "listening", "idle")
    event_bus.publish.assert_called_once_with(
        "voice:state:change",
        {"session_id": "session-1", "state": "listening", "previous_state": "idle"},
        source="voice",
    )


@pytest.mark.asyncio
async def test_publish_audio_level(publisher, event_bus):
    await publisher.publish_audio_level("session-1", 0.5)
    event_bus.publish.assert_called_once_with(
        "voice:audio:level",
        {"session_id": "session-1", "level": 0.5},
        source="voice",
    )


@pytest.mark.asyncio
async def test_all_event_names_defined():
    from aios.voice.events import (
        EVENT_LISTENING_START,
        EVENT_LISTENING_STOP,
        EVENT_TRANSCRIPT_PARTIAL,
        EVENT_TRANSCRIPT_FINAL,
        EVENT_SPEAKING_START,
        EVENT_SPEAKING_STOP,
        EVENT_ERROR,
        EVENT_STATE_CHANGE,
        EVENT_AUDIO_LEVEL,
    )
    assert EVENT_LISTENING_START == "voice:listening:start"
    assert EVENT_LISTENING_STOP == "voice:listening:stop"
    assert EVENT_TRANSCRIPT_PARTIAL == "voice:transcript:partial"
    assert EVENT_TRANSCRIPT_FINAL == "voice:transcript:final"
    assert EVENT_SPEAKING_START == "voice:speaking:start"
    assert EVENT_SPEAKING_STOP == "voice:speaking:stop"
    assert EVENT_ERROR == "voice:error"
    assert EVENT_STATE_CHANGE == "voice:state:change"
    assert EVENT_AUDIO_LEVEL == "voice:audio:level"
