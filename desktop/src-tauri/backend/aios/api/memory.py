"""Memory API routes — CRUD, search, traversal over Memory Core graph."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(tags=["memory"])


class NodeCreateRequest(BaseModel):
    type: str = "custom"
    subtype: str = ""
    title: str = ""
    summary: str | None = None
    source: str = ""
    metadata: dict | None = None
    tags: list[str] | None = None
    importance: float | None = None
    confidence: float | None = None
    pinned: bool | None = None


class NodeUpdateRequest(BaseModel):
    title: str | None = None
    summary: str | None = None
    source: str | None = None
    metadata: dict | None = None
    tags: list[str] | None = None
    importance: float | None = None
    confidence: float | None = None
    pinned: bool | None = None
    archived: bool | None = None


class EdgeCreateRequest(BaseModel):
    source_node_id: str
    source_node_type: str
    target_node_id: str
    target_node_type: str
    edge_type: str = "related_to"
    strength: float | None = None
    weight: float | None = None
    metadata: dict | None = None


class SearchRequest(BaseModel):
    keyword: str | None = None
    filters: dict | None = None
    relationship: dict | None = None
    options: dict | None = None


class TraversalRequest(BaseModel):
    node_id: str
    node_type: str = "custom"
    max_depth: int = 3
    edge_types: list[str] | None = None


def _node_to_dict(node) -> dict:
    return {
        "id": node.id.value,
        "type": node.type,
        "subtype": node.subtype,
        "title": node.title,
        "summary": node.summary,
        "created_at": node.createdAt,
        "updated_at": node.updatedAt,
        "last_accessed": node.lastAccessed,
        "source": node.source,
        "tags": list(node.tags),
        "importance": node.importance,
        "confidence": node.confidence,
        "access_count": node.accessCount,
        "pinned": node.pinned,
        "archived": node.archived,
        "status": node.status,
        "verified": node.verified,
        "metadata": dict(node.metadata) if node.metadata else {},
    }


def _edge_to_dict(edge) -> dict:
    return {
        "id": edge.id.value,
        "source_node_id": edge.sourceNodeId.value,
        "source_node_type": edge.sourceNodeId.type,
        "target_node_id": edge.targetNodeId.value,
        "target_node_type": edge.targetNodeId.type,
        "type": edge.type,
        "strength": edge.strength,
        "weight": edge.weight,
        "created_at": edge.createdAt,
        "metadata": dict(edge.metadata) if edge.metadata else {},
    }


@router.get("/memory/nodes")
async def list_nodes(req: Request, type: str | None = None, super_type: str | None = None, limit: int = 100, offset: int = 0):
    ms = req.app.state.memory
    from aios.models.memory import QueryOptions
    opts = QueryOptions(limit=limit, offset=offset)
    if type:
        result = await ms._store.find_by_type(type, opts)
    elif super_type:
        result = await ms._store.find_by_super_type(super_type, opts)
    else:
        result = await ms._store.find_all(opts)
    return {"nodes": [_node_to_dict(n) for n in result.nodes], "total": result.total, "has_more": result.hasMore}


@router.post("/memory/nodes")
async def create_node(req: Request, body: NodeCreateRequest):
    ms = req.app.state.memory
    from aios.models.memory import NodeInput
    node_input = NodeInput(
        type=body.type,
        subtype=body.subtype,
        title=body.title,
        summary=body.summary,
        source=body.source,
        metadata=body.metadata,
        tags=body.tags,
        importance=body.importance,
        confidence=body.confidence,
        pinned=body.pinned,
    )
    node, errors = await ms.create_node(node_input)
    if errors:
        raise HTTPException(status_code=400, detail=[str(e) for e in errors])
    return {"success": True, "node": _node_to_dict(node)}


@router.get("/memory/nodes/{node_id}")
async def get_node(req: Request, node_id: str, node_type: str = "custom"):
    ms = req.app.state.memory
    from aios.models.memory import NodeId
    nid = NodeId(value=node_id, type=node_type)
    node = await ms.get_node(nid)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return _node_to_dict(node)


@router.patch("/memory/nodes/{node_id}")
async def update_node(req: Request, node_id: str, body: NodeUpdateRequest, node_type: str = "custom"):
    ms = req.app.state.memory
    from aios.models.memory import NodeId
    nid = NodeId(value=node_id, type=node_type)
    partial = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    node, errors = await ms.update_node(nid, partial)
    if errors:
        raise HTTPException(status_code=400, detail=[str(e) for e in errors])
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return {"success": True, "node": _node_to_dict(node)}


@router.delete("/memory/nodes/{node_id}")
async def delete_node(req: Request, node_id: str, node_type: str = "custom"):
    ms = req.app.state.memory
    from aios.models.memory import NodeId
    nid = NodeId(value=node_id, type=node_type)
    deleted = await ms.delete_node(nid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Node not found")
    return {"success": True}


@router.post("/memory/edges")
async def create_edge(req: Request, body: EdgeCreateRequest):
    ms = req.app.state.memory
    from aios.models.memory import NodeId, EdgeInput
    edge_input = EdgeInput(
        sourceNodeId=NodeId(value=body.source_node_id, type=body.source_node_type),
        targetNodeId=NodeId(value=body.target_node_id, type=body.target_node_type),
        type=body.edge_type,
        strength=body.strength,
        weight=body.weight,
        metadata=body.metadata,
    )
    edge, errors = await ms.create_edge(edge_input)
    if errors:
        raise HTTPException(status_code=400, detail=[str(e) for e in errors])
    if not edge:
        raise HTTPException(status_code=400, detail="Failed to create edge")
    return {"success": True, "edge": _edge_to_dict(edge)}


@router.delete("/memory/edges/{edge_id}")
async def delete_edge(req: Request, edge_id: str):
    ms = req.app.state.memory
    from aios.models.memory import EdgeId
    eid = EdgeId(value=edge_id)
    deleted = await ms.delete_edge(eid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Edge not found")
    return {"success": True}


@router.post("/memory/search")
async def search_memory(req: Request, body: SearchRequest):
    ms = req.app.state.memory
    from aios.models.memory import SearchQuery, SearchFilters, QueryOptions
    query = SearchQuery(
        keyword=body.keyword,
        filters=SearchFilters(**(body.filters or {})),
        relationship=body.relationship,
        options=QueryOptions(**(body.options or {})),
    )
    result = await ms.search_nodes(query)
    return {
        "nodes": [_node_to_dict(n) for n in result.nodes],
        "total": result.total,
        "has_more": result.hasMore,
    }


@router.post("/memory/traverse")
async def traverse_graph(req: Request, body: TraversalRequest):
    ms = req.app.state.memory
    from aios.models.memory import NodeId
    nid = NodeId(value=body.node_id, type=body.node_type)
    result = await ms.bfs(nid, max_depth=body.max_depth, edge_types=body.edge_types)
    return {
        "nodes": [_node_to_dict(n) for n in result.nodes],
        "edges": [_edge_to_dict(e) for e in result.edges],
        "depth": result.depth,
    }


@router.get("/memory/stats")
async def memory_stats(req: Request):
    ms = req.app.state.memory
    stats = await ms.stats()
    return {
        "total_nodes": stats.totalNodes,
        "total_edges": stats.totalEdges,
        "by_type": stats.byType,
        "by_super_type": stats.bySuperType,
        "total_archived": stats.totalArchived,
        "total_pinned": stats.totalPinned,
        "avg_edges_per_node": stats.averageEdgesPerNode,
    }


@router.post("/memory/snapshot")
async def export_snapshot(req: Request):
    ms = req.app.state.memory
    snap = await ms.snapshot()
    return {
        "nodes": [_node_to_dict(n) for n in snap.nodes],
        "edges": [_edge_to_dict(e) for e in snap.edges],
        "timestamp": snap.timestamp,
    }


@router.put("/memory/snapshot")
async def import_snapshot(req: Request, body: dict):
    ms = req.app.state.memory
    from aios.models.memory import MemorySnapshot, MemoryNode, MemoryEdge, NodeId, EdgeId
    nodes = []
    for n in body.get("nodes", []):
        node = MemoryNode(
            id=NodeId(value=n["id"], type=n["type"]),
            type=n["type"],
            subtype=n.get("subtype", ""),
            title=n.get("title", ""),
            summary=n.get("summary", ""),
            createdAt=n.get("created_at", 0),
            updatedAt=n.get("updated_at", 0),
            lastAccessed=n.get("last_accessed", 0),
            source=n.get("source", ""),
            metadata=n.get("metadata", {}),
            tags=n.get("tags", []),
            importance=n.get("importance", 1.0),
            confidence=n.get("confidence", 1.0),
            accessCount=n.get("access_count", 0),
            pinned=n.get("pinned", False),
            archived=n.get("archived", False),
            verified=n.get("verified", False),
            verificationMethod=n.get("verification_method", ""),
            status=n.get("status", "active"),
        )
        nodes.append(node)
    edges = []
    for e in body.get("edges", []):
        edge = MemoryEdge(
            id=EdgeId(value=e["id"]),
            sourceNodeId=NodeId(value=e["source_node_id"], type=e["source_node_type"]),
            targetNodeId=NodeId(value=e["target_node_id"], type=e["target_node_type"]),
            type=e["type"],
            strength=e.get("strength", 1.0),
            weight=e.get("weight", 1.0),
            metadata=e.get("metadata", {}),
            createdAt=e.get("created_at", 0),
        )
        edges.append(edge)
    snapshot = MemorySnapshot(nodes=nodes, edges=edges)
    await ms.load_snapshot(snapshot)
    return {"success": True, "node_count": len(nodes), "edge_count": len(edges)}
