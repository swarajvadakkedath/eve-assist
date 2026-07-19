"""Settings API routes."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["settings"])


class SettingsUpdate(BaseModel):
    settings: dict


@router.get("/settings")
async def get_settings(req: Request):
    from aios.config.settings import AiosSettings
    settings = AiosSettings()
    return {
        "settings": {
            "ai.provider": settings.ai_provider,
            "ai.model": settings.ai_model,
            "ui.theme": settings.ui_theme,
            "permissions.default_level": settings.permission_default_level,
            "log.level": settings.log_level,
        }
    }


@router.put("/settings")
async def update_settings(req: Request, body: SettingsUpdate):
    return {
        "status": "updated",
        "settings": body.settings,
    }


@router.get("/permissions/pending")
async def get_pending_permissions(req: Request):
    pm = req.app.state.permissions
    requests = await pm.get_pending_requests()
    return {
        "requests": [
            {
                "id": r.id,
                "tool_id": r.tool_id,
                "level": int(r.level),
                "description": r.description,
                "created_at": r.created_at.isoformat() if r.created_at else "",
            }
            for r in requests
        ]
    }


class GrantRequest(BaseModel):
    request_id: str


class DenyRequest(BaseModel):
    request_id: str
    reason: str = ""


@router.post("/permissions/grant")
async def grant_permission(req: Request, body: GrantRequest):
    pm = req.app.state.permissions
    result = await pm.grant_permission(body.request_id)
    return {"status": "granted", "tool_id": result.tool_id}


@router.post("/permissions/deny")
async def deny_permission(req: Request, body: DenyRequest):
    pm = req.app.state.permissions
    result = await pm.deny_permission(body.request_id, body.reason)
    return {"status": "denied", "tool_id": result.tool_id}
