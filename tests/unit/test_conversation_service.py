"""Tests for ConversationService."""

import pytest
from aios.conversation.service import ConversationService
from aios.conversation.manager import ConversationManager
from aios.conversation.models import Message, MessageRole
from aios.conversation.exceptions import ConversationNotFoundError, AIProviderError


class FakeEventBus:
    def __init__(self):
        self.events = []

    async def publish(self, event_type, data):
        self.events.append((event_type, data))


class FakeAIRouter:
    async def route(self, request):
        return type("AIResponse", (), {
            "content": "Test response",
            "tokens_used": 10,
            "provider": "test",
            "model": "test-model",
            "cost": 0.0,
            "tool_calls": [],
        })()

    async def route_stream(self, request):
        for char in "streaming":
            yield char


class FakeMemory:
    async def search(self, query, limit=10):
        return []

    async def store(self, memory):
        pass


class FakePlanner:
    async def create_plan(self, request, context=None):
        return type("Plan", (), {"steps": [], "id": "plan-1"})()


class FakeToolManager:
    async def list_tools(self):
        return []


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


@pytest.fixture
def event_bus():
    return FakeEventBus()


@pytest.fixture
def service(manager, event_bus):
    return ConversationService(manager=manager, event_bus=event_bus)


@pytest.mark.asyncio
class TestConversationService:
    async def test_create_conversation(self, service, event_bus):
        conv = await service.create_conversation(title="Test")
        assert conv.id
        assert conv.title == "Test"
        assert ("conversation:created", {"id": conv.id, "title": conv.title}) in event_bus.events

    async def test_create_conversation_default_title(self, service):
        conv = await service.create_conversation()
        assert conv.title == "New Conversation"

    async def test_get_conversation(self, service):
        created = await service.create_conversation(title="Get Me")
        fetched = await service.get_conversation(created.id)
        assert fetched.id == created.id

    async def test_get_conversation_not_found(self, service):
        with pytest.raises(ConversationNotFoundError):
            await service.get_conversation("nonexistent")

    async def test_list_conversations(self, service):
        await service.create_conversation(title="A")
        await service.create_conversation(title="B")
        convs = await service.list_conversations()
        assert len(convs) >= 2

    async def test_delete_conversation(self, service, event_bus):
        conv = await service.create_conversation(title="Delete Me")
        await service.delete_conversation(conv.id)
        with pytest.raises(ConversationNotFoundError):
            await service.get_conversation(conv.id)
        assert ("conversation:deleted", {"id": conv.id}) in event_bus.events

    async def test_rename_conversation(self, service, event_bus):
        conv = await service.create_conversation(title="Old")
        renamed = await service.rename_conversation(conv.id, "New")
        assert renamed.title == "New"
        found_event = any(
            e[0] == "conversation:renamed" and e[1]["title"] == "New"
            for e in event_bus.events
        )
        assert found_event

    async def test_send_message(self, service, event_bus):
        conv = await service.create_conversation(title="Chat")
        response = await service.send_message(conv.id, "Hello")
        assert response.role == MessageRole.ASSISTANT
        assert response.content
        found_event = any(
            e[0] == "message:sent" and e[1]["conversation_id"] == conv.id
            for e in event_bus.events
        )
        assert found_event

    async def test_send_message_conversation_not_found(self, service):
        with pytest.raises(ConversationNotFoundError):
            await service.send_message("nonexistent", "Hello")

    async def test_stream_message(self, service):
        conv = await service.create_conversation(title="Stream")
        events = []
        async for event in service.stream_message(conv.id, "Hello"):
            events.append(event)
        assert len(events) > 0

    async def test_stream_message_not_found(self, service):
        events = []
        async for event in service.stream_message("nonexistent", "Hello"):
            events.append(event)
        assert len(events) == 1
        assert events[0]["type"] == "error"
        assert events[0]["data"]["recoverable"] is False

    async def test_get_history(self, service):
        conv = await service.create_conversation(title="History")
        await service.send_message(conv.id, "Msg 1")
        await service.send_message(conv.id, "Msg 2")
        history = await service.get_history(conv.id)
        assert len(history) >= 4

    async def test_clear_history(self, service, event_bus):
        conv = await service.create_conversation(title="Clear")
        await service.send_message(conv.id, "Test")
        await service.clear_history(conv.id)
        history = await service.get_history(conv.id)
        assert len(history) == 0
        assert ("conversation:history_cleared", {"id": conv.id}) in event_bus.events

    async def test_service_no_event_bus(self, manager):
        service = ConversationService(manager=manager, event_bus=None)
        conv = await service.create_conversation(title="No Bus")
        assert conv.id

    async def test_service_pagination(self, service):
        for i in range(5):
            await service.create_conversation(title=f"Chat {i}")
        first_page = await service.list_conversations(limit=2, offset=0)
        assert len(first_page) == 2
        second_page = await service.list_conversations(limit=2, offset=2)
        assert len(second_page) == 2
