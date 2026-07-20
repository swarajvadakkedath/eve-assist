"""Tool Manager — tool registration, validation, and execution."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable
from aios.core.permission_manager import PermissionLevel, PermissionManager
from aios.core.capability_registry import CapabilityRegistry, Capability


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
        version="1.0.0",
        quality=1.0,
        requires_confirmation=contract.requires_confirmation,
        supported_interfaces=["chat"],
        related_capabilities=contract.capabilities,
    )


class ToolManager:
    def __init__(self, permission_manager: PermissionManager, capability_registry: CapabilityRegistry | None = None):
        self._tools: dict[str, tuple[ToolContract, Callable]] = {}
        self._permission_manager = permission_manager
        self._capability_registry = capability_registry

    def tool(self, name: str = "", description: str = "", **kwargs) -> Callable:
        """Decorator-based tool registration.

        Usage::

            @tm.tool(name="my_tool", description="...", parameters={...})
            async def my_handler(params: dict) -> str: ...

        Accepted kwargs: parameters, returns, permission_level, timeout,
        requires_confirmation, category, tags, capabilities.
        """
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
            asyncio.create_task(self.register_tool(contract, handler))
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

        perm_result = await self._permission_manager.check_permission(tool_id, contract.permission_level)
        if not perm_result.granted:
            req_result = await self._permission_manager.request_permission(tool_id, contract.permission_level, action=tool_id)
            req_id = req_result.request.id if req_result.request else ""
            return ToolResult(
                success=False,
                error=f"Permission denied: {tool_id}",
                data={"permission_request_id": req_id, "level": int(contract.permission_level)},
            )

        start = datetime.utcnow()
        try:
            result = await handler(params) if hasattr(handler, "__await__") or hasattr(handler, "__call__") else handler(params)
            duration = (datetime.utcnow() - start).total_seconds()
            if isinstance(result, ToolResult):
                result.duration = duration
                return result
            return ToolResult(success=True, data=result, duration=duration)
        except Exception as e:
            duration = (datetime.utcnow() - start).total_seconds()
            return ToolResult(success=False, error=str(e), duration=duration)

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
            c for c, _ in self._tools.values()
            if q in c.id.lower() or q in c.name.lower() or q in c.description.lower()
        ]
