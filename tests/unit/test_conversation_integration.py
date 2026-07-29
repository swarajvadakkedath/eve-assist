"""Integration tests for conversation module — full chat cycle."""

import asyncio
import pytest
from datetime import datetime

from aios.conversation.manager import ConversationManager
from aios.conversation.models import Message, MessageRole, ToolCall
from aios.conversation.exceptions import ConversationNotFoundError
from aios.conversation.search import SearchResult


class FakeAIRouter:
    async def route(self, request):
        return type("AIResponse", (), {
            "content": "Integration test response",
            "tokens_used": 25,
            "provider": "test",
            "model": "test-model",
            "cost": 0.0,
            "tool_calls": [],
        })()

    async def route_stream(self, request):
        for char in "streaming integration response":
            yield char


class FakeMemory:
    def __init__(self):
        self.memories = []

    async def search(self, query, limit=10):
        return self.memories[:limit]

    async def store(self, memory):
        self.memories.append(memory)


class FakePlanner:
    async def create_plan(self, request, context=None):
        plan = type("Plan", (), {
            "id": "plan-int",
            "steps": [],
            "request": request,
        })()
        if any(kw in request.lower() for kw in ["file", "read", "write"]):
            plan.steps = [type("Step", (), {"capability": "file.read", "params": {"path": "test.txt"}})()]
        return plan


class FakeToolManager:
    async def list_tools(self):
        return [type("Tool", (), {
            "name": "file.read",
            "description": "Read a file",
            "parameters": {"path": {"type": "string"}},
        })()]

    async def execute(self, tool_id, params):
        return type("ToolResult", (), {"success": True, "data": {"content": "file content"}, "error": None, "duration": 0.1})()


class FakeContextEngine:
    async def get_active_app(self):
        return "vscode"

    async def get_active_file(self):
        return "/home/user/project/main.py"

    async def detect_project(self):
        return "/home/user/project"


class FakeExecutionEngine:
    async def execute_plan(self, plan, objective, conversation_id, owner="", priority=1):
        return type("Execution", (), {
            "id": "exec-int-1",
            "status": type("ExecStatus", (), {"value": "completed"})(),
            "started_at": datetime.utcnow(),
            "completed_at": datetime.utcnow(),
        })()

    async def wait_for_execution(self, execution_id):
        pass

    async def get_execution_result(self, execution_id):
        return type("Result", (), {
            "success": True,
            "duration_ms": 350.0,
            "tools_executed": ["file.read"],
            "capabilities_used": ["file.read"],
            "retry_count": 0,
            "permission_requests": 0,
            "warnings": [],
            "errors": [],
        })()

    async def get_execution_progress(self, execution_id):
        return type("Progress", (), {
            "total_tasks": 1,
            "completed_tasks": 1,
            "percentage": 100.0,
        })()

    def stream_events(self, execution_id):
        async def _gen():
            yield {"type": "progress", "data": "reading file"}
        return _gen()


@pytest.fixture
def manager():
    return ConversationManager(
        ai_router=FakeAIRouter(),
        memory_system=FakeMemory(),
        planner=FakePlanner(),
        tool_manager=FakeToolManager(),
        context_engine=FakeContextEngine(),
        execution_engine=FakeExecutionEngine(),
    )


