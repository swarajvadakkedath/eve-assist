"""Execution API routes — expose execution engine to frontend."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from aios.execution.engine import ExecutionEngine
from aios.execution.exceptions import ExecutionNotFoundError

router = APIRouter(prefix="/api/v1/execution", tags=["execution"])


class StartExecutionRequest(BaseModel):
    objective: str
    conversation_id: str = ""
    owner: str = ""
    priority: int = 1


def _get_engine(req: Request) -> ExecutionEngine:
    engine = req.app.state.execution_engine
    if not engine:
        raise HTTPException(status_code=500, detail="Execution engine not initialized")
    return engine


@router.post("/start")
async def start_execution(request: Request, body: StartExecutionRequest):
    engine = _get_engine(request)
    execution = await engine.start_execution(
        objective=body.objective,
        conversation_id=body.conversation_id,
        owner=body.owner,
        priority=body.priority,
    )
    return {
        "execution_id": execution.id,
        "status": execution.status.value,
        "objective": execution.objective,
    }


@router.get("/{execution_id}")
async def get_execution(request: Request, execution_id: str):
    engine = _get_engine(request)
    try:
        execution = await engine.get_execution(execution_id)
        tasks = await engine.get_execution_tasks(execution_id)
        result = await engine.get_execution_result(execution_id)
        return {
            "execution": {
                "id": execution.id,
                "status": execution.status.value,
                "objective": execution.objective,
                "priority": execution.priority.value,
                "created_at": execution.created_at.isoformat() if execution.created_at else None,
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "owner": execution.owner,
                "conversation_id": execution.conversation_id,
            },
            "tasks": [
                {
                    "id": t.id,
                    "capability": t.capability,
                    "tool": t.tool,
                    "status": t.status.value,
                    "retries": t.retries,
                    "error": t.error,
                    "duration_ms": t.duration_ms,
                    "is_optional": t.is_optional,
                }
                for t in tasks
            ],
            "result": {
                "success": result.success if result else False,
                "duration_ms": result.duration_ms if result else 0,
                "completed_count": result.completed_count if result else 0,
                "failed_count": result.failed_count if result else 0,
                "errors": result.errors if result else [],
            } if result else None,
        }
    except ExecutionNotFoundError:
        raise HTTPException(status_code=404, detail="Execution not found")


@router.get("/history")
async def get_execution_history(request: Request, limit: int = 50):
    engine = _get_engine(request)
    history = await engine.get_history(limit=limit)
    return {"executions": history}


@router.post("/{execution_id}/pause")
async def pause_execution(request: Request, execution_id: str):
    engine = _get_engine(request)
    try:
        execution = await engine.pause_execution(execution_id)
        return {"execution_id": execution.id, "status": execution.status.value}
    except ExecutionNotFoundError:
        raise HTTPException(status_code=404, detail="Execution not found")


@router.post("/{execution_id}/resume")
async def resume_execution(request: Request, execution_id: str):
    engine = _get_engine(request)
    try:
        execution = await engine.resume_execution(execution_id)
        return {"execution_id": execution.id, "status": execution.status.value}
    except ExecutionNotFoundError:
        raise HTTPException(status_code=404, detail="Execution not found")


@router.post("/{execution_id}/cancel")
async def cancel_execution(request: Request, execution_id: str):
    engine = _get_engine(request)
    try:
        execution = await engine.cancel_execution(execution_id)
        return {"execution_id": execution.id, "status": execution.status.value}
    except ExecutionNotFoundError:
        raise HTTPException(status_code=404, detail="Execution not found")


@router.get("/{execution_id}/events")
async def stream_execution_events(request: Request, execution_id: str):
    engine = _get_engine(request)
    try:
        execution = await engine.get_execution(execution_id)
    except ExecutionNotFoundError:
        raise HTTPException(status_code=404, detail="Execution not found")

    async def event_generator():
        async for event in engine.stream_events(execution_id):
            yield {"data": event}

    return EventSourceResponse(event_generator())


@router.get("/{execution_id}/progress")
async def get_execution_progress(request: Request, execution_id: str):
    engine = _get_engine(request)
    try:
        progress = await engine.get_execution_progress(execution_id)
        return {
            "percentage": progress.percentage,
            "current_capability": progress.current_capability,
            "completed_tasks": progress.completed_tasks,
            "total_tasks": progress.total_tasks,
            "remaining_tasks": progress.remaining_tasks,
            "status": progress.status.value,
        }
    except ExecutionNotFoundError:
        raise HTTPException(status_code=404, detail="Execution not found")
