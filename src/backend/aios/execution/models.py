"""Execution Models — strongly typed execution, task, and result models."""

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


class ExecutionStatus(str, enum.Enum):
    PENDING = "pending"
    PLANNING = "planning"
    WAITING_FOR_PERMISSION = "waiting_for_permission"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    RETRYING = "retrying"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class Priority(int, enum.Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Execution:
    id: str = ""
    status: ExecutionStatus = ExecutionStatus.PENDING
    objective: str = ""
    created_at: datetime = None
    updated_at: datetime = None
    started_at: datetime = None
    completed_at: datetime = None
    owner: str = ""
    priority: Priority = Priority.NORMAL
    metadata: dict = field(default_factory=dict)
    plan_id: str = ""
    conversation_id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = uuid4().hex
        if not self.created_at:
            self.created_at = datetime.utcnow()
        if not self.updated_at:
            self.updated_at = self.created_at


@dataclass
class Task:
    id: str = ""
    execution_id: str = ""
    parent_task: str | None = None
    capability: str = ""
    tool: str = ""
    parameters: dict = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    retries: int = 0
    max_retries: int = 3
    timeout: int = 60
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str | None = None
    started_at: datetime = None
    completed_at: datetime = None
    duration_ms: float = 0.0
    permission_request_id: str | None = None
    is_optional: bool = False
    index: int = 0

    def __post_init__(self):
        if not self.id:
            self.id = uuid4().hex


@dataclass
class ExecutionResult:
    success: bool = False
    output: str = ""
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    tool_results: list[dict] = field(default_factory=list)
    task_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    tools_executed: list[str] = field(default_factory=list)
    capabilities_used: list[str] = field(default_factory=list)
    retry_count: int = 0
    permission_requests: int = 0


@dataclass
class ExecutionProgress:
    percentage: float = 0.0
    current_task: str = ""
    current_capability: str = ""
    completed_tasks: int = 0
    total_tasks: int = 0
    remaining_tasks: int = 0
    estimated_completion_ms: float = 0.0
    status: ExecutionStatus = ExecutionStatus.PENDING
