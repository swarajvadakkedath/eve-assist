"""MemoryGraph — in-memory graph with dual-indexed adjacency."""

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
    MemorySnapshot,
    MemoryGraphStats,
    NodeSuperType,
    NodeChange,
    EdgeChange,
)


def _generate_node_id(type_str: str) -> NodeId:
    return NodeId(value=uuid4().hex, type=type_str)


def _generate_edge_id() -> EdgeId:
    return EdgeId(value=uuid4().hex)


class MemoryGraph:
    def __init__(self):
        self._nodes: dict[str, MemoryNode] = {}
        self._edges: dict[str, MemoryEdge] = {}
        self._adjacency_out: dict[str, set[str]] = {}
        self._adjacency_in: dict[str, set[str]] = {}
        self._node_by_type: dict[str, set[str]] = {}
        self._node_listeners: list[callable] = []
        self._edge_listeners: list[callable] = []

    def on_node_change(self, listener: callable) -> callable:
        self._node_listeners.append(listener)
        return lambda: self._node_listeners.remove(listener)

    def on_edge_change(self, listener: callable) -> callable:
        self._edge_listeners.append(listener)
        return lambda: self._edge_listeners.remove(listener)

    def _notify_node(self, change: NodeChange):
        for fn in self._node_listeners:
            fn(change)

    def _notify_edge(self, change: EdgeChange):
        for fn in self._edge_listeners:
            fn(change)

    def _node_key(self, node_id: NodeId) -> str:
        return f"{node_id.type}:{node_id.value}"

    def add_node(self, input: NodeInput) -> MemoryNode:
        now = input.createdAt or int(datetime.now().timestamp() * 1000)
        node_id = NodeId(value=input.id or uuid4().hex, type=input.type) if input.id else _generate_node_id(input.type)
        node = MemoryNode(
            id=node_id,
            type=input.type,
            subtype=input.subtype,
            title=input.title,
            summary=input.summary or "",
            createdAt=now,
            updatedAt=now,
            lastAccessed=now,
            source=input.source,
            metadata=dict(input.metadata) if input.metadata else {},
            tags=list(input.tags) if input.tags else [],
            importance=input.importance if input.importance is not None else 1.0,
            confidence=input.confidence if input.confidence is not None else 1.0,
            accessCount=0,
            pinned=input.pinned or False,
            archived=input.archived or False,
            verified=input.verified or False,
            verificationMethod=input.verificationMethod or "",
            status=input.status or "active",
        )
        key = self._node_key(node.id)
        self._nodes[key] = node
        self._add_type_index(node)
        self._notify_node(NodeChange(type="created", node=node, timestamp=now))
        return node

    def update_node(self, node_id: NodeId, partial: dict[str, Any]) -> MemoryNode | None:
        key = self._node_key(node_id)
        existing = self._nodes.get(key)
        if not existing:
            return None
        now = int(datetime.now().timestamp() * 1000)
        updated_dict = {
            k: v for k, v in vars(existing).items()
            if not k.startswith("_")
        }
        updated_dict.update(partial)
        updated_dict["id"] = existing.id
        updated_dict["updatedAt"] = now
        updated = MemoryNode(**updated_dict)
        self._nodes[key] = updated
        self._notify_node(NodeChange(type="updated", node=updated, previous=existing, timestamp=now))
        return updated

    def delete_node(self, node_id: NodeId) -> bool:
        key = self._node_key(node_id)
        existing = self._nodes.get(key)
        if not existing:
            return False
        now = int(datetime.now().timestamp() * 1000)
        for edge_key in list(self._edges.keys()):
            edge = self._edges[edge_key]
            if self._node_key(edge.sourceNodeId) == key or self._node_key(edge.targetNodeId) == key:
                self._remove_edge_data(edge.id)
        self._nodes.pop(key, None)
        self._remove_type_index(existing)
        self._adjacency_out.pop(key, None)
        self._adjacency_in.pop(key, None)
        for adj in self._adjacency_out.values():
            adj.discard(key)
        for adj in self._adjacency_in.values():
            adj.discard(key)
        self._notify_node(NodeChange(type="deleted", node=existing, timestamp=now))
        return True

    def get_node(self, node_id: NodeId) -> MemoryNode | None:
        key = self._node_key(node_id)
        node = self._nodes.get(key)
        if node:
            self._touch_node(node_id)
        return node

    def get_node_by_id(self, node_id: NodeId) -> MemoryNode | None:
        return self._nodes.get(self._node_key(node_id))

    def has_node(self, node_id: NodeId) -> bool:
        return self._node_key(node_id) in self._nodes

    def get_all_nodes(self) -> list[MemoryNode]:
        return list(self._nodes.values())

    def get_nodes_by_type(self, type_str: str) -> list[MemoryNode]:
        keys = self._node_by_type.get(type_str)
        if not keys:
            return []
        return [self._nodes[k] for k in keys if k in self._nodes]

    def get_nodes_by_super_type(self, super_type: NodeSuperType) -> list[MemoryNode]:
        return [n for n in self._nodes.values() if n.type.split(":")[0] == super_type]

    def archive_node(self, node_id: NodeId) -> MemoryNode | None:
        key = self._node_key(node_id)
        existing = self._nodes.get(key)
        if not existing:
            return None
        now = int(datetime.now().timestamp() * 1000)
        updated_dict = {k: v for k, v in vars(existing).items() if not k.startswith("_")}
        updated_dict.update({"archived": True, "status": "archived", "updatedAt": now})
        updated_dict["id"] = existing.id
        node = MemoryNode(**updated_dict)
        self._nodes[key] = node
        self._notify_node(NodeChange(type="archived", node=node, timestamp=now))
        return node

    def restore_node(self, node_id: NodeId) -> MemoryNode | None:
        key = self._node_key(node_id)
        existing = self._nodes.get(key)
        if not existing:
            return None
        now = int(datetime.now().timestamp() * 1000)
        updated_dict = {k: v for k, v in vars(existing).items() if not k.startswith("_")}
        updated_dict.update({"archived": False, "status": "active", "updatedAt": now})
        updated_dict["id"] = existing.id
        node = MemoryNode(**updated_dict)
        self._nodes[key] = node
        self._notify_node(NodeChange(type="restored", node=node, timestamp=now))
        return node

    def add_edge(self, input: EdgeInput) -> MemoryEdge | None:
        source_key = self._node_key(input.sourceNodeId)
        target_key = self._node_key(input.targetNodeId)
        if source_key not in self._nodes or target_key not in self._nodes:
            return None
        now = int(datetime.now().timestamp() * 1000)
        edge_id = EdgeId(value=input.id or uuid4().hex) if input.id else _generate_edge_id()
        edge = MemoryEdge(
            id=edge_id,
            sourceNodeId=input.sourceNodeId,
            targetNodeId=input.targetNodeId,
            type=input.type,
            strength=input.strength if input.strength is not None else 1.0,
            weight=input.weight if input.weight is not None else 1.0,
            metadata=dict(input.metadata) if input.metadata else {},
            createdAt=now,
        )
        self._edges[edge.id.value] = edge
        if source_key not in self._adjacency_out:
            self._adjacency_out[source_key] = set()
        self._adjacency_out[source_key].add(target_key)
        if target_key not in self._adjacency_in:
            self._adjacency_in[target_key] = set()
        self._adjacency_in[target_key].add(source_key)
        self._notify_edge(EdgeChange(type="created", edge=edge, timestamp=now))
        return edge

    def delete_edge(self, edge_id: EdgeId) -> bool:
        return self._remove_edge_data(edge_id)

    def get_edge(self, edge_id: EdgeId) -> MemoryEdge | None:
        return self._edges.get(edge_id.value)

    def get_edges_by_node(self, node_id: NodeId) -> list[MemoryEdge]:
        key = self._node_key(node_id)
        return [
            e for e in self._edges.values()
            if self._node_key(e.sourceNodeId) == key or self._node_key(e.targetNodeId) == key
        ]

    def get_outgoing_edges(self, node_id: NodeId) -> list[MemoryEdge]:
        key = self._node_key(node_id)
        return [e for e in self._edges.values() if self._node_key(e.sourceNodeId) == key]

    def get_incoming_edges(self, node_id: NodeId) -> list[MemoryEdge]:
        key = self._node_key(node_id)
        return [e for e in self._edges.values() if self._node_key(e.targetNodeId) == key]

    def get_outgoing_neighbors(self, node_id: NodeId) -> list[MemoryNode]:
        key = self._node_key(node_id)
        neighbors = self._adjacency_out.get(key)
        if not neighbors:
            return []
        return [self._nodes[k] for k in neighbors if k in self._nodes]

    def get_incoming_neighbors(self, node_id: NodeId) -> list[MemoryNode]:
        key = self._node_key(node_id)
        neighbors = self._adjacency_in.get(key)
        if not neighbors:
            return []
        return [self._nodes[k] for k in neighbors if k in self._nodes]

    def get_neighbors(self, node_id: NodeId) -> list[MemoryNode]:
        seen: set[str] = set()
        result: list[MemoryNode] = []
        for n in self.get_outgoing_neighbors(node_id):
            k = self._node_key(n.id)
            if k not in seen:
                seen.add(k)
                result.append(n)
        for n in self.get_incoming_neighbors(node_id):
            k = self._node_key(n.id)
            if k not in seen:
                seen.add(k)
                result.append(n)
        return result

    def get_connected_edges(self, node_id: NodeId) -> dict[str, list[MemoryEdge]]:
        return {
            "outgoing": self.get_outgoing_edges(node_id),
            "incoming": self.get_incoming_edges(node_id),
        }

    def node_count(self) -> int:
        return len(self._nodes)

    def edge_count(self) -> int:
        return len(self._edges)

    def snapshot(self) -> MemorySnapshot:
        return MemorySnapshot(
            nodes=list(self._nodes.values()),
            edges=list(self._edges.values()),
            timestamp=int(datetime.now().timestamp() * 1000),
        )

    def load_snapshot(self, snapshot: MemorySnapshot):
        self._nodes.clear()
        self._edges.clear()
        self._adjacency_out.clear()
        self._adjacency_in.clear()
        self._node_by_type.clear()
        for node in snapshot.nodes:
            key = self._node_key(node.id)
            self._nodes[key] = node
            self._add_type_index(node)
        for edge in snapshot.edges:
            self._edges[edge.id.value] = edge
            source_key = self._node_key(edge.sourceNodeId)
            target_key = self._node_key(edge.targetNodeId)
            if source_key not in self._adjacency_out:
                self._adjacency_out[source_key] = set()
            self._adjacency_out[source_key].add(target_key)
            if target_key not in self._adjacency_in:
                self._adjacency_in[target_key] = set()
            self._adjacency_in[target_key].add(source_key)

    def clear(self):
        self._nodes.clear()
        self._edges.clear()
        self._adjacency_out.clear()
        self._adjacency_in.clear()
        self._node_by_type.clear()

    def stats(self) -> MemoryGraphStats:
        by_super_type: dict[NodeSuperType, int] = {}
        by_type: dict[str, int] = {}
        total_archived = 0
        total_pinned = 0
        for node in self._nodes.values():
            st = node.type.split(":")[0]
            by_super_type[st] = by_super_type.get(st, 0) + 1
            by_type[node.type] = by_type.get(node.type, 0) + 1
            if node.archived:
                total_archived += 1
            if node.pinned:
                total_pinned += 1
        return MemoryGraphStats(
            totalNodes=self.node_count(),
            totalEdges=self.edge_count(),
            bySuperType=by_super_type,
            byType=by_type,
            totalArchived=total_archived,
            totalPinned=total_pinned,
            averageEdgesPerNode=self.edge_count() / self.node_count() if self.node_count() > 0 else 0.0,
        )

    def _touch_node(self, node_id: NodeId):
        key = self._node_key(node_id)
        node = self._nodes.get(key)
        if node:
            now = int(datetime.now().timestamp() * 1000)
            updated_dict = {k: v for k, v in vars(node).items() if not k.startswith("_")}
            updated_dict.update({"lastAccessed": now, "accessCount": node.accessCount + 1})
            updated_dict["id"] = node.id
            self._nodes[key] = MemoryNode(**updated_dict)

    def _remove_edge_data(self, edge_id: EdgeId) -> bool:
        edge = self._edges.get(edge_id.value)
        if not edge:
            return False
        self._edges.pop(edge_id.value, None)
        source_key = self._node_key(edge.sourceNodeId)
        target_key = self._node_key(edge.targetNodeId)
        if source_key in self._adjacency_out:
            self._adjacency_out[source_key].discard(target_key)
        if target_key in self._adjacency_in:
            self._adjacency_in[target_key].discard(source_key)
        self._notify_edge(EdgeChange(type="deleted", edge=edge, timestamp=int(datetime.now().timestamp() * 1000)))
        return True

    def _add_type_index(self, node: MemoryNode):
        if node.type not in self._node_by_type:
            self._node_by_type[node.type] = set()
        self._node_by_type[node.type].add(self._node_key(node.id))

    def _remove_type_index(self, node: MemoryNode):
        keys = self._node_by_type.get(node.type)
        if keys:
            keys.discard(self._node_key(node.id))
            if not keys:
                del self._node_by_type[node.type]
