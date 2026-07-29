"""Tests for Tool Manager."""

import asyncio
import pytest
from aios.core.tool_manager import (
    ToolManager,
    ToolContract,
    ToolResult,
    ToolManagerError,
    ValidationError,
    ToolTimeoutError,
    ToolExecutionError,
)
from aios.core.permission_manager import PermissionManager, PermissionLevel
from aios.core.capability_registry import CapabilityRegistry
from aios.core.event_bus import EventBus
from aios.core.di_container import DIContainer


@pytest.fixture
def tm():
    return ToolManager(PermissionManager())


@pytest.fixture
def tm_with_cr():
    return ToolManager(PermissionManager(), CapabilityRegistry())


@pytest.fixture
async def event_bus():
    bus = EventBus()
    await bus.start()
    yield bus
    await bus.stop()


@pytest.mark.asyncio
async def test_register_tool(tm):
    contract = ToolContract(id="test_tool", name="Test", description="A test tool")
    await tm.register_tool(contract, lambda p: ToolResult(success=True, data="ok"))
    found = await tm.get_tool("test_tool")
    assert found is not None
    assert found.id == "test_tool"


@pytest.mark.asyncio
async def test_execute_tool(tm):
    async def handler(params):
        return ToolResult(success=True, data={"result": 42})

    contract = ToolContract(id="calc", name="Calc", description="Calculator", permission_level=PermissionLevel.READ)
    await tm.register_tool(contract, handler)
    result = await tm.execute("calc", {"x": 1})
    assert result.success
    assert result.data["result"] == 42


@pytest.mark.asyncio
async def test_tool_not_found(tm):
    result = await tm.execute("nonexistent", {})
    assert not result.success
    assert "not found" in result.error


@pytest.mark.asyncio
async def test_list_tools(tm):
    c1 = ToolContract(id="a", name="A", description="Tool A", category="files")
    c2 = ToolContract(id="b", name="B", description="Tool B", category="system")
    await tm.register_tool(c1, lambda p: ToolResult(success=True))
    await tm.register_tool(c2, lambda p: ToolResult(success=True))
    tools = await tm.list_tools()
    assert len(tools) == 2


@pytest.mark.asyncio
async def test_search_tools(tm):
    c = ToolContract(id="file_search", name="File Search", description="Search files")
    await tm.register_tool(c, lambda p: ToolResult(success=True))
    results = await tm.search_tools("search")
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_tool_decorator(tm):
    @tm.tool(name="decorator_test", description="Decorator test tool")
    async def my_handler(params: dict) -> str:
        return "ok"

    await asyncio.sleep(0.05)
    found = await tm.get_tool("decorator_test")
    assert found is not None
    assert found.id == "decorator_test"
    assert found.description == "Decorator test tool"
    assert found.permission_level == PermissionLevel.READ


@pytest.mark.asyncio
async def test_tool_decorator_no_name(tm):
    @tm.tool(description="Auto-named tool")
    async def auto_named_handler(params: dict) -> str:
        return "ok"

    await asyncio.sleep(0.05)
    found = await tm.get_tool("auto_named_handler")
    assert found is not None


@pytest.mark.asyncio
async def test_register_tool_auto_capability(tm_with_cr):
    contract = ToolContract(id="auto.cap.test", name="Auto Cap Test",
                            description="Should auto-register capability",
                            category="test", tags=["auto"])
    await tm_with_cr.register_tool(contract, lambda p: ToolResult(success=True))
    caps = await tm_with_cr._capability_registry.list_capabilities()
    assert len(caps) == 1
    assert caps[0].id == "auto.cap.test"
    assert caps[0].name == "Auto Cap Test"
    assert caps[0].supports_streaming is False


@pytest.mark.asyncio
async def test_register_tool_no_capability_registry(tm):
    contract = ToolContract(id="no.cr.test", name="No CR", description="No capability registry")
    await tm.register_tool(contract, lambda p: ToolResult(success=True))
    assert tm._capability_registry is None


@pytest.mark.asyncio
async def test_tool_decorator_auto_capability(tm_with_cr):
    @tm_with_cr.tool(name="decorator.cap.test", description="Decorator auto cap",
                      category="test", tags=["decorator"])
    async def handler(params: dict) -> str:
        return "ok"

    await asyncio.sleep(0.05)
    caps = await tm_with_cr._capability_registry.list_capabilities()
    assert len(caps) == 1
    assert caps[0].id == "decorator.cap.test"


