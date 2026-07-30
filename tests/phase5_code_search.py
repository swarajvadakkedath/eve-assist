"""Phase 5: Test code search capabilities."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "desktop", "src-tauri", "backend"))

from aios.core.tool_manager import ToolManager
from aios.core.permission_manager import PermissionManager
from aios.core.capability_registry import CapabilityRegistry
from aios.tools.builtin import register_builtin_tools
from aios.tools.system_tools import register_system_tools
from aios.tools.git_tools import register_git_tools
from aios.core.event_bus import EventBus


async def test_code_search():
    print("=== Code Search Test ===")
    
    event_bus = EventBus()
    await event_bus.start()
    
    permissions = PermissionManager()
    permissions.configure(default_level=0)
    registry = CapabilityRegistry()
    tool_manager = ToolManager(permissions, registry, event_bus)
    
    register_builtin_tools(tool_manager)
    register_system_tools(tool_manager, event_bus)
    register_git_tools(tool_manager)
    
    await asyncio.sleep(0.1)
    
    tools = await tool_manager.list_tools()
    print(f"Available tools: {len(tools)}")
    for t in tools:
        print(f"  - {t.name}: {t.description[:60]}...")
    
    print("\n--- Test: List files in sandbox ---")
    result = await tool_manager.execute("file.list", {"path": "E:\\Eve_Ai\\sandbox\\demo-project"})
    print(f"Result: {result}")
    
    print("\n--- Test: Read file ---")
    result = await tool_manager.execute("file.read", {"path": "E:\\Eve_Ai\\sandbox\\demo-project\\app.py"})
    print(f"Result: {result}")
    
    print("\n--- Test: Search files ---")
    result = await tool_manager.execute("file.search", {"path": "E:\\Eve_Ai\\sandbox\\demo-project", "pattern": "*.py"})
    print(f"Result: {result}")
    
    print("\n--- Test: Git status ---")
    result = await tool_manager.execute("git.status", {"path": "E:\\Eve_Ai\\sandbox\\demo-project"})
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(test_code_search())
