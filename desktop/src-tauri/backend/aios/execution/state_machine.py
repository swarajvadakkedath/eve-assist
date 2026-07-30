"""Execution State Machine — deterministic state transitions."""

from dataclasses import dataclass, field
from typing import Any

from aios.execution.models import ExecutionStatus
from aios.execution.exceptions import InvalidStateTransitionError


@dataclass
class StateTransition:
    from_state: ExecutionStatus
    to_state: ExecutionStatus
    reason: str = ""
    metadata: dict = field(default_factory=dict)


VALID_TRANSITIONS: dict[ExecutionStatus, set[ExecutionStatus]] = {
    ExecutionStatus.PENDING: {
        ExecutionStatus.PLANNING,
        ExecutionStatus.CANCELLED,
    },
    ExecutionStatus.PLANNING: {
        ExecutionStatus.WAITING_FOR_PERMISSION,
        ExecutionStatus.READY,
        ExecutionStatus.FAILED,
        ExecutionStatus.CANCELLED,
    },
    ExecutionStatus.WAITING_FOR_PERMISSION: {
        ExecutionStatus.READY,
        ExecutionStatus.CANCELLED,
        ExecutionStatus.FAILED,
    },
    ExecutionStatus.READY: {
        ExecutionStatus.RUNNING,
        ExecutionStatus.CANCELLED,
    },
    ExecutionStatus.RUNNING: {
        ExecutionStatus.WAITING,
        ExecutionStatus.RETRYING,
        ExecutionStatus.PAUSED,
        ExecutionStatus.COMPLETED,
        ExecutionStatus.FAILED,
        ExecutionStatus.CANCELLED,
    },
    ExecutionStatus.WAITING: {
        ExecutionStatus.RUNNING,
        ExecutionStatus.CANCELLED,
        ExecutionStatus.FAILED,
    },
    ExecutionStatus.RETRYING: {
        ExecutionStatus.RUNNING,
        ExecutionStatus.FAILED,
        ExecutionStatus.CANCELLED,
    },
    ExecutionStatus.PAUSED: {
        ExecutionStatus.RUNNING,
        ExecutionStatus.CANCELLED,
    },
    ExecutionStatus.CANCELLED: set(),
    ExecutionStatus.COMPLETED: set(),
    ExecutionStatus.FAILED: set(),
}


class ExecutionStateMachine:
    def __init__(self):
        self._transitions: list[StateTransition] = []

    def validate_transition(self, current: ExecutionStatus, target: ExecutionStatus) -> bool:
        return target in VALID_TRANSITIONS.get(current, set())

    def transition(self, current: ExecutionStatus, target: ExecutionStatus, reason: str = "") -> StateTransition:
        if not self.validate_transition(current, target):
            raise InvalidStateTransitionError(current.value, target.value)
        transition = StateTransition(from_state=current, to_state=target, reason=reason)
        self._transitions.append(transition)
        return transition

    def get_history(self) -> list[StateTransition]:
        return list(self._transitions)

    def get_allowed_transitions(self, status: ExecutionStatus) -> list[ExecutionStatus]:
        return list(VALID_TRANSITIONS.get(status, set()))

    def is_terminal(self, status: ExecutionStatus) -> bool:
        return status in {ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED}
