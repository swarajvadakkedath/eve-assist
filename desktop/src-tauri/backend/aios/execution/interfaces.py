"""Execution Interfaces — abstract contracts for the Execution Engine."""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from aios.execution.models import Execution, Task, ExecutionResult, ExecutionProgress


class IExecutionEngine(ABC):
    @abstractmethod
    async def start_execution(self, objective: str, conversation_id: str = "", owner: str = "", priority: int = 1) -> Execution:
        ...

    @abstractmethod
    async def get_execution(self, execution_id: str) -> Execution:
        ...

    @abstractmethod
    async def pause_execution(self, execution_id: str) -> Execution:
        ...

    @abstractmethod
    async def resume_execution(self, execution_id: str) -> Execution:
        ...

    @abstractmethod
    async def cancel_execution(self, execution_id: str) -> Execution:
        ...

    @abstractmethod
    async def get_execution_progress(self, execution_id: str) -> ExecutionProgress:
        ...

    @abstractmethod
    async def stream_events(self, execution_id: str) -> AsyncIterator[dict]:
        ...


class IExecutor(ABC):
    @abstractmethod
    async def execute_task(self, task: Task) -> Task:
        ...

    @abstractmethod
    async def validate_task(self, task: Task) -> bool:
        ...


class IScheduler(ABC):
    @abstractmethod
    async def schedule(self, execution: Execution, tasks: list[Task]) -> AsyncIterator[Task]:
        ...

    @abstractmethod
    async def cancel(self, execution_id: str) -> None:
        ...

    @abstractmethod
    async def pause(self, execution_id: str) -> None:
        ...

    @abstractmethod
    async def resume(self, execution_id: str) -> None:
        ...


class IRecoveryEngine(ABC):
    @abstractmethod
    async def handle_failure(self, execution: Execution, task: Task) -> tuple[bool, Task | None]:
        ...

    @abstractmethod
    async def can_continue(self, execution: Execution) -> bool:
        ...
