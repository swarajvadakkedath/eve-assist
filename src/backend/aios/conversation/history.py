"""History management — optimize context windows for LLM calls."""

from typing import Any

from aios.conversation.models import Message, MessageRole
from aios.utils.logger import get_logger

logger = get_logger(__name__)


class HistoryManager:
    def __init__(self, max_context_messages: int = 50, max_context_tokens: int = 8000):
        self._max_context_messages = max_context_messages
        self._max_context_tokens = max_context_tokens

    async def get_history(self, messages: list[Message], limit: int = 100) -> list[Message]:
        return messages[-limit:]

    async def build_context_window(
        self,
        messages: list[Message],
        relevant_memories: list[Any] | None = None,
    ) -> list[Message]:
        window = list(messages)

        window = self._trim_messages(window)

        if relevant_memories:
            memory_msg = Message(
                role=MessageRole.SYSTEM,
                content=self._format_memories(relevant_memories),
            )
            window.insert(0, memory_msg)

        return window

    def _trim_messages(self, messages: list[Message]) -> list[Message]:
        if len(messages) <= self._max_context_messages:
            return messages

        system_msgs = [m for m in messages if m.role == MessageRole.SYSTEM]
        non_system = [m for m in messages if m.role != MessageRole.SYSTEM]

        trimmed = non_system[-(self._max_context_messages - len(system_msgs)):]
        return system_msgs + trimmed

    def _format_memories(self, memories: list[Any]) -> str:
        if not memories:
            return ""
        lines = ["Relevant context from previous conversations:"]
        for m in memories[:5]:
            lines.append(f"- {m.content}")
        return "\n".join(lines)

    async def estimate_tokens(self, messages: list[Message]) -> int:
        total = 0
        for msg in messages:
            total += len(msg.content.split()) * 1.5
            total += 10
        return int(total)
