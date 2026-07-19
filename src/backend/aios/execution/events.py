"""Execution Event Publisher — publishes execution events to the Event Bus."""

from typing import Any
from aios.utils.logger import get_logger

logger = get_logger(__name__)


EXECUTION_EVENT_TYPES = {
    "created": "execution.created",
    "started": "execution.started",
    "paused": "execution.paused",
    "resumed": "execution.resumed",
    "completed": "execution.completed",
    "failed": "execution.failed",
    "cancelled": "execution.cancelled",
    "planning_started": "execution.planning_started",
    "planning_completed": "execution.planning_completed",
    "permission_requested": "execution.permission_requested",
    "permission_granted": "execution.permission_granted",
    "permission_denied": "execution.permission_denied",
    "task_queued": "execution.task_queued",
    "task_started": "execution.task_started",
    "task_completed": "execution.task_completed",
    "task_failed": "execution.task_failed",
    "task_retrying": "execution.task_retrying",
    "tool_executing": "execution.tool_executing",
    "tool_completed": "execution.tool_completed",
    "warning": "execution.warning",
    "error": "execution.error",
    "progress": "execution.progress",
}


class ExecutionEventPublisher:
    def __init__(self, event_bus: Any | None = None):
        self._event_bus = event_bus

    async def publish(self, event_type: str, payload: dict, correlation_id: str = "") -> None:
        if not self._event_bus:
            return
        try:
            event_id = await self._event_bus.publish(
                event_type=event_type,
                payload=payload,
                source="execution_engine",
                correlation_id=correlation_id,
            )
            logger.debug("event.published", event_type=event_type, event_id=event_id)
        except Exception as e:
            logger.error("event.publish_failed", event_type=event_type, error=str(e))

    async def execution_created(self, execution_id: str, objective: str, priority: int) -> None:
        await self.publish("execution.created", {
            "execution_id": execution_id,
            "objective": objective,
            "priority": priority,
        }, correlation_id=execution_id)

    async def execution_started(self, execution_id: str, task_count: int) -> None:
        await self.publish("execution.started", {
            "execution_id": execution_id,
            "task_count": task_count,
        }, correlation_id=execution_id)

    async def execution_completed(self, execution_id: str, result: Any) -> None:
        await self.publish("execution.completed", {
            "execution_id": execution_id,
            "success": result.success,
            "duration_ms": result.duration_ms,
            "completed_count": result.completed_count,
            "failed_count": result.failed_count,
        }, correlation_id=execution_id)

    async def execution_failed(self, execution_id: str, error: str) -> None:
        await self.publish("execution.failed", {
            "execution_id": execution_id,
            "error": error,
        }, correlation_id=execution_id)

    async def task_started(self, execution_id: str, task: Any) -> None:
        await self.publish("execution.task_started", {
            "execution_id": execution_id,
            "task_id": task.id,
            "capability": task.capability or task.tool,
        }, correlation_id=execution_id)

    async def task_completed(self, execution_id: str, task: Any) -> None:
        await self.publish("execution.task_completed", {
            "execution_id": execution_id,
            "task_id": task.id,
            "capability": task.capability or task.tool,
            "duration_ms": task.duration_ms,
        }, correlation_id=execution_id)

    async def task_failed(self, execution_id: str, task: Any, error: str) -> None:
        await self.publish("execution.task_failed", {
            "execution_id": execution_id,
            "task_id": task.id,
            "capability": task.capability or task.tool,
            "error": error,
        }, correlation_id=execution_id)

    async def permission_requested(self, execution_id: str, task: Any, request_id: str) -> None:
        await self.publish("execution.permission_requested", {
            "execution_id": execution_id,
            "task_id": task.id,
            "capability": task.capability or task.tool,
            "request_id": request_id,
        }, correlation_id=execution_id)

    async def progress(self, execution_id: str, progress: Any) -> None:
        await self.publish("execution.progress", {
            "execution_id": execution_id,
            "percentage": progress.percentage,
            "completed_tasks": progress.completed_tasks,
            "total_tasks": progress.total_tasks,
            "current_capability": progress.current_capability,
        }, correlation_id=execution_id)

    async def warning(self, execution_id: str, warning: str) -> None:
        await self.publish("execution.warning", {
            "execution_id": execution_id,
            "warning": warning,
        }, correlation_id=execution_id)

    async def pause_resume(self, execution_id: str, action: str) -> None:
        await self.publish(f"execution.{action}", {
            "execution_id": execution_id,
        }, correlation_id=execution_id)
