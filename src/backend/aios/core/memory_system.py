"""Memory System — short-term, long-term, and semantic memory."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


class MemoryType:
    FACT = "fact"
    PREFERENCE = "preference"
    LEARNING = "learning"
    PATTERN = "pattern"


@dataclass
class Memory:
    id: str = ""
    type: str = MemoryType.FACT
    content: str = ""
    embedding: list[float] = field(default_factory=list)
    importance: float = 0.5
    source: str = ""
    conversation_id: str = ""
    conversation_ids: list[str] = field(default_factory=list)
    created_at: datetime = None
    accessed_at: datetime = None
    access_count: int = 0

    def __post_init__(self):
        if not self.id:
            self.id = uuid4().hex
        if not self.created_at:
            now = datetime.utcnow()
            self.created_at = now
            self.accessed_at = now


@dataclass
class ShortTermMemory:
    conversation_id: str = ""
    messages: list[dict] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    active_tools: list[str] = field(default_factory=list)
    current_plan: Any = None
    expires_at: datetime = None

    def __post_init__(self):
        if not self.expires_at:
            from datetime import timedelta
            self.expires_at = datetime.utcnow() + timedelta(hours=1)


class MemorySystem:
    def __init__(self):
        self._short_term: dict[str, ShortTermMemory] = {}
        self._long_term: list[Memory] = []
        self._conversations: dict[str, list[dict]] = {}

    async def store(self, memory: Memory) -> None:
        self._long_term.append(memory)

    async def search(self, query: str, limit: int = 10) -> list[Memory]:
        q = query.lower()
        results = [
            m for m in self._long_term
            if q in m.content.lower()
        ]
        results.sort(key=lambda m: m.importance, reverse=True)
        return results[:limit]

    async def recall(self, memory_id: str) -> Memory | None:
        for m in self._long_term:
            if m.id == memory_id:
                m.access_count += 1
                m.accessed_at = datetime.utcnow()
                return m
        return None

    async def forget(self, memory_id: str) -> None:
        self._long_term = [m for m in self._long_term if m.id != memory_id]

    async def get_conversation(self, conversation_id: str) -> list[dict]:
        return self._conversations.get(conversation_id, [])

    async def add_to_conversation(self, conversation_id: str, message: dict) -> None:
        self._conversations.setdefault(conversation_id, []).append(message)
