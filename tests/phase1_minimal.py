"""Minimal P0 reproduction test"""
import asyncio
import sys
import os

sys.path.insert(0, r'E:\Eve_Ai\desktop\src-tauri\backend')

async def test():
    from aios.core.planner import Planner
    from aios.core.capability_registry import CapabilityRegistry
    from aios.core.tool_manager import ToolManager
    from aios.core.permission_manager import PermissionManager
    from aios.core.event_bus import EventBus

    eb = EventBus()
    pm = PermissionManager(event_bus=eb)
    cr = CapabilityRegistry()
    tm = ToolManager(permission_manager=pm, capability_registry=cr, event_bus=eb)

    from aios.tools.builtin import register_builtin_tools
    register_builtin_tools(tm)
    await asyncio.sleep(0.3)

    tools = await tm.list_tools()
    caps = await cr.list_capabilities()
    print(f"Tools: {len(tools)}, Caps: {len(caps)}")

    # Fixed planner
    p = Planner(capability_registry=cr)
    plan = await p.create_plan("Create a file containing Hello from Eve", {})
    print(f"Plan: {len(plan.steps)} steps")
    for s in plan.steps:
        print(f"  capability='{s.capability}', params={s.params}")
        cap = await cr.find_best_match(s.capability)
        resolved = cap.id if cap else "NOT FOUND"
        print(f"    -> resolves to: {resolved}")

    # Execute
    for s in plan.steps:
        if s.capability == "file.write":
            params = {"path": "C:\\Users\\swara\\eve_test.txt", "content": "Hello from Eve"}
        else:
            params = s.params
        r = await tm.execute(s.capability, params)
        print(f"  Execute '{s.capability}': success={r.success}, error={r.error}")

    # Check file
    if os.path.exists(r"C:\Users\swara\eve_test.txt"):
        with open(r"C:\Users\swara\eve_test.txt") as f:
            print(f"  FILE: '{f.read()}'")
        os.remove(r"C:\Users\swara\eve_test.txt")
    else:
        print("  FILE NOT CREATED")

    await eb.stop()

asyncio.run(test())
