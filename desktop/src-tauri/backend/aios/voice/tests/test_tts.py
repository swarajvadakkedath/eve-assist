"""Unit tests for the TTS engine (mock provider)."""

import asyncio

import pytest
from aios.voice.tts import TTSEngine
from aios.voice.models import TTSProvider


@pytest.fixture
async def mock_tts():
    engine = TTSEngine(provider=TTSProvider.MOCK)
    await engine.initialize()
    yield engine
    await engine.cleanup()


@pytest.mark.asyncio
async def test_tts_initialization():
    engine = TTSEngine(provider=TTSProvider.MOCK)
    assert engine.provider == TTSProvider.MOCK
    assert not engine.is_speaking
    await engine.initialize()
    assert not engine.is_speaking


@pytest.mark.asyncio
async def test_tts_speak(mock_tts):
    utterance_id = await mock_tts.speak("Hi")
    assert utterance_id
    await asyncio.sleep(0.15)
    assert not mock_tts.is_speaking


@pytest.mark.asyncio
async def test_tts_empty_text(mock_tts):
    result = await mock_tts.speak("")
    assert result == ""


@pytest.mark.asyncio
async def test_tts_stop(mock_tts):
    await mock_tts.speak("Testing stop functionality.")
    await mock_tts.stop()
    assert not mock_tts.is_speaking
    assert mock_tts._queue.qsize() == 0


@pytest.mark.asyncio
async def test_tts_voice_settings(mock_tts):
    mock_tts.set_voice("test-voice")
    assert mock_tts._voice_id == "test-voice"
    mock_tts.set_rate(200)
    assert mock_tts._rate == 200
    mock_tts.set_pitch(1.5)
    assert mock_tts._pitch == 1.5


@pytest.mark.asyncio
async def test_tts_get_voices(mock_tts):
    voices = await mock_tts.get_available_voices()
    assert len(voices) > 0


@pytest.mark.asyncio
async def test_tts_get_devices(mock_tts):
    devices = await mock_tts.get_available_devices()
    assert len(devices) > 0


@pytest.mark.asyncio
async def test_tts_update_config(mock_tts):
    mock_tts.update_config({"voice_id": "new-voice", "rate": 180, "pitch": 1.2})
    assert mock_tts._voice_id == "new-voice"
    assert mock_tts._rate == 180
    assert mock_tts._pitch == 1.2


@pytest.mark.asyncio
async def test_tts_is_processing(mock_tts):
    uid = await mock_tts.speak("Hi")
    assert uid
    assert mock_tts._queue.qsize() == 1
    assert not mock_tts.is_processing("nonexistent")
    await asyncio.sleep(0.3)
    assert not mock_tts.is_processing(uid)


@pytest.mark.asyncio
async def test_tts_queue_management(mock_tts):
    await mock_tts.speak("First")
    await mock_tts.speak("Second")
    await mock_tts.speak("Third")
    assert mock_tts._queue.qsize() == 3
    await mock_tts.stop()
    assert mock_tts._queue.qsize() == 0
