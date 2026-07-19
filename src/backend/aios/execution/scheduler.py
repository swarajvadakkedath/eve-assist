"""Scheduler — sequential/parallel task execution with queue management."""

import asyncio
from typing import Any, AsyncIterator
from aios.execution.models import Execution, Task, TaskStatus
from aios.execution.exceptions import DependencyError
from aios.utils.logger import get_logger

logger = get_logger(__name__)


class Scheduler:
    def __init__(self, max_concurrent: int = 5):
        self._max_concurrent = max_concurrent
        self._cancelled: dict[str, bool] = {}
        self._paused: dict[str, asyncio.Event] = {}
        self._completed_tasks: dict[str, set[str]] = {}

    async def schedule(self, execution: Execution, tasks: list[Task]) -> AsyncIterator[Task]:
        exec_id = execution.id
        self._cancelled[exec_id] = False
        self._paused[exec_id] = asyncio.Event()
        self._paused[exec_id].set()
        self._completed_tasks[exec_id] = set()

        while True:
            if self._cancelled.get(exec_id, False):
                for t in tasks:
                    if t.status == TaskStatus.PENDING:
                        t.status = TaskStatus.CANCELLED
                        yield t
                break

            await self._paused[exec_id].wait()

            available = [
                t for t in tasks
                if t.status == TaskStatus.PENDING
                and all(dep in self._completed_tasks[exec_id] for dep in t.dependencies)
            ]

            if not available:
                pending = [t for t in tasks if t.status == TaskStatus.PENDING]
                if not pending:
                    break
                await asyncio.sleep(0.05)
                continue

            for task in available:
                task.status = TaskStatus.QUEUED
                yield task
                self._completed_tasks[exec_id].add(task.id)

            done_count = len(self._completed_tasks[exec_id])
            if done_count >= len(tasks):
                break

    async def mark_completed(self, execution_id: str, task_id: str) -> None:
        if execution_id in self._completed_tasks:
            self._completed_tasks[execution_id].add(task_id)

    async def cancel(self, execution_id: str) -> None:
        self._cancelled[execution_id] = True
        logger.info("scheduler.cancelled", execution_id=execution_id)

    async def pause(self, execution_id: str) -> None:
        event = self._paused.get(execution_id)
        if event:
            event.clear()
        logger.info("scheduler.paused", execution_id=execution_id)

    async def resume(self, execution_id: str) -> None:
        event = self._paused.get(execution_id)
        if event:
            event.set()
        logger.info("scheduler.resumed", execution_id=execution_id)

    def is_cancelled(self, execution_id: str) -> bool:
        return self._cancelled.get(execution_id, False)

    async def cleanup(self, execution_id: str) -> None:
        self._cancelled.pop(execution_id, None)
        self._paused.pop(execution_id, None)
        self._completed_tasks.pop(execution_id, None)
