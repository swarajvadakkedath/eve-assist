"""API routes for AI Provider Management."""

from aios.utils.tracer import trace_async
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(tags=["providers"])


class AddProviderRequest(BaseModel):
    provider_type: str
    name: str | None = None
    endpoint_url: str | None = None
    api_key: str | None = None
    organization: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    streaming_enabled: bool = True
    models_enabled: list[str] | None = None


class UpdateProviderRequest(BaseModel):
    name: str | None = None
    endpoint_url: str | None = None
    api_key: str | None = None
    organization: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    streaming_enabled: bool | None = None
    model_updates: list[dict] | None = None


class ReorderRequest(BaseModel):
    provider_ids: list[str]


class RoutingEntry(BaseModel):
    id: str
    label: str | None = None
    provider_id: str | None = None
    model_id: str | None = None


class ToggleModelRequest(BaseModel):
    model_id: str
    enabled: bool


class SetRoutingRequest(BaseModel):
    routing: list[RoutingEntry]


def _get_manager(request: Request):
    manager = getattr(request.app.state, "provider_manager", None)
    if not manager:
        raise HTTPException(status_code=503, detail="Provider manager not initialized")
    return manager


@router.get("/api/v1/providers")
@trace_async
async def list_providers(request: Request):
    manager = _get_manager(request)
    return {"providers": manager.list_providers()}


@router.get("/api/v1/providers/available-types")
@trace_async
async def list_available_types(request: Request):
    manager = _get_manager(request)
    return {"types": manager.get_available_types()}


@router.get("/api/v1/providers/test-all")
@trace_async
async def test_all_connections(request: Request):
    manager = _get_manager(request)
    results = await manager.test_all_connections()
    return {"results": results}


@router.post("/api/v1/providers")
@trace_async
async def add_provider(body: AddProviderRequest, request: Request):
    manager = _get_manager(request)
    try:
        result = manager.add_provider(
            provider_type=body.provider_type,
            name=body.name,
            endpoint_url=body.endpoint_url,
            api_key=body.api_key,
            organization=body.organization,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
            streaming_enabled=body.streaming_enabled,
            models_enabled=body.models_enabled,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/v1/providers/{provider_id}")
@trace_async
async def get_provider(provider_id: str, request: Request):
    manager = _get_manager(request)
    result = manager.get_provider(provider_id)
    if not result:
        raise HTTPException(status_code=404, detail="Provider not found")
    return result


@router.put("/api/v1/providers/{provider_id}")
@trace_async
async def update_provider(provider_id: str, body: UpdateProviderRequest, request: Request):
    manager = _get_manager(request)
    try:
        result = manager.update_provider(
            provider_id=provider_id,
            name=body.name,
            endpoint_url=body.endpoint_url,
            api_key=body.api_key,
            organization=body.organization,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
            streaming_enabled=body.streaming_enabled,
            model_updates=body.model_updates,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/api/v1/providers/{provider_id}")
@trace_async
async def remove_provider(provider_id: str, request: Request):
    manager = _get_manager(request)
    try:
        manager.remove_provider(provider_id)
        return {"status": "ok"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/api/v1/providers/{provider_id}/default")
@trace_async
async def set_default_provider(provider_id: str, request: Request):
    manager = _get_manager(request)
    try:
        result = manager.set_default_provider(provider_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/api/v1/providers/reorder")
@trace_async
async def reorder_providers(body: ReorderRequest, request: Request):
    manager = _get_manager(request)
    manager.reorder_providers(body.provider_ids)
    return {"status": "ok"}


@router.post("/api/v1/providers/{provider_id}/test")
@trace_async
async def test_connection(provider_id: str, request: Request):
    manager = _get_manager(request)
    result = await manager.test_connection(provider_id)
    return result


@router.get("/api/v1/providers/{provider_id}/models")
@trace_async
async def fetch_models(provider_id: str, request: Request):
    manager = _get_manager(request)
    try:
        models = await manager.fetch_models(provider_id)
        return {"models": models}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/api/v1/providers/{provider_id}/models")
@trace_async
async def toggle_model(provider_id: str, body: ToggleModelRequest, request: Request):
    manager = _get_manager(request)
    try:
        result = manager.toggle_model(provider_id, body.model_id, body.enabled)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/api/v1/providers/{provider_id}/models/refresh")
@trace_async
async def refresh_models(provider_id: str, request: Request):
    manager = _get_manager(request)
    try:
        models = await manager.refresh_models(provider_id)
        return {"models": models}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api/v1/routing")
@trace_async
async def get_routing(request: Request):
    manager = _get_manager(request)
    return {"routing": manager.get_routing()}


@router.put("/api/v1/routing")
@trace_async
async def set_routing(body: SetRoutingRequest, request: Request):
    manager = _get_manager(request)
    manager.set_routing([r.model_dump() for r in body.routing])
    return {"routing": manager.get_routing()}