@pytest.mark.asyncio
async def test_parameter_validation_valid(tm):
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "count": {"type": "integer"},
        },
        "required": ["name"],
    }
    contract = ToolContract(id="valid_test", name="Valid Test", description="Test validation",
                            parameters=schema, permission_level=PermissionLevel.READ)
    async def handler(params):
        return ToolResult(success=True, data=params)

    await tm.register_tool(contract, handler)
    result = await tm.execute("valid_test", {"name": "hello", "count": 5})
    assert result.success
    assert result.data == {"name": "hello", "count": 5}


@pytest.mark.asyncio
async def test_parameter_validation_invalid_type(tm):
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "count": {"type": "integer"},
        },
    }
    contract = ToolContract(id="type_test", name="Type Test", description="Test type validation",
                            parameters=schema, permission_level=PermissionLevel.READ)
    async def handler(params):
        return ToolResult(success=True)

    await tm.register_tool(contract, handler)
    result = await tm.execute("type_test", {"name": "hello", "count": "not_an_int"})
    assert not result.success
    assert "validation error" in result.error.lower()
    assert "expected type integer" in result.error


@pytest.mark.asyncio
async def test_parameter_validation_missing_required(tm):
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
        },
        "required": ["name"],
    }
    contract = ToolContract(id="required_test", name="Required Test",
                            description="Test required field",
                            parameters=schema, permission_level=PermissionLevel.READ)
    async def handler(params):
        return ToolResult(success=True)

    await tm.register_tool(contract, handler)
    result = await tm.execute("required_test", {})
    assert not result.success
    assert "missing required field" in result.error.lower()


@pytest.mark.asyncio
async def test_parameter_validation_no_schema(tm):
    contract = ToolContract(id="no_schema", name="No Schema",
                            description="No schema defined",
                            parameters={}, permission_level=PermissionLevel.READ)
    async def handler(params):
        return ToolResult(success=True, data=params)

    await tm.register_tool(contract, handler)
    result = await tm.execute("no_schema", {"anything": "goes"})
    assert result.success


@pytest.mark.asyncio
async def test_execute_timeout(tm):
    async def slow_handler(params):
        await asyncio.sleep(10)
        return ToolResult(success=True)

    contract = ToolContract(id="timeout_test", name="Timeout Test",
                            description="Should timeout", timeout=1,
                            permission_level=PermissionLevel.READ)
    await tm.register_tool(contract, slow_handler)
    result = await tm.execute("timeout_test", {})
    assert not result.success
    assert "timed out" in result.error.lower()


@pytest.mark.asyncio
async def test_event_publication_on_started(event_bus):
    tm = ToolManager(PermissionManager(), event_bus=event_bus)
    events = []

    async def collector(event):
        events.append(event.type)

    await event_bus.subscribe("tool:started", collector)

    async def handler(params):
        return ToolResult(success=True, data="ok")

    contract = ToolContract(id="event_start", name="Event Start",
                            description="Test event",
                            permission_level=PermissionLevel.READ)
    await tm.register_tool(contract, handler)
    await tm.execute("event_start", {})
    await asyncio.sleep(0.05)
    assert "tool:started" in events


@pytest.mark.asyncio
async def test_event_publication_on_completed(event_bus):
    tm = ToolManager(PermissionManager(), event_bus=event_bus)
    events = []

    async def collector(event):
        events.append(event.type)

    await event_bus.subscribe("tool:completed", collector)

    async def handler(params):
        return ToolResult(success=True, data="ok")

    contract = ToolContract(id="event_done", name="Event Done",
                            description="Test event",
                            permission_level=PermissionLevel.READ)
    await tm.register_tool(contract, handler)
    result = await tm.execute("event_done", {})
    assert result.success
    await asyncio.sleep(0.05)
    assert "tool:completed" in events


@pytest.mark.asyncio
async def test_event_publication_on_failed(event_bus):
    tm = ToolManager(PermissionManager(), event_bus=event_bus)
    events = []

    async def collector(event):
        events.append(event.type)

    await event_bus.subscribe("tool:failed", collector)

    async def failing_handler(params):
        raise RuntimeError("Something went wrong")

    contract = ToolContract(id="event_fail", name="Event Fail",
                            description="Test failure event",
                            permission_level=PermissionLevel.READ)
    await tm.register_tool(contract, failing_handler)
    result = await tm.execute("event_fail", {})
    assert not result.success
    await asyncio.sleep(0.05)
    assert "tool:failed" in events


