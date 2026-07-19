"""Execution Engine — central orchestration layer for AIOS task execution."""

import asyncio
import time
from datetime import datetime
from typing import Any, AsyncIterator
from uuid import uuid4

from aios.execution.models import (
    Execution, Task, ExecutionResult, ExecutionProgress,
    ExecutionStatus, TaskStatus, Priority,
)
from aios.execution.state_machine import ExecutionStateMachine
from aios.execution.scheduler import Scheduler
from aios.execution.executor import TaskExecutor
from aios.execution.planner_adapter import PlannerAdapter
from aios.execution.recovery import RecoveryEngine
from aios.execution.progress import ProgressTracker
from aios.execution.permissions import ExecutionPermissionManager
from aios.execution.events import ExecutionEventPublisher
from aios.execution.repository import ExecutionRepository
from aios.execution.workflow import WorkflowBuilder
from aios.execution.exceptions import (
    ExecutionNotFoundError, InvalidStateTransitionError,
)
from aios.utils.logger import get_logger

logger = get_logger(__name__)


class ExecutionEngine:
    def __init__(
        self,
        planner: Any | None = None,
        capability_registry: Any | None = None,
        tool_manager: Any | None = None,
        permission_manager: Any | None = None,
        event_bus: Any | None = None,
        db: Any | None = None,
        max_concurrent: int = 5,
    ):
        self._state_machine = ExecutionStateMachine()
        self._scheduler = Scheduler(max_concurrent=max_concurrent)
        self._executor = TaskExecutor(capability_registry, tool_manager)
        self._planner_adapter = PlannerAdapter(planner)
        self._recovery = RecoveryEngine(self._planner_adapter)
        self._progress = ProgressTracker()
        self._permissions = ExecutionPermissionManager(permission_manager)
        self._events = ExecutionEventPublisher(event_bus)
        self._repository = ExecutionRepository(db)
        self._workflow = WorkflowBuilder()

        self._active_executions: dict[str, asyncio.Task] = {}

    async def start_execution(
        self,
        objective: str,
        conversation_id: str = "",
        owner: str = "",
        priority: int = 1,
    ) -> Execution:
        execution = Execution(
            objective=objective,
            conversation_id=conversation_id,
            owner=owner,
            priority=Priority(priority),
            status=ExecutionStatus.PENDING,
        )
        await self._repository.save_execution(execution)
        await self._events.execution_created(execution.id, objective, priority)

        run_task = asyncio.create_task(self._run_execution(execution))
        self._active_executions[execution.id] = run_task

        logger.info("engine.execution_started", execution_id=execution.id, objective=objective[:100])
        return execution

    async def _run_execution(self, execution: Execution) -> None:
        start_time = time.monotonic()
        try:
            transition = self._state_machine.transition(
                execution.status, ExecutionStatus.PLANNING, "Starting execution"
            )
            execution.status = ExecutionStatus.PLANNING
            await self._repository.save_execution(execution)

            plan = await self._planner_adapter.create_plan(
                execution.objective,
                {"execution_id": execution.id, "conversation_id": execution.conversation_id},
            )

            if not plan:
                execution.status = ExecutionStatus.FAILED
                execution.completed_at = datetime.utcnow()
                await self._repository.save_execution(execution)
                await self._events.execution_failed(execution.id, "Failed to create plan")
                return

            execution.plan_id = plan.id
            tasks = self._workflow.build_tasks(execution, plan)

            if not tasks:
                execution.status = ExecutionStatus.FAILED
                execution.completed_at = datetime.utcnow()
                await self._repository.save_execution(execution)
                await self._events.execution_failed(execution.id, "No tasks in plan")
                return

            execution.status = ExecutionStatus.READY
            await self._repository.save_execution(execution)

            progress = self._progress.initialize(execution, tasks)

            execution.status = ExecutionStatus.RUNNING
            execution.started_at = datetime.utcnow()
            await self._repository.save_execution(execution)
            await self._events.execution_started(execution.id, len(tasks))

            async for task in self._scheduler.schedule(execution, tasks):
                if task.status == TaskStatus.CANCELLED:
                    await self._repository.save_task(execution.id, task)
                    continue

                permission_granted, request_id = await self._permissions.check_task(task)
                if not permission_granted and request_id:
                    task.status = TaskStatus.PENDING
                    await self._events.permission_requested(execution.id, task, request_id)
                    execution.status = ExecutionStatus.WAITING_FOR_PERMISSION
                    self._progress.set_status(execution.id, ExecutionStatus.WAITING_FOR_PERMISSION)
                    await self._repository.save_execution(execution)
                    continue

                self._progress.task_started(execution.id, task)
                await self._events.task_started(execution.id, task)

                executed_task = await self._executor.execute_task(task)

                if executed_task.status == TaskStatus.FAILED:
                    recovered, new_task = await self._recovery.handle_failure(execution, executed_task)
                    if recovered and new_task:
                        new_task.index = executed_task.index
                        await self._repository.save_task(execution.id, executed_task)
                        executed_task = await self._executor.execute_task(new_task)

                await self._repository.save_task(execution.id, executed_task)
                self._progress.task_completed(execution.id, executed_task)

                if executed_task.status == TaskStatus.SUCCESS:
                    await self._events.task_completed(execution.id, executed_task)
                else:
                    await self._events.task_failed(execution.id, executed_task, executed_task.error or "Unknown")

                can_continue = await self._recovery.can_continue(execution, tasks)
                if not can_continue:
                    execution.status = ExecutionStatus.FAILED
                    break

                current_progress = self._progress.get_progress(execution.id)
                if current_progress:
                    await self._events.progress(execution.id, current_progress)

            if execution.status != ExecutionStatus.FAILED:
                result = self._workflow.build_execution_result(execution, tasks)
                result.duration_ms = (time.monotonic() - start_time) * 1000
                await self._repository.save_result(execution.id, result)

                execution.status = ExecutionStatus.COMPLETED if result.success else ExecutionStatus.FAILED
                execution.completed_at = datetime.utcnow()
                await self._repository.save_execution(execution)

                if result.success:
                    await self._events.execution_completed(execution.id, result)
                else:
                    await self._events.execution_failed(execution.id, "; ".join(result.errors))

        except asyncio.CancelledError:
            execution.status = ExecutionStatus.CANCELLED
            execution.completed_at = datetime.utcnow()
            await self._repository.save_execution(execution)
            return

        except Exception as e:
            logger.error("engine.execution_failed", execution_id=execution.id, error=str(e))
            execution.status = ExecutionStatus.FAILED
            execution.completed_at = datetime.utcnow()
            await self._repository.save_execution(execution)
            await self._events.execution_failed(execution.id, str(e))

        finally:
            await self._scheduler.cleanup(execution.id)

    async def get_execution(self, execution_id: str) -> Execution:
        execution = await self._repository.get_execution(execution_id)
        if not execution:
            raise ExecutionNotFoundError(execution_id)
        return execution

    async def pause_execution(self, execution_id: str) -> Execution:
        execution = await self.get_execution(execution_id)
        try:
            self._state_machine.transition(execution.status, ExecutionStatus.PAUSED, "User requested pause")
        except InvalidStateTransitionError:
            return execution
        execution.status = ExecutionStatus.PAUSED
        await self._scheduler.pause(execution_id)
        await self._repository.save_execution(execution)
        await self._events.pause_resume(execution_id, "paused")
        return execution

    async def resume_execution(self, execution_id: str) -> Execution:
        execution = await self.get_execution(execution_id)
        try:
            self._state_machine.transition(execution.status, ExecutionStatus.RUNNING, "User requested resume")
        except InvalidStateTransitionError:
            return execution
        execution.status = ExecutionStatus.RUNNING
        await self._scheduler.resume(execution_id)
        await self._repository.save_execution(execution)
        await self._events.pause_resume(execution_id, "resumed")
        return execution

    async def cancel_execution(self, execution_id: str) -> Execution:
        execution = await self.get_execution(execution_id)
        try:
            self._state_machine.transition(execution.status, ExecutionStatus.CANCELLED, "User requested cancel")
        except InvalidStateTransitionError:
            return execution
        execution.status = ExecutionStatus.CANCELLED
        execution.completed_at = datetime.utcnow()
        await self._scheduler.cancel(execution_id)
        await self._repository.save_execution(execution)

        active_task = self._active_executions.get(execution_id)
        if active_task:
            active_task.cancel()
        return execution

    async def get_execution_progress(self, execution_id: str) -> ExecutionProgress:
        progress = self._progress.get_progress(execution_id)
        if progress:
            return progress
        execution = await self.get_execution(execution_id)
        tasks = await self._repository.get_tasks(execution_id)
        return ExecutionProgress(
            total_tasks=len(tasks),
            completed_tasks=sum(1 for t in tasks if t.status == TaskStatus.SUCCESS),
            status=execution.status,
        )

    async def get_execution_result(self, execution_id: str) -> ExecutionResult | None:
        return await self._repository.get_result(execution_id)

    async def get_execution_tasks(self, execution_id: str) -> list[Task]:
        return await self._repository.get_tasks(execution_id)

    async def list_executions(self, limit: int = 50, offset: int = 0) -> list[Execution]:
        return await self._repository.list_executions(limit, offset)

    async def stream_events(self, execution_id: str) -> AsyncIterator[dict]:
        execution = await self.get_execution(execution_id)
        offset = 0
        while execution.status not in {
            ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED
        }:
            events = await self._repository.get_events(execution_id)
            for event in events[offset:]:
                yield event
                offset += 1
            await asyncio.sleep(0.5)
            execution = await self.get_execution(execution_id)

        events = await self._repository.get_events(execution_id)
        for event in events[offset:]:
            yield event

    async def get_history(self, limit: int = 50) -> list[dict]:
        executions = await self._repository.list_executions(limit, 0)
        history = []
        for ex in executions:
            result = await self._repository.get_result(ex.id)
            history.append({
                "id": ex.id,
                "objective": ex.objective,
                "status": ex.status.value,
                "created_at": ex.created_at.isoformat() if ex.created_at else "",
                "completed_at": ex.completed_at.isoformat() if ex.completed_at else "",
                "task_count": result.task_count if result else 0,
                "completed_count": result.completed_count if result else 0,
                "failed_count": result.failed_count if result else 0,
                "duration_ms": result.duration_ms if result else 0,
            })
        return history