@pytest.mark.asyncio
class TestFullConversationFlow:
    """Full chat cycle: create → message → branch → export → analytics."""

    async def test_full_chat_cycle(self, manager):
        # 1. Create conversation
        conv = await manager.create_conversation(title="Integration Chat")
        assert conv.id
        assert conv.title == "Integration Chat"

        # 2. Send messages
        response1 = await manager.send_message(conv.id, "Hello!")
        assert response1.role == MessageRole.ASSISTANT
        assert response1.content == "Integration test response"

        response2 = await manager.send_message(conv.id, "Read file test.txt")
        assert response2.detected_intent is not None

        # 3. Get history
        history = await manager.get_history(conv.id)
        assert len(history) >= 4

        # 4. Ensure title generated
        title = await manager.ensure_title(conv.id)
        assert title is not None

        # 5. Search
        results = await manager.search_conversations("integration")
        assert len(results) >= 1

        # 6. Export
        md_export = await manager.export_conversation(conv.id, format="markdown")
        assert md_export is not None
        json_export = await manager.export_conversation(conv.id, format="json")
        assert '"export_version"' in json_export

        # 7. Analytics
        summary = await manager.get_conversation_analytics(conv.id)
        assert isinstance(summary, dict)

        # 8. Rename
        renamed = await manager.rename_conversation(conv.id, "Renamed Chat")
        assert renamed.title == "Renamed Chat"

        # 9. Branch
        user_msgs = [m for m in history if m.role == MessageRole.USER]
        if user_msgs:
            branch = await manager.create_branch(conv.id, user_msgs[0].id, title="Branch Chat")
            assert branch.id != conv.id
            branches = await manager.get_branches(conv.id)
            assert len(branches) >= 1

        # 10. Delete
        await manager.delete_conversation(conv.id)
        with pytest.raises(ConversationNotFoundError):
            await manager.get_conversation(conv.id)

    async def test_stream_chat_cycle(self, manager):
        conv = await manager.create_conversation(title="Stream Cycle")

        events = []
        async for event in manager.stream_message(conv.id, "Hello via stream"):
            events.append(event)

        assert len(events) > 0
        history = await manager.get_history(conv.id)
        assert len(history) >= 2

    async def test_memory_integration(self, manager):
        conv = await manager.create_conversation(title="Memory Integration")
        await manager.send_message(conv.id, "Remember this fact")
        assert len(manager._memory.memories) >= 1

    async def test_execution_integration(self, manager):
        conv = await manager.create_conversation(title="Execution Integration")
        response = await manager.send_message(conv.id, "Read file test.txt")
        assert response.execution_context is not None
        assert response.execution_context.execution_id == "exec-int-1"
        assert response.execution_context.tools_executed == ["file.read"]

    async def test_context_engine_integration(self, manager):
        conv = await manager.create_conversation(title="Context Integration")
        response = await manager.send_message(conv.id, "Hello")
        assert response is not None

    async def test_edit_and_regenerate_cycle(self, manager):
        conv = await manager.create_conversation(title="Edit Cycle")
        response = await manager.send_message(conv.id, "Original message")

        # Regenerate response first
        regenerated = await manager.regenerate_message(conv.id, response.id)
        assert regenerated.is_regenerated is True

        # Edit user message
        history = await manager.get_history(conv.id)
        user_msg = next(m for m in history if m.role == MessageRole.USER)
        edited = await manager.edit_message(conv.id, user_msg.id, "Edited message")
        assert edited.content == "Edited message"

    async def test_multiple_conversations(self, manager):
        conv1 = await manager.create_conversation(title="Chat 1")
        conv2 = await manager.create_conversation(title="Chat 2")

        await manager.send_message(conv1.id, "Message in chat 1")
        await manager.send_message(conv2.id, "Message in chat 2")

        convs = await manager.list_conversations()
        assert len(convs) == 2

    async def test_reindex_and_search(self, manager):
        conv = await manager.create_conversation(title="Searchable Chat")
        await manager.send_message(conv.id, "Python programming discussion")
        await manager.reindex_conversation(conv.id)
        results = await manager.search_conversations("Python")
        assert len(results) >= 1
        assert results[0].conversation_id == conv.id

    async def test_analytics_after_multiple_messages(self, manager):
        conv = await manager.create_conversation(title="Analytics Multi")
        await manager.send_message(conv.id, "First")
        await manager.send_message(conv.id, "Second")
        await manager.send_message(conv.id, "Third")
        summary = await manager.get_conversation_analytics(conv.id)
        assert isinstance(summary, dict)

    async def test_branch_with_execution_context(self, manager):
        conv = await manager.create_conversation(title="Branch Exec")
        response = await manager.send_message(conv.id, "Read file test.txt")
        assert response.execution_context is not None
        history = await manager.get_history(conv.id)
        user_msgs = [m for m in history if m.role == MessageRole.USER]
        if user_msgs:
            branch = await manager.create_branch(conv.id, user_msgs[0].id)
            assert branch.id != conv.id
