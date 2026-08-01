"""EVE v1.2.1 Phase 10: Multi-Tool Workflow Test"""
import asyncio
import sys
import os
import json
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, r'E:\Eve_Ai\desktop\src-tauri\backend')

async def test_multi_tool_workflow():
    print("=" * 70)
    print("PHASE 10: MULTI-TOOL WORKFLOW TEST")
    print("=" * 70)
    
    from aios.core.planner import Planner
    from aios.core.capability_registry import CapabilityRegistry
    from aios.core.tool_manager import ToolManager
    from aios.core.permission_manager import PermissionManager, PermissionLevel
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

    # Create isolated project
    project_dir = Path(tempfile.mkdtemp(prefix="eve_project_"))
    
    # Create sample project files
    (project_dir / "main.py").write_text("def hello():\n    print('Hello')\n\n# TODO: Add more functions\n")
    (project_dir / "utils.py").write_text("def helper():\n    pass\n\n# TODO: Implement helper\n")
    (project_dir / "README.md").write_text("# Sample Project\n\nThis is a test project.\n")
    
    # Grant permissions
    for tool in ["file.write", "file.read", "file.list", "file.search"]:
        req = await pm.request_permission(tool, PermissionLevel.WORKSPACE, action=tool)
        await pm.grant_permission(req.request.id, session_id="test")
    
    try:
        # Step 1: List project files
        print("\n[Step 1] List project files...")
        result = await tm.execute("file.list", {"path": str(project_dir)})
        assert result.success, f"file.list failed: {result.error}"
        files = [e["name"] for e in result.data.get("entries", [])]
        print(f"  Files: {files}")
        assert "main.py" in files
        assert "utils.py" in files
        
        # Step 2: Search for TODO comments
        print("\n[Step 2] Search for TODOs...")
        result = await tm.execute("file.search", {"path": str(project_dir), "pattern": "*.py"})
        assert result.success, f"file.search failed: {result.error}"
        py_files = result.data.get("files", [])
        print(f"  Python files: {py_files}")
        
        # Step 3: Read files and find TODOs
        print("\n[Step 3] Read files and find TODOs...")
        todos = []
        for f in py_files:
            result = await tm.execute("file.read", {"path": f})
            if result.success:
                content = result.data.get("content", "")
                for i, line in enumerate(content.split("\n"), 1):
                    if "TODO" in line:
                        todos.append({"file": f, "line": i, "text": line.strip()})
                        print(f"  TODO: {f}:{i} - {line.strip()}")
        
        assert len(todos) == 2, f"Expected 2 TODOs, found {len(todos)}"
        
        # Step 4: Create summary file
        print("\n[Step 4] Create summary file...")
        summary_path = project_dir / "TODO_SUMMARY.md"
        summary_content = "# TODO Summary\n\n"
        for todo in todos:
            summary_content += f"- {todo['file']}:{todo['line']}: {todo['text']}\n"
        
        result = await tm.execute("file.write", {"path": str(summary_path), "content": summary_content})
        assert result.success, f"file.write failed: {result.error}"
        
        # Step 5: Verify summary
        print("\n[Step 5] Verify summary file...")
        result = await tm.execute("file.read", {"path": str(summary_path)})
        assert result.success, f"file.read failed: {result.error}"
        content = result.data.get("content", "")
        assert "TODO" in content
        assert "main.py" in content
        assert "utils.py" in content
        print(f"  Summary content:\n{content}")
        
        print("\n" + "=" * 70)
        print("MULTI-TOOL WORKFLOW: PASS")
        print("=" * 70)
        print(f"Tools invoked: file.list -> file.search -> file.read -> file.write -> file.read")
        print(f"Files inspected: {len(py_files)}")
        print(f"TODOs found: {len(todos)}")
        print(f"Summary created: {summary_path}")
        
    finally:
        shutil.rmtree(project_dir, ignore_errors=True)
    
    await eb.stop()

asyncio.run(test_multi_tool_workflow())
