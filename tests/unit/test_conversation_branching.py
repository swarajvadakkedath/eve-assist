"""Tests for BranchManager."""

import pytest
from aios.conversation.branching import BranchManager
from aios.conversation.models import Conversation, Message, MessageRole


class TestBranchManager:
    @pytest.mark.asyncio
    async def test_create_branch(self):
        bm = BranchManager()
        parent = Conversation(title="Original")
        branch = await bm.create_branch(parent, "msg-1", title="My Branch")
        assert branch.id
        assert branch.title == "My Branch"
        assert branch.metadata["parent_id"] == parent.id
        assert branch.metadata["branch_point_message_id"] == "msg-1"
        assert branch.metadata["is_branch"] is True

    @pytest.mark.asyncio
    async def test_create_branch_default_title(self):
        bm = BranchManager()
        parent = Conversation(title="Original Conversation")
        branch = await bm.create_branch(parent, "msg-1")
        assert "Original" in branch.title

    @pytest.mark.asyncio
    async def test_get_branches_empty(self):
        bm = BranchManager()
        branches = await bm.get_branches("nonexistent")
        assert branches == []

    @pytest.mark.asyncio
    async def test_get_branches(self):
        bm = BranchManager()
        parent = Conversation(title="Parent")
        branch1 = await bm.create_branch(parent, "msg-1")
        branch2 = await bm.create_branch(parent, "msg-2")
        branches = await bm.get_branches(parent.id)
        assert len(branches) == 2

    @pytest.mark.asyncio
    async def test_get_parent_id(self):
        bm = BranchManager()
        parent = Conversation(title="Parent")
        branch = await bm.create_branch(parent, "msg-1")
        parent_id = await bm.get_parent_id(branch)
        assert parent_id == parent.id

    @pytest.mark.asyncio
    async def test_get_parent_id_no_parent(self):
        bm = BranchManager()
        conv = Conversation(title="Orphan")
        parent_id = await bm.get_parent_id(conv)
        assert parent_id is None

    @pytest.mark.asyncio
    async def test_get_branch_point(self):
        bm = BranchManager()
        parent = Conversation(title="Parent")
        branch = await bm.create_branch(parent, "msg-42")
        point = await bm.get_branch_point(branch)
        assert point == "msg-42"

    @pytest.mark.asyncio
    async def test_get_branch_point_no_point(self):
        bm = BranchManager()
        conv = Conversation(title="No Point")
        point = await bm.get_branch_point(conv)
        assert point is None

    @pytest.mark.asyncio
    async def test_is_branch_true(self):
        bm = BranchManager()
        parent = Conversation(title="Parent")
        branch = await bm.create_branch(parent, "msg-1")
        assert await bm.is_branch(branch) is True

    @pytest.mark.asyncio
    async def test_is_branch_false(self):
        bm = BranchManager()
        conv = Conversation(title="Original")
        assert await bm.is_branch(conv) is False

    @pytest.mark.asyncio
    async def test_delete_branch(self):
        bm = BranchManager()
        parent = Conversation(title="Parent")
        branch = await bm.create_branch(parent, "msg-1")
        result = await bm.delete_branch(branch.id)
        assert result is True
        branches = await bm.get_branches(parent.id)
        assert len(branches) == 0

    @pytest.mark.asyncio
    async def test_delete_branch_not_found(self):
        bm = BranchManager()
        result = await bm.delete_branch("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_rename_branch(self):
        bm = BranchManager()
        parent = Conversation(title="Parent")
        branch = await bm.create_branch(parent, "msg-1", title="Old Name")
        result = await bm.rename_branch(branch.id, "New Name")
        assert result is True
        branches = await bm.get_branches(parent.id)
        assert branches[0].title == "New Name"

    @pytest.mark.asyncio
    async def test_rename_branch_not_found(self):
        bm = BranchManager()
        result = await bm.rename_branch("nonexistent", "New Name")
        assert result is False

    @pytest.mark.asyncio
    async def test_copy_messages_to_branch(self):
        bm = BranchManager()
        msgs = [
            Message(id="m1", role=MessageRole.USER, content="Hello"),
            Message(id="m2", role=MessageRole.ASSISTANT, content="Hi"),
            Message(id="m3", role=MessageRole.USER, content="How are you?"),
        ]
        copied = await bm.copy_messages_to_branch(msgs, "m2", "branch-1")
        assert len(copied) == 2
        assert copied[0].content == "Hello"
        assert copied[1].content == "Hi"
        assert all(m.conversation_id == "branch-1" for m in copied)

    @pytest.mark.asyncio
    async def test_copy_messages_to_branch_with_tool_calls(self):
        bm = BranchManager()
        from aios.conversation.models import ToolCall
        tc = ToolCall(tool_name="file.read", capability="file.read", parameters={"path": "/tmp"})
        msgs = [
            Message(id="m1", role=MessageRole.USER, content="Read a file"),
            Message(id="m2", role=MessageRole.ASSISTANT, content="Sure", tool_calls=[tc]),
        ]
        copied = await bm.copy_messages_to_branch(msgs, "m2", "branch-2")
        assert len(copied) == 2
        assert len(copied[1].tool_calls) == 1
        assert copied[1].tool_calls[0].tool_name == "file.read"

    @pytest.mark.asyncio
    async def test_copy_messages_to_branch_with_attachments(self):
        bm = BranchManager()
        msgs = [
            Message(id="m1", role=MessageRole.USER, content="See this", attachments=[{"type": "image"}]),
        ]
        copied = await bm.copy_messages_to_branch(msgs, "m1", "branch-3")
        assert len(copied[0].attachments) == 1

    @pytest.mark.asyncio
    async def test_copy_messages_empty(self):
        bm = BranchManager()
        copied = await bm.copy_messages_to_branch([], "msg-1", "branch-empty")
        assert copied == []
