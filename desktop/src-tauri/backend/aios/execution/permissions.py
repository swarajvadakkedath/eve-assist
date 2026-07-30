"""Execution Permission Manager — handles permission gating for tasks."""

from typing import Any
from aios.execution.models import Task, TaskStatus
from aios.utils.logger import get_logger

logger = get_logger(__name__)


class ExecutionPermissionManager:
    def __init__(self, permission_manager: Any | None = None):
        self._permission_manager = permission_manager

    async def check_task(self, task: Task) -> tuple[bool, str | None]:
        if not self._permission_manager:
            return True, None
        try:
            result = await self._permission_manager.request_permission(
                task.tool or task.capability,
                2 if task.parameters else 1,
                f"Execute {task.capability or task.tool}",
            )
            if result.granted:
                return True, None
            return False, result.request.id
        except Exception as e:
            logger.error("permission.check_failed", task_id=task.id, error=str(e))
            return True, None

    async def grant_permission(self, task: Task, request_id: str) -> bool:
        if not self._permission_manager:
            return True
        try:
            await self._permission_manager.grant_permission(request_id)
            logger.info("permission.granted", task_id=task.id)
            return True
        except Exception as e:
            logger.error("permission.grant_failed", task_id=task.id, error=str(e))
            return False

    async def deny_permission(self, task: Task, request_id: str, reason: str = "") -> None:
        if not self._permission_manager:
            return
        try:
            await self._permission_manager.deny_permission(request_id, reason)
            task.status = TaskStatus.CANCELLED
            logger.info("permission.denied", task_id=task.id, reason=reason)
        except Exception as e:
            logger.error("permission.deny_failed", task_id=task.id, error=str(e))
