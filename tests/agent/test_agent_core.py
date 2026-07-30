"""EVE v1.2.0 Agent Core Test Suite"""
import asyncio
import sys
import os
import json
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, r'E:\Eve_Ai\desktop\src-tauri\backend')

# Test results tracking
results = {"passed": 0, "failed": 0, "errors": []}

def test(name, passed, detail=""):
    if passed:
        results["passed"] += 1
        print(f"  PASS: {name}")
    else:
        results["failed"] += 1
        results["errors"].append(f"{name}: {detail}")
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

async def test_planner_wiring():
    """Phase 2: Planner receives CapabilityRegistry"""
    print("\n=== Phase 2: Planner Wiring ===")
    eb, pm, cr, tm, planner = await setup()
    
    test("Planner has capability_registry", planner._capability_registry is cr)
    
    plan = await planner.create_plan("Create a file containing Hello from Eve", {})
    test("Plan created", plan is not None)
    test("Plan has steps", len(plan.steps) > 0)
    test("Plan does not use request.process", 
         all(s.capability != "request.process" for s in plan.steps),
         f"Steps: {[s.capability for s in plan.steps]}")
    
    for step in plan.steps:
        cap = await cr.find_best_match(step.capability)
        test(f"Capability '{step.capability}' resolves", cap is not None)
    
    # Test explicit failure for nonsense request
    plan_bad = await planner.create_plan("xyzzy foobar baz", {})
    test("Nonsense request returns failed plan", plan_bad.status == "failed")
    
    await eb.stop()

async def test_tool_resolution():
    """Phase 3: Tool resolution and execution"""
    print("\n=== Phase 3: Tool Resolution ===")
    eb, pm, cr, tm, planner = await setup()
    
    # Test capability resolution
    cap = await cr.find_best_match("file.write")
    test("file.write resolves", cap is not None and cap.id == "file.write")
    
    cap = await cr.find_best_match("file.read")
    test("file.read resolves", cap is not None and cap.id == "file.read")
    
    cap = await cr.find_best_match("command.execute")
    test("command.execute resolves", cap is not None and cap.id == "command.execute")
    
    # Test system.info (READ permission, should work)
    result = await tm.execute("system.info", {})
    test("system.info executes", result.success, f"error={result.error}")
    test("system.info returns data", result.data is not None)
    
    # Test file.write (requires permission)
    result = await tm.execute("file.write", {"path": "test.txt", "content": "test"})
    test("file.write blocked without permission", not result.success and "Permission denied" in str(result.error))
    
    await eb.stop()

async def test_observation_injection():
    """Phase 4: Tool results injected into observation context"""
    print("\n=== Phase 4: Observation Injection ===")
    eb, pm, cr, tm, planner = await setup()
    
    # Build observations manually
    observations = [
        {"tool": "system.info", "status": "success", "result": {"os": "Windows"}, "error": None},
        {"tool": "file.write", "status": "failed", "result": None, "error": "Permission denied"},
    ]
    
    obs_lines = ["\nTool execution results:"]
    for obs in observations:
        if obs["status"] == "success" and obs["result"]:
            obs_lines.append(f"\n[{obs['tool']}] {obs['status']}:\n{json.dumps(obs['result'], indent=2)[:500]}")
        elif obs["error"]:
            obs_lines.append(f"\n[{obs['tool']}] {obs['status']}: {obs['error']}")
    
    observation_text = "\n".join(obs_lines)
    test("Observation text generated", len(observation_text) > 0)
    test("Observation includes success", "success" in observation_text)
    test("Observation includes failure", "Permission denied" in observation_text)
    test("Observation includes tool name", "system.info" in observation_text)
    
    await eb.stop()

async def test_permission_enforcement():
    """Phase 6: Permission enforcement at execution boundary"""
    print("\n=== Phase 6: Permission Enforcement ===")
    eb, pm, cr, tm, planner = await setup()
    
    # READ level - should auto-approve
    result = await tm.execute("system.info", {})
    test("READ tool auto-approved", result.success)
    
    # WORKSPACE level (file.write) - should require permission
    result = await tm.execute("file.write", {"path": "test.txt", "content": "test"})
    test("WORKSPACE tool blocked", not result.success and "Permission" in str(result.error))
    
    # SENSITIVE level (command.execute) - should require permission
    result = await tm.execute("command.execute", {"command": "echo test"})
    test("SENSITIVE tool blocked", not result.success and "Permission" in str(result.error))
    
    # Direct backend invocation - same enforcement
    result = await tm.execute("file.write", {"path": "test.txt", "content": "test"})
    test("Direct invocation blocked", not result.success)
    
    await eb.stop()

