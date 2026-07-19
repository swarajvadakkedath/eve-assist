"""Permission Manager — gating all tool execution."""

from enum import IntEnum
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


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
    status: str = "pending"  # pending, granted, denied
    reason: str = ""
    created_at: datetime = None
    resolved_at: datetime = None

    def __post_init__(self):
        if not self.id:
            self.id = uuid4().hex
        if not self.created_at:
            self.created_at = datetime.utcnow()


@dataclass
class PermissionResult:
    granted: bool
    request: PermissionRequest
    auto_approved: bool = False
    session_approved: bool = False


class PermissionManager:
    def __init__(self):
        self._pending: dict[str, PermissionRequest] = {}
        self._session_approvals: dict[str, datetime] = {}
        self._session_timeout = 300  # 5 minutes
        self._granted_requests: dict[str, PermissionRequest] = {}

    async def check_permission(self, tool_id: str, level: PermissionLevel) -> PermissionResult:
        if level <= PermissionLevel.SAFE:
            return PermissionResult(
                granted=True,
                request=PermissionRequest(tool_id=tool_id, level=level, status="granted"),
                auto_approved=True,
            )
        if level == PermissionLevel.WORKSPACE:
            if tool_id in self._session_approvals:
                if (datetime.utcnow() - self._session_approvals[tool_id]).seconds < self._session_timeout:
                    return PermissionResult(
                        granted=True,
                        request=PermissionRequest(tool_id=tool_id, level=level, status="granted"),
                        session_approved=True,
                    )
        # Check granted requests cache (for SENSITIVE and un-cached WORKSPACE grants)
        for req in self._granted_requests.values():
            if req.tool_id == tool_id and req.status == "granted":
                return PermissionResult(
                    granted=True,
                    request=req,
                    auto_approved=False,
                )
        return PermissionResult(
            granted=False,
            request=PermissionRequest(tool_id=tool_id, level=level),
        )

    async def request_permission(self, tool_id: str, level: PermissionLevel, action: str = "") -> PermissionResult:
        result = await self.check_permission(tool_id, level)
        if result.granted:
            return result

        req = PermissionRequest(tool_id=tool_id, action=action, level=level)
        self._pending[req.id] = req
        return PermissionResult(granted=False, request=req)

    async def grant_permission(self, request_id: str) -> PermissionRequest:
        req = self._pending.pop(request_id, None)
        if req is None:
            raise ValueError(f"No pending request with id: {request_id}")
        req.status = "granted"
        req.resolved_at = datetime.utcnow()
        self._granted_requests[req.tool_id] = req
        if req.level == PermissionLevel.WORKSPACE:
            self._session_approvals[req.tool_id] = datetime.utcnow()
        return req

    async def deny_permission(self, request_id: str, reason: str = "") -> PermissionRequest:
        req = self._pending.pop(request_id, None)
        if req is None:
            raise ValueError(f"No pending request with id: {request_id}")
        req.status = "denied"
        req.reason = reason
        req.resolved_at = datetime.utcnow()
        return req

    async def get_pending_requests(self) -> list[PermissionRequest]:
        return list(self._pending.values())
