"""Tests for HistoryManager."""

import pytest
from aios.conversation.history import HistoryManager
from aios.conversation.models import Message, MessageRole


class TestHistoryManager:
    def test_init_defaults(self):
        hm = HistoryManager()
        assert hm._max_context_messages == 50
        assert hm._max_context_tokens == 8000

    def test_init_custom(self):
        hm = HistoryManager(max_context_messages=20, max_context_tokens=4000)
        assert hm._max_context_messages == 20
        assert hm._max_context_tokens == 4000

    @pytest.mark.asyncio
    async def test_get_history(self):
        hm = HistoryManager()
        msgs = [Message(role=MessageRole.USER, content=f"msg {i}") for i in range(10)]
        history = await hm.get_history(msgs, limit=5)
        assert len(history) == 5
        assert history[0].content == "msg 5"

    @pytest.mark.asyncio
    async def test_get_history_no_limit(self):
        hm = HistoryManager()
        msgs = [Message(role=MessageRole.USER, content=f"msg {i}") for i in range(10)]
        history = await hm.get_history(msgs)
        assert len(history) == 10

    @pytest.mark.asyncio
    async def test_get_history_limit_larger_than_list(self):
        hm = HistoryManager()
        msgs = [Message(role=MessageRole.USER, content="test")]
        history = await hm.get_history(msgs, limit=100)
        assert len(history) == 1


class TestBuildContextWindow:
    @pytest.mark.asyncio
    async def test_build_context_window_no_memories(self):
        hm = HistoryManager(max_context_messages=50)
        msgs = [Message(role=MessageRole.USER, content=f"msg {i}") for i in range(5)]
        window = await hm.build_context_window(msgs)
        assert len(window) == 5

    @pytest.mark.asyncio
    async def test_build_context_window_with_memories(self):
        hm = HistoryManager()
        msgs = [Message(role=MessageRole.USER, content="Hello")]
        memories = [type("Mem", (), {"content": "User likes Python"})()]
        window = await hm.build_context_window(msgs, relevant_memories=memories)
        assert len(window) == 2
        assert window[0].role == MessageRole.SYSTEM
        assert "User likes Python" in window[0].content

    @pytest.mark.asyncio
    async def test_build_context_window_trims(self):
        hm = HistoryManager(max_context_messages=5)
        msgs = [Message(role=MessageRole.USER, content=f"msg {i}") for i in range(20)]
        window = await hm.build_context_window(msgs)
        assert len(window) <= 5

    @pytest.mark.asyncio
    async def test_build_context_window_preserves_system_messages(self):
        hm = HistoryManager(max_context_messages=3)
        msgs = [
            Message(role=MessageRole.SYSTEM, content="system"),
            Message(role=MessageRole.USER, content="user 1"),
            Message(role=MessageRole.USER, content="user 2"),
            Message(role=MessageRole.USER, content="user 3"),
            Message(role=MessageRole.USER, content="user 4"),
        ]
        window = await hm.build_context_window(msgs)
        system_msgs = [m for m in window if m.role == MessageRole.SYSTEM]
        assert len(system_msgs) == 1

    @pytest.mark.asyncio
    async def test_build_context_window_no_memories_empty(self):
        hm = HistoryManager()
        window = await hm.build_context_window([])
        assert window == []

    @pytest.mark.asyncio
    async def test_build_context_window_with_empty_memories(self):
        hm = HistoryManager()
        msgs = [Message(role=MessageRole.USER, content="Hello")]
        window = await hm.build_context_window(msgs, relevant_memories=[])
        assert len(window) == 1
        assert window[0].role == MessageRole.USER


class TestTrimMessages:
    def test_no_trim_needed(self):
        hm = HistoryManager(max_context_messages=10)
        msgs = [Message(role=MessageRole.USER, content=f"msg {i}") for i in range(5)]
        trimmed = hm._trim_messages(msgs)
        assert len(trimmed) == 5

    def test_trims_to_max(self):
        hm = HistoryManager(max_context_messages=5)
        msgs = [Message(role=MessageRole.USER, content=f"msg {i}") for i in range(20)]
        trimmed = hm._trim_messages(msgs)
        assert len(trimmed) == 5
        assert trimmed[-1].content == "msg 19"

    def test_keeps_most_recent(self):
        hm = HistoryManager(max_context_messages=3)
        msgs = [Message(role=MessageRole.USER, content=f"msg {i}") for i in range(10)]
        trimmed = hm._trim_messages(msgs)
        assert trimmed[-1].content == "msg 9"
        assert trimmed[0].content == "msg 7"


class TestFormatMemories:
    def test_empty_memories(self):
        hm = HistoryManager()
        result = hm._format_memories([])
        assert result == ""

    def test_with_memories(self):
        hm = HistoryManager()
        memories = [type("Mem", (), {"content": "test memory"})()]
        result = hm._format_memories(memories)
        assert "test memory" in result

    def test_memory_limit(self):
        hm = HistoryManager()
        memories = [type("Mem", (), {"content": f"memory {i}"}) for i in range(10)]
        result = hm._format_memories(memories)
        assert result.count("memory") <= 5

    def test_memory_header_present(self):
        hm = HistoryManager()
        memories = [type("Mem", (), {"content": "test"})()]
        result = hm._format_memories(memories)
        assert "Relevant context" in result


class TestEstimateTokens:
    @pytest.mark.asyncio
    async def test_estimate_tokens_empty(self):
        hm = HistoryManager()
        count = await hm.estimate_tokens([])
        assert count == 0

    @pytest.mark.asyncio
    async def test_estimate_tokens_single_message(self):
        hm = HistoryManager()
        msg = Message(role=MessageRole.USER, content="hello world")
        count = await hm.estimate_tokens([msg])
        # 2 words * 1.5 + 10 overhead = 13
        assert count == 13

    @pytest.mark.asyncio
    async def test_estimate_tokens_multiple_messages(self):
        hm = HistoryManager()
        msgs = [
            Message(role=MessageRole.USER, content="hello world"),
            Message(role=MessageRole.ASSISTANT, content="hi there"),
        ]
        count = await hm.estimate_tokens(msgs)
        # Each msg: 2 words * 1.5 + 10 = 13, so 26 total
        assert count == 26

    @pytest.mark.asyncio
    async def test_estimate_tokens_long_message(self):
        hm = HistoryManager()
        msg = Message(role=MessageRole.USER, content="a " * 100)
        count = await hm.estimate_tokens([msg])
        # 100 words * 1.5 + 10 = 160
        assert count == 160
