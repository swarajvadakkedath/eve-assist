"""Tests for StreamManager."""

import asyncio
import pytest
from aios.conversation.stream import StreamManager
from aios.conversation.exceptions import StreamError


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
        token_events = [e for e in events if e["type"] == "token"]
        assert len(token_events) == 5
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

        assert "status" in events[0]["type"] or "done" in events[-1]["type"]

    async def test_stream_cancel_mid_stream(self):
        async def token_gen():
            for char in "abcdefghij":
                yield char

        manager = StreamManager()
        events = []
        async for event in manager.stream("test-mid-cancel", token_gen()):
            events.append(event)
            if len(events) == 3:
                manager.cancel("test-mid-cancel")

        assert len(events) < 12

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

    async def test_stream_max_retries_exhausted(self):
        class AlwaysFailing:
            def __aiter__(self):
                return self

            async def __anext__(self):
                raise Exception("Persistent failure")

        manager = StreamManager()
        events = []
        async for event in manager.stream("test-max-retry", AlwaysFailing(), max_retries=2):
            events.append(event)

        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) >= 1
        assert error_events[-1]["data"].get("recoverable") is False

    async def test_stream_retry_then_success(self):
        class EventuallySucceeds:
            def __init__(self):
                self.count = 0
                self.tokens = iter(["a", "b", "c"])

            def __aiter__(self):
                return self

            async def __anext__(self):
                self.count += 1
                if self.count <= 2:
                    raise Exception("Transient error")
                try:
                    return next(self.tokens)
                except StopIteration:
                    raise StopAsyncIteration

        manager = StreamManager()
        events = []
        async for event in manager.stream("test-retry-ok", EventuallySucceeds(), max_retries=3):
            events.append(event)

        assert events[-1]["type"] == "done"

    async def test_stream_empty_generator(self):
        async def empty_gen():
            return
            yield

        manager = StreamManager()
        events = []
        async for event in manager.stream("test-empty", empty_gen()):
            events.append(event)

        assert len(events) == 1
        assert events[0]["type"] == "done"

    def test_cancel_nonexistent_stream(self):
        manager = StreamManager()
        result = manager.cancel("nonexistent")
        assert result is False

    def test_is_active_no_stream(self):
        manager = StreamManager()
        assert manager.is_active("nonexistent") is False

    def test_cancel_twice(self):
        manager = StreamManager()
        manager.cancel("double-cancel")
        result = manager.cancel("double-cancel")
        assert result is False

    async def test_cancel_cleans_up(self):
        async def token_gen():
            for char in "test":
                yield char

        manager = StreamManager()
        async for _ in manager.stream("cleanup-test", token_gen()):
            pass

        assert manager.is_active("cleanup-test") is False
        assert manager.cancel("cleanup-test") is False

    async def test_asyncio_cancelled_error(self):
        async def cancelling_gen():
            for char in "abc":
                yield char
            raise asyncio.CancelledError()

        manager = StreamManager()
        events = []
        async for event in manager.stream("test-cancelled", cancelling_gen()):
            events.append(event)

        assert any("cancelled" in str(e) for e in events)
