"""NodeTypeRegistry, EdgeTypeRegistry, and MemoryRegistry."""

from typing import Any

from aios.models.memory import (
    NodeTypeDefinition,
    EdgeTypeDefinition,
    NodeSuperType,
    NodeId,
    MemoryProvider,
    MemoryNode,
    MemoryEdge,
)


class NodeTypeRegistry:
    def __init__(self):
        self._types: dict[str, NodeTypeDefinition] = {}

    def register(self, defn: NodeTypeDefinition):
        if defn.name not in self._types:
            self._types[defn.name] = defn
        return self

    def register_many(self, defns: list[NodeTypeDefinition]):
        for d in defns:
            self.register(d)
        return self

    def get(self, name: str) -> NodeTypeDefinition | None:
        return self._types.get(name)

    def has(self, name: str) -> bool:
        return name in self._types

    def get_all(self) -> list[NodeTypeDefinition]:
        return list(self._types.values())

    def get_by_super_type(self, super_type: NodeSuperType) -> list[NodeTypeDefinition]:
        return [t for t in self._types.values() if t.superType == super_type]

    def get_allowed_edge_types(self, node_type: str) -> list[str]:
        defn = self._types.get(node_type)
        return list(defn.allowedEdgeTypes) if defn else []

    def is_valid_node_type(self, node_type: str) -> bool:
        return node_type in self._types

    def is_allowed_edge_type(self, node_type: str, edge_type: str) -> bool:
        defn = self._types.get(node_type)
        if not defn:
            return False
        return edge_type in defn.allowedEdgeTypes

    def validate_node_id(self, node_id: NodeId) -> bool:
        return self.is_valid_node_type(node_id.type)

    def get_default_metadata(self, node_type: str) -> dict[str, Any]:
        defn = self._types.get(node_type)
        return dict(defn.defaultMetadata) if defn else {}

    def count(self) -> int:
        return len(self._types)

    def clear(self):
        self._types.clear()


class EdgeTypeRegistry:
    def __init__(self):
        self._types: dict[str, EdgeTypeDefinition] = {}

    def register(self, defn: EdgeTypeDefinition):
        if defn.name not in self._types:
            self._types[defn.name] = defn
        return self

    def register_many(self, defns: list[EdgeTypeDefinition]):
        for d in defns:
            self.register(d)
        return self

    def get(self, name: str) -> EdgeTypeDefinition | None:
        return self._types.get(name)

    def has(self, name: str) -> bool:
        return name in self._types

    def get_all(self) -> list[EdgeTypeDefinition]:
        return list(self._types.values())

    def can_connect(self, source_type: str, edge_type: str, target_type: str) -> bool:
        defn = self._types.get(edge_type)
        if not defn:
            return False
        if defn.allowedSourceTypes and source_type not in defn.allowedSourceTypes:
            return False
        if defn.allowedTargetTypes and target_type not in defn.allowedTargetTypes:
            return False
        return True

    def count(self) -> int:
        return len(self._types)

    def clear(self):
        self._types.clear()


class MemoryRegistry:
    def __init__(self):
        self.nodeTypes = NodeTypeRegistry()
        self.edgeTypes = EdgeTypeRegistry()
        self._providers: dict[str, MemoryProvider] = {}

    def register_provider(self, provider: MemoryProvider):
        self._providers[provider.name] = provider
        provider.registerTypes()
        return self

    def get_provider(self, name: str) -> MemoryProvider | None:
        return self._providers.get(name)

    def get_all_providers(self) -> list[MemoryProvider]:
        return list(self._providers.values())

    def can_handle_node(self, node: MemoryNode) -> bool:
        for p in self._providers.values():
            if p.canHandleNode(node):
                return True
        return False

    def can_handle_edge(self, edge: MemoryEdge) -> bool:
        for p in self._providers.values():
            if p.canHandleEdge(edge):
                return True
        return False

    def validate_all(self) -> list[str]:
        errors: list[str] = []
        for p in self._providers.values():
            errors.extend(p.validate())
        return errors

    def load_defaults(self):
        from .constants import DEFAULT_NODE_TYPES, DEFAULT_EDGE_TYPES
        for nt in DEFAULT_NODE_TYPES:
            self.nodeTypes.register(NodeTypeDefinition(**nt))
        for et in DEFAULT_EDGE_TYPES:
            self.edgeTypes.register(EdgeTypeDefinition(**et))
        return self

    def clear(self):
        self.nodeTypes.clear()
        self.edgeTypes.clear()
        self._providers.clear()


_REGISTRY: MemoryRegistry | None = None


def get_memory_registry() -> MemoryRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = MemoryRegistry().load_defaults()
    return _REGISTRY


def set_memory_registry(registry: MemoryRegistry):
    global _REGISTRY
    _REGISTRY = registry


def reset_memory_registry():
    global _REGISTRY
    _REGISTRY = None
