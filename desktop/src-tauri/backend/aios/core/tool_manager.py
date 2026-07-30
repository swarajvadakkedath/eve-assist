"""Tool Manager — tool registration, validation, and execution."""

import asyncio
import inspect
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable
from aios.core.event_bus import EventBus
from aios.core.di_container import DIContainer
from aios.core.permission_manager import PermissionLevel, PermissionManager
from aios.core.capability_registry import CapabilityRegistry, Capability


class ToolManagerError(Exception):
    code: str = "TOOL_MANAGER_ERROR"


class ValidationError(ToolManagerError):
    code: str = "VALIDATION_ERROR"


class ToolTimeoutError(ToolManagerError):
    code: str = "TOOL_TIMEOUT"


class ToolExecutionError(ToolManagerError):
    code: str = "TOOL_EXECUTION_ERROR"


@dataclass
class ToolContract:
    id: str
    name: str
    description: str
    parameters: dict = field(default_factory=dict)
    returns: dict = field(default_factory=dict)
    permission_level: PermissionLevel = PermissionLevel.READ
    timeout: int = 30
    requires_confirmation: bool = True
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)


@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: str | None = None
    duration: float = 0.0
    warnings: list[str] = field(default_factory=list)


def _validate_params(params_schema: dict, actual_params: dict) -> str | None:
    if not params_schema:
        return None
    schema_type = params_schema.get("type", "object")
    if schema_type != "object":
        return None
    properties = params_schema.get("properties", {})
    required = params_schema.get("required", [])
    for field_name in required:
        if field_name not in actual_params:
            return f"Missing required field: {field_name}"
    for field_name, value in actual_params.items():
        if field_name not in properties:
            continue
        prop = properties[field_name]
        expected = prop.get("type", "")
        if not expected:
            continue
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": (list, tuple),
            "object": dict,
        }
        py_type = type_map.get(expected)
        if py_type is not None and not isinstance(value, py_type):
            return (
                f"Field '{field_name}' expected type {expected}, "
                f"got {type(value).__name__}"
            )
    return None


def _contract_to_capability(contract: ToolContract) -> Capability:
    return Capability(
        id=contract.id,
        name=contract.name,
        description=contract.description,
        provider_type="tool",
        provider_id=contract.id,
        parameters=contract.parameters,
        returns=contract.returns,
        permission_level=int(contract.permission_level),
        tags=contract.tags,
        version="1.1.0",
        quality=1.0,
        requires_confirmation=contract.requires_confirmation,
        supported_interfaces=["chat"],
        related_capabilities=contract.capabilities,
    )


async def _run_handler(handler: Callable, params: dict) -> Any:
    if inspect.iscoroutinefunction(handler):
        return await handler(params)
    result = await asyncio.to_thread(handler, params)
    if inspect.iscoroutine(result):
        return await result
    return result


