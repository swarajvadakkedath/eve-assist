"""Permission management API routes."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(tags=["permissions"])


class GrantRequest(BaseModel):
    request_id: str
    session_id: str = ""


class DenyRequest(BaseModel):
    request_id: str
    reason: str = ""
    session_id: str = ""


class AuditQuery(BaseModel):
    tool_id: str | None = None
    decision: str | None = None
    limit: int = 100


@router.get("/permissions/pending")
async def get_pending_requests(req: Request):
    pm = req.app.state.permissions
    pending = await pm.get_pending_requests()
    return {
        "pending": [
            {
                "id": r.id,
                "tool_id": r.tool_id,
                "action": r.action,
                "level": int(r.level),
                "status": r.status,
                "description": r.description,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in pending
        ],
        "count": len(pending),
    }


@router.post("/permissions/grant")
async def grant_permission(req: Request, body: GrantRequest):
    pm = req.app.state.permissions
    try:
        result = await pm.grant_permission(body.request_id, session_id=body.session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "success": True,
        "request": {
            "id": result.id,
            "tool_id": result.tool_id,
            "action": result.action,
            "level": int(result.level),
            "status": result.status,
            "resolved_at": result.resolved_at.isoformat() if result.resolved_at else None,
        },
    }


@router.post("/permissions/deny")
async def deny_permission(req: Request, body: DenyRequest):
    pm = req.app.state.permissions
    try:
        result = await pm.deny_permission(body.request_id, reason=body.reason, session_id=body.session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "success": True,
        "request": {
            "id": result.id,
            "tool_id": result.tool_id,
            "action": result.action,
            "level": int(result.level),
            "status": result.status,
            "reason": result.reason,
            "resolved_at": result.resolved_at.isoformat() if result.resolved_at else None,
        },
    }


@router.get("/permissions/audit")
async def get_audit_log(req: Request, tool_id: str | None = None, decision: str | None = None, limit: int = 100):
    pm = req.app.state.permissions
    entries = await pm.get_audit_history(tool_id=tool_id, decision=decision, limit=limit)
    return {
        "entries": [
            {
                "timestamp": e.timestamp.isoformat(),
                "tool_id": e.tool_id,
                "action": e.action,
                "level": e.level,
                "decision": e.decision,
                "session_id": e.session_id,
                "reason": e.reason,
                "request_id": e.request_id,
            }
            for e in entries
        ],
        "count": len(entries),
    }
