"""Memory data models — nodes, edges, types, and query types for Memory Core."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from typing import Literal

NodeSuperType = Literal["action", "observation", "knowledge", "artifact", "entity", "meta"]
NodeStatus = Literal["active", "archived", "deleted"]
EdgeDirection = Literal["outgoing", "incoming", "both"]
SortOrder = Literal["asc", "desc"]
SortField = Literal["createdAt", "updatedAt", "lastAccessed", "importance", "confidence", "accessCount", "title"]


@dataclass(frozen=True)
class NodeId:
    value: str
    type: str

    def __str__(self) -> str:
        return f"{self.type}:{self.value}"


@dataclass(frozen=True)
class EdgeId:
    value: str

    def __str__(self) -> str:
        return self.value


@dataclass
class MemoryNode:
    id: NodeId = field(default_factory=lambda: NodeId(value=uuid4().hex, type="custom"))
    type: str = "custom"
    subtype: str = ""
    title: str = ""
    summary: str = ""
    createdAt: int = 0
    updatedAt: int = 0
    lastAccessed: int = 0
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    importance: float = 1.0
    confidence: float = 1.0
    accessCount: int = 0
    pinned: bool = False
    archived: bool = False
    verified: bool = False
    verificationMethod: str = ""
    status: NodeStatus = "active"

    def __post_init__(self):
        now = datetime.now().timestamp() * 1000
        now_int = int(now)
        object.__setattr__(self, "createdAt", now_int)
        object.__setattr__(self, "updatedAt", now_int)
        object.__setattr__(self, "lastAccessed", now_int)


@dataclass
class MemoryEdge:
    id: EdgeId = field(default_factory=lambda: EdgeId(value=uuid4().hex))
    sourceNodeId: NodeId = field(default_factory=lambda: NodeId(value="", type=""))
    targetNodeId: NodeId = field(default_factory=lambda: NodeId(value="", type=""))
    type: str = "related_to"
    strength: float = 1.0
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    createdAt: int = 0

    def __post_init__(self):
        if not self.createdAt:
            object.__setattr__(self, "createdAt", int(datetime.now().timestamp() * 1000))


@dataclass
class NodeTypeDefinition:
    name: str
    superType: NodeSuperType
    description: str = ""
    allowedEdgeTypes: list[str] = field(default_factory=list)
    allowedAsTargetFor: list[str] = field(default_factory=list)
    defaultMetadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EdgeTypeDefinition:
    name: str
    description: str = ""
    allowedSourceTypes: list[str] = field(default_factory=list)
    allowedTargetTypes: list[str] = field(default_factory=list)
    directional: bool = True
    defaultMetadata: dict[str, Any] = field(default_factory=dict)


class MemoryProvider:
    name: str = ""
    def registerTypes(self) -> None: ...
    def canHandleNode(self, node: MemoryNode) -> bool: ...
    def canHandleEdge(self, edge: MemoryEdge) -> bool: ...
    def validate(self) -> list[str]: ...


@dataclass
class NodeChange:
    type: str  # created | updated | deleted | archived | restored
    node: MemoryNode
    previous: MemoryNode | None = None
    timestamp: int = 0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = int(datetime.now().timestamp() * 1000)


@dataclass
class EdgeChange:
    type: str  # created | deleted
    edge: MemoryEdge
    timestamp: int = 0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = int(datetime.now().timestamp() * 1000)


@dataclass
class SearchFilters:
    types: list[str] | None = None
    superTypes: list[NodeSuperType] | None = None
    tags: list[str] | None = None
    statuses: list[NodeStatus] | None = None
    sources: list[str] | None = None
    dateFrom: int | None = None
    dateTo: int | None = None
    importanceMin: float | None = None
    importanceMax: float | None = None
    confidenceMin: float | None = None
    confidenceMax: float | None = None
    pinned: bool | None = None
    archived: bool | None = None


@dataclass
class RelationshipFilter:
    edgeTypes: list[str] | None = None
    maxDepth: int = 3
    direction: EdgeDirection = "both"


@dataclass
class QueryOptions:
    sortField: SortField = "updatedAt"
    sortOrder: SortOrder = "desc"
    limit: int | None = None
    offset: int = 0


@dataclass
class SearchQuery:
    keyword: str | None = None
    filters: SearchFilters | None = None
    relationship: dict | None = None  # { seedNodeId: NodeId, filter: RelationshipFilter }
    options: QueryOptions = field(default_factory=QueryOptions)


@dataclass
class SearchResult:
    nodes: list[MemoryNode]
    total: int
    hasMore: bool = False
    query: SearchQuery | None = None


@dataclass
class TraversalResult:
    nodes: list[MemoryNode]
    edges: list[MemoryEdge]
    depth: int = 0
    path: list[NodeId] | None = None


@dataclass
class ValidationError:
    code: str
    message: str
    nodeId: NodeId | None = None
    edgeId: EdgeId | None = None
    field: str | None = None


@dataclass
class CircularDependency:
    path: list[NodeId]
    edge: MemoryEdge | None = None


@dataclass
class MemorySnapshot:
    nodes: list[MemoryNode]
    edges: list[MemoryEdge]
    timestamp: int = 0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = int(datetime.now().timestamp() * 1000)


@dataclass
class NodeInput:
    id: str | None = None
    type: str = "custom"
    subtype: str = ""
    title: str = ""
    summary: str | None = None
    source: str = ""
    metadata: dict[str, Any] | None = None
    tags: list[str] | None = None
    importance: float | None = None
    confidence: float | None = None
    pinned: bool | None = None
    archived: bool | None = None
    verified: bool | None = None
    verificationMethod: str | None = None
    createdAt: int | None = None
    status: NodeStatus | None = None


@dataclass
class EdgeInput:
    id: str | None = None
    sourceNodeId: NodeId = field(default_factory=lambda: NodeId(value="", type=""))
    targetNodeId: NodeId = field(default_factory=lambda: NodeId(value="", type=""))
    type: str = "related_to"
    strength: float | None = None
    weight: float | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class MemoryGraphStats:
    totalNodes: int = 0
    totalEdges: int = 0
    bySuperType: dict[str, int] = field(default_factory=dict)
    byType: dict[str, int] = field(default_factory=dict)
    totalArchived: int = 0
    totalPinned: int = 0
    averageEdgesPerNode: float = 0.0


MemoryEvent = (
    dict  # { type: str, payload: NodeChange | EdgeChange | dict }
)
