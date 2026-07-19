"""Unit tests for StreamManager."""

import pytest
from aios.conversation.stream import StreamManager


@pytest.mark.asyncio
class TestStreamManager:
    async def test_stream_success(self):
        async def token_gen():
            for char in "hello":
                yield char

        manager = StreamManager()
        events = []
        async for event in manager.stream("test-1", token_gen()):
            events.append(event)

        assert len(events) > 0
        assert events[-1]["type"] == "done"

    async def test_stream_cancellation(self):
        async def token_gen():
            for char in "hello world this is a long message":
                yield char

        manager = StreamManager()
        manager.cancel("test-cancel")

        events = []
        async for event in manager.stream("test-cancel", token_gen()):
            events.append(event)
            if len(events) == 1:
                break

    async def test_stream_retry_on_error(self):
        class FailingGenerator:
            def __init__(self):
                self.count = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                self.count += 1
                if self.count == 1:
                    return "token1"
                raise Exception("Stream error")

        manager = StreamManager()
        events = []
        async for event in manager.stream("test-retry", FailingGenerator(), max_retries=1):
            events.append(event)

        assert len(events) > 0
        assert any(e["type"] == "error" for e in events)

    def test_cancel_nonexistent_stream(self):
        manager = StreamManager()
        result = manager.cancel("nonexistent")
        assert result is False

    def test_is_active(self):
        manager = StreamManager()
        assert manager.is_active("nonexistent") is False
