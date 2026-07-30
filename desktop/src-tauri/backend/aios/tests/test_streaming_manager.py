"""Tests for the StreamingManager."""

import asyncio
import pytest
from aios.core.streaming_manager import StreamingManager, StreamAborted


@pytest.mark.asyncio
async def test_stream_basic():
    sm = StreamingManager()
    async def _gen():
        for c in "hello":
            yield c
    result = []
    async for token in sm.stream("test1", _gen()):
        result.append(token)
    assert "".join(result) == "hello"


@pytest.mark.asyncio
async def test_stream_cancel():
    sm = StreamingManager()
    async def _gen():
        yield "a"
        await asyncio.sleep(10)
        yield "b"
    collected = []
    async def read():
        async for t in sm.stream("test2", _gen()):
            collected.append(t)
    task = asyncio.create_task(read())
    await asyncio.sleep(0.01)
    sm.cancel("test2")
    await task
    assert "".join(collected) == "a"


@pytest.mark.asyncio
async def test_stream_timeout():
    sm = StreamingManager(default_timeout=0.05)
    async def _gen():
        await asyncio.sleep(10)
        yield "x"
    with pytest.raises(TimeoutError):
        async for _ in sm.stream("test3", _gen()):
            pass


@pytest.mark.asyncio
async def test_read_sse_lines():
    """Test SSE line parsing via StreamingManager.read_sse_lines."""
    import json

    class MockResponse:
        def __init__(self, lines):
            self._lines = lines
        async def aiter_lines(self):
            for l in self._lines:
                yield l

    resp = MockResponse([
        'data: {"choices": [{"delta": {"content": "Hello"}}]}',
        "",
        'data: {"choices": [{"delta": {"content": " world"}}]}',
        'data: [DONE]',
    ])
    chunks = []
    async for chunk in StreamingManager.read_sse_lines(resp):
        chunks.append(chunk)
    assert len(chunks) == 2
    assert chunks[0]["choices"][0]["delta"]["content"] == "Hello"


@pytest.mark.asyncio
async def test_extract_openai_chunk():
    chunk = {"choices": [{"delta": {"content": "Hello"}}]}
    assert StreamingManager.extract_openai_chunk(chunk) == "Hello"
    assert StreamingManager.extract_openai_chunk({}) == ""
    assert StreamingManager.extract_openai_chunk({"choices": []}) == ""


@pytest.mark.asyncio
async def test_extract_google_chunk():
    chunk = {"candidates": [{"content": {"parts": [{"text": "Hi"}]}}]}
    assert StreamingManager.extract_google_chunk(chunk) == "Hi"
    assert StreamingManager.extract_google_chunk({}) == ""


@pytest.mark.asyncio
async def test_stream_error_propagates():
    """Errors in the generator propagate to the caller."""
    sm = StreamingManager()
    async def _gen():
        yield "a"
        raise ConnectionError("drop")
    result = []
    with pytest.raises(ConnectionError):
        async for token in sm.stream("test_err", _gen()):
            result.append(token)
    assert "".join(result) == "a"


@pytest.mark.asyncio
async def test_stream_on_error_callback():
    """The on_error callback is invoked when an error occurs (error still propagates)."""
    sm = StreamingManager()
    errors = []
    async def _gen():
        yield "x"
        raise ValueError("stream error")
    with pytest.raises(ValueError):
        async for _ in sm.stream("test_cb", _gen(), on_error=lambda e: errors.append(e)):
            pass
    assert len(errors) == 1
    assert isinstance(errors[0], ValueError)


@pytest.mark.asyncio
async def test_stream_cancel_all():
    sm = StreamingManager()
    async def _gen():
        await asyncio.sleep(10)
        yield "x"
    task = asyncio.create_task(_collect(sm, "cid1", _gen))
    await asyncio.sleep(0.01)
    sm.cancel_all()
    await task


async def _collect(sm, sid, gen_fn):
    async for _ in sm.stream(sid, gen_fn()):
        pass


@pytest.mark.asyncio
async def test_is_active():
    sm = StreamingManager()
    async def _gen():
        await asyncio.sleep(10)
        yield "x"
    task = asyncio.create_task(_collect(sm, "active1", _gen))
    await asyncio.sleep(0.01)
    sm.cancel("active1")
    await task
    # After cancel + completion, is_active should be False
    assert not sm.is_active("active1")
