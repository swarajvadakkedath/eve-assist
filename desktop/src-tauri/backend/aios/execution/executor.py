"""Task Executor — resolves capabilities and executes tasks through Tool Manager."""

from datetime import datetime, timezone
from typing import Any
from aios.execution.models import Task, TaskStatus
from aios.execution.exceptions import CapabilityResolutionError, TimeoutError
from aios.utils.logger import get_logger

logger = get_logger(__name__)


class TaskExecutor:
    def __init__(
        self,
        capability_registry: Any | None = None,
        tool_manager: Any | None = None,
    ):
        self._capability_registry = capability_registry
        self._tool_manager = tool_manager

    async def execute_task(self, task: Task) -> Task:
        task.started_at = datetime.now(timezone.utc)
        task.status = TaskStatus.RUNNING

        try:
            resolved_tool = await self._resolve_capability(task)
            if not resolved_tool:
                raise CapabilityResolutionError(task.capability)

            tool_result = await self._tool_manager.execute(resolved_tool, task.parameters)

            task.completed_at = datetime.now(timezone.utc)
            task.duration_ms = (task.completed_at - task.started_at).total_seconds() * 1000

            if tool_result.success:
                task.status = TaskStatus.SUCCESS
                task.result = tool_result.data
            else:
                task.status = TaskStatus.FAILED
                task.error = tool_result.error

            return task

        except TimeoutError as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now(timezone.utc)
            task.duration_ms = (task.completed_at - task.started_at).total_seconds() * 1000
            return task

        except CapabilityResolutionError as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now(timezone.utc)
            task.duration_ms = (task.completed_at - task.started_at).total_seconds() * 1000
            return task

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now(timezone.utc)
            task.duration_ms = (task.completed_at - task.started_at).total_seconds() * 1000
            return task

    async def _resolve_capability(self, task: Task) -> str | None:
        capability_id = task.capability or task.tool
        if not capability_id:
            return None

        if self._capability_registry:
            capability = await self._capability_registry.find_best_match(capability_id)
            if capability:
                logger.info("executor.capability_resolved", capability=capability_id, tool=capability.provider_id)
                return capability.provider_id

        if self._tool_manager:
            tool = await self._tool_manager.get_tool(capability_id)
            if tool:
                return tool.id

        return capability_id

    async def validate_task(self, task: Task) -> bool:
        if not task.capability and not task.tool:
            return False
        if task.timeout <= 0:
            return False
        return True
