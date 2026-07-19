import pytest
from aios.execution.workflow import WorkflowBuilder
from aios.execution.models import Execution, Task, TaskStatus
from aios.core.planner import Plan, Step


@pytest.fixture
def builder():
    return WorkflowBuilder()


def test_build_tasks_from_plan(builder):
    execution = Execution(objective="test")
    plan = Plan(request="test request")
    plan.steps = [
        Step(id="step-1", capability="tool.1", params={"key": "value"}, depends_on=[], timeout=30),
        Step(id="step-2", capability="tool.2", params={}, depends_on=["step-1"], timeout=60),
    ]
    tasks = builder.build_tasks(execution, plan)
    assert len(tasks) == 2
    assert tasks[0].capability == "tool.1"
    assert tasks[0].parameters == {"key": "value"}
    assert tasks[1].dependencies == ["step-1"]
    assert tasks[1].timeout == 60


def test_build_execution_result_all_success(builder):
    execution = Execution(objective="test")
    tasks = [
        Task(execution_id=execution.id, capability="tool.1", id="t1", status=TaskStatus.SUCCESS),
        Task(execution_id=execution.id, capability="tool.2", id="t2", status=TaskStatus.SUCCESS),
    ]
    result = builder.build_execution_result(execution, tasks)
    assert result.success
    assert result.completed_count == 2
    assert result.failed_count == 0


def test_build_execution_result_with_failures(builder):
    execution = Execution(objective="test")
    tasks = [
        Task(execution_id=execution.id, capability="tool.1", id="t1", status=TaskStatus.SUCCESS),
        Task(execution_id=execution.id, capability="tool.2", id="t2", status=TaskStatus.FAILED, error="Something failed"),
    ]
    result = builder.build_execution_result(execution, tasks)
    assert not result.success
    assert result.completed_count == 1
    assert result.failed_count == 1
    assert "Something failed" in result.errors
