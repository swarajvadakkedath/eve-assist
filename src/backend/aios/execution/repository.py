"""Execution Repository — persist execution history."""

from datetime import datetime
from typing import Any
from aios.execution.models import Execution, Task, ExecutionResult
from aios.utils.logger import get_logger

logger = get_logger(__name__)


class ExecutionRepository:
    def __init__(self, db: Any | None = None):
        self._db = db
        self._executions: dict[str, Execution] = {}
        self._tasks: dict[str, dict[str, Task]] = {}
        self._results: dict[str, ExecutionResult] = {}
        self._events: dict[str, list[dict]] = {}

    async def save_execution(self, execution: Execution) -> None:
        self._executions[execution.id] = execution
        execution.updated_at = datetime.utcnow()
        if self._db:
            try:
                await self._db.execute(
                    "INSERT OR REPLACE INTO executions (id, status, objective, created_at, updated_at, owner, priority, plan_id, conversation_id) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (execution.id, execution.status.value, execution.objective,
                     execution.created_at.isoformat(), execution.updated_at.isoformat(),
                     execution.owner, execution.priority.value,
                     execution.plan_id, execution.conversation_id),
                )
            except Exception as e:
                logger.error("repository.save_execution_failed", error=str(e))

    async def get_execution(self, execution_id: str) -> Execution | None:
        return self._executions.get(execution_id)

    async def list_executions(self, limit: int = 50, offset: int = 0) -> list[Execution]:
        executions = sorted(
            self._executions.values(),
            key=lambda e: e.created_at or datetime.min,
            reverse=True,
        )
        return executions[offset:offset + limit]

    async def save_task(self, execution_id: str, task: Task) -> None:
        self._tasks.setdefault(execution_id, {})[task.id] = task
        if self._db:
            try:
                await self._db.execute(
                    "INSERT OR REPLACE INTO execution_tasks (id, execution_id, capability, tool, status, retries, error, duration_ms, is_optional, dependency) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (task.id, execution_id, task.capability, task.tool,
                     task.status.value, task.retries, task.error,
                     task.duration_ms, task.is_optional,
                     ",".join(task.dependencies)),
                )
            except Exception as e:
                logger.error("repository.save_task_failed", error=str(e))

    async def get_tasks(self, execution_id: str) -> list[Task]:
        tasks_map = self._tasks.get(execution_id, {})
        return list(tasks_map.values())

    async def get_task(self, execution_id: str, task_id: str) -> Task | None:
        tasks_map = self._tasks.get(execution_id, {})
        return tasks_map.get(task_id)

    async def save_result(self, execution_id: str, result: ExecutionResult) -> None:
        self._results[execution_id] = result

    async def get_result(self, execution_id: str) -> ExecutionResult | None:
        return self._results.get(execution_id)

    async def save_event(self, execution_id: str, event: dict) -> None:
        self._events.setdefault(execution_id, []).append(event)

    async def get_events(self, execution_id: str, limit: int = 100) -> list[dict]:
        events = self._events.get(execution_id, [])
        return events[-limit:]

    async def count_executions(self) -> int:
        return len(self._executions)

    async def delete_execution(self, execution_id: str) -> None:
        self._executions.pop(execution_id, None)
        self._tasks.pop(execution_id, None)
        self._results.pop(execution_id, None)
        self._events.pop(execution_id, None)
