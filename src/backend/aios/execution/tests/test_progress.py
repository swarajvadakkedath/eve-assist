import pytest
from aios.execution.progress import ProgressTracker
from aios.execution.models import Execution, Task, ExecutionStatus, TaskStatus


@pytest.fixture
def tracker():
    return ProgressTracker()


def test_initialize(tracker):
    execution = Execution(objective="test")
    tasks = [Task(execution_id=execution.id, capability="tool.1"), Task(execution_id=execution.id, capability="tool.2")]
    progress = tracker.initialize(execution, tasks)
    assert progress.total_tasks == 2
    assert progress.completed_tasks == 0
    assert progress.percentage == 0.0


def test_task_started(tracker):
    execution = Execution(objective="test")
    tasks = [Task(execution_id=execution.id, capability="tool.1")]
    tracker.initialize(execution, tasks)
    progress = tracker.task_started(execution.id, tasks[0])
    assert progress.current_capability == "tool.1"


def test_task_completed(tracker):
    execution = Execution(objective="test")
    tasks = [Task(execution_id=execution.id, capability="tool.1")]
    tracker.initialize(execution, tasks)
    tracker.task_started(execution.id, tasks[0])
    progress = tracker.task_completed(execution.id, tasks[0])
    assert progress.completed_tasks == 1
    assert progress.percentage == 100.0


def test_get_progress(tracker):
    execution = Execution(objective="test")
    tracker.initialize(execution, [Task(execution_id=execution.id, capability="tool.1")])
    progress = tracker.get_progress(execution.id)
    assert progress is not None
    assert progress.percentage == 0.0


def test_set_status(tracker):
    execution = Execution(objective="test")
    tracker.initialize(execution, [])
    tracker.set_status(execution.id, ExecutionStatus.RUNNING)
    progress = tracker.get_progress(execution.id)
    assert progress.status == ExecutionStatus.RUNNING


def test_remove(tracker):
    execution = Execution(objective="test")
    tracker.initialize(execution, [])
    tracker.remove(execution.id)
    assert tracker.get_progress(execution.id) is None
