"""Workflow — defines execution workflow from plan to tasks."""

from typing import Any
from aios.execution.models import Task, TaskStatus, Execution
from aios.core.planner import Plan, Step


class WorkflowBuilder:
    def build_tasks(self, execution: Execution, plan: Any) -> list[Task]:
        tasks: list[Task] = []
        if hasattr(plan, "steps"):
            for i, step in enumerate(plan.steps):
                task = Task(
                    execution_id=execution.id,
                    capability=step.capability,
                    tool=step.capability,
                    parameters=step.params,
                    dependencies=step.depends_on,
                    timeout=step.timeout or 60,
                    max_retries=3,
                    status=TaskStatus.PENDING,
                    index=i,
                )
                tasks.append(task)
        return tasks

    def build_execution_result(self, execution: Execution, tasks: list[Task]) -> Any:
        from aios.execution.models import ExecutionResult
        result = ExecutionResult(
            success=all(t.status == TaskStatus.SUCCESS for t in tasks if not t.is_optional),
            task_count=len(tasks),
            completed_count=sum(1 for t in tasks if t.status == TaskStatus.SUCCESS),
            failed_count=sum(1 for t in tasks if t.status == TaskStatus.FAILED),
            skipped_count=sum(1 for t in tasks if t.status == TaskStatus.SKIPPED),
            output="",
            tool_results=[
                {
                    "task_id": t.id,
                    "capability": t.capability,
                    "success": t.status == TaskStatus.SUCCESS,
                    "error": t.error,
                    "duration_ms": t.duration_ms,
                }
                for t in tasks
            ],
        )
        if result.failed_count > 0:
            result.errors = [t.error for t in tasks if t.status == TaskStatus.FAILED and t.error]
        return result
