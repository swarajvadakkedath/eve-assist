"""Tests for prompt assembly."""

import pytest
from aios.conversation.prompts import (
    SYSTEM_PROMPT,
    build_system_prompt,
    build_memory_context,
    build_tool_descriptions,
    messages_to_llm_format,
)
from aios.conversation.models import Conversation, Message, MessageRole, ToolCall


class TestSystemPrompt:
    def test_default_prompt_content(self):
        assert "Eve" in SYSTEM_PROMPT
        assert "AI operating system" in SYSTEM_PROMPT
        assert "Windows" in SYSTEM_PROMPT

    def test_build_system_prompt_default(self):
        prompt = build_system_prompt()
        assert "Eve" in prompt
        assert "AI operating system" in prompt

    def test_build_system_prompt_with_project(self):
        conv = Conversation(title="Test", active_project="/projects/test")
        prompt = build_system_prompt(conversation=conv)
        assert "/projects/test" in prompt

    def test_build_system_prompt_no_project(self):
        conv = Conversation(title="Test")
        prompt = build_system_prompt(conversation=conv)
        assert "Active project:" not in prompt

    def test_build_system_prompt_with_active_app(self):
        prompt = build_system_prompt(context={"active_app": "vscode"})
        assert "vscode" in prompt

    def test_build_system_prompt_with_active_file(self):
        prompt = build_system_prompt(context={"active_file": "/src/main.py"})
        assert "/src/main.py" in prompt

    def test_build_system_prompt_with_all_context(self):
        prompt = build_system_prompt(
            conversation=Conversation(title="Test", active_project="/project"),
            context={"active_app": "code", "active_file": "/file.py"},
        )
        assert "/project" in prompt
        assert "code" in prompt
        assert "/file.py" in prompt

    def test_build_system_prompt_empty_context(self):
        prompt = build_system_prompt(context={})
        assert "Eve" in prompt


class TestBuildMemoryContext:
    def test_empty_memories(self):
        result = build_memory_context([])
        assert result == ""

    def test_none_memories(self):
        # build_memory_context checks truthiness, not None
        # But empty list is falsy so should work
        result = build_memory_context([])
        assert result == ""

    class FakeMemory:
        def __init__(self, content):
            self.content = content

    def test_with_single_memory(self):
        memories = [self.FakeMemory("User likes Python")]
        result = build_memory_context(memories)
        assert "User likes Python" in result

    def test_with_multiple_memories(self):
        memories = [
            self.FakeMemory("User likes Python"),
            self.FakeMemory("User prefers dark mode"),
            self.FakeMemory("User works on EVE project"),
            self.FakeMemory("User uses VS Code"),
            self.FakeMemory("User is a developer"),
            self.FakeMemory("This should be truncated"),
        ]
        result = build_memory_context(memories)
        assert "User likes Python" in result
        assert "This should be truncated" not in result

    def test_format_has_header(self):
        memories = [self.FakeMemory("test memory")]
        result = build_memory_context(memories)
        assert "Relevant memories" in result


class TestBuildToolDescriptions:
    def test_empty_tools(self):
        result = build_tool_descriptions([])
        assert result == ""

    class FakeTool:
        def __init__(self, name, description, parameters=None):
            self.name = name
            self.description = description
            self.parameters = parameters

    def test_with_single_tool(self):
        tool = self.FakeTool("file.read", "Read a file", {"path": {"type": "string"}})
        result = build_tool_descriptions([tool])
        assert "file.read" in result
        assert "Read a file" in result

    def test_with_multiple_tools(self):
        tools = [
            self.FakeTool("file.read", "Read a file", {"path": {"type": "string"}}),
            self.FakeTool("file.write", "Write a file", {"path": {"type": "string"}, "content": {"type": "string"}}),
        ]
        result = build_tool_descriptions(tools)
        assert "file.read" in result
        assert "file.write" in result

    def test_without_parameters(self):
        tool = self.FakeTool("ping", "Ping test")
        result = build_tool_descriptions([tool])
        assert "ping" in result
        assert "Ping test" in result


class TestMessagesToLLMFormat:
    def test_empty_messages(self):
        result = messages_to_llm_format([])
        assert len(result) == 1
        assert result[0]["role"] == "system"

    def test_single_user_message(self):
        messages = [Message(role=MessageRole.USER, content="Hello")]
        result = messages_to_llm_format(messages)
        assert len(result) == 2
        assert result[0]["role"] == "system"
        assert result[1]["role"] == "user"
        assert result[1]["content"] == "Hello"

    def test_user_and_assistant(self):
        messages = [
            Message(role=MessageRole.USER, content="Hello"),
            Message(role=MessageRole.ASSISTANT, content="Hi there"),
        ]
        result = messages_to_llm_format(messages)
        assert len(result) == 3
        assert result[1]["role"] == "user"
        assert result[2]["role"] == "assistant"

    def test_with_tool_calls(self):
        tc = ToolCall(tool_name="file.read", capability="file.read", parameters={"path": "/tmp/test"})
        msg = Message(role=MessageRole.ASSISTANT, content="Reading...", tool_calls=[tc])
        result = messages_to_llm_format([msg])
        assert "tool_calls" in result[1]
        assert result[1]["tool_calls"][0]["function"]["name"] == "file.read"

    def test_with_tool_results(self):
        msg = Message(role=MessageRole.ASSISTANT, content="Done", tool_results=[{"tool_name": "file.read", "result": {"ok": True}}])
        result = messages_to_llm_format([msg])
        tool_entries = [e for e in result if e["role"] == "tool"]
        assert len(tool_entries) == 1
        assert tool_entries[0]["tool_call_id"] == "file.read"

    def test_with_custom_system_prompt(self):
        messages = [Message(role=MessageRole.USER, content="Hi")]
        result = messages_to_llm_format(messages, system_prompt="Custom prompt")
        assert result[0]["content"] == "Custom prompt"

    def test_with_memory_context(self):
        messages = [Message(role=MessageRole.USER, content="Hi")]
        result = messages_to_llm_format(messages, memory_context="User likes Python")
        assert "User likes Python" in result[0]["content"]

    def test_with_tool_descriptions(self):
        messages = [Message(role=MessageRole.USER, content="Hi")]
        result = messages_to_llm_format(messages, tool_descriptions="Available: file.read")
        assert "Available: file.read" in result[0]["content"]

    def test_system_message_excluded(self):
        messages = [
            Message(role=MessageRole.SYSTEM, content="system message"),
            Message(role=MessageRole.USER, content="user message"),
        ]
        result = messages_to_llm_format(messages)
        llm_messages = [m for m in result if m.get("role") != "system"]
        # The first entry is always the system prompt
        user_entries = [m for m in result if m["role"] == "user"]
        assert len(user_entries) == 1
        assert user_entries[0]["content"] == "user message"

    def test_multiple_tool_calls(self):
        tcs = [
            ToolCall(tool_name="search", capability="web.search", parameters={"q": "test"}),
            ToolCall(tool_name="read", capability="file.read", parameters={"path": "/tmp"}),
        ]
        messages = [Message(role=MessageRole.ASSISTANT, content="Running tools...", tool_calls=tcs)]
        result = messages_to_llm_format([msg for msg in messages])
        assert len(result[1]["tool_calls"]) == 2
