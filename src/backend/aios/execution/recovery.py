"""Recovery Engine — automatic retry, skip, and failure management."""

import asyncio
from typing import Any
from aios.execution.models import Execution, Task, TaskStatus, ExecutionStatus
from aios.execution.exceptions import TaskExecutionError
from aios.utils.logger import get_logger

logger = get_logger(__name__)


class RecoveryEngine:
    def __init__(self, planner_adapter: Any | None = None):
        self._planner_adapter = planner_adapter
        self._max_retries = 3
        self._base_delay = 1.0

    async def handle_failure(self, execution: Execution, task: Task) -> tuple[bool, Task | None]:
        if task.retries < task.max_retries:
            task.retries += 1
            task.status = TaskStatus.RETRYING
            delay = self._base_delay * (2 ** (task.retries - 1))
            await asyncio.sleep(delay)
            logger.info("recovery.retrying", task_id=task.id, attempt=task.retries, delay=delay)
            return True, task

        if task.is_optional:
            task.status = TaskStatus.SKIPPED
            logger.info("recovery.skipped_optional", task_id=task.id)
            return True, None

        task.status = TaskStatus.FAILED
        logger.error("recovery.failed", task_id=task.id, error=task.error)
        return False, None

    async def can_continue(self, execution: Execution, tasks: list[Task]) -> bool:
        failed_tasks = [t for t in tasks if t.status == TaskStatus.FAILED]
        if not failed_tasks:
            return True
        optional_failed = all(t.is_optional for t in failed_tasks)
        if optional_failed:
            return True
        critical_failed = [t for t in failed_tasks if not t.is_optional]
        return len(critical_failed) == 0
