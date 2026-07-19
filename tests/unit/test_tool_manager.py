"""Tests for Tool Manager."""

import pytest
from aios.core.tool_manager import ToolManager, ToolContract, ToolResult
from aios.core.permission_manager import PermissionManager, PermissionLevel


@pytest.fixture
def tm():
    return ToolManager(PermissionManager())


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
