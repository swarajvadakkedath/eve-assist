"""Plugin management API routes — full REST-style endpoints."""

"""Plugin management API routes — full REST-style endpoints."""

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

router = APIRouter(prefix="/plugins", tags=["plugins"])


class InstallRequest(BaseModel):
    path: str
    enable: bool = True


class ConfigUpdateRequest(BaseModel):
    config: dict


@router.get("")
async def list_plugins(
    request: Request,
    search: str | None = Query(None, description="Search plugin by id, name, description or tags"),
):
    pm = request.app.state.plugin_manager
    if not pm:
        return {"plugins": []}

    if search:
        plugins = await pm.search_plugins(search)
    else:
        plugins = await pm.list_plugins()

    return {"plugins": [p.to_dict() for p in plugins]}


@router.get("/health")
async def get_plugins_health(request: Request):
    pm = request.app.state.plugin_manager
    if not pm:
        return {"status": "ok", "total": 0, "active": 0, "failed": 0, "loaded": 0}
    return await pm.get_health_summary()


@router.get("/{plugin_id}")
async def get_plugin(plugin_id: str, request: Request):
    pm = request.app.state.plugin_manager
    if not pm:
        raise HTTPException(status_code=503, detail="Plugin system not available")
    plugin = await pm.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")
    return plugin.to_dict()


@router.get("/{plugin_id}/manifest")
async def get_plugin_manifest(plugin_id: str, request: Request):
    pm = request.app.state.plugin_manager
    if not pm:
        raise HTTPException(status_code=503, detail="Plugin system not available")
    manifest = await pm.get_plugin_manifest(plugin_id)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' manifest not found")
    return manifest


@router.get("/{plugin_id}/capabilities")
async def get_plugin_capabilities(plugin_id: str, request: Request):
    pm = request.app.state.plugin_manager
    if not pm:
        raise HTTPException(status_code=503, detail="Plugin system not available")
    caps = await pm.get_plugin_capabilities(plugin_id)
    return {"capabilities": caps}


@router.get("/{plugin_id}/permissions")
async def get_plugin_permissions(plugin_id: str, request: Request):
    pm = request.app.state.plugin_manager
    if not pm:
        raise HTTPException(status_code=503, detail="Plugin system not available")
    return await pm.get_plugin_permissions(plugin_id)


@router.get("/{plugin_id}/config")
async def get_plugin_config(plugin_id: str, request: Request):
    pm = request.app.state.plugin_manager
    if not pm:
        raise HTTPException(status_code=503, detail="Plugin system not available")
    config = await pm.get_plugin_config(plugin_id)
    return {"plugin_id": plugin_id, "config": config}


@router.put("/{plugin_id}/config")
async def update_plugin_config(plugin_id: str, body: ConfigUpdateRequest, request: Request):
    pm = request.app.state.plugin_manager
    if not pm:
        raise HTTPException(status_code=503, detail="Plugin system not available")
    await pm.update_plugin_config(plugin_id, body.config)
    return {"status": "updated", "plugin_id": plugin_id}


@router.get("/{plugin_id}/health")
async def get_plugin_health(plugin_id: str, request: Request):
    pm = request.app.state.plugin_manager
    if not pm:
        raise HTTPException(status_code=503, detail="Plugin system not available")
    health = await pm.get_plugin_health(plugin_id)
    if not health:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' health data not found")
    return health.to_dict()


@router.post("/install")
async def install_plugin(body: InstallRequest, request: Request):
    pm = request.app.state.plugin_manager
    if not pm:
        raise HTTPException(status_code=503, detail="Plugin system not available")

    manifests = await pm.scan_plugins(body.path)
    if not manifests:
        raise HTTPException(status_code=400, detail=f"No valid plugin found at path: {body.path}")

    manifest = manifests[0]
    success = await pm.load_plugin(manifest)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to install plugin from {body.path}")

    if not body.enable:
        await pm.disable_plugin(manifest.id)

    return {"status": "installed", "plugin_id": manifest.id, "name": manifest.name, "version": manifest.version}


@router.post("/{plugin_id}/enable")
async def enable_plugin(plugin_id: str, request: Request):
    pm = request.app.state.plugin_manager
    if not pm:
        raise HTTPException(status_code=503, detail="Plugin system not available")
    success = await pm.enable_plugin(plugin_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to enable plugin '{plugin_id}'")
    return {"status": "enabled", "plugin_id": plugin_id}


@router.post("/{plugin_id}/disable")
async def disable_plugin(plugin_id: str, request: Request):
    pm = request.app.state.plugin_manager
    if not pm:
        raise HTTPException(status_code=503, detail="Plugin system not available")
    success = await pm.disable_plugin(plugin_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to disable plugin '{plugin_id}'")
    return {"status": "disabled", "plugin_id": plugin_id}


@router.post("/{plugin_id}/reload")
async def reload_plugin(plugin_id: str, request: Request):
    pm = request.app.state.plugin_manager
    if not pm:
        raise HTTPException(status_code=503, detail="Plugin system not available")
    success = await pm.reload_plugin(plugin_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to reload plugin '{plugin_id}'")
    return {"status": "reloaded", "plugin_id": plugin_id}


@router.delete("/{plugin_id}")
async def remove_plugin(plugin_id: str, request: Request):
    pm = request.app.state.plugin_manager
    if not pm:
        raise HTTPException(status_code=503, detail="Plugin system not available")
    plugin = await pm.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")
    success = await pm.unload_plugin(plugin_id)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to remove plugin '{plugin_id}'")
    return {"status": "removed", "plugin_id": plugin_id}
