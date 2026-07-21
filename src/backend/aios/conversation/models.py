"""Strongly-typed data models for conversations."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolCallStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StreamEventType(str, Enum):
    TOKEN = "token"
    DONE = "done"
    ERROR = "error"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    STATUS = "status"
    PLANNER_STARTED = "planner_started"
    PLANNER_COMPLETED = "planner_completed"
    MEMORY_RETRIEVAL = "memory_retrieval"
    TOOL_REQUESTED = "tool_requested"
    TOOL_RUNNING = "tool_running"
    TOOL_COMPLETED = "tool_completed"
    CONTEXT_LOADED = "context_loaded"
    FINAL_RESPONSE = "final_response"
    TITLE_GENERATED = "title_generated"
    ANALYTICS = "analytics"
    VISION_OBSERVATION = "vision_observation"


@dataclass
class ToolCall:
    tool_name: str = ""
    capability: str = ""
    parameters: dict = field(default_factory=dict)
    result: Any = None
    execution_time: float = 0.0
    status: ToolCallStatus = ToolCallStatus.PENDING

    def __post_init__(self):
        if isinstance(self.status, str):
            self.status = ToolCallStatus(self.status)


@dataclass
class EditEntry:
    original_content: str
    edited_content: str
    timestamp: datetime
    regenerated: bool = False


@dataclass
class PlanningContext:
    intent: str | None = None
    plan: Any | None = None
    selected_capabilities: list[str] = field(default_factory=list)
    planning_time_ms: float | None = None
    planner_version: str | None = None


@dataclass
class ExecutionContext:
    execution_id: str | None = None
    status: str | None = None
    current_step: int = 0
    completed_steps: int = 0
    total_steps: int = 0
    progress: float = 0.0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float | None = None
    error: str | None = None
    cancelled: bool = False
    tools_executed: list[str] = field(default_factory=list)
    capabilities_used: list[str] = field(default_factory=list)
    retry_count: int = 0
    permission_requests: int = 0
    warnings: list[str] = field(default_factory=list)


@dataclass
class Message:
    id: str = ""
    conversation_id: str = ""
    role: MessageRole = MessageRole.USER
    content: str = ""
    timestamp: datetime | None = None
    attachments: list[dict] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    tokens_used: int = 0
    edit_history: list[EditEntry] = field(default_factory=list)
    is_regenerated: bool = False
    latency_ms: float = 0.0
    planning_context: PlanningContext | None = None
    execution_context: ExecutionContext | None = None

    @property
    def detected_intent(self) -> str | None:
        return self.planning_context.intent if self.planning_context else None

    @property
    def generated_plan(self) -> Any | None:
        return self.planning_context.plan if self.planning_context else None

    @property
    def selected_capabilities(self) -> list[str]:
        return self.planning_context.selected_capabilities if self.planning_context else []

    def __post_init__(self):
        if not self.id:
            self.id = uuid4().hex
        if not self.timestamp:
            self.timestamp = datetime.utcnow()
        if isinstance(self.role, str):
            self.role = MessageRole(self.role)


@dataclass
class Conversation:
    id: str = ""
    title: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    active_project: str | None = None
    is_active: bool = True
    mode: str = "chat"
    metadata: dict = field(default_factory=dict)
    message_count: int = 0
    parent_id: str | None = None
    branch_point_message_id: str | None = None

    def __post_init__(self):
        if not self.id:
            self.id = uuid4().hex
        now = datetime.utcnow()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    @property
    def is_branch(self) -> bool:
        return bool(self.parent_id or (self.metadata and self.metadata.get("is_branch")))

    @property
    def title_is_custom(self) -> bool:
        return bool(self.metadata and self.metadata.get("title_is_custom"))


@dataclass
class Session:
    session_id: str = ""
    conversation_id: str = ""
    current_context: dict = field(default_factory=dict)
    active_capabilities: list[str] = field(default_factory=list)
    memory_reference: dict = field(default_factory=dict)
    planner_state: dict = field(default_factory=dict)
    created_at: datetime | None = None
    expires_at: datetime | None = None

    def __post_init__(self):
        if not self.session_id:
            self.session_id = uuid4().hex
        if not self.created_at:
            self.created_at = datetime.utcnow()


class StreamEvent:
    def __init__(self, type: StreamEventType, data: dict):
        self.type = type
        self.data = data
