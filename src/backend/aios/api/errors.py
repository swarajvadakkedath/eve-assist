"""API routes for AI Error Intelligence — Recovery Center backend."""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse, JSONResponse

from aios.error_intelligence import get_error_intelligence

router = APIRouter(tags=["errors"])


@router.get("/errors")
async def list_errors(
    limit: int = Query(100, ge=1, le=1000),
    category: str | None = Query(None),
    severity: str | None = Query(None),
    resolved: bool | None = Query(None),
):
    svc = get_error_intelligence()
    events = svc.list_events(limit=limit, category=category, severity=severity, resolved=resolved)
    return {"errors": [e.to_dict() for e in events], "count": len(events)}


@router.get("/errors/stats")
async def error_stats():
    svc = get_error_intelligence()
    return svc.stats()


@router.get("/errors/timeline")
async def error_timeline(limit: int = Query(100, ge=1, le=1000)):
    svc = get_error_intelligence()
    return {"timeline": svc.timeline(limit=limit)}


@router.get("/errors/recoveries")
async def error_recoveries(limit: int = Query(100, ge=1, le=1000)):
    svc = get_error_intelligence()
    events = svc.recoveries(limit=limit)
    return {"recoveries": [e.to_dict() for e in events], "count": len(events)}


@router.get("/errors/{error_id}")
async def get_error(error_id: str):
    svc = get_error_intelligence()
    event = svc.get_event(error_id)
    if event is None:
        raise HTTPException(status_code=404, detail=f"Error {error_id} not found")
    return event.to_dict()


@router.get("/errors/{error_id}/report")
async def error_report(error_id: str, format: str = Query("markdown")):
    svc = get_error_intelligence()
    report = svc.report(error_id, fmt=format)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Error {error_id} not found")
    if format == "json":
        return JSONResponse(content={"report": report})
    if format == "plain":
        return PlainTextResponse(content=report)
    return {"report": report}


@router.post("/errors/clear")
async def clear_errors():
    svc = get_error_intelligence()
    svc.clear()
    return {"status": "cleared"}


@router.get("/routing/categories")
async def routing_categories():
    from aios.core.smart_router import ROUTING_CATEGORIES
    return {"categories": ROUTING_CATEGORIES}
