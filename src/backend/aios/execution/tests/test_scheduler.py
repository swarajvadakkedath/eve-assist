import pytest
from aios.execution.scheduler import Scheduler
from aios.execution.models import Execution, Task, TaskStatus, ExecutionStatus


@pytest.fixture
def scheduler():
    return Scheduler(max_concurrent=5)


@pytest.mark.asyncio
async def test_schedule_single_task(scheduler):
    execution = Execution(objective="test")
    tasks = [Task(execution_id=execution.id, capability="test.tool", id="task-1")]
    results = []
    async for task in scheduler.schedule(execution, tasks):
        results.append(task)
    assert len(results) == 1
    assert results[0].status == TaskStatus.QUEUED


@pytest.mark.asyncio
async def test_schedule_multiple_tasks(scheduler):
    execution = Execution(objective="test")
    tasks = [
        Task(execution_id=execution.id, capability="tool.1", id="task-1", index=0),
        Task(execution_id=execution.id, capability="tool.2", id="task-2", index=1),
    ]
    results = []
    async for task in scheduler.schedule(execution, tasks):
        results.append(task)
    assert len(results) == 2


@pytest.mark.asyncio
async def test_schedule_with_dependencies(scheduler):
    execution = Execution(objective="test")
    tasks = [
        Task(execution_id=execution.id, capability="tool.1", id="task-1", index=0),
        Task(execution_id=execution.id, capability="tool.2", id="task-2", dependencies=["task-1"], index=1),
    ]
    results = []
    async for task in scheduler.schedule(execution, tasks):
        if task.id == "task-1":
            task.status = TaskStatus.SUCCESS
        results.append(task)
    assert len(results) == 2
    task2 = [t for t in results if t.id == "task-2"][0]
    assert task2.status == TaskStatus.QUEUED


@pytest.mark.asyncio
async def test_cancel(scheduler):
    execution = Execution(objective="test")
    tasks = [Task(execution_id=execution.id, capability="test.tool", id="task-1")]
    results = []
    async for task in scheduler.schedule(execution, tasks):
        if task.id == "task-1":
            await scheduler.cancel(execution.id)
        results.append(task)
    assert scheduler.is_cancelled(execution.id)
    assert len(results) == 1


@pytest.mark.asyncio
async def test_pause_resume(scheduler):
    execution = Execution(objective="test")
    await scheduler.pause(execution.id)
    await scheduler.resume(execution.id)
    tasks = [Task(execution_id=execution.id, capability="test.tool", id="task-1")]
    results = []
    async for task in scheduler.schedule(execution, tasks):
        results.append(task)
    assert len(results) == 1


@pytest.mark.asyncio
async def test_cleanup(scheduler):
    execution = Execution(objective="test")
    await scheduler.cleanup(execution.id)
    assert not scheduler.is_cancelled(execution.id)
