"""Permission Manager — gating all tool execution with audit, events, and config."""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import IntEnum
from time import monotonic
from typing import Any
from uuid import uuid4

from aios.core.event_bus import EventBus
from aios.core.di_container import DIContainer


class PermissionLevel(IntEnum):
    READ = 0
    SAFE = 1
    WORKSPACE = 2
    SENSITIVE = 3


@dataclass
class PermissionRequest:
    id: str = ""
    tool_id: str = ""
    action: str = ""
    level: PermissionLevel = PermissionLevel.READ
    description: str = ""
    status: str = "pending"
    reason: str = ""
    created_at: datetime = None
    resolved_at: datetime = None
    session_id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = uuid4().hex
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc)


@dataclass
class PermissionResult:
    granted: bool
    request: PermissionRequest
    auto_approved: bool = False
    session_approved: bool = False


@dataclass
class AuditEntry:
    timestamp: datetime
    tool_id: str
    action: str
    level: int
    decision: str
    session_id: str
    reason: str
    request_id: str


class PermissionManager:
    def __init__(
        self,
        event_bus: EventBus | None = None,
        config: Any | None = None,
    ):
        self._pending: dict[str, PermissionRequest] = {}
        self._session_approvals: dict[str, float] = {}
        self._session_timeout: float = 300.0
        self._granted_requests: dict[str, PermissionRequest] = {}
        self._audit_log: list[AuditEntry] = []
        self._event_bus = event_bus
        self._config = config
        self._sensitive_actions: set[str] = set()
        self._default_level: int = 1

    @staticmethod
    def register_in_container(
        container: DIContainer,
        event_bus: EventBus | None = None,
        config: Any | None = None,
    ) -> DIContainer:
        def factory() -> PermissionManager:
            return PermissionManager(event_bus=event_bus, config=config)

        container.register(PermissionManager, factory=factory)
        return container

    def configure(self, default_level: int | None = None, sensitive_actions: list[str] | None = None, session_timeout: float | None = None) -> None:
        if default_level is not None:
            self._default_level = default_level
        if sensitive_actions is not None:
            self._sensitive_actions = set(sensitive_actions)
        if session_timeout is not None:
            self._session_timeout = session_timeout

    def _load_config(self) -> None:
        if self._config is None:
            return
        try:
            level = int(getattr(self._config, "permission_default_level", 1))
            sensitive = list(getattr(self._config, "permission_sensitive_actions", []))
            timeout = float(getattr(self._config, "session_timeout_seconds", 300))
            self._default_level = level
            if sensitive:
                self._sensitive_actions = set(sensitive)
            self._session_timeout = timeout
        except (ValueError, TypeError, AttributeError):
            pass

    def _apply_default_level(self, level: PermissionLevel) -> PermissionLevel:
        self._load_config()
        if level < PermissionLevel(self._default_level):
            return PermissionLevel(self._default_level)
        return level

    async def check_permission(self, tool_id: str, level: PermissionLevel) -> PermissionResult:
        self._load_config()
        level = self._apply_default_level(level)

        if tool_id in self._sensitive_actions:
            level = PermissionLevel.SENSITIVE

        if level == PermissionLevel.WORKSPACE:
            if await self._check_session_valid(tool_id):
                return PermissionResult(
                    granted=True,
                    request=PermissionRequest(tool_id=tool_id, level=level, status="granted"),
                    session_approved=True,
                )

        for req in list(self._granted_requests.values()):
            if req.tool_id == tool_id and req.status == "granted":
                if level == PermissionLevel.WORKSPACE:
                    if await self._check_session_valid(tool_id):
                        return PermissionResult(
                            granted=True,
                            request=req,
                            session_approved=True,
                        )
                    continue
                return PermissionResult(
                    granted=True,
                    request=req,
                )

        if level <= PermissionLevel.SAFE:
            return PermissionResult(
                granted=True,
                request=PermissionRequest(tool_id=tool_id, level=level, status="granted"),
                auto_approved=True,
            )

        return PermissionResult(
            granted=False,
            request=PermissionRequest(tool_id=tool_id, level=level),
        )

    async def _check_session_valid(self, tool_id: str) -> bool:
        entry = self._session_approvals.get(tool_id)
        if entry is None:
            return False
        elapsed = monotonic() - entry
        if elapsed < self._session_timeout:
            return True
        del self._session_approvals[tool_id]
        await self._publish_event(
            "permission:expired",
            {"tool_id": tool_id, "session_duration": elapsed, "session_timeout": self._session_timeout},
        )
        self._audit_log.append(AuditEntry(
            timestamp=datetime.now(timezone.utc),
            tool_id=tool_id,
            action="",
            level=int(PermissionLevel.WORKSPACE),
            decision="expired",
            session_id="",
            reason="Session approval expired",
            request_id="",
        ))
        return False

    async def request_permission(self, tool_id: str, level: PermissionLevel, action: str = "") -> PermissionResult:
        result = await self.check_permission(tool_id, level)
        if result.granted:
            return result

        req = PermissionRequest(tool_id=tool_id, action=action, level=level)
        self._pending[req.id] = req

        await self._publish_event(
            "permission:requested",
            {
                "request_id": req.id,
                "tool_id": tool_id,
                "action": action,
                "level": int(level),
            },
        )
        self._audit_log.append(AuditEntry(
            timestamp=datetime.now(timezone.utc),
            tool_id=tool_id,
            action=action,
            level=int(level),
            decision="requested",
            session_id="",
            reason="",
            request_id=req.id,
        ))
        return PermissionResult(granted=False, request=req)

    async def grant_permission(self, request_id: str, session_id: str = "") -> PermissionRequest:
        req = self._pending.pop(request_id, None)
        if req is None:
            raise ValueError(f"No pending request with id: {request_id}")
        req.status = "granted"
        req.resolved_at = datetime.now(timezone.utc)
        req.session_id = session_id
        self._granted_requests[req.tool_id] = req
        if req.level == PermissionLevel.WORKSPACE:
            self._session_approvals[req.tool_id] = monotonic()
        await self._publish_event(
            "permission:granted",
            {
                "request_id": req.id,
                "tool_id": req.tool_id,
                "action": req.action,
                "level": int(req.level),
                "session_id": session_id,
            },
        )
        self._audit_log.append(AuditEntry(
            timestamp=datetime.now(timezone.utc),
            tool_id=req.tool_id,
            action=req.action,
            level=int(req.level),
            decision="granted",
            session_id=session_id,
            reason="",
            request_id=req.id,
        ))
        return req

    async def deny_permission(self, request_id: str, reason: str = "", session_id: str = "") -> PermissionRequest:
        req = self._pending.pop(request_id, None)
        if req is None:
            raise ValueError(f"No pending request with id: {request_id}")
        req.status = "denied"
        req.reason = reason
        req.resolved_at = datetime.now(timezone.utc)
        req.session_id = session_id
        await self._publish_event(
            "permission:denied",
            {
                "request_id": req.id,
                "tool_id": req.tool_id,
                "action": req.action,
                "level": int(req.level),
                "reason": reason,
                "session_id": session_id,
            },
        )
        self._audit_log.append(AuditEntry(
            timestamp=datetime.now(timezone.utc),
            tool_id=req.tool_id,
            action=req.action,
            level=int(req.level),
            decision="denied",
            session_id=session_id,
            reason=reason,
            request_id=req.id,
        ))
        return req

    async def get_pending_requests(self) -> list[PermissionRequest]:
        return list(self._pending.values())

    async def get_audit_history(
        self,
        tool_id: str | None = None,
        decision: str | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        results = list(self._audit_log)
        if tool_id:
            results = [e for e in results if e.tool_id == tool_id]
        if decision:
            results = [e for e in results if e.decision == decision]
        return results[-limit:]

    async def _publish_event(self, event_type: str, payload: dict) -> None:
        if self._event_bus:
            await self._event_bus.publish(event_type, payload, source="permission_manager")
