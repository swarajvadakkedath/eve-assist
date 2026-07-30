import pytest
from aios.execution.models import (
    Execution, Task, ExecutionResult, ExecutionProgress,
    ExecutionStatus, TaskStatus, Priority,
)


def test_execution_defaults():
    ex = Execution(objective="Test execution")
    assert ex.id
    assert ex.status == ExecutionStatus.PENDING
    assert ex.objective == "Test execution"
    assert ex.priority == Priority.NORMAL
    assert ex.created_at is not None


def test_execution_with_custom_id():
    ex = Execution(id="custom-id", objective="Test")
    assert ex.id == "custom-id"


def test_task_defaults():
    task = Task(execution_id="ex-1", capability="test.tool")
    assert task.id
    assert task.status == TaskStatus.PENDING
    assert task.max_retries == 3
    assert task.timeout == 60
    assert task.retries == 0


def test_task_with_dependencies():
    task = Task(
        execution_id="ex-1",
        capability="test.tool",
        dependencies=["task-1", "task-2"],
        is_optional=True,
    )
    assert len(task.dependencies) == 2
    assert task.is_optional


def test_execution_result_defaults():
    result = ExecutionResult()
    assert result.success is False
    assert result.task_count == 0
    assert result.warnings == []
    assert result.errors == []
    assert result.tool_results == []


def test_execution_result_with_data():
    result = ExecutionResult(
        success=True,
        output="Done",
        completed_count=5,
        failed_count=0,
        duration_ms=1500.0,
    )
    assert result.success
    assert result.output == "Done"
    assert result.completed_count == 5
    assert result.duration_ms == 1500.0


def test_execution_progress():
    progress = ExecutionProgress(
        percentage=50.0,
        completed_tasks=2,
        total_tasks=4,
        remaining_tasks=2,
        current_capability="test.tool",
    )
    assert progress.percentage == 50.0
    assert progress.completed_tasks == 2
    assert progress.remaining_tasks == 2


def test_priority_values():
    assert Priority.LOW.value == 0
    assert Priority.NORMAL.value == 1
    assert Priority.HIGH.value == 2
    assert Priority.CRITICAL.value == 3


def test_execution_status_enum():
    assert len(ExecutionStatus) == 11
    assert ExecutionStatus.PENDING.value == "pending"
    assert ExecutionStatus.COMPLETED.value == "completed"
    assert ExecutionStatus.FAILED.value == "failed"


def test_task_status_enum():
    assert len(TaskStatus) == 8
    assert TaskStatus.PENDING.value == "pending"
    assert TaskStatus.SUCCESS.value == "success"
    assert TaskStatus.FAILED.value == "failed"
