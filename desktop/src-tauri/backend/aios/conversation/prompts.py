"""System prompt assembly and context building."""

import json
from typing import Any

from aios.conversation.models import Message, MessageRole


SYSTEM_PROMPT = """You are Eve, an intelligent AI operating system for Windows. You help users accomplish tasks through natural conversation.

Your capabilities include:
- Answering questions and providing information
- Reading and writing files
- Executing commands
- Managing projects
- Searching and organizing files
- Controlling applications

You can use tools to help the user, but you should prefer natural conversation. Only use tools when necessary.

When using tools:
1. Explain what you're doing
2. Execute the tool
3. Explain the results

Be concise, helpful, and friendly. If you cannot do something, explain why and offer alternatives."""


def build_system_prompt(conversation: Any | None = None, context: dict | None = None) -> str:
    parts = [SYSTEM_PROMPT]

    if conversation and conversation.active_project:
        parts.append(f"\nActive project: {conversation.active_project}")

    if context:
        if context.get("active_app"):
            parts.append(f"\nActive application: {context['active_app']}")
        if context.get("active_file"):
            parts.append(f"\nActive file: {context['active_file']}")

    return "\n".join(parts)


def build_memory_context(memories: list[Any]) -> str:
    if not memories:
        return ""
    lines = ["\nRelevant memories:"]
    for m in memories[:5]:
        lines.append(f"- {m.content}")
    return "\n".join(lines)


def build_tool_descriptions(tools: list[Any]) -> str:
    if not tools:
        return ""
    lines = ["\nAvailable tools:"]
    for t in tools:
        params = json.dumps(t.parameters, indent=2) if t.parameters else "{}"
        lines.append(f"\n- {t.name}: {t.description}")
        lines.append(f"  Parameters: {params}")
    return "\n".join(lines)


def messages_to_llm_format(
    messages: list[Message],
    system_prompt: str | None = None,
    memory_context: str = "",
    tool_descriptions: str = "",
) -> list[dict]:
    result: list[dict] = []

    system_content = system_prompt or build_system_prompt()
    if memory_context:
        system_content += f"\n\n{memory_context}"
    if tool_descriptions:
        system_content += f"\n\n{tool_descriptions}"

    result.append({"role": "system", "content": system_content})

    for msg in messages:
        entry: dict = {"role": msg.role.value if hasattr(msg.role, "value") else msg.role, "content": msg.content}
        if msg.tool_calls:
            entry["tool_calls"] = [
                {
                    "id": tc.tool_name,
                    "type": "function",
                    "function": {
                        "name": tc.capability,
                        "arguments": json.dumps(tc.parameters),
                    },
                }
                for tc in msg.tool_calls
            ]
        result.append(entry)

        for tr in msg.tool_results:
            result.append({
                "role": "tool",
                "tool_call_id": tr.get("tool_name", ""),
                "content": json.dumps(tr.get("result", {})),
            })

    return result
