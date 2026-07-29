"""MemoryStore — facade combining graph, traversal, query, events, validation."""

from datetime import datetime
from typing import Any

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
    MemoryGraphStats,
    ValidationError,
    TraversalResult,
)
from .graph import MemoryGraph
from .traversal import GraphTraversal
from .query import QueryEngine
from .events import MemoryEventBus
from .validation import MemoryValidation
from ..event_bus import EventBus


class MemoryStore:
    def __init__(self, event_bus: EventBus | None = None):
        self.graph = MemoryGraph()
        self.events = MemoryEventBus()
        self.traversal = GraphTraversal(self.graph)
        self.query = QueryEngine(self.graph, self.traversal)
        self.validation = MemoryValidation(self.graph)
        self._backend_event_bus = event_bus

        self.graph.on_node_change(self._on_node_change)
        self.graph.on_edge_change(self._on_edge_change)

    def _on_node_change(self, change: dict):
        event_map = {
            "created": "node:created",
            "updated": "node:updated",
            "deleted": "node:deleted",
            "archived": "node:archived",
            "restored": "node:restored",
        }
        event_type = event_map.get(change.type, f"node:{change.type}")
        self.events.publish(event_type, change)
        if self._backend_event_bus:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(self._backend_event_bus.publish(
                        f"memory:{event_type}",
                        {"node_id": str(change.node.id), "type": change.node.type, "title": change.node.title, "timestamp": change.timestamp},
                        source="memory_system",
                    ))
            except RuntimeError:
                pass

    def _on_edge_change(self, change: dict):
        event_map = {
            "created": "edge:created",
            "deleted": "edge:deleted",
        }
        event_type = event_map.get(change.type, f"edge:{change.type}")
        self.events.publish(event_type, change)
        if self._backend_event_bus:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(self._backend_event_bus.publish(
                        f"memory:{event_type}",
                        {"edge_id": str(change.edge.id), "type": change.edge.type, "source_node_id": str(change.edge.sourceNodeId), "target_node_id": str(change.edge.targetNodeId), "timestamp": change.timestamp},
                        source="memory_system",
                    ))
            except RuntimeError:
                pass

    def create_node(self, input: NodeInput) -> tuple[MemoryNode | None, list[ValidationError]]:
        errors = self.validation.validate_node_input(input)
        if errors:
            return None, errors
        node = self.graph.add_node(input)
        return node, []

    def get_node(self, node_id: NodeId) -> MemoryNode | None:
        return self.graph.get_node(node_id)

    def update_node(self, node_id: NodeId, partial: dict[str, Any]) -> tuple[MemoryNode | None, list[ValidationError]]:
        existing = self.graph.get_node_by_id(node_id)
        if not existing:
            return None, [ValidationError(code="NOT_FOUND", message=f"Node {node_id} not found")]
        node = self.graph.update_node(node_id, partial)
        return node, []

    def delete_node(self, node_id: NodeId) -> bool:
        return self.graph.delete_node(node_id)

    def archive_node(self, node_id: NodeId) -> MemoryNode | None:
        return self.graph.archive_node(node_id)

    def restore_node(self, node_id: NodeId) -> MemoryNode | None:
        return self.graph.restore_node(node_id)

    def create_edge(self, input: EdgeInput) -> tuple[MemoryEdge | None, list[ValidationError]]:
        errors = self.validation.validate_edge_input(input)
        if not errors:
            source_node = self.graph.get_node_by_id(input.sourceNodeId)
            target_node = self.graph.get_node_by_id(input.targetNodeId)
            if not source_node:
                errors.append(ValidationError(code="SOURCE_NOT_FOUND", message=f"Source node {input.sourceNodeId} not found"))
            if not target_node:
                errors.append(ValidationError(code="TARGET_NOT_FOUND", message=f"Target node {input.targetNodeId} not found"))
        if errors:
            return None, errors
        cycle = self.validation.would_create_cycle(input.sourceNodeId, input.targetNodeId)
        if cycle:
            return None, [ValidationError(code="CIRCULAR_DEPENDENCY", message="Adding this edge would create a circular dependency")]
        edge = self.graph.add_edge(input)
        if edge:
            self.events.publish("relationship:changed", {"nodeId": input.sourceNodeId, "timestamp": int(datetime.now().timestamp() * 1000)})
        return edge, []

    def get_edge(self, edge_id: EdgeId) -> MemoryEdge | None:
        return self.graph.get_edge(edge_id)

    def delete_edge(self, edge_id: EdgeId) -> bool:
        deleted = self.graph.delete_edge(edge_id)
        if deleted:
            self.events.publish("relationship:changed", {"timestamp": int(datetime.now().timestamp() * 1000)})
        return deleted

    def search(self, query: SearchQuery) -> SearchResult:
        return self.query.execute(query)

    def search_by_keyword(self, keyword: str, options: QueryOptions | None = None) -> SearchResult:
        return self.query.search_by_keyword(keyword, options)

    def find_all(self, options: QueryOptions | None = None) -> SearchResult:
        return self.query.find_all(options)

    def find_by_type(self, type_str: str, options: QueryOptions | None = None) -> SearchResult:
        return self.query.find_by_type(type_str, options)

    def find_by_super_type(self, super_type: str, options: QueryOptions | None = None) -> SearchResult:
        return self.query.find_by_super_type(super_type, options)

    def bfs(self, start_id: NodeId, max_depth: int = 10, edge_types: list[str] | None = None) -> TraversalResult:
        return self.traversal.bfs(start_id, max_depth, edge_types)

    def dfs(self, start_id: NodeId, max_depth: int = 10, edge_types: list[str] | None = None) -> TraversalResult:
        return self.traversal.dfs(start_id, max_depth, edge_types)

    def find_paths(self, start_id: NodeId, end_id: NodeId, max_depth: int = 10, edge_types: list[str] | None = None) -> list[TraversalResult]:
        return self.traversal.find_paths(start_id, end_id, max_depth, edge_types)

    def find_shortest_path(self, start_id: NodeId, end_id: NodeId, edge_types: list[str] | None = None) -> TraversalResult | None:
        return self.traversal.find_shortest_path(start_id, end_id, edge_types)

    def snapshot(self) -> MemorySnapshot:
        return self.graph.snapshot()

    def load_snapshot(self, snapshot: MemorySnapshot):
        self.graph.load_snapshot(snapshot)

    def stats(self) -> MemoryGraphStats:
        return self.graph.stats()

    def clear(self):
        self.graph.clear()
        self.events.publish("graph:cleared", {"timestamp": int(datetime.now().timestamp() * 1000)})


_STORE: MemoryStore | None = None


def get_memory_store(event_bus: EventBus | None = None) -> MemoryStore:
    global _STORE
    if _STORE is None:
        _STORE = MemoryStore(event_bus=event_bus)
    return _STORE


def set_memory_store(store: MemoryStore):
    global _STORE
    _STORE = store


def reset_memory_store():
    global _STORE
    _STORE = None
