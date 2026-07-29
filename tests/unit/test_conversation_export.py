"""Tests for ConversationExporter."""

import json
import pytest
from datetime import datetime
from aios.conversation.export import ConversationExporter
from aios.conversation.models import Conversation, Message, MessageRole, ToolCall, ToolCallStatus


class TestConversationExporter:
    @pytest.fixture
    def exporter(self):
        return ConversationExporter()

    @pytest.fixture
    def conversation(self):
        return Conversation(title="Test Chat", created_at=datetime(2026, 7, 21), updated_at=datetime(2026, 7, 21))

    @pytest.fixture
    def messages(self):
        return [
            Message(id="m1", role=MessageRole.USER, content="Hello", timestamp=datetime(2026, 7, 21, 10, 0)),
            Message(id="m2", role=MessageRole.ASSISTANT, content="Hi there", timestamp=datetime(2026, 7, 21, 10, 1), tokens_used=10),
            Message(id="m3", role=MessageRole.SYSTEM, content="system note", timestamp=datetime(2026, 7, 21, 10, 2)),
        ]

    @pytest.mark.asyncio
    async def test_export_markdown(self, exporter, conversation, messages):
        output = await exporter.export_markdown(conversation, messages)
        assert "# Test Chat" in output
        assert "**Date:**" in output
        assert "Hello" in output
        assert "Hi there" in output
        assert "system note" not in output

    @pytest.mark.asyncio
    async def test_export_markdown_with_tool_calls(self, exporter, conversation):
        tc = ToolCall(tool_name="file.read", capability="file.read", status=ToolCallStatus.SUCCESS, execution_time=0.5)
        msgs = [
            Message(id="m1", role=MessageRole.USER, content="Read file"),
            Message(id="m2", role=MessageRole.ASSISTANT, content="Done", tool_calls=[tc], tokens_used=20),
        ]
        output = await exporter.export_markdown(conversation, msgs)
        assert "file.read" in output
        assert "success" in output
        assert "0.50s" in output
        assert "(20 tokens)" in output

    @pytest.mark.asyncio
    async def test_export_markdown_empty_messages(self, exporter, conversation):
        output = await exporter.export_markdown(conversation, [])
        assert "# Test Chat" in output
        assert "0" in output

    @pytest.mark.asyncio
    async def test_export_html(self, exporter, conversation, messages):
        output = await exporter.export_html(conversation, messages)
        assert "<!DOCTYPE html>" in output
        assert "Test Chat" in output
        assert "Hello" in output
        assert "Hi there" in output
        assert "system note" not in output

    @pytest.mark.asyncio
    async def test_export_html_with_tool_calls(self, exporter, conversation):
        tc = ToolCall(tool_name="file.read", capability="file.read", status=ToolCallStatus.SUCCESS, execution_time=0.5)
        msgs = [
            Message(id="m1", role=MessageRole.USER, content="Read file"),
            Message(id="m2", role=MessageRole.ASSISTANT, content="Done", tool_calls=[tc], tokens_used=20),
        ]
        output = await exporter.export_html(conversation, msgs)
        assert "file.read" in output
        assert "20 tokens" in output

    @pytest.mark.asyncio
    async def test_export_html_empty_messages(self, exporter, conversation):
        output = await exporter.export_html(conversation, [])
        assert "<!DOCTYPE html>" in output
        assert "Messages" in output

    @pytest.mark.asyncio
    async def test_export_json(self, exporter, conversation, messages):
        output = await exporter.export_json(conversation, messages)
        data = json.loads(output)
        assert data["export_version"] == "1.0"
        assert data["conversation"]["title"] == "Test Chat"
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_export_json_with_tool_calls(self, exporter, conversation):
        tc = ToolCall(tool_name="file.read", capability="file.read", parameters={"path": "/tmp"}, status=ToolCallStatus.SUCCESS, execution_time=0.5)
        msgs = [
            Message(id="m1", role=MessageRole.USER, content="Read"),
            Message(id="m2", role=MessageRole.ASSISTANT, content="Done", tool_calls=[tc]),
        ]
        output = await exporter.export_json(conversation, msgs)
        data = json.loads(output)
        assert len(data["messages"][1]["tool_calls"]) == 1
        assert data["messages"][1]["tool_calls"][0]["tool_name"] == "file.read"
        assert data["messages"][1]["tool_calls"][0]["status"] == "success"

    @pytest.mark.asyncio
    async def test_export_json_system_excluded(self, exporter, conversation, messages):
        output = await exporter.export_json(conversation, messages)
        data = json.loads(output)
        assert len(data["messages"]) == 2
        assert data["conversation"]["message_count"] == 2

    @pytest.mark.asyncio
    async def test_export_json_empty_messages(self, exporter, conversation):
        output = await exporter.export_json(conversation, [])
        data = json.loads(output)
        assert data["messages"] == []
        assert data["conversation"]["message_count"] == 0

    @pytest.mark.asyncio
    async def test_export_json_with_attachments(self, exporter, conversation):
        msgs = [
            Message(id="m1", role=MessageRole.USER, content="See this", attachments=[{"type": "image", "path": "/img.png"}]),
        ]
        output = await exporter.export_json(conversation, msgs)
        data = json.loads(output)
        assert len(data["messages"][0]["attachments"]) == 1
        assert data["messages"][0]["attachments"][0]["type"] == "image"
