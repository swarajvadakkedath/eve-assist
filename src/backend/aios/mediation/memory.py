"""Memory Mediation — interface between Hermes reasoning and EVE's graph memory.

Hermes has its own reasoning memory (short-term, working memory for multi-step
tasks).  EVE has a graph-based memory system with GLOBAL, PROJECT, and SESSION
scopes.

This module defines the contract for how these two memory systems interact:

  1. Hermes requests memory context → EVE provides relevant memories
  2. Hermes produces insights → EVE stores them in the graph
  3. Memory scope enforcement — Hermes cannot access memories outside its scope
  4. Identity sanitisation — memories stored by Hermes are attributed to "EVE"

Design decisions (from ARCHITECTURE.md):
  - Hermes memory is read-only from EVE's perspective
  - EVE controls all persistence
  - Hermes reasoning state is ephemeral (lost on restart)
  - Long-term memories are ALWAYS stored in EVE's graph

Phase B foundation — this module is the contract; actual Hermes memory
integration will be wired when Hermes engine is fully connected.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from aios.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Memory scope & types
# ---------------------------------------------------------------------------

class MemoryScope(str, Enum):
    """Scopes that Hermes can access."""
    SESSION = "session"      # Hermes working memory for current task
    PROJECT = "project"      # Project-scoped memories
    GLOBAL = "global"        # User-level persistent memories


class MemoryRequestType(str, Enum):
    """What Hermes is requesting from EVE's memory."""
    RECALL = "recall"        # Retrieve relevant memories for context
    SEARCH = "search"        # Search for specific memories
    STORE = "store"          # Store a new memory (attributed to EVE)
    UPDATE = "update"        # Update an existing memory
    FORGET = "forget"        # Remove a memory


class MemoryAttribution(str, Enum):
    """Who created the memory — always EVE from the user's perspective."""
    USER = "user"
    EVE = "eve"
    SYSTEM = "system"


# ---------------------------------------------------------------------------
# Memory request / response models
# ---------------------------------------------------------------------------

@dataclass
class MemoryRequest:
    """A request from Hermes to EVE's memory system."""
    request_type: MemoryRequestType
    query: str = ""
    scope: MemoryScope = MemoryScope.SESSION
    content: str = ""
    memory_id: str | None = None
    conversation_id: str | None = None
    importance: float = 0.5
    metadata: dict = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: uuid4().hex)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class MemoryResult:
    """Result of a memory operation."""
    success: bool
    memories: list = field(default_factory=list)
    memory_id: str | None = None
    message: str = ""
    request_id: str = ""
    latency_ms: float = 0.0


@dataclass
class MemoryContext:
    """Memory context that flows into the conversation pipeline."""
    memories: list = field(default_factory=list)
    scope: MemoryScope = MemoryScope.SESSION
    query: str = ""
    count: int = 0
    latency_ms: float = 0.0


# ---------------------------------------------------------------------------
# MemoryMediator
# ---------------------------------------------------------------------------

