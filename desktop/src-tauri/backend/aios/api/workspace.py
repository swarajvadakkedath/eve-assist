"""Workspace API routes."""

from fastapi import APIRouter, Request, HTTPException

router = APIRouter(tags=["workspace"])


@router.get("/workspace/current")
async def get_current_workspace(request: Request):
    ws = request.app.state.workspace_service
    return await ws.get_current_workspace()


@router.get("/workspace/projects")
async def get_projects(request: Request):
    ws = request.app.state.workspace_service
    projects = await ws.get_projects()
    return {"projects": [p.to_dict() for p in projects]}


@router.get("/workspace/applications")
async def get_applications(request: Request):
    ws = request.app.state.workspace_service
    apps = await ws.get_applications()
    return {"applications": [a.to_dict() for a in apps]}


@router.get("/workspace/git")
async def get_git_status(request: Request):
    ws = request.app.state.workspace_service
    repos = await ws.get_git_repositories()
    return {"repositories": [r.to_dict() for r in repos]}


@router.get("/workspace/editors")
async def get_editors(request: Request):
    ws = request.app.state.workspace_service
    editors = await ws.get_editors()
    return {"editors": [e.to_dict() for e in editors]}


@router.get("/workspace/terminals")
async def get_terminals(request: Request):
    ws = request.app.state.workspace_service
    terminals = await ws.get_terminals()
    return {"terminals": [t.to_dict() for t in terminals]}


@router.get("/workspace/history")
async def get_workspace_history(request: Request, limit: int = 10):
    ws = request.app.state.workspace_service
    history = await ws.get_history(limit=limit)
    return {"history": [s.to_dict() for s in history]}


@router.post("/workspace/refresh")
async def refresh_workspace(request: Request):
    ws = request.app.state.workspace_service
    await ws.refresh()
    return {"status": "ok"}
