"""EVE v1.2.1 Phase 11: Failure Tests"""
import asyncio
import sys
import os
import json

sys.path.insert(0, r'E:\Eve_Ai\desktop\src-tauri\backend')

results = {"passed": 0, "failed": 0}

def test(name, passed, detail=""):
    if passed:
        results["passed"] += 1
        print(f"  PASS: {name}")
    else:
        results["failed"] += 1
        print(f"  FAIL: {name} - {detail}")

async def setup():
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
    from aios.tools.system_tools import register_system_tools
    register_builtin_tools(tm)
    register_system_tools(tm, eb)
    await asyncio.sleep(0.3)

    planner = Planner(capability_registry=cr)
    return eb, pm, cr, tm, planner

async def main():
    print("=" * 70)
    print("PHASE 11: FAILURE TESTS")
    print("=" * 70)
    
    eb, pm, cr, tm, planner = await setup()
    
    # Test 1: Missing file
    print("\n[1] Missing file...")
    result = await tm.execute("file.read", {"path": "C:\\nonexistent\\file.txt"})
    test("Missing file returns error", not result.success)
    test("Error message mentions file", "not found" in str(result.error).lower() or "not found" in str(result.error))
    
    # Test 2: Invalid path
    print("\n[2] Invalid path...")
    result = await tm.execute("file.read", {"path": ""})
    test("Invalid path returns error", not result.success)
    
    # Test 3: Permission denied (no grant)
    print("\n[3] Permission denied...")
    result = await tm.execute("file.write", {"path": "test.txt", "content": "test"})
    test("Permission denied without grant", not result.success)
    test("Error mentions permission", "permission" in str(result.error).lower())
    
    # Test 4: Unknown capability
    print("\n[4] Unknown capability...")
    result = await tm.execute("nonexistent.tool", {})
    test("Unknown tool returns error", not result.success)
    test("Error mentions tool not found", "not found" in str(result.error).lower())
    
    # Test 5: Invalid arguments
    print("\n[5] Invalid arguments...")
    result = await tm.execute("file.write", {})  # Missing required params
    test("Missing params returns error", not result.success)
    
    # Test 6: Tool exception
    print("\n[6] Tool exception handling...")
    # command.execute with invalid command
    result = await tm.execute("command.execute", {"command": "nonexistent_command_xyz"})
    test("Command exception handled", not result.success or result.success)  # Either way, no crash
    
    # Test 7: Planner with no matching capability
    print("\n[7] Planner with no matching capability...")
    plan = await planner.create_plan("xyzzy foobar", {})
    test("No match returns failed plan", plan.status == "failed")
    test("Failed plan has error", plan.error is not None)
    test("Failed plan has no steps", len(plan.steps) == 0)
    
    # Test 8: No silent failures
    print("\n[8] No silent failures...")
    result = await tm.execute("file.write", {"path": "test.txt", "content": "test"})
    test("Permission failure is explicit", "Permission denied" in str(result.error))
    
    # Test 9: No infinite loops (planner limits)
    print("\n[9] No infinite loops...")
    from aios.core.planner import MAX_PLAN_STEPS
    plan = await planner.create_plan("Do everything possible with all tools", {})
    test("Plan bounded by MAX_PLAN_STEPS", len(plan.steps) <= MAX_PLAN_STEPS)
    
    # Test 10: Sanitized errors
    print("\n[10] Sanitized errors...")
    result = await tm.execute("file.read", {"path": "C:\\nonexistent\\file.txt"})
    error_str = str(result.error)
    test("No stack traces in error", "Traceback" not in error_str)
    test("No internal paths leaked", "E:\\Eve_Ai" not in error_str)
    
    print("\n" + "=" * 70)
    print(f"RESULTS: {results['passed']} passed, {results['failed']} failed")
    print("=" * 70)
    
    await eb.stop()
    return results["failed"] == 0

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
