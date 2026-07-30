"""Capability Registry API routes."""

from fastapi import APIRouter, Request, Query
from pydantic import BaseModel

router = APIRouter(tags=["capabilities"])


class CapabilitySearchRequest(BaseModel):
    query: str
    limit: int = 10


def _capability_to_dict(c):
    return {
        "id": c.id,
        "name": c.name,
        "description": c.description,
        "provider_type": c.provider_type,
        "provider_id": c.provider_id,
        "parameters": c.parameters,
        "returns": c.returns,
        "permission_level": c.permission_level,
        "tags": c.tags,
        "version": c.version,
        "quality": c.quality,
        "supported_interfaces": c.supported_interfaces,
        "supports_streaming": c.supports_streaming,
        "supports_cancellation": c.supports_cancellation,
        "estimated_latency": c.estimated_latency,
        "estimated_cost": c.estimated_cost,
        "reliability_score": c.reliability_score,
        "requires_confirmation": c.requires_confirmation,
        "related_capabilities": c.related_capabilities,
    }


@router.get("/capabilities")
async def list_capabilities(req: Request, tag: str = None):
    cr = req.app.state.capability_registry
    caps = await cr.list_capabilities(tag)
    return {"capabilities": [_capability_to_dict(c) for c in caps]}


@router.post("/capabilities/search")
async def search_capabilities(req: Request, body: CapabilitySearchRequest):
    cr = req.app.state.capability_registry
    caps = await cr.find_capability(body.query)
    return {
        "query": body.query,
        "results": [_capability_to_dict(c) for c in caps[:body.limit]],
        "count": min(len(caps), body.limit),
    }


@router.get("/capabilities/{capability_id}")
async def get_capability(req: Request, capability_id: str):
    cr = req.app.state.capability_registry
    caps = await cr.find_capability(capability_id)
    if not caps:
        return {"error": "Capability not found"}, 404
    return _capability_to_dict(caps[0])


@router.post("/capabilities/rank")
async def rank_capabilities(req: Request, body: CapabilitySearchRequest):
    cr = req.app.state.capability_registry
    ranked = await cr.rank_for_task(body.query)
    items = [
        {**_capability_to_dict(cap), "relevance_score": round(score, 4)}
        for cap, score in ranked[:body.limit]
    ]
    return {"query": body.query, "results": items, "count": len(items)}


@router.get("/capabilities/{capability_id}/recommend")
async def recommend_capabilities(req: Request, capability_id: str, max_results: int = Query(5, ge=1, le=20)):
    cr = req.app.state.capability_registry
    caps = await cr.recommend_alternatives(capability_id, max_results)
    return {"capability_id": capability_id, "recommendations": [_capability_to_dict(c) for c in caps], "count": len(caps)}


@router.get("/capabilities/filter/by-interface/{interface}")
async def filter_by_interface(req: Request, interface: str):
    cr = req.app.state.capability_registry
    caps = await cr.filter_by_interface(interface)
    return {"interface": interface, "capabilities": [_capability_to_dict(c) for c in caps], "count": len(caps)}


@router.get("/capabilities/filter/by-permission")
async def filter_by_permission(req: Request, min_level: int = Query(0, ge=0), max_level: int = Query(None)):
    cr = req.app.state.capability_registry
    caps = await cr.filter_by_permission(min_level, max_level)
    return {"min_level": min_level, "max_level": max_level, "capabilities": [_capability_to_dict(c) for c in caps], "count": len(caps)}
