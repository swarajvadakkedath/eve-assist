"""Memory System — facade over Memory Core (graph-based memory)."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from aios.models.memory import (
    MemoryNode,
    MemoryEdge,
    NodeId,
    EdgeId,
    NodeInput,
    EdgeInput,
    SearchQuery,
    SearchResult,
    QueryOptions,
    MemorySnapshot,
    TraversalResult,
    MemoryGraphStats,
)
from aios.core.memory.store import get_memory_store
from aios.core.memory.constants import NodeTypeConstants
from aios.core.event_bus import EventBus

class MemoryType:
    FACT = "fact"
    PREFERENCE = "preference"
    LEARNING = "learning"
    PATTERN = "pattern"
    NodeTypeConstants = NodeTypeConstants


@dataclass
class Memory:
    """Backward-compatible Memory dataclass wrapping MemoryNode fields."""
    id: str = ""
    type: str = "fact"
    content: str = ""
    embedding: list[float] = field(default_factory=list)
    importance: float = 0.5
    source: str = ""
    conversation_id: str = ""
    conversation_ids: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    accessed_at: datetime | None = None
    access_count: int = 0

    def __post_init__(self):
        if not self.id:
            self.id = uuid4().hex
        if not self.created_at:
            now = datetime.utcnow()
            self.created_at = now
            self.accessed_at = now

    @classmethod
    def from_node(cls, node: MemoryNode) -> "Memory":
        return cls(
            id=node.id.value,
            type=node.type,
            content=node.summary or node.title,
            importance=node.importance,
            source=node.source,
            access_count=node.accessCount,
            created_at=datetime.fromtimestamp(node.createdAt / 1000) if node.createdAt else None,
            accessed_at=datetime.fromtimestamp(node.lastAccessed / 1000) if node.lastAccessed else None,
        )


class MemorySystem:
    def __init__(self, event_bus: EventBus | None = None):
        self._store = get_memory_store(event_bus=event_bus)
        self._short_term: dict[str, ShortTermMemory] = {}
        self._conversations: dict[str, list[dict]] = {}

    async def store(self, memory: Memory) -> str:
        node_input = NodeInput(
            type=memory.type,
            subtype=memory.type,
            title=memory.content[:100] if memory.content else "Untitled",
            summary=memory.content,
            source=memory.source,
            importance=memory.importance or 1.0,
            tags=[memory.type],
            metadata={"embedding": memory.embedding, "conversation_id": memory.conversation_id, "conversation_ids": memory.conversation_ids},
        )
        node, errors = self._store.create_node(node_input)
        if errors:
            raise ValueError(f"Failed to store memory: {[str(e) for e in errors]}")
        return node.id.value

    async def search(self, query: str, limit: int = 10) -> list[Memory]:
        result = self._store.search_by_keyword(query, QueryOptions(limit=limit))
        return [Memory.from_node(n) for n in result.nodes]

    async def recall(self, memory_id: str) -> Memory | None:
        for node in self._store.graph.get_all_nodes():
            if node.id.value == memory_id:
                return Memory.from_node(node)
        return None

    async def forget(self, memory_id: str) -> None:
        for node in self._store.graph.get_all_nodes():
            if node.id.value == memory_id:
                self._store.delete_node(node.id)
                return

    async def search_nodes(self, query: SearchQuery) -> SearchResult:
        return self._store.search(query)

    async def create_node(self, input: NodeInput) -> tuple[MemoryNode | None, list[Any]]:
        node, errors = self._store.create_node(input)
        return node, errors

    async def get_node(self, node_id: NodeId) -> MemoryNode | None:
        return self._store.get_node(node_id)

    async def update_node(self, node_id: NodeId, partial: dict[str, Any]) -> tuple[MemoryNode | None, list[Any]]:
        return self._store.update_node(node_id, partial)

    async def delete_node(self, node_id: NodeId) -> bool:
        return self._store.delete_node(node_id)

    async def create_edge(self, input: EdgeInput) -> tuple[MemoryEdge | None, list[Any]]:
        return self._store.create_edge(input)

    async def get_edge(self, edge_id: EdgeId) -> MemoryEdge | None:
        return self._store.get_edge(edge_id)

    async def delete_edge(self, edge_id: EdgeId) -> bool:
        return self._store.delete_edge(edge_id)

    async def bfs(self, start_id: NodeId, max_depth: int = 10, edge_types: list[str] | None = None) -> TraversalResult:
        return self._store.bfs(start_id, max_depth, edge_types)

    async def snapshot(self) -> MemorySnapshot:
        return self._store.snapshot()

    async def load_snapshot(self, snapshot: MemorySnapshot):
        self._store.load_snapshot(snapshot)

    async def stats(self) -> MemoryGraphStats:
        return self._store.stats()

    async def clear(self):
        self._store.clear()

    async def get_conversation(self, conversation_id: str) -> list[dict]:
        return self._conversations.get(conversation_id, [])

    async def add_to_conversation(self, conversation_id: str, message: dict) -> None:
        self._conversations.setdefault(conversation_id, []).append(message)

    async def register_in_container(self, container, event_bus: EventBus | None = None):
        container.register(
            "aios.core.memory_system.MemorySystem",
            lambda: MemorySystem(event_bus=event_bus),
            scope="singleton",
        )


@dataclass
class ShortTermMemory:
    conversation_id: str = ""
    messages: list[dict] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    active_tools: list[str] = field(default_factory=list)
    current_plan: Any = None
    expires_at: datetime | None = None

    def __post_init__(self):
        if not self.expires_at:
            from datetime import timedelta
            self.expires_at = datetime.utcnow() + timedelta(hours=1)
