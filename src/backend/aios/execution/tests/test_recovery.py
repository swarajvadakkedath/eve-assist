import pytest
from aios.execution.recovery import RecoveryEngine
from aios.execution.models import Execution, Task, TaskStatus


@pytest.fixture
def recovery():
    return RecoveryEngine()


@pytest.mark.asyncio
async def test_retry_on_failure(recovery):
    execution = Execution(objective="test")
    task = Task(execution_id=execution.id, capability="test.tool", id="task-1", max_retries=3)
    recovered, new_task = await recovery.handle_failure(execution, task)
    assert recovered
    assert task.retries == 1
    assert task.status == TaskStatus.RETRYING


@pytest.mark.asyncio
async def test_max_retries_exceeded(recovery):
    execution = Execution(objective="test")
    task = Task(
        execution_id=execution.id, capability="test.tool", id="task-1",
        retries=3, max_retries=3,
    )
    recovered, new_task = await recovery.handle_failure(execution, task)
    assert not recovered
    assert task.status == TaskStatus.FAILED


@pytest.mark.asyncio
async def test_skip_optional_task(recovery):
    execution = Execution(objective="test")
    task = Task(
        execution_id=execution.id, capability="test.tool", id="task-1",
        max_retries=3, is_optional=True,
    )
    task.retries = 3
    recovered, new_task = await recovery.handle_failure(execution, task)
    assert recovered
    assert new_task is None
    assert task.status == TaskStatus.SKIPPED


@pytest.mark.asyncio
async def test_can_continue_no_failures(recovery):
    execution = Execution(objective="test")
    tasks = [
        Task(execution_id=execution.id, capability="tool.1", id="t1", status=TaskStatus.SUCCESS),
        Task(execution_id=execution.id, capability="tool.2", id="t2", status=TaskStatus.SUCCESS),
    ]
    assert await recovery.can_continue(execution, tasks)


@pytest.mark.asyncio
async def test_can_continue_optional_failures(recovery):
    execution = Execution(objective="test")
    tasks = [
        Task(execution_id=execution.id, capability="tool.1", id="t1", status=TaskStatus.FAILED, is_optional=True),
        Task(execution_id=execution.id, capability="tool.2", id="t2", status=TaskStatus.SUCCESS),
    ]
    assert await recovery.can_continue(execution, tasks)


@pytest.mark.asyncio
async def test_cannot_continue_critical_failure(recovery):
    execution = Execution(objective="test")
    tasks = [
        Task(execution_id=execution.id, capability="tool.1", id="t1", status=TaskStatus.FAILED, is_optional=False),
    ]
    assert not await recovery.can_continue(execution, tasks)
