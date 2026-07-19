"""Unit tests for ConversationManager."""

import pytest
from datetime import datetime

from aios.conversation.manager import ConversationManager
from aios.conversation.models import Message, MessageRole
from aios.conversation.exceptions import ConversationNotFoundError


class FakeAIRouter:
    async def route(self, request):
        return type("AIResponse", (), {
            "content": "This is a test response",
            "tokens_used": 10,
            "provider": "test",
            "model": "test-model",
            "cost": 0.0,
            "tool_calls": [],
        })()

    async def route_stream(self, request):
        for char in "test response":
            yield char


class FakeMemory:
    async def search(self, query, limit=10):
        return []

    async def store(self, memory):
        pass


class FakePlanner:
    async def create_plan(self, request, context=None):
        from aios.core.planner import Plan
        plan = Plan(request=request)
        plan.steps = []
        return plan

    async def execute_plan(self, plan):
        from aios.core.planner import PlanResult
        return PlanResult(success=True, plan=plan)


class FakeToolManager:
    async def list_tools(self):
        return []

    async def execute(self, tool_id, params):
        return type("ToolResult", (), {"success": True, "data": {}, "error": None, "duration": 0.0})()


class FakeContextEngine:
    async def get_active_app(self):
        return "test-app"

    async def get_active_file(self):
        return None

    async def detect_project(self):
        return None


@pytest.fixture
def manager():
    return ConversationManager(
        ai_router=FakeAIRouter(),
        memory_system=FakeMemory(),
        planner=FakePlanner(),
        tool_manager=FakeToolManager(),
        context_engine=FakeContextEngine(),
    )


class TestConversationManager:
    @pytest.mark.asyncio
    async def test_create_conversation(self, manager):
        conv = await manager.create_conversation(title="Test")
        assert conv.id
        assert conv.title == "Test"

    @pytest.mark.asyncio
    async def test_get_conversation(self, manager):
        created = await manager.create_conversation(title="Test")
        fetched = await manager.get_conversation(created.id)
        assert fetched.id == created.id

    @pytest.mark.asyncio
    async def test_get_conversation_not_found(self, manager):
        with pytest.raises(ConversationNotFoundError):
            await manager.get_conversation("nonexistent")

    @pytest.mark.asyncio
    async def test_list_conversations(self, manager):
        await manager.create_conversation(title="First")
        await manager.create_conversation(title="Second")
        convs = await manager.list_conversations()
        assert len(convs) >= 2

    @pytest.mark.asyncio
    async def test_delete_conversation(self, manager):
        conv = await manager.create_conversation(title="Delete Me")
        await manager.delete_conversation(conv.id)
        with pytest.raises(ConversationNotFoundError):
            await manager.get_conversation(conv.id)

    @pytest.mark.asyncio
    async def test_rename_conversation(self, manager):
        conv = await manager.create_conversation(title="Old Name")
        renamed = await manager.rename_conversation(conv.id, "New Name")
        assert renamed.title == "New Name"

    @pytest.mark.asyncio
    async def test_send_message(self, manager):
        conv = await manager.create_conversation(title="Chat")
        response = await manager.send_message(conv.id, "Hello")
        assert response.role == MessageRole.ASSISTANT
        assert response.content

    @pytest.mark.asyncio
    async def test_get_history(self, manager):
        conv = await manager.create_conversation(title="History")
        await manager.send_message(conv.id, "Message 1")
        await manager.send_message(conv.id, "Message 2")
        history = await manager.get_history(conv.id)
        assert len(history) >= 4

    @pytest.mark.asyncio
    async def test_clear_history(self, manager):
        conv = await manager.create_conversation(title="Clear")
        await manager.send_message(conv.id, "Test")
        await manager.clear_history(conv.id)
        history = await manager.get_history(conv.id)
        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_stream_message(self, manager):
        conv = await manager.create_conversation(title="Stream")
        events = []
        async for event in manager.stream_message(conv.id, "Hello"):
            events.append(event)
        assert len(events) > 0
