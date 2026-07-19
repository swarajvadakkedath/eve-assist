"""Execution Exceptions."""


class ExecutionBaseError(Exception):
    message = "An execution error occurred"


class ExecutionNotFoundError(ExecutionBaseError):
    def __init__(self, execution_id: str):
        super().__init__(f"Execution not found: {execution_id}")


class TaskNotFoundError(ExecutionBaseError):
    def __init__(self, task_id: str):
        super().__init__(f"Task not found: {task_id}")


class InvalidStateTransitionError(ExecutionBaseError):
    def __init__(self, from_state: str, to_state: str):
        super().__init__(f"Invalid state transition: {from_state} -> {to_state}")


class TaskExecutionError(ExecutionBaseError):
    def __init__(self, task_id: str, reason: str):
        super().__init__(f"Task {task_id} execution failed: {reason}")


class CapabilityResolutionError(ExecutionBaseError):
    def __init__(self, capability: str):
        super().__init__(f"Could not resolve capability: {capability}")


class SchedulerQueueFullError(ExecutionBaseError):
    def __init__(self, max_size: int):
        super().__init__(f"Scheduler queue is full, max size: {max_size}")

class DependencyError(ExecutionBaseError):
    def __init__(self, task_id: str, missing_deps: list):
        super().__init__(f"Task {task_id} has missing dependencies: {missing_deps}")


class PermissionRequiredError(ExecutionBaseError):
    def __init__(self, task_id: str, request_id: str):
        super().__init__(f"Permission required for task {task_id} (request: {request_id})")
        self.request_id = request_id


class TimeoutError(ExecutionBaseError):
    def __init__(self, task_id: str, timeout: int):
        super().__init__(f"Task {task_id} timed out after {timeout}s")


class RollbackError(ExecutionBaseError):
    def __init__(self, reason: str):
        super().__init__(f"Rollback error: {reason}")
