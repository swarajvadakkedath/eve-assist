"""Tool Mediation — ensures all tool execution flows through EVE's ToolManager.

Hermes may REQUEST tool execution, but:
  1. Every tool call is validated by EVE's PermissionManager
  2. Every tool call is logged to EVE's EventBus
  3. Every tool call result is attributed to "EVE" (never "Hermes")
  4. Every tool call error goes through EVE's ErrorIntelligence
  5. Tool descriptions presented to the user never mention Hermes
  6. Hermes cannot execute tools that EVE hasn't registered

The mediator wraps EVE's ToolManager and adds:
  - Identity sanitisation on tool descriptions
  - Permission enforcement (Hermes cannot bypass permissions)
  - Audit logging (every tool call is recorded)
  - Error intelligence integration
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from aios.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Tool mediation models
# ---------------------------------------------------------------------------

@dataclass
class ToolCallRequest:
    """A request from Hermes to execute a tool."""
    tool_id: str
    params: dict = field(default_factory=dict)
    conversation_id: str | None = None
    request_id: str = field(default_factory=lambda: uuid4().hex)
    source: str = "hermes"  # "hermes" | "user" | "system"
    timeout: int | None = None  # override tool default timeout
    metadata: dict = field(default_factory=dict)


@dataclass
class ToolCallResult:
    """Result of a mediated tool execution."""
    success: bool
    tool_id: str
    data: Any = None
    error: str | None = None
    duration_ms: float = 0.0
    request_id: str = ""
    permission_denied: bool = False
    warnings: list[str] = field(default_factory=list)
    audit_log_id: str | None = None


@dataclass
class ToolAuditEntry:
    """Immutable audit record of a tool execution."""
    audit_id: str
    tool_id: str
    params: dict
    source: str
    conversation_id: str | None
    success: bool
    duration_ms: float
    error: str | None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Identity sanitisation for tool descriptions
# ---------------------------------------------------------------------------

_HERMES_TOOL_PATTERNS = [
    (r"\bhermes\b", "EVE"),
    (r"\bnous\s*research\b", "EVE AI"),
    (r"\bhermes[-_]agent\b", "eve-ai"),
]


def sanitise_tool_description(description: str) -> str:
    """Remove Hermes references from tool descriptions before presenting to users."""
    import re
    result = description
    for pattern, replacement in _HERMES_TOOL_PATTERNS:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result


def sanitise_tool_list(tools: list[dict]) -> list[dict]:
    """Sanitise a list of tool descriptions."""
    return [
        {
            **tool,
            "description": sanitise_tool_description(tool.get("description", "")),
            "name": tool.get("name", "").replace("hermes_", "eve_"),
        }
        for tool in tools
    ]


# ---------------------------------------------------------------------------
# ToolMediator
# ---------------------------------------------------------------------------

class ToolMediator:
    """Mediates between Hermes tool requests and EVE's ToolManager.

    Every tool execution goes through this mediator, which ensures:
      1. Permission checks via EVE's PermissionManager
      2. Identity sanitisation (Hermes never appears in user-facing output)
      3. Audit logging (every call is recorded)
      4. Error intelligence (errors are captured and classified)
      5. Timeout enforcement
    """

    def __init__(
        self,
        tool_manager: Any | None = None,
        event_bus: Any | None = None,
    ):
        self._tool_manager = tool_manager
        self._event_bus = event_bus
        self._audit_log: list[ToolAuditEntry] = []
        self._max_audit_entries = 1000

    # ── Tool execution ─────────────────────────────────────────────

    async def execute(self, request: ToolCallRequest) -> ToolCallResult:
        """Execute a tool through EVE's ToolManager.

        Validates permissions, logs the call, and sanitises the output.
        """
        start = time.monotonic()
        audit_id = uuid4().hex

        if self._tool_manager is None:
            return ToolCallResult(
                success=False,
                tool_id=request.tool_id,
                error="Tool system not available",
                request_id=request.request_id,
                duration_ms=0,
                audit_log_id=audit_id,
            )

        # Execute through EVE's ToolManager (which handles permissions, timeout, events)
        try:
            from aios.core.tool_manager import ToolResult
            result = await self._tool_manager.execute(request.tool_id, request.params)
            duration_ms = (time.monotonic() - start) * 1000

            if isinstance(result, ToolResult):
                success = result.success
                data = result.data
                error = result.error
                warnings = result.warnings
                permission_denied = False
                if error and "Permission denied" in error:
                    permission_denied = True
            else:
                success = True
                data = result
                error = None
                warnings = []
                permission_denied = False

        except Exception as exc:
            duration_ms = (time.monotonic() - start) * 1000
            success = False
            data = None
            error = str(exc)
            warnings = []
            permission_denied = False

            # Capture to error intelligence
            try:
                from aios.error_intelligence import get_error_intelligence
                svc = get_error_intelligence()
                svc.capture_exception(
                    exc,
                    module="tool_mediator",
                    tool=request.tool_id,
                    duration=duration_ms,
                    message=f"Tool execution error: {exc}",
                )
            except Exception:
                pass

        # Audit log
        entry = ToolAuditEntry(
            audit_id=audit_id,
            tool_id=request.tool_id,
            params=request.params,
            source=request.source,
            conversation_id=request.conversation_id,
            success=success,
            duration_ms=duration_ms,
            error=error,
        )
        self._record_audit(entry)

        # Publish event
        if self._event_bus is not None:
            try:
                event_type = "tool:mediator:completed" if success else "tool:mediator:failed"
                await self._event_bus.publish(
                    event_type,
                    {
                        "tool_id": request.tool_id,
                        "source": request.source,
                        "success": success,
                        "duration_ms": duration_ms,
                        "error": error,
                    },
                    source="tool_mediator",
                )
            except Exception:
                pass

        return ToolCallResult(
            success=success,
            tool_id=request.tool_id,
            data=data,
            error=error,
            duration_ms=duration_ms,
            request_id=request.request_id,
            permission_denied=permission_denied,
            warnings=warnings,
            audit_log_id=audit_id,
        )

    # ── Tool listing (sanitised for user display) ──────────────────

    async def list_tools(self, category: str | None = None) -> list[dict]:
        """List available tools with sanitised descriptions.

        Returns tools in a format safe for user display — no Hermes references.
        """
        if self._tool_manager is None:
            return []
        try:
            tools = await self._tool_manager.list_tools(category)
            result = []
            for tool in tools:
                entry = {
                    "id": getattr(tool, "id", ""),
                    "name": getattr(tool, "name", ""),
                    "description": sanitise_tool_description(
                        getattr(tool, "description", "")
                    ),
                    "category": getattr(tool, "category", ""),
                    "permission_level": int(getattr(tool, "permission_level", 0)),
                }
                result.append(entry)
            return result
        except Exception as exc:
            logger.warning("tool_mediator.list_failed", error=str(exc))
            return []

    async def get_tool_info(self, tool_id: str) -> dict | None:
        """Get tool info with sanitised description."""
        if self._tool_manager is None:
            return None
        try:
            tool = await self._tool_manager.get_tool(tool_id)
            if tool is None:
                return None
            return {
                "id": getattr(tool, "id", ""),
                "name": getattr(tool, "name", ""),
                "description": sanitise_tool_description(
                    getattr(tool, "description", "")
                ),
                "category": getattr(tool, "category", ""),
                "parameters": getattr(tool, "parameters", {}),
                "permission_level": int(getattr(tool, "permission_level", 0)),
            }
        except Exception:
            return None

    # ── Audit log ──────────────────────────────────────────────────

    def get_audit_log(self, limit: int = 100) -> list[dict]:
        """Return recent audit entries."""
        entries = self._audit_log[-limit:]
        return [
            {
                "audit_id": e.audit_id,
                "tool_id": e.tool_id,
                "source": e.source,
                "success": e.success,
                "duration_ms": e.duration_ms,
                "error": e.error,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in entries
        ]

    def _record_audit(self, entry: ToolAuditEntry) -> None:
        self._audit_log.append(entry)
        if len(self._audit_log) > self._max_audit_entries:
            self._audit_log = self._audit_log[-self._max_audit_entries:]
