"""Unit tests for the STT engine (mock provider)."""

import pytest
from aios.voice.stt import STTEngine
from aios.voice.models import STTProvider


@pytest.fixture
async def mock_stt():
    engine = STTEngine(provider=STTProvider.MOCK)
    await engine.initialize()
    yield engine
    await engine.cleanup()


@pytest.mark.asyncio
async def test_stt_initialization():
    engine = STTEngine(provider=STTProvider.MOCK)
    assert engine.provider == STTProvider.MOCK
    assert not engine.is_listening
    await engine.initialize()
    assert not engine.is_listening


@pytest.mark.asyncio
async def test_stt_start_stop_listening(mock_stt):
    assert not mock_stt.is_listening
    await mock_stt.start_listening()
    assert mock_stt.is_listening
    await mock_stt.stop_listening()
    assert not mock_stt.is_listening


@pytest.mark.asyncio
async def test_stt_recognize_once_mock(mock_stt):
    result = await mock_stt.recognize_once(timeout=1.0, phrase_time_limit=2.0)
    assert result.text == ""
    assert result.confidence == 0.0
    assert not result.is_final


@pytest.mark.asyncio
async def test_stt_recognize_stream_mock(mock_stt):
    await mock_stt.start_listening()
    transcripts = []
    async for t in mock_stt.recognize_stream():
        transcripts.append(t)
        if t.status.value == "final":
            break
        if len(transcripts) > 3:
            break
    await mock_stt.stop_listening()
    assert len(transcripts) >= 1
    assert transcripts[-1].status.value == "final"


@pytest.mark.asyncio
async def test_stt_get_devices(mock_stt):
    devices = await mock_stt.get_available_devices()
    assert len(devices) > 0
    assert any(d.is_default for d in devices)


@pytest.mark.asyncio
async def test_stt_update_config(mock_stt):
    mock_stt.update_config({"language": "fr-FR", "input_device": "test"})
    assert mock_stt._language == "fr-FR"
    assert mock_stt._input_device == "test"


@pytest.mark.asyncio
async def test_stt_double_start(mock_stt):
    await mock_stt.start_listening()
    await mock_stt.start_listening()
    assert mock_stt.is_listening
    await mock_stt.stop_listening()


@pytest.mark.asyncio
async def test_stt_cleanup(mock_stt):
    await mock_stt.start_listening()
    await mock_stt.cleanup()
    assert not mock_stt.is_listening
    assert mock_stt._recognizer is None
