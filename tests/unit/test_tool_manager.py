"""Tests for Tool Manager."""

import pytest
from aios.core.tool_manager import ToolManager, ToolContract, ToolResult
from aios.core.permission_manager import PermissionManager, PermissionLevel
from aios.core.capability_registry import CapabilityRegistry


@pytest.fixture
def tm():
    return ToolManager(PermissionManager())


@pytest.fixture
def tm_with_cr():
    return ToolManager(PermissionManager(), CapabilityRegistry())


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

    import asyncio
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

    import asyncio
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

    import asyncio
    await asyncio.sleep(0.05)
    caps = await tm_with_cr._capability_registry.list_capabilities()
    assert len(caps) == 1
    assert caps[0].id == "decorator.cap.test"