@pytest.mark.asyncio
async def test_event_publication_on_timeout(event_bus):
    tm = ToolManager(PermissionManager(), event_bus=event_bus)
    events = []

    async def collector(event):
        events.append(event.type)

    await event_bus.subscribe("tool:timeout", collector)

    async def slow_handler(params):
        await asyncio.sleep(10)
        return ToolResult(success=True)

    contract = ToolContract(id="event_timeout", name="Event Timeout",
                            description="Test timeout event",
                            timeout=1, permission_level=PermissionLevel.READ)
    await tm.register_tool(contract, slow_handler)
    result = await tm.execute("event_timeout", {})
    assert not result.success
    await asyncio.sleep(0.05)
    assert "tool:timeout" in events


@pytest.mark.asyncio
async def test_di_registration():
    container = DIContainer()
    pm = PermissionManager()
    container.register(PermissionManager, factory=lambda: pm)
    ToolManager.register_in_container(container)
    resolved = container.resolve(ToolManager)
    assert isinstance(resolved, ToolManager)
    assert resolved._permission_manager is pm


@pytest.mark.asyncio
async def test_di_registration_with_event_bus():
    container = DIContainer()
    pm = PermissionManager()
    eb = EventBus()
    container.register(PermissionManager, factory=lambda: pm)
    container.register(EventBus, factory=lambda: eb)
    ToolManager.register_in_container(container, event_bus=eb)
    resolved = container.resolve(ToolManager)
    assert resolved._event_bus is eb


@pytest.mark.asyncio
async def test_exception_types():
    assert issubclass(ValidationError, ToolManagerError)
    assert issubclass(ToolTimeoutError, ToolManagerError)
    assert issubclass(ToolExecutionError, ToolManagerError)


@pytest.mark.asyncio
async def test_unregister_tool(tm):
    contract = ToolContract(id="unreg", name="Unreg", description="To be unregistered")
    await tm.register_tool(contract, lambda p: ToolResult(success=True))
    found = await tm.get_tool("unreg")
    assert found is not None
    await tm.unregister_tool("unreg")
    found = await tm.get_tool("unreg")
    assert found is None


@pytest.mark.asyncio
async def test_execute_tool_exception_wraps_error(tm):
    async def broken_handler(params):
        raise ValueError("internal failure")

    contract = ToolContract(id="broken", name="Broken", description="Broken tool",
                            permission_level=PermissionLevel.READ)
    await tm.register_tool(contract, broken_handler)
    result = await tm.execute("broken", {})
    assert not result.success
    assert "Tool execution error" in result.error
    assert "internal failure" in result.error


@pytest.mark.asyncio
async def test_execute_tool_with_contract_result(tm):
    async def handler(params):
        return ToolResult(success=True, data="from_contract")

    contract = ToolContract(id="contract_result", name="Contract Result",
                            description="Returns ToolResult directly",
                            permission_level=PermissionLevel.READ)
    await tm.register_tool(contract, handler)
    result = await tm.execute("contract_result", {})
    assert result.success
    assert result.data == "from_contract"
    assert result.duration > 0


@pytest.mark.asyncio
async def test_validation_error_does_not_execute(tm):
    schema = {
        "type": "object",
        "properties": {
            "x": {"type": "integer"},
        },
        "required": ["x"],
    }
    executed = False

    async def handler(params):
        nonlocal executed
        executed = True
        return ToolResult(success=True)

    contract = ToolContract(id="noexec", name="No Exec", description="Should not execute",
                            parameters=schema, permission_level=PermissionLevel.READ)
    await tm.register_tool(contract, handler)
    result = await tm.execute("noexec", {"x": "bad"})
    assert not result.success
    assert not executed


@pytest.mark.asyncio
async def test_tool_timeout_error_sets_duration(tm):
    async def infinite_handler(params):
        await asyncio.sleep(999)

    contract = ToolContract(id="infinite", name="Infinite", description="Never returns",
                            timeout=1, permission_level=PermissionLevel.READ)
    await tm.register_tool(contract, infinite_handler)
    result = await tm.execute("infinite", {})
    assert not result.success
    assert "timed out" in result.error
    assert result.duration > 0
