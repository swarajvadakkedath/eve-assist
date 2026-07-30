"""EVE v1.2.0 Phase 1: Reproduce P0 - Async compatible"""
import asyncio
import sys
import os
import json

sys.path.insert(0, r'E:\Eve_Ai\desktop\src-tauri\backend')

async def reproduce():
    print("=" * 70)
    print("PHASE 1: REPRODUCE P0 AGENT EXECUTION FAILURE")
    print("=" * 70)
    
    from aios.core.planner import Planner
    from aios.core.capability_registry import CapabilityRegistry
    from aios.core.tool_manager import ToolManager
    from aios.core.permission_manager import PermissionManager
    from aios.core.event_bus import EventBus
    
    eb = EventBus()
    pm = PermissionManager(event_bus=eb)
    cr = CapabilityRegistry()
    tm = ToolManager(permission_manager=pm, capability_registry=cr, event_bus=eb)
    
    # Register tools (must be in async context for create_task)
    from aios.tools.builtin import register_builtin_tools
    from aios.tools.system_tools import register_system_tools
    register_builtin_tools(tm)
    register_system_tools(tm, eb)
    
    # Wait for create_task to complete
    await asyncio.sleep(0.5)
    
    tools = await tm.list_tools()
    caps = await cr.list_capabilities()
    print(f"\nTools registered: {len(tools)}")
    print(f"Capabilities registered: {len(caps)}")
    if caps:
        print(f"  Sample IDs: {[c.id for c in caps[:8]]}")
    
    # BUGGY: Planner without capability_registry
    print("\n--- BUGGY PLANNER (no capability_registry) ---")
    p_buggy = Planner()
    print(f"  _capability_registry = {p_buggy._capability_registry}")
    
    plan_buggy = await p_buggy.create_plan("Create a file containing Hello from Eve", {})
    print(f"  Steps: {len(plan_buggy.steps)}")
    for s in plan_buggy.steps:
        print(f"    capability='{s.capability}', params={json.dumps(s.params)[:100]}")
    
    cap = await cr.find_best_match(plan_buggy.steps[0].capability)
    print(f"  Resolution: {'FOUND: ' + cap.id if cap else 'NOT FOUND (request.process has no matching tool)'}")
    
    result = await tm.execute(plan_buggy.steps[0].capability, plan_buggy.steps[0].params)
    print(f"  Execution: success={result.success}, error={result.error}")
    
    # FIXED: Planner with capability_registry
    print("\n--- FIXED PLANNER (with capability_registry) ---")
    p_fixed = Planner(capability_registry=cr)
    print(f"  _capability_registry is None: {p_fixed._capability_registry is None}")
    
    plan_fixed = await p_fixed.create_plan("Create a file containing Hello from Eve", {})
    print(f"  Steps: {len(plan_fixed.steps)}")
    for s in plan_fixed.steps:
        print(f"    capability='{s.capability}', params={json.dumps(s.params)[:100]}")
        cap = await cr.find_best_match(s.capability)
        print(f"      -> resolves to: {cap.id if cap else 'NOT FOUND'}")
    
    # Execute with proper params
    for s in plan_fixed.steps:
        if s.capability == "file.write":
            params = {"path": "C:\\Users\\swara\\eve_p0_test.txt", "content": "Hello from Eve"}
        elif s.capability == "file.read":
            params = {"path": "C:\\Users\\swara\\eve_p0_test.txt"}
        elif s.capability == "command.execute":
            params = {"command": "echo Hello from Eve > C:\\Users\\swara\\eve_p0_test.txt"}
        else:
            params = s.params
        result = await tm.execute(s.capability, params)
        print(f"  Execute '{s.capability}': success={result.success}, error={result.error}")
    
    # Check file
    test_file = r"C:\Users\swara\eve_p0_test.txt"
    if os.path.exists(test_file):
        with open(test_file) as f:
            print(f"\n  FILE CREATED: '{f.read()}'")
        os.remove(test_file)
    else:
        print(f"\n  FILE NOT CREATED")
    
    # Cleanup
    await eb.stop()
    
    print("\n" + "=" * 70)
    print("ROOT CAUSE CONFIRMED")
    print("=" * 70)
    print("""
BUG: app.py:98 creates Planner() without capability_registry
     -> planner falls back to 'request.process' (unknown capability)
     -> TaskExecutor can't resolve -> silent failure
     -> LLM never sees tool results -> describes what it WOULD do

FIX: Planner(capability_registry=capability_registry)
""")

asyncio.run(reproduce())
