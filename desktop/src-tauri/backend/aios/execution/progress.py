"""Progress Tracker — real-time execution progress tracking."""

from typing import Any
from aios.execution.models import Execution, Task, ExecutionProgress, ExecutionStatus, TaskStatus


class ProgressTracker:
    def __init__(self):
        self._progress: dict[str, ExecutionProgress] = {}

    def initialize(self, execution: Execution, tasks: list[Task]) -> ExecutionProgress:
        progress = ExecutionProgress(
            percentage=0.0,
            current_task="",
            current_capability="",
            completed_tasks=0,
            total_tasks=len(tasks),
            remaining_tasks=len(tasks),
            estimated_completion_ms=0.0,
            status=execution.status,
        )
        self._progress[execution.id] = progress
        return progress

    def update(self, execution_id: str, **kwargs) -> ExecutionProgress:
        progress = self._progress.get(execution_id)
        if not progress:
            return ExecutionProgress()
        for key, value in kwargs.items():
            if hasattr(progress, key):
                setattr(progress, key, value)
        if progress.total_tasks > 0:
            progress.percentage = (progress.completed_tasks / progress.total_tasks) * 100.0
        progress.remaining_tasks = progress.total_tasks - progress.completed_tasks
        return progress

    def task_started(self, execution_id: str, task: Task) -> ExecutionProgress:
        return self.update(
            execution_id,
            current_task=task.id,
            current_capability=task.capability or task.tool,
            status=ExecutionStatus.RUNNING,
        )

    def task_completed(self, execution_id: str, task: Task) -> ExecutionProgress:
        return self.update(
            execution_id,
            completed_tasks=self._progress.get(execution_id).completed_tasks + 1 if self._progress.get(execution_id) else 1,
        )

    def get_progress(self, execution_id: str) -> ExecutionProgress | None:
        return self._progress.get(execution_id)

    def set_status(self, execution_id: str, status: ExecutionStatus) -> None:
        self.update(execution_id, status=status)

    def remove(self, execution_id: str) -> None:
        self._progress.pop(execution_id, None)
