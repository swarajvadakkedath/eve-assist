"""Tests for ConversationSearch."""

import pytest
from aios.conversation.search import ConversationSearch, SearchResult
from aios.conversation.models import Conversation, Message, MessageRole, ToolCall


class TestConversationSearch:
    @pytest.mark.asyncio
    async def test_search_empty_index(self):
        searcher = ConversationSearch()
        results = await searcher.search("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_empty_query(self):
        searcher = ConversationSearch()
        conv = Conversation(title="Test")
        msg = Message(role=MessageRole.USER, content="Hello")
        await searcher.index_conversation(conv, [msg])
        results = await searcher.search("")
        assert results == []
        results = await searcher.search("   ")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_exact_match_title(self):
        searcher = ConversationSearch()
        conv = Conversation(title="Python Tips")
        msg = Message(role=MessageRole.USER, content="How do I use Python?")
        await searcher.index_conversation(conv, [msg])
        results = await searcher.search("Python")
        assert len(results) > 0
        assert results[0].conversation_title == "Python Tips"
        assert results[0].score >= 10.0

    @pytest.mark.asyncio
    async def test_search_content_match(self):
        searcher = ConversationSearch()
        conv = Conversation(title="General")
        msg = Message(role=MessageRole.USER, content="I love programming in Python")
        await searcher.index_conversation(conv, [msg])
        results = await searcher.search("programming")
        assert len(results) > 0
        assert "programming" in results[0].content.lower()

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self):
        searcher = ConversationSearch()
        conv = Conversation(title="Test")
        msg = Message(role=MessageRole.USER, content="Hello World")
        await searcher.index_conversation(conv, [msg])
        results = await searcher.search("hello")
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_search_multiple_conversations(self):
        searcher = ConversationSearch()
        conv1 = Conversation(title="Chat 1")
        conv2 = Conversation(title="Chat 2")
        await searcher.index_conversation(conv1, [Message(role=MessageRole.USER, content="Python is great")])
        await searcher.index_conversation(conv2, [Message(role=MessageRole.USER, content="Java is also good")])
        results = await searcher.search("Python")
        python_results = [r for r in results if r.conversation_id == conv1.id]
        assert len(python_results) >= 1
        results = await searcher.search("Java")
        java_results = [r for r in results if r.conversation_id == conv2.id]
        assert len(java_results) >= 1

    @pytest.mark.asyncio
    async def test_search_returns_snippets(self):
        searcher = ConversationSearch()
        conv = Conversation(title="Test")
        long_content = "This is a very long message that should be snipped for display in search results properly"
        msg = Message(role=MessageRole.USER, content=long_content)
        await searcher.index_conversation(conv, [msg])
        results = await searcher.search("snipped")
        assert len(results) > 0
        assert len(results[0].snippet) <= len(long_content) + 6

    @pytest.mark.asyncio
    async def test_search_by_conversations(self):
        searcher = ConversationSearch()
        convs = [
            Conversation(title="First Chat"),
            Conversation(title="Second Chat"),
        ]
        msgs_by_id = {
            convs[0].id: [Message(role=MessageRole.USER, content="Hello Python")],
            convs[1].id: [Message(role=MessageRole.USER, content="Hello World")],
        }
        results = await searcher.search_conversations("Python", convs, msgs_by_id)
        python_results = [r for r in results if r.conversation_id == convs[0].id]
        assert len(python_results) >= 1
        if python_results:
            assert python_results[0].conversation_id == convs[0].id

    @pytest.mark.asyncio
    async def test_search_conversations_empty_query(self):
        searcher = ConversationSearch()
        results = await searcher.search_conversations("", [], {})
        assert results == []

    @pytest.mark.asyncio
    async def test_clear_index_specific(self):
        searcher = ConversationSearch()
        conv = Conversation(title="Test")
        msg = Message(role=MessageRole.USER, content="Test content")
        await searcher.index_conversation(conv, [msg])
        results = await searcher.search("Test")
        assert len(results) > 0
        await searcher.clear_index(conv.id)
        results = await searcher.search("Test")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_clear_index_all(self):
        searcher = ConversationSearch()
        conv1 = Conversation(title="Chat 1")
        conv2 = Conversation(title="Chat 2")
        await searcher.index_conversation(conv1, [Message(role=MessageRole.USER, content="Hello")])
        await searcher.index_conversation(conv2, [Message(role=MessageRole.USER, content="World")])
        await searcher.clear_index()
        results = await searcher.search("Hello")
        assert len(results) == 0
        results = await searcher.search("World")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_multiple_messages_in_conversation(self):
        searcher = ConversationSearch()
        conv = Conversation(title="Multi Message")
        msgs = [
            Message(role=MessageRole.USER, content="First message"),
            Message(role=MessageRole.ASSISTANT, content="Response to first"),
            Message(role=MessageRole.USER, content="Second question"),
        ]
        await searcher.index_conversation(conv, msgs)
        results = await searcher.search("First")
        assert len(results) >= 1
        results = await searcher.search("Second")
        assert len(results) >= 1

    def test_search_result_dataclass(self):
        result = SearchResult(
            conversation_id="conv-1",
            conversation_title="Test",
            message_id="msg-1",
            role="user",
            content="Hello world",
            snippet="...Hello...",
            score=10.0,
            highlights=[(6, 11)],
        )
        assert result.conversation_id == "conv-1"
        assert result.score == 10.0
        assert result.highlights == [(6, 11)]

    def test_calculate_score_multiple_factors(self):
        searcher = ConversationSearch()
        score = searcher._calculate_score("python", {
            "title": "Python Tips",
            "content": "I love python programming in python",
            "role": "user",
        })
        assert score > 10.0

    def test_calculate_score_title_start(self):
        searcher = ConversationSearch()
        score = searcher._calculate_score("python", {
            "title": "python tips",
            "content": "nothing relevant here",
            "role": "assistant",
        })
        assert score >= 15.0

    def test_calculate_score_user_bonus(self):
        searcher = ConversationSearch()
        score_user = searcher._calculate_score("test", {
            "title": "title",
            "content": "test content",
            "role": "user",
        })
        score_assistant = searcher._calculate_score("test", {
            "title": "title",
            "content": "test content",
            "role": "assistant",
        })
        assert score_user > score_assistant

    def test_find_highlights(self):
        searcher = ConversationSearch()
        highlights = searcher._find_highlights("python", "I love Python and python is great")
        assert len(highlights) == 2
        assert highlights[0] == (7, 13)

    def test_find_highlights_no_match(self):
        searcher = ConversationSearch()
        highlights = searcher._find_highlights("xyz", "hello world")
        assert highlights == []

    def test_build_snippet_with_highlights(self):
        searcher = ConversationSearch()
        snippet = searcher._build_snippet("a" * 50 + "Python" + "b" * 50, [(50, 56)], "Python")
        assert "Python" in snippet

    def test_build_snippet_without_highlights(self):
        searcher = ConversationSearch()
        snippet = searcher._build_snippet("This is a very long text " * 10, [], "very")
        assert "..." in snippet or "very" in snippet
