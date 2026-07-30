"""Unit tests for prompt assembly."""

from aios.conversation.prompts import (
    build_system_prompt,
    build_memory_context,
    build_tool_descriptions,
    messages_to_llm_format,
)
from aios.conversation.models import Conversation, Message, MessageRole, ToolCall


class TestPrompts:
    def test_build_system_prompt_default(self):
        prompt = build_system_prompt()
        assert "Eve" in prompt
        assert "AI operating system" in prompt

    def test_build_system_prompt_with_project(self):
        conv = Conversation(title="Test", active_project="/projects/test")
        prompt = build_system_prompt(conversation=conv)
        assert "/projects/test" in prompt

    def test_build_system_prompt_with_context(self):
        prompt = build_system_prompt(context={"active_app": "vscode"})
        assert "vscode" in prompt

    def test_build_memory_context_empty(self):
        result = build_memory_context([])
        assert result == ""

    class FakeMemory:
        def __init__(self, content):
            self.content = content

    def test_build_memory_context_with_memories(self):
        memories = [self.FakeMemory("User likes Python")]
        result = build_memory_context(memories)
        assert "User likes Python" in result

    def test_build_tool_descriptions_empty(self):
        result = build_tool_descriptions([])
        assert result == ""

    class FakeTool:
        def __init__(self, name, description, parameters):
            self.name = name
            self.description = description
            self.parameters = parameters

    def test_build_tool_descriptions_with_tools(self):
        tool = self.FakeTool("file.read", "Read a file", {"path": {"type": "string"}})
        result = build_tool_descriptions([tool])
        assert "file.read" in result
        assert "Read a file" in result

    def test_messages_to_llm_format(self):
        messages = [
            Message(role=MessageRole.USER, content="Hello"),
            Message(role=MessageRole.ASSISTANT, content="Hi"),
        ]
        result = messages_to_llm_format(messages)
        assert len(result) == 3
        assert result[0]["role"] == "system"
        assert result[1]["role"] == "user"
        assert result[1]["content"] == "Hello"
        assert result[2]["role"] == "assistant"

    def test_messages_with_tool_calls(self):
        tc = ToolCall(tool_name="file.read", capability="file.read", parameters={"path": "/tmp/test"})
        msg = Message(role=MessageRole.ASSISTANT, content="Reading...", tool_calls=[tc])
        result = messages_to_llm_format([msg])
        assert "tool_calls" in result[1]
        assert result[1]["tool_calls"][0]["function"]["name"] == "file.read"
