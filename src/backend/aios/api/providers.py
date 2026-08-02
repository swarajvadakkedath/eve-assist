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
    """Return all provider types with registry metadata (needs_endpoint, icon, etc.)."""
    from aios.core.provider_registry import all_as_dicts
    return {"types": all_as_dicts()}


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


# ------------------------------------------------------------------
# Commercial policy endpoints (spec §7-11)
# ------------------------------------------------------------------

class CommercialPolicyRequest(BaseModel):
    policy: str  # "free_only" | "no_direct_paid" | "allow_paid"


@router.get("/api/v1/routing/commercial-policy")
@trace_async
async def get_commercial_policy(request: Request):
    manager = _get_manager(request)
    smart_router = getattr(manager, "_smart_router", None)
    policy = smart_router.commercial_policy.value if smart_router else "allow_paid"
    return {"policy": policy}


@router.put("/api/v1/routing/commercial-policy")
@trace_async
async def set_commercial_policy(body: CommercialPolicyRequest, request: Request):
    from aios.core.routing_types import CommercialPolicy
    try:
        policy = CommercialPolicy(body.policy)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid policy: {body.policy}. Must be free_only, no_direct_paid, or allow_paid")
    manager = _get_manager(request)
    smart_router = getattr(manager, "_smart_router", None)
    if smart_router:
        smart_router.commercial_policy = policy
    return {"policy": policy.value}


# ------------------------------------------------------------------
# Multi-account aggregation endpoints
# ------------------------------------------------------------------

@router.get("/api/v1/providers/models/free")
@trace_async
async def get_all_free_models(request: Request):
    manager = _get_manager(request)
    return {"models": manager.get_all_free_models()}


@router.get("/api/v1/providers/types/{provider_type}/models")
@trace_async
async def get_provider_type_models(provider_type: str, request: Request):
    manager = _get_manager(request)
    return {"models": manager.get_provider_type_models(provider_type)}


@router.get("/api/v1/providers/{provider_id}/models/{model_id}/status")
@trace_async
async def get_model_commercial_status(provider_id: str, model_id: str, request: Request):
    manager = _get_manager(request)
    result = manager.get_model_commercial_status(provider_id, model_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/api/v1/providers/{provider_id}/models/{model_id}/rate-limit")
@trace_async
async def get_model_rate_limit(provider_id: str, model_id: str, request: Request):
    manager = _get_manager(request)
    rl = manager.health_monitor.get_model_rate_limit(provider_id, model_id)
    return rl.to_dict()


@router.get("/api/v1/providers/health")
@trace_async
async def get_all_health(request: Request):
    manager = _get_manager(request)
    all_health = manager.health_monitor.get_all_health()
    return {"health": {pid: h.to_dict() for pid, h in all_health.items()}}


@router.get("/api/v1/providers/{provider_id}/health")
@trace_async
async def get_provider_health(provider_id: str, request: Request):
    manager = _get_manager(request)
    health = manager.health_monitor.get_health(provider_id)
    if not health:
        raise HTTPException(status_code=404, detail="No health data for this provider")
    return health.to_dict()


# ------------------------------------------------------------------
# Routing diagnostics endpoint (spec §36)
# ------------------------------------------------------------------

@router.get("/api/v1/routing/diagnostics")
@trace_async
async def get_routing_diagnostics(request: Request):
    """Sanitized routing diagnostics — no credentials exposed.

    Returns:
      - commercial_policy: current commercial policy setting
      - provider health: per-instance health status (sanitized)
      - rate limits: per-model rate limit state
      - capability summary: per-provider models + capabilities
    """
    manager = _get_manager(request)
    smart_router = getattr(manager, "_smart_router", None)

    # Commercial policy
    commercial_policy = "allow_paid"
    if smart_router:
        commercial_policy = smart_router.commercial_policy.value

    # Provider health (sanitized via to_dict)
    all_health = manager.health_monitor.get_all_health()
    health_summary = {}
    for pid, h in all_health.items():
        hd = h.to_dict()
        # Strip any potential credential fields (defense in depth)
        hd.pop("api_key", None)
        hd.pop("secret", None)
        hd.pop("token", None)
        health_summary[pid] = hd

    # Rate limits (all models, sanitized)
    all_rate_limits = manager.health_monitor.get_all_model_rate_limits()
    rate_limit_summary = {}
    for key, rl in all_rate_limits.items():
        rl_dict = rl.to_dict()
        rl_dict.pop("api_key", None)
        rate_limit_summary[key] = rl_dict

    # Capability summary (if smart_router available)
    capability_summary = {}
    if smart_router:
        capability_summary = smart_router.get_capability_summary()

    return {
        "commercial_policy": commercial_policy,
        "routing_config": manager.get_routing(),
        "health": health_summary,
        "rate_limits": rate_limit_summary,
        "capabilities": capability_summary,
    }


# ------------------------------------------------------------------
# Onboarding endpoint (spec §6.3)
# ------------------------------------------------------------------

class OnboardProviderRequest(BaseModel):
    provider_type: str
    api_key: str | None = None
    endpoint_url: str | None = None
    organization: str | None = None
    name: str | None = None


@router.post("/api/v1/providers/onboard")
@trace_async
async def onboard_provider(body: OnboardProviderRequest, request: Request):
    """Add a new provider instance using registry metadata.

    The caller only needs to supply provider_type + api_key (+ endpoint_url
    for OpenAI-compatible).  All other fields (adapter class, default endpoint,
    models endpoint, auth headers) are resolved from the registry.
    """
    from aios.core.onboarding import get_onboarding_fields

    fields = get_onboarding_fields(body.provider_type)
    if not fields:
        raise HTTPException(status_code=400, detail=f"Unknown provider type: {body.provider_type}")

    manager = _get_manager(request)
    try:
        result = manager.add_provider(
            provider_type=body.provider_type,
            name=body.name,
            endpoint_url=body.endpoint_url,
            api_key=body.api_key,
            organization=body.organization,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
