"""Memory System — facade over Memory Core (graph-based memory)."""

import re
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
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
from aios.utils.logger import get_logger

logger = get_logger(__name__)

SENSITIVE_PATTERNS = [
    r"api[_\s]?key",
    r"access[_\s]?token",
    r"secret[_\s]?key",
    r"password",
    r"passwd",
    r"private[_\s]?key",
    r"credit[_\s]?card",
    r"session[_\s]?token",
    r"auth[_\s]?token",
    r"bearer",
    r"sk-[a-zA-Z0-9]{20,}",
    r"ghp_[a-zA-Z0-9]{36}",
    r"xox[bps]-[a-zA-Z0-9-]+",
]

MEMORY_CANDIDATE_KEYWORDS = [
    "remember", "prefer", "favorite", "always", "never",
    "note", "important", "rule", "convention", "standard",
    "project uses", "project has", "we use", "we have",
]


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
    project_id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = uuid4().hex
        if not self.created_at:
            now = datetime.now(timezone.utc)
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
            project_id=node.metadata.get("project_id", "") if node.metadata else "",
        )


class MemorySystem:
    def __init__(self, event_bus: EventBus | None = None, persistence_path: str | None = None):
        self._store = get_memory_store(event_bus=event_bus)
        self._short_term: dict[str, ShortTermMemory] = {}
        self._conversations: dict[str, list[dict]] = {}
        self._persistence_path = persistence_path
        self._dirty = False

    def _is_sensitive(self, content: str) -> bool:
        content_lower = content.lower()
        for pattern in SENSITIVE_PATTERNS:
            if re.search(pattern, content_lower):
                return True
        return False

    def _is_candidate(self, content: str) -> bool:
        content_lower = content.lower()
        if any(kw in content_lower for kw in MEMORY_CANDIDATE_KEYWORDS):
            return True
        if len(content) > 50:
            return False
        return False

    def _find_similar(self, content: str, memory_type: str) -> Memory | None:
        for node in self._store.graph.get_all_nodes():
            if node.type == memory_type:
                existing = node.summary or node.title
                if existing and content.lower() in existing.lower():
                    return Memory.from_node(node)
        return None

    def _find_conflict(self, content: str, memory_type: str) -> Memory | None:
        if memory_type != MemoryType.PREFERENCE:
            return None
        for node in self._store.graph.get_all_nodes():
            if node.type == MemoryType.PREFERENCE:
                existing = node.summary or node.title
                if existing:
                    existing_key = existing.split(" is ")[-1].split(" are ")[-1].strip().lower()
                    new_key = content.split(" is ")[-1].split(" are ")[-1].strip().lower()
                    if existing_key and new_key and existing_key != new_key:
                        if any(word in existing.lower() for word in content.lower().split()):
                            return Memory.from_node(node)
        return None

    async def store(self, memory: Memory, force: bool = False) -> str:
        if not force and self._is_sensitive(memory.content):
            logger.warning("memory blocked: sensitive content", content_preview=memory.content[:50])
            raise ValueError("Cannot store memory containing sensitive information")

        if not force and not self._is_candidate(memory.content) and memory.importance < 0.7:
            logger.debug("memory skipped: not a candidate", content_preview=memory.content[:50])
            raise ValueError("Content is not a memory candidate")

        existing = self._find_similar(memory.content, memory.type)
        if existing:
            logger.info("memory deduplicated", existing_id=existing.id)
            return existing.id

        conflict = self._find_conflict(memory.content, memory.type)
        if conflict:
            logger.info("memory conflict resolved", old_id=conflict.id, new_content=memory.content[:50])
            self._store.delete_node(NodeId(value=conflict.id, type=conflict.type))

        node_input = NodeInput(
            type=memory.type,
            subtype=memory.type,
            title=memory.content[:100] if memory.content else "Untitled",
            summary=memory.content,
            source=memory.source,
            importance=memory.importance or 1.0,
            tags=[memory.type],
            metadata={
                "embedding": memory.embedding,
                "conversation_id": memory.conversation_id,
                "conversation_ids": memory.conversation_ids,
                "project_id": memory.project_id,
            },
        )
        node, errors = self._store.create_node(node_input)
        if errors:
            raise ValueError(f"Failed to store memory: {[str(e) for e in errors]}")
        self._dirty = True
        return node.id.value

    async def search(self, query: str, limit: int = 10, project_id: str | None = None) -> list[Memory]:
        result = self._store.search_by_keyword(query, QueryOptions(limit=limit * 2))
        memories = [Memory.from_node(n) for n in result.nodes]
        if project_id:
            memories = [m for m in memories if m.project_id == project_id or not m.project_id]
        return memories[:limit]

    async def recall(self, memory_id: str) -> Memory | None:
        for node in self._store.graph.get_all_nodes():
            if node.id.value == memory_id:
                return Memory.from_node(node)
        return None

    async def forget(self, memory_id: str) -> None:
        for node in self._store.graph.get_all_nodes():
            if node.id.value == memory_id:
                self._store.delete_node(node.id)
                self._dirty = True
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
        self._dirty = True

    async def save(self) -> bool:
        if not self._persistence_path:
            return False
        try:
            snapshot = await self.snapshot()
            path = Path(self._persistence_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "nodes": [{"id": n.id.value, "type": n.type, "subtype": n.subtype, "title": n.title, "summary": n.summary, "source": n.source, "importance": n.importance, "tags": n.tags, "metadata": n.metadata, "createdAt": n.createdAt, "status": n.status} for n in snapshot.nodes],
                "edges": [{"id": e.id.value, "sourceNodeId": e.sourceNodeId.value, "targetNodeId": e.targetNodeId.value, "type": e.type, "strength": e.strength, "weight": e.weight, "metadata": e.metadata, "createdAt": e.createdAt} for e in snapshot.edges],
                "timestamp": snapshot.timestamp,
            }
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            self._dirty = False
            logger.info("memory saved", path=self._persistence_path, nodes=len(snapshot.nodes))
            return True
        except Exception as e:
            logger.error("memory save failed", error=str(e))
            return False

    async def load(self) -> bool:
        if not self._persistence_path:
            return False
        path = Path(self._persistence_path)
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            nodes = []
            for n in data.get("nodes", []):
                nodes.append(MemoryNode(
                    id=NodeId(value=n["id"], type=n["type"]),
                    type=n["type"],
                    subtype=n.get("subtype", n["type"]),
                    title=n.get("title", ""),
                    summary=n.get("summary", ""),
                    source=n.get("source", ""),
                    importance=n.get("importance", 1.0),
                    tags=n.get("tags", []),
                    metadata=n.get("metadata"),
                    createdAt=n.get("createdAt"),
                    status=n.get("status", "active"),
                ))
            edges = []
            for e in data.get("edges", []):
                edges.append(MemoryEdge(
                    id=EdgeId(value=e["id"]),
                    sourceNodeId=NodeId(value=e["sourceNodeId"], type=""),
                    targetNodeId=NodeId(value=e["targetNodeId"], type=""),
                    type=e["type"],
                    strength=e.get("strength", 1.0),
                    weight=e.get("weight", 1.0),
                    metadata=e.get("metadata"),
                    createdAt=e.get("createdAt"),
                ))
            snapshot = MemorySnapshot(nodes=nodes, edges=edges, timestamp=data.get("timestamp", 0))
            await self.load_snapshot(snapshot)
            logger.info("memory loaded", path=self._persistence_path, nodes=len(nodes))
            return True
        except Exception as e:
            logger.error("memory load failed", error=str(e))
            return False

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



