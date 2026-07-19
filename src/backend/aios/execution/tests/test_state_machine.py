import pytest
from aios.execution.state_machine import ExecutionStateMachine
from aios.execution.models import ExecutionStatus
from aios.execution.exceptions import InvalidStateTransitionError


@pytest.fixture
def machine():
    return ExecutionStateMachine()


def test_valid_transition(machine):
    t = machine.transition(ExecutionStatus.PENDING, ExecutionStatus.PLANNING)
    assert t.from_state == ExecutionStatus.PENDING
    assert t.to_state == ExecutionStatus.PLANNING


def test_invalid_transition(machine):
    with pytest.raises(InvalidStateTransitionError):
        machine.transition(ExecutionStatus.PENDING, ExecutionStatus.COMPLETED)


def test_terminal_states(machine):
    assert machine.is_terminal(ExecutionStatus.COMPLETED)
    assert machine.is_terminal(ExecutionStatus.FAILED)
    assert machine.is_terminal(ExecutionStatus.CANCELLED)
    assert not machine.is_terminal(ExecutionStatus.RUNNING)


def test_allowed_transitions(machine):
    allowed = machine.get_allowed_transitions(ExecutionStatus.PENDING)
    assert ExecutionStatus.PLANNING in allowed
    assert ExecutionStatus.CANCELLED in allowed


def test_full_execution_lifecycle(machine):
    machine.transition(ExecutionStatus.PENDING, ExecutionStatus.PLANNING)
    machine.transition(ExecutionStatus.PLANNING, ExecutionStatus.READY)
    machine.transition(ExecutionStatus.READY, ExecutionStatus.RUNNING)
    machine.transition(ExecutionStatus.RUNNING, ExecutionStatus.COMPLETED)
    history = machine.get_history()
    assert len(history) == 4


def test_pause_resume(machine):
    machine.transition(ExecutionStatus.RUNNING, ExecutionStatus.PAUSED)
    machine.transition(ExecutionStatus.PAUSED, ExecutionStatus.RUNNING)
    history = machine.get_history()
    assert len(history) == 2


def test_failure_and_retry(machine):
    machine.transition(ExecutionStatus.RUNNING, ExecutionStatus.RETRYING)
    machine.transition(ExecutionStatus.RETRYING, ExecutionStatus.RUNNING)
    history = machine.get_history()
    assert len(history) == 2


def test_validate_transition(machine):
    assert machine.validate_transition(ExecutionStatus.PENDING, ExecutionStatus.PLANNING)
    assert not machine.validate_transition(ExecutionStatus.COMPLETED, ExecutionStatus.RUNNING)