class ToolManager:
    def __init__(
        self,
        permission_manager: PermissionManager,
        capability_registry: CapabilityRegistry | None = None,
        event_bus: EventBus | None = None,
    ):
        self._tools: dict[str, tuple[ToolContract, Callable]] = {}
        self._permission_manager = permission_manager
        self._capability_registry = capability_registry
        self._event_bus = event_bus

    @staticmethod
    def register_in_container(
        container: DIContainer,
        permission_manager: PermissionManager | None = None,
        capability_registry: CapabilityRegistry | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        def factory() -> ToolManager:
            pm = permission_manager or container.resolve(PermissionManager)
            cr = capability_registry
            eb = event_bus
            return ToolManager(
                permission_manager=pm,
                capability_registry=cr,
                event_bus=eb,
            )

        container.register(ToolManager, factory=factory)

    def tool(self, name: str = "", description: str = "", **kwargs) -> Callable:
        def decorator(handler: Callable) -> Callable:
            contract = ToolContract(
                id=name or handler.__name__,
                name=name or handler.__name__,
                description=description,
                parameters=kwargs.get("parameters", {}),
                returns=kwargs.get("returns", {}),
                permission_level=kwargs.get("permission_level", PermissionLevel.READ),
                timeout=kwargs.get("timeout", 30),
                requires_confirmation=kwargs.get("requires_confirmation", False),
                category=kwargs.get("category", "general"),
                tags=kwargs.get("tags", []),
                capabilities=kwargs.get("capabilities", [name or handler.__name__]),
            )
            try:
                asyncio.get_running_loop().create_task(self.register_tool(contract, handler))
            except RuntimeError:
                pass
            return handler

        return decorator

    async def register_tool(self, contract: ToolContract, handler: Callable) -> None:
        self._tools[contract.id] = (contract, handler)
        if self._capability_registry:
            cap = _contract_to_capability(contract)
            await self._capability_registry.register_capability(cap)

    async def unregister_tool(self, tool_id: str) -> None:
        self._tools.pop(tool_id, None)

    async def execute(self, tool_id: str, params: dict) -> ToolResult:
        entry = self._tools.get(tool_id)
        if entry is None:
            return ToolResult(success=False, error=f"Tool not found: {tool_id}")

        contract, handler = entry

        error_msg = _validate_params(contract.parameters, params)
        if error_msg is not None:
            return ToolResult(
                success=False,
                error=f"Validation error: {error_msg}",
                data={"validation_error": error_msg},
            )

        perm_result = await self._permission_manager.check_permission(
            tool_id, contract.permission_level
        )
        if not perm_result.granted:
            req_result = await self._permission_manager.request_permission(
                tool_id, contract.permission_level, action=tool_id
            )
            req_id = req_result.request.id if req_result.request else ""
            return ToolResult(
                success=False,
                error=f"Permission denied: {tool_id}",
                data={
                    "permission_request_id": req_id,
                    "level": int(contract.permission_level),
                },
            )

        await self._publish_event(
            "tool:started",
            {"tool_id": tool_id, "params": params, "timeout": contract.timeout},
        )

        start = datetime.now(timezone.utc)
        try:
            result = await asyncio.wait_for(
                _run_handler(handler, params),
                timeout=contract.timeout,
            )
            duration = (datetime.now(timezone.utc) - start).total_seconds()
            if isinstance(result, ToolResult):
                result.duration = duration
                await self._publish_event(
                    "tool:completed",
                    {
                        "tool_id": tool_id,
                        "duration": duration,
                        "success": result.success,
                    },
                )
                return result
            await self._publish_event(
                "tool:completed",
                {
                    "tool_id": tool_id,
                    "duration": duration,
                    "success": True,
                },
            )
            return ToolResult(success=True, data=result, duration=duration)
        except asyncio.TimeoutError:
            duration = (datetime.now(timezone.utc) - start).total_seconds()
            await self._publish_event(
                "tool:timeout",
                {
                    "tool_id": tool_id,
                    "duration": duration,
                    "timeout": contract.timeout,
                },
            )
            return ToolResult(
                success=False,
                error=f"Tool timed out after {contract.timeout}s: {tool_id}",
                duration=duration,
            )
        except ToolManagerError:
            raise
        except Exception as e:
            duration = (datetime.now(timezone.utc) - start).total_seconds()
            await self._publish_event(
                "tool:failed",
                {
                    "tool_id": tool_id,
                    "duration": duration,
                    "error": str(e),
                },
            )
            return ToolResult(
                success=False,
                error=f"Tool execution error: {e}",
                duration=duration,
            )

    async def get_tool(self, tool_id: str) -> ToolContract | None:
        entry = self._tools.get(tool_id)
        return entry[0] if entry else None

    async def list_tools(self, category: str | None = None) -> list[ToolContract]:
        if category:
            return [c for c, _ in self._tools.values() if c.category == category]
        return [c for c, _ in self._tools.values()]

    async def search_tools(self, query: str) -> list[ToolContract]:
        q = query.lower()
        return [
            c
            for c, _ in self._tools.values()
            if q in c.id.lower()
            or q in c.name.lower()
            or q in c.description.lower()
        ]

    async def _publish_event(self, event_type: str, payload: dict) -> None:
        if self._event_bus:
            await self._event_bus.publish(event_type, payload, source="tool_manager")