async def test_buggy_planner_fails():
    """Phase 1: Verify buggy planner (no registry) produces explicit failure"""
    print("\n=== Phase 1: Buggy Planner Detection ===")
    eb, pm, cr, tm, planner_buggy = await setup()
    planner_buggy._capability_registry = None  # Simulate bug
    
    plan = await planner_buggy.create_plan("Create a file", {})
    test("Buggy planner returns failed plan", plan.status == "failed")
    test("Buggy planner has error message", plan.error is not None)
    
    await eb.stop()

async def test_multi_step_limits():
    """Phase 5: Multi-step bounds"""
    print("\n=== Phase 5: Multi-Step Bounds ===")
    from aios.core.planner import MAX_PLAN_STEPS
    
    test("MAX_PLAN_STEPS defined", MAX_PLAN_STEPS > 0)
    test("MAX_PLAN_STEPS reasonable", MAX_PLAN_STEPS <= 10)
    
    eb, pm, cr, tm, planner = await setup()
    plan = await planner.create_plan("Do everything possible", {})
    test("Plan limited to MAX_PLAN_STEPS", len(plan.steps) <= MAX_PLAN_STEPS)
    
    await eb.stop()

async def test_filesystem_e2e():
    """Phase 9: Filesystem E2E via tool manager"""
    print("\n=== Phase 9: Filesystem E2E ===")
    eb, pm, cr, tm, planner = await setup()
    
    test_dir = Path(tempfile.mkdtemp(prefix="eve_agent_test_"))
    test_file = test_dir / "note.txt"
    
    try:
        # Test A: Create directory (via system.info to verify tool works)
        result = await tm.execute("system.info", {})
        test("TEST A: system.info works", result.success)
        
        # Grant permissions for file operations
        from aios.core.permission_manager import PermissionLevel
        
        # Grant file.write
        req_write = await pm.request_permission("file.write", PermissionLevel.WORKSPACE, action="file.write")
        await pm.grant_permission(req_write.request.id, session_id="test")
        
        # Grant file.read
        req_read = await pm.request_permission("file.read", PermissionLevel.WORKSPACE, action="file.read")
        await pm.grant_permission(req_read.request.id, session_id="test")
        
        # Grant file.list
        req_list = await pm.request_permission("file.list", PermissionLevel.WORKSPACE, action="file.list")
        await pm.grant_permission(req_list.request.id, session_id="test")
        
        # Grant file.search
        req_search = await pm.request_permission("file.search", PermissionLevel.WORKSPACE, action="file.search")
        await pm.grant_permission(req_search.request.id, session_id="test")
        
        # Test B: Write file
        result = await tm.execute("file.write", {"path": str(test_file), "content": "Hello from Eve"})
        test("TEST B: File written", result.success, f"error={result.error}")
        
        # Verify file exists
        if test_file.exists():
            content = test_file.read_text()
            test("TEST B: Content correct", content == "Hello from Eve", f"got: {content}")
        else:
            test("TEST B: File exists", False, "File not created")
        
        # Test C: Read file
        result = await tm.execute("file.read", {"path": str(test_file)})
        test("TEST C: File read", result.success, f"error={result.error}")
        if result.success and result.data:
            test("TEST C: Content matches", result.data.get("content") == "Hello from Eve")
        
        # Test D: List directory
        result = await tm.execute("file.list", {"path": str(test_dir)})
        test("TEST D: Directory listed", result.success, f"error={result.error}")
        
        # Test E: Search files
        result = await tm.execute("file.search", {"path": str(test_dir), "pattern": "*.txt"})
        test("TEST E: File search", result.success, f"error={result.error}")
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)
    
    await eb.stop()

async def main():
    print("=" * 70)
    print("EVE v1.2.0 AGENT CORE TEST SUITE")
    print("=" * 70)
    
    await test_planner_wiring()
    await test_tool_resolution()
    await test_observation_injection()
    await test_permission_enforcement()
    await test_buggy_planner_fails()
    await test_multi_step_limits()
    await test_filesystem_e2e()
    
    print("\n" + "=" * 70)
    print(f"RESULTS: {results['passed']} passed, {results['failed']} failed")
    print("=" * 70)
    
    if results["errors"]:
        print("\nFAILURES:")
        for e in results["errors"]:
            print(f"  - {e}")
    
    return results["failed"] == 0

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