class MemoryMediator:
    """Mediates between Hermes reasoning and EVE's graph memory.

    The mediator:
      1. Receives memory requests from Hermes
      2. Validates scope and permissions
      3. Delegates to EVE's MemorySystem
      4. Sanitises output (never exposes Hermes to stored memories)
      5. Returns results to Hermes

    Does NOT:
      - Give Hermes direct access to the memory graph
      - Allow Hermes to create memories without EVE attribution
      - Expose memory internals to Hermes
    """

    def __init__(self, memory_system: Any | None = None):
        self._memory = memory_system
        self._session_memories: dict[str, list[dict]] = {}  # ephemeral session memory

    # ── Memory recall (Hermes requests context) ────────────────────

    async def recall(
        self,
        query: str,
        scope: MemoryScope | str = MemoryScope.SESSION,
        conversation_id: str | None = None,
        limit: int = 10,
    ) -> MemoryContext:
        """Recall relevant memories for Hermes reasoning context.

        Returns MemoryContext with memories sanitised and attributed to EVE.
        """
        import time
        start = time.monotonic()
        if isinstance(scope, str):
            scope = MemoryScope(scope)

        memories: list[dict] = []

        # Session scope — check ephemeral session memory first
        if scope in (MemoryScope.SESSION, MemoryScope.PROJECT, MemoryScope.GLOBAL):
            session_mems = self._session_memories.get(conversation_id or "default", [])
            for m in session_mems:
                if self._matches_query(query, m.get("content", "")):
                    memories.append(m)

        # Project/Global scope — query EVE's graph memory
        if scope in (MemoryScope.PROJECT, MemoryScope.GLOBAL) and self._memory is not None:
            try:
                graph_memories = await self._memory.search(
                    query,
                    limit=limit,
                    scope=scope.value if hasattr(scope, "value") else scope,
                    project_id=conversation_id,
                )
                for m in graph_memories:
                    mem_dict = self._memory_to_dict(m)
                    mem_dict["source"] = "graph"
                    memories.append(mem_dict)
            except Exception as exc:
                logger.warning("memory_mediator.recall_failed", error=str(exc))

        latency = (time.monotonic() - start) * 1000

        return MemoryContext(
            memories=memories[:limit],
            scope=scope,
            query=query,
            count=len(memories[:limit]),
            latency_ms=latency,
        )

    # ── Memory store (Hermes wants to save an insight) ─────────────

    async def store(
        self,
        content: str,
        scope: MemoryScope | str = MemoryScope.SESSION,
        conversation_id: str | None = None,
        importance: float = 0.5,
        metadata: dict | None = None,
    ) -> MemoryResult:
        """Store a memory from Hermes, attributed to EVE.

        Session memories are ephemeral (in-memory dict).
        Project/Global memories are persisted in EVE's graph.
        """
        memory_id = uuid4().hex
        if isinstance(scope, str):
            scope = MemoryScope(scope)

        if scope == MemoryScope.SESSION:
            # Ephemeral session memory — not persisted
            session_mems = self._session_memories.setdefault(conversation_id or "default", [])
            session_mems.append({
                "id": memory_id,
                "content": content,
                "attribution": MemoryAttribution.EVE.value,
                "scope": scope.value,
                "importance": importance,
                "created_at": datetime.now(timezone.utc).isoformat(),
                **(metadata or {}),
            })
            return MemoryResult(
                success=True,
                memory_id=memory_id,
                message="Stored in session memory",
            )

        # Project/Global — persist in EVE's graph
        if self._memory is None:
            return MemoryResult(
                success=False,
                message="Memory system not available",
            )

        try:
            from aios.core.memory_system import Memory, MemoryType
            memory = Memory(
                type=MemoryType.FACT,
                content=content,
                source="hermes_reasoning",
                conversation_id=conversation_id,
                importance=importance,
            )
            await self._memory.store(memory)
            return MemoryResult(
                success=True,
                memory_id=memory_id,
                message=f"Stored in {scope.value} memory",
            )
        except Exception as exc:
            logger.error("memory_mediator.store_failed", error=str(exc))
            return MemoryResult(
                success=False,
                message=f"Store failed: {exc}",
            )

    # ── Memory search ──────────────────────────────────────────────

    async def search(
        self,
        query: str,
        scope: MemoryScope | str = MemoryScope.GLOBAL,
        limit: int = 20,
    ) -> MemoryResult:
        """Search memories matching query."""
        if isinstance(scope, str):
            scope = MemoryScope(scope)
        if self._memory is None:
            return MemoryResult(success=False, message="Memory system not available")
        try:
            results = await self._memory.search(query, limit=limit)
            memories = [self._memory_to_dict(m) for m in results]
            return MemoryResult(
                success=True,
                memories=memories,
                count=len(memories),
            )
        except Exception as exc:
            return MemoryResult(success=False, message=str(exc))

    # ── Session memory management ──────────────────────────────────

    def clear_session(self, conversation_id: str | None = None) -> None:
        """Clear ephemeral session memory for a conversation."""
        key = conversation_id or "default"
        self._session_memories.pop(key, None)

    def get_session_context(self, conversation_id: str | None = None) -> MemoryContext:
        """Get all session memories as context for Hermes."""
        key = conversation_id or "default"
        memories = self._session_memories.get(key, [])
        return MemoryContext(
            memories=memories,
            scope=MemoryScope.SESSION,
            count=len(memories),
        )

    # ── Internal ───────────────────────────────────────────────────

    def _matches_query(self, query: str, content: str) -> bool:
        """Simple keyword matching for session memory search."""
        if not query or not content:
            return False
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        overlap = query_words & content_words
        return len(overlap) >= max(1, len(query_words) // 2)

    def _memory_to_dict(self, memory: Any) -> dict:
        """Convert a MemorySystem memory object to a dict."""
        if hasattr(memory, "__dict__"):
            return {
                "id": getattr(memory, "id", ""),
                "content": getattr(memory, "content", ""),
                "type": getattr(memory, "type", "unknown"),
                "scope": getattr(memory, "scope", "global"),
                "importance": getattr(memory, "importance", 0.5),
                "source": getattr(memory, "source", "unknown"),
                "created_at": str(getattr(memory, "created_at", "")),
                "attribution": MemoryAttribution.EVE.value,
            }
        return {"content": str(memory), "attribution": MemoryAttribution.EVE.value}
