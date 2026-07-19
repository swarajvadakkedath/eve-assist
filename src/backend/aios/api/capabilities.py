"""Capability Registry API routes."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["capabilities"])


class CapabilitySearchRequest(BaseModel):
    query: str
    limit: int = 10


@router.get("/capabilities")
async def list_capabilities(req: Request, tag: str = None):
    cr = req.app.state.capability_registry
    caps = await cr.list_capabilities(tag)
    return {
        "capabilities": [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "provider_type": c.provider_type,
                "provider_id": c.provider_id,
                "permission_level": c.permission_level,
                "tags": c.tags,
                "version": c.version,
            }
            for c in caps
        ]
    }


@router.post("/capabilities/search")
async def search_capabilities(req: Request, body: CapabilitySearchRequest):
    cr = req.app.state.capability_registry
    caps = await cr.find_capability(body.query)
    return {
        "query": body.query,
        "results": [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "provider_type": c.provider_type,
                "provider_id": c.provider_id,
                "quality": c.quality,
            }
            for c in caps[:body.limit]
        ],
        "count": min(len(caps), body.limit),
    }


@router.get("/capabilities/{capability_id}")
async def get_capability(req: Request, capability_id: str):
    cr = req.app.state.capability_registry
    caps = await cr.find_capability(capability_id)
    if not caps:
        return {"error": "Capability not found"}, 404
    c = caps[0]
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
    }
