"""Tests for TitleGenerator."""

import pytest
from aios.conversation.titles import TitleGenerator
from aios.conversation.models import Conversation, Message, MessageRole


class FakeAIRouter:
    def __init__(self):
        self.route_called = False

    async def route(self, request):
        self.route_called = True
        return type("AIResponse", (), {
            "content": '"Generated Title"',
            "tokens_used": 5,
        })()


class FakeFailingAIRouter:
    async def route(self, request):
        raise Exception("API error")


class TestTitleGenerator:
    @pytest.mark.asyncio
    async def test_ai_title_generation(self):
        router = FakeAIRouter()
        gen = TitleGenerator(ai_router=router)
        conv = Conversation(title="New Conversation")
        messages = [
            Message(role=MessageRole.USER, content="What is Python?"),
            Message(role=MessageRole.ASSISTANT, content="Python is a programming language"),
        ]
        title = await gen.generate_title(conv, messages)
        assert title == "Generated Title"
        assert router.route_called

    @pytest.mark.asyncio
    async def test_ai_title_generation_with_custom_title(self):
        router = FakeAIRouter()
        gen = TitleGenerator(ai_router=router)
        conv = Conversation(title="Custom Title", metadata={"title_is_custom": True})
        messages = [
            Message(role=MessageRole.USER, content="Hello"),
        ]
        title = await gen.generate_title(conv, messages)
        assert title is None
        assert not router.route_called

    @pytest.mark.asyncio
    async def test_fallback_when_no_ai_router(self):
        gen = TitleGenerator(ai_router=None)
        conv = Conversation(title="New Conversation")
        messages = [
            Message(role=MessageRole.USER, content="What is the meaning of life?"),
        ]
        title = await gen.generate_title(conv, messages)
        assert title is not None
        assert any(word in title for word in ["What", "meaning", "life"])

    @pytest.mark.asyncio
    async def test_fallback_when_ai_fails(self):
        router = FakeFailingAIRouter()
        gen = TitleGenerator(ai_router=router)
        conv = Conversation(title="New Conversation")
        messages = [
            Message(role=MessageRole.USER, content="Tell me a joke"),
        ]
        title = await gen.generate_title(conv, messages)
        assert title is not None
        assert "Tell me a joke" in title

    @pytest.mark.asyncio
    async def test_title_max_length(self):
        gen = TitleGenerator(ai_router=None)
        conv = Conversation(title="New Conversation")
        messages = [
            Message(role=MessageRole.USER, content="a" * 200),
        ]
        title = await gen.generate_title(conv, messages)
        assert len(title) <= 60

    @pytest.mark.asyncio
    async def test_no_user_messages(self):
        gen = TitleGenerator(ai_router=None)
        conv = Conversation(title="New Conversation")
        messages = [
            Message(role=MessageRole.ASSISTANT, content="Hello"),
        ]
        title = await gen.generate_title(conv, messages)
        assert title is None

    @pytest.mark.asyncio
    async def test_empty_messages(self):
        gen = TitleGenerator(ai_router=None)
        conv = Conversation(title="New Conversation")
        title = await gen.generate_title(conv, messages=[])
        assert title is None

    @pytest.mark.asyncio
    async def test_title_already_set_non_default(self):
        gen = TitleGenerator(ai_router=None)
        conv = Conversation(title="I Like Python", metadata={"title_is_custom": True})
        messages = [
            Message(role=MessageRole.USER, content="Hello"),
        ]
        title = await gen.generate_title(conv, messages)
        assert title is None

    @pytest.mark.asyncio
    async def test_fallback_title_short_message(self):
        gen = TitleGenerator(ai_router=None)
        conv = Conversation(title="New Conversation")
        messages = [
            Message(role=MessageRole.USER, content="Hi"),
        ]
        title = await gen.generate_title(conv, messages)
        assert title == "Hi"

    def test_clean_title_strips_quotes(self):
        gen = TitleGenerator()
        assert gen._clean_title('"Hello World"') == "Hello World"
        assert gen._clean_title("'Test Title'") == "Test Title"

    def test_clean_title_collapses_whitespace(self):
        gen = TitleGenerator()
        assert gen._clean_title("Hello    World") == "Hello World"

    def test_clean_title_truncates(self):
        gen = TitleGenerator()
        long = "x" * 100
        assert len(gen._clean_title(long)) == 60

    def test_clean_title_strips_whitespace(self):
        gen = TitleGenerator()
        assert gen._clean_title("  Hello  ") == "Hello"

    def test_fallback_title_truncates_to_max(self):
        gen = TitleGenerator()
        result = gen._fallback_title("a" * 100)
        assert len(result) <= 60

    def test_fallback_title_removes_special_chars(self):
        gen = TitleGenerator()
        result = gen._fallback_title("Hello! @World #$%")
        assert "!" not in result
        assert "@" not in result

    def test_fallback_title_few_words(self):
        gen = TitleGenerator()
        result = gen._fallback_title("Hello")
        assert result == "Hello"

    def test_fallback_title_many_words(self):
        gen = TitleGenerator()
        result = gen._fallback_title("a b c d e f g h i j")
        words = result.split()
        assert len(words) <= 5

    @pytest.mark.asyncio
    async def test_generate_title_sync(self):
        gen = TitleGenerator(ai_router=None)
        conv = Conversation(title="New Conversation")
        messages = [Message(role=MessageRole.USER, content="Hello World")]
        title = await gen.generate_title_sync(conv, messages)
        assert title is not None

    @pytest.mark.asyncio
    async def test_ai_title_short_response(self):
        router = FakeAIRouter()
        gen = TitleGenerator(ai_router=router)
        conv = Conversation(title="New Conversation")
        messages = [
            Message(role=MessageRole.USER, content="What is Python?"),
            Message(role=MessageRole.ASSISTANT, content="Python is a programming language"),
        ]
        title = await gen.generate_title(conv, messages)
        assert len(title) <= 60
