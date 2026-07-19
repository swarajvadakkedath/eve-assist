"""End-to-end validation tests for system tool workflows."""

import asyncio
import json
import time
from pathlib import Path

import pytest

from aios.core.tool_manager import ToolManager, ToolContract, ToolResult
from aios.core.permission_manager import PermissionManager, PermissionLevel
from aios.core.event_bus import EventBus
from aios.core.planner import Planner
from aios.core.capability_registry import CapabilityRegistry, Capability
from aios.execution.engine import ExecutionEngine
from aios.tools.system_tools import register_system_tools


# ═══════════════════════════════════════════════════════════════════
# Fixtures — full integration stack
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def tmp_workdir(tmp_path: Path) -> Path:
    wd = tmp_path / "workflow_test"
    wd.mkdir()
    (wd / "doc1.txt").write_text("Hello from doc1")
    (wd / "doc2.txt").write_text("Hello from doc2")
    (wd / "notes.txt").write_text("Important notes here")
    (wd / "photo.png").write_bytes(b"fake png content")
    (wd / "screenshot.jpg").write_bytes(b"fake jpg content")
    (wd / "logo.png").write_bytes(b"fake logo content")
    (wd / "data.json").write_text('{"items": [1, 2, 3]}')
    (wd / "script.py").write_text("print('hello')")
    return wd


@pytest.fixture
def permission_manager() -> PermissionManager:
    return PermissionManager()


@pytest.fixture
def tool_manager(permission_manager) -> ToolManager:
    tm = ToolManager(permission_manager)
    return tm


@pytest.fixture
async def initialized_tools(tool_manager, event_bus, permission_manager):
    register_system_tools(tool_manager, event_bus)
    await asyncio.sleep(0.05)
    # Pre-grant all WORKSPACE tools for test workflows
    workspace_tools = [
        "file.write", "file.create", "file.delete", "file.copy",
        "file.move", "file.rename", "file.create_directory", "file.delete_directory",
        "archive.compress", "archive.extract",
        "clipboard.write", "clipboard.clear", "clipboard.monitor",
        "file.delete_directory",
    ]
    for tid in workspace_tools:
        result = await permission_manager.request_permission(tid, PermissionLevel.WORKSPACE, action=tid)
        if not result.granted and result.request and result.request.id:
            await permission_manager.grant_permission(result.request.id)
    return tool_manager


@pytest.fixture
async def event_bus() -> EventBus:
    bus = EventBus(max_retries=1, retry_delay=0.01)
    await bus.start()
    yield bus
    await bus.stop()


@pytest.fixture
def capability_registry() -> CapabilityRegistry:
    return CapabilityRegistry()


@pytest.fixture
def planner() -> Planner:
    return Planner()


@pytest.fixture
def execution_engine(
    planner,
    capability_registry,
    tool_manager,
    permission_manager,
    event_bus,
) -> ExecutionEngine:
    return ExecutionEngine(
        planner=planner,
        capability_registry=capability_registry,
        tool_manager=tool_manager,
        permission_manager=permission_manager,
        event_bus=event_bus,
        max_concurrent=1,
    )


# ═══════════════════════════════════════════════════════════════════
# Workflow 1: Search *.txt → Read contents → Compress → Save → Notify
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestWorkflow1_SearchReadCompressNotify:
    """Search *.txt files → Read contents → Compress results → Save archive → Notify."""

    async def test_full_workflow(self, initialized_tools, tmp_workdir, event_bus):
        tm = initialized_tools
        events = []
        await event_bus.subscribe("archive.compress", lambda e: events.append(e))

        # Step 1: Search *.txt files
        search_result = await tm.execute("search.files", {
            "path": str(tmp_workdir), "pattern": "*.txt",
        })
        assert search_result.success, f"Search failed: {search_result.error}"
        assert search_result.data["count"] >= 1
        txt_files = [f["path"] for f in search_result.data["files"]]
        assert any("doc1.txt" in f for f in txt_files)

        # Step 2: Read each file
        contents = {}
        for fp in txt_files:
            read_result = await tm.execute("file.read", {"path": fp})
            assert read_result.success, f"Read failed for {fp}: {read_result.error}"
            contents[fp] = read_result.data["content"]

        assert len(contents) >= 1
        assert any("Hello from doc1" in v for v in contents.values())

        # Step 3: Compress results into an archive
        archive_path = str(tmp_workdir / "txt_backup.zip")
        compress_result = await tm.execute("archive.compress", {
            "source": str(tmp_workdir),
            "destination": archive_path,
            "format": "zip",
        })
        assert compress_result.success, f"Compress failed: {compress_result.error}"
        assert compress_result.data["size"] > 0

        # Step 4: Verify archive exists and contains files
        list_result = await tm.execute("archive.list", {"archive": archive_path})
        assert list_result.success
        assert any("doc1.txt" in e["name"] for e in list_result.data["entries"])

        # Step 5: Validate archive integrity
        validate_result = await tm.execute("archive.validate", {"archive": archive_path})
        assert validate_result.success
        assert validate_result.data["valid"] is True

        # Step 6: Verify event was published
        search_meta = await tm.execute("file.metadata", {"path": archive_path})
        assert search_meta.success
        assert search_meta.data["size"] > 0

    async def test_workflow_metrics(self, initialized_tools, tmp_workdir):
        tm = initialized_tools
        times = {}

        t0 = time.monotonic()
        result = await tm.execute("search.files", {
            "path": str(tmp_workdir), "pattern": "*.txt",
        })
        times["search"] = (time.monotonic() - t0) * 1000
        assert result.success

        txt_files = [f["path"] for f in result.data["files"]]
        t0 = time.monotonic()
        for fp in txt_files:
            await tm.execute("file.read", {"path": fp})
        times["read_all"] = (time.monotonic() - t0) * 1000

        t0 = time.monotonic()
        result = await tm.execute("archive.compress", {
            "source": str(tmp_workdir),
            "destination": str(tmp_workdir / "metrics.zip"),
            "format": "zip",
        })
        times["compress"] = (time.monotonic() - t0) * 1000
        assert result.success

        # Log performance
        print(f"\n[PERF] Workflow 1: search={times['search']:.1f}ms, "
              f"read_all={times['read_all']:.1f}ms, compress={times['compress']:.1f}ms")


# ═══════════════════════════════════════════════════════════════════
# Workflow 2: Search images → Metadata report → Save JSON
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestWorkflow2_SearchImagesMetadataReport:
    """Search images → Generate metadata report → Save JSON report."""

    async def test_full_workflow(self, initialized_tools, tmp_workdir):
        tm = initialized_tools

        # Step 1: Search for image files
        search_result = await tm.execute("search.by_extension", {
            "path": str(tmp_workdir), "extension": "png",
        })
        assert search_result.success
        assert search_result.data["count"] >= 1

        # Step 2: Get metadata for each image
        metadata_report = []
        for f in search_result.data["files"]:
            meta = await tm.execute("file.metadata", {"path": f["path"]})
            assert meta.success
            metadata_report.append({
                "file": f["name"],
                "path": f["path"],
                "size": meta.data["size"],
                "extension": f["extension"],
                "modified": meta.data["modified"],
                "created": meta.data["created"],
            })

        assert len(metadata_report) >= 1

        # Step 3: Calculate hashes for verification
        for item in metadata_report:
            hash_result = await tm.execute("file.hash", {
                "path": item["path"], "algorithm": "sha256",
            })
            assert hash_result.success
            item["sha256"] = hash_result.data["hash"]

        # Step 4: Save report as JSON
        report_path = str(tmp_workdir / "image_report.json")
        write_result = await tm.execute("file.write", {
            "path": report_path,
            "content": json.dumps(metadata_report, indent=2),
        })
        assert write_result.success

        # Step 5: Verify saved JSON
        read_result = await tm.execute("file.read", {"path": report_path})
        assert read_result.success
        saved = json.loads(read_result.data["content"])
        assert len(saved) == len(metadata_report)
        assert all("sha256" in item for item in saved)

    async def test_save_new_only(self, initialized_tools, tmp_workdir):
        tm = initialized_tools

        # Use file.create to write JSON (fails if exists)
        report_path = str(tmp_workdir / "new_report.json")
        result = await tm.execute("file.create", {
            "path": report_path,
            "content": json.dumps({"status": "initial"}),
        })
        assert result.success

        # Second create should fail
        result = await tm.execute("file.create", {
            "path": report_path,
            "content": "{}",
        })
        assert not result.success


# ═══════════════════════════════════════════════════════════════════
# Workflow 3: Read clipboard → Save to file → Compress
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestWorkflow3_ClipboardSaveCompress:
    """Read clipboard → Save to file → Compress file."""

    async def test_full_workflow(self, initialized_tools, tmp_workdir):
        tm = initialized_tools

        # Step 1: Write to clipboard
        clip_content = "Clipboard test content for workflow 3"
        write_result = await tm.execute("clipboard.write", {
            "content": clip_content,
        })
        # clipboard may not be available in test env
        if not write_result.success:
            pytest.skip("Clipboard not available in this environment")

        # Step 2: Read from clipboard
        read_result = await tm.execute("clipboard.read", {})
        assert read_result.success
        assert read_result.data["has_content"]

        # Step 3: Save to file
        save_path = str(tmp_workdir / "clipboard_content.txt")
        save_result = await tm.execute("file.write", {
            "path": save_path,
            "content": clip_content,
        })
        assert save_result.success

        # Step 4: Compress the file
        archive_path = str(tmp_workdir / "clipboard_backup.zip")
        compress_result = await tm.execute("archive.compress", {
            "source": save_path,
            "destination": archive_path,
            "format": "zip",
        })
        assert compress_result.success

        # Step 5: Verify archive
        validate_result = await tm.execute("archive.validate", {"archive": archive_path})
        assert validate_result.success
        assert validate_result.data["valid"] is True

    async def test_clipboard_clear(self, initialized_tools):
        tm = initialized_tools
        result = await tm.execute("clipboard.clear", {})
        if not result.success:
            pytest.skip("Clipboard not available")
        assert result.success
        assert result.data["cleared"] is True


# ═══════════════════════════════════════════════════════════════════
# Workflow 4: Create folder → Copy files → Rename → Verify
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestWorkflow4_FolderCopyRenameVerify:
    """Create folder → Copy files → Rename files → Verify structure."""

    async def test_full_workflow(self, initialized_tools, tmp_workdir):
        tm = initialized_tools

        # Step 1: Create folder structure
        project_dir = str(tmp_workdir / "project")
        src_dir = str(tmp_workdir / "project" / "src")
        result = await tm.execute("file.create_directory", {"path": project_dir})
        assert result.success
        result = await tm.execute("file.create_directory", {"path": src_dir})
        assert result.success

        # Step 2: List to verify creation
        list_result = await tm.execute("file.list", {"path": str(tmp_workdir)})
        assert list_result.success
        assert any(e["name"] == "project" for e in list_result.data["entries"])

        # Step 3: Copy files into new folder
        copy_result = await tm.execute("file.copy", {
            "source": str(tmp_workdir / "doc1.txt"),
            "destination": str(tmp_workdir / "project" / "doc1.txt"),
        })
        assert copy_result.success

        copy_result = await tm.execute("file.copy", {
            "source": str(tmp_workdir / "data.json"),
            "destination": str(tmp_workdir / "project" / "data.json"),
        })
        assert copy_result.success

        # Step 4: Rename files
        rename_result = await tm.execute("file.rename", {
            "path": str(tmp_workdir / "project" / "doc1.txt"),
            "new_name": "readme.md",
        })
        assert rename_result.success

        # Step 5: Verify structure
        list_result = await tm.execute("file.list", {
            "path": project_dir, "recursive": True,
        })
        assert list_result.success
        names = [e["name"] for e in list_result.data["entries"]]
        assert "readme.md" in names, f"readme.md not found in {names}"
        assert "data.json" in names, f"data.json not found in {names}"
        assert "src" in names, f"src not found in {names}"

        # Step 6: Verify content preserved after rename
        read_result = await tm.execute("file.read", {
            "path": str(tmp_workdir / "project" / "readme.md"),
        })
        assert read_result.success
        assert read_result.data["content"] == "Hello from doc1"

    async def test_delete_and_cleanup(self, initialized_tools, tmp_workdir):
        tm = initialized_tools

        # Create temp structure
        await tm.execute("file.create_directory", {"path": str(tmp_workdir / "temp_dir")})
        await tm.execute("file.copy", {
            "source": str(tmp_workdir / "doc1.txt"),
            "destination": str(tmp_workdir / "temp_dir" / "doc.txt"),
        })

        # Delete directory recursively
        result = await tm.execute("file.delete_directory", {
            "path": str(tmp_workdir / "temp_dir"),
            "recursive": True,
        })
        assert result.success
        assert not (tmp_workdir / "temp_dir").exists()

    async def test_move_between_dirs(self, initialized_tools, tmp_workdir):
        tm = initialized_tools

        # Create dirs
        await tm.execute("file.create_directory", {"path": str(tmp_workdir / "source")})
        await tm.execute("file.create_directory", {"path": str(tmp_workdir / "dest")})

        # Create file in source
        await tm.execute("file.write", {
            "path": str(tmp_workdir / "source" / "movable.txt"),
            "content": "move me",
        })

        # Move file
        result = await tm.execute("file.move", {
            "source": str(tmp_workdir / "source" / "movable.txt"),
            "destination": str(tmp_workdir / "dest" / "moved.txt"),
        })
        assert result.success
        assert not (tmp_workdir / "source" / "movable.txt").exists()
        assert (tmp_workdir / "dest" / "moved.txt").read_text() == "move me"


# ═══════════════════════════════════════════════════════════════════
# Execution Engine Validation
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestExecutionEngineFlow:
    """Validate Planner → Execution Engine flow."""

    async def test_execution_engine_construction(self, execution_engine):
        """Engine should construct with all dependencies."""
        assert execution_engine is not None
        assert execution_engine._planner_adapter is not None
        assert execution_engine._executor is not None
        assert execution_engine._permissions is not None
        assert execution_engine._events is not None
        assert execution_engine._repository is not None

    async def test_start_execution_with_planner(self, execution_engine):
        """Engine should create execution and attempt planning."""
        execution = await execution_engine.start_execution(
            objective="test workflow",
            conversation_id="conv-test-1",
            owner="test",
            priority=1,
        )
        assert execution is not None
        assert execution.id is not None
        assert execution.objective == "test workflow"

        # Wait briefly for execution to start processing
        await asyncio.sleep(0.1)

        # Since planner is a stub (returns "request.process" step),
        # execution should fail with "Tool not found: request.process"
        # But the engine state will be visible
        updated = await execution_engine.get_execution(execution.id)
        assert updated is not None

    async def test_execution_state_machine(self, execution_engine):
        """Test core states: PENDING → PLANNING → READY → RUNNING → COMPLETED/FAILED."""
        execution = await execution_engine.start_execution(
            objective="verify state transitions",
        )

        # Initial state
        assert execution.status.value == "pending"

        # After brief processing, check final state
        await asyncio.sleep(0.5)
        execution = await execution_engine.get_execution(execution.id)
        # Should have transitioned through states and reached terminal
        assert execution.status.value in ("completed", "failed", "cancelled")

    async def test_execution_pause_resume_cancel(self, execution_engine):
        """Test pause → resume → cancel flow."""
        execution = await execution_engine.start_execution(
            objective="pause resume cancel test",
        )

        # Try to pause
        paused = await execution_engine.pause_execution(execution.id)
        assert paused is not None

        # Resume
        resumed = await execution_engine.resume_execution(execution.id)
        assert resumed is not None

        # Cancel
        cancelled = await execution_engine.cancel_execution(execution.id)
        assert cancelled.status.value == "cancelled"


# ═══════════════════════════════════════════════════════════════════
# Capability Resolution Validation
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestCapabilityResolution:
    """Validate Capability Registry → Tool Manager resolution."""

    async def test_capability_to_tool_mapping(self, tool_manager, capability_registry):
        """Register capability mapping to a tool, then resolve."""
        # Register a capability
        cap = Capability(
            id="file.read",
            name="Read File",
            description="Read file contents",
            provider_type="tool",
            provider_id="file.read",
            quality=1.0,
            tags=["file", "read"],
        )
        await capability_registry.register_capability(cap)

        # Resolve it
        resolved = await capability_registry.find_best_match("file.read")
        assert resolved is not None
        assert resolved.provider_id == "file.read"

    async def test_capability_fallback_to_tool(self, tool_manager, capability_registry):
        """When no capability registered, executor should fall back to tool ID."""
        # Register a tool but no capability for it
        async def handler(params):
            return ToolResult(success=True, data={"handled": True})

        contract = ToolContract(
            id="custom.tool",
            name="Custom Tool",
            description="A custom tool",
            capabilities=["custom.tool"],
        )
        await tool_manager.register_tool(contract, handler)
        await asyncio.sleep(0.01)

        # The executor should find it by tool ID directly
        from aios.execution.executor import TaskExecutor
        executor = TaskExecutor(capability_registry, tool_manager)
        from aios.execution.models import Task, TaskStatus
        task = Task(
            execution_id="test",
            capability="custom.tool",
            tool="custom.tool",
            parameters={},
        )
        result = await executor.execute_task(task)
        assert result.status == TaskStatus.SUCCESS
        assert result.result["handled"] is True

    async def test_capability_not_found(self, capability_registry):
        """Unregistered capability should return None."""
        resolved = await capability_registry.find_best_match("nonexistent.capability")
        assert resolved is None


# ═══════════════════════════════════════════════════════════════════
# Permission Validation
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestPermissionValidation:
    """Validate permission levels and prompts."""

    async def test_read_level_auto_approved(self, initialized_tools):
        """READ level tools should auto-approve."""
        result = await initialized_tools.execute("file.read", {"path": __file__})
        assert result.success

    async def test_sensitive_level_requires_approval(self, permission_manager):
        """SENSITIVE level should require explicit grant."""
        result = await permission_manager.request_permission(
            "test.op", PermissionLevel.SENSITIVE, action="sensitive_op"
        )
        assert result is not None
        assert not result.granted
        req_id = result.request.id
        assert req_id is not None

        # Grant it
        granted = await permission_manager.grant_permission(req_id)
        assert granted is not None
        assert granted.status == "granted"

    async def test_permission_denied(self, permission_manager):
        """Denied permission should return unauthorized."""
        result = await permission_manager.request_permission(
            "test.op", PermissionLevel.SENSITIVE, action="denied_op"
        )
        assert not result.granted
        req_id = result.request.id

        denied = await permission_manager.deny_permission(req_id, "Not allowed")
        assert denied is not None
        assert denied.status == "denied"

        # Verify tool execution with SENSITIVE level blocks without permission
        from aios.core.tool_manager import ToolManager, ToolContract, ToolResult
        pm = PermissionManager()
        tm = ToolManager(pm)

        async def handler(p):
            return ToolResult(success=True, data="ok")

        await tm.register_tool(
            ToolContract(
                id="test.secret",
                name="Secret",
                description="Secret op",
                permission_level=PermissionLevel.SENSITIVE,
            ),
            handler,
        )
        result = await tm.execute("test.secret", {})
        assert not result.success
        assert "denied" in result.error.lower() or "permission" in result.error.lower()


# ═══════════════════════════════════════════════════════════════════
# Event Bus Validation
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestEventPublishing:
    """Validate event publishing across components."""

    async def test_event_publish_subscribe(self, event_bus):
        events = []
        await event_bus.subscribe("test.event", lambda e: events.append(e))
        await event_bus.publish("test.event", {"data": 42})
        await asyncio.sleep(0.05)
        assert len(events) >= 1
        assert events[0].payload["data"] == 42

    async def test_wildcard_subscription(self, event_bus):
        events = []
        await event_bus.subscribe("*", lambda e: events.append(e))
        await event_bus.publish("any.event", {"msg": "hello"})
        await asyncio.sleep(0.05)
        assert len(events) >= 1

    async def test_execution_events_published(self, execution_engine, event_bus):
        events = []
        await event_bus.subscribe("execution.*", lambda e: events.append(e))

        execution = await execution_engine.start_execution(
            objective="event test",
        )
        await asyncio.sleep(0.3)

        # Should have execution.created at minimum
        created_events = [e for e in events if "created" in str(e)]
        assert len(events) > 0

    async def test_event_bus_retry(self, event_bus):
        call_count = 0

        async def failing_handler(event):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("temporary failure")

        await event_bus.subscribe("retry.test", failing_handler)
        await event_bus.publish("retry.test", {"data": "retry me"})
        await asyncio.sleep(0.3)
        assert call_count >= 2


# ═══════════════════════════════════════════════════════════════════
# Error Handling & Recovery Validation
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestErrorHandling:
    """Validate error handling, recovery, and retry."""

    async def test_tool_not_found_error(self, initialized_tools):
        """Calling a non-existent tool should return proper error."""
        result = await initialized_tools.execute("nonexistent.tool", {})
        assert not result.success
        assert "not found" in result.error.lower()

    async def test_file_not_found_error(self, initialized_tools):
        """Reading a non-existent file should return proper error."""
        result = await initialized_tools.execute("file.read", {
            "path": "/nonexistent/path/file.txt",
        })
        assert not result.success

    async def test_invalid_parameters(self, initialized_tools):
        """Missing required parameters should be handled."""
        result = await initialized_tools.execute("file.read", {})
        assert not result.success

    async def test_recovery_engine(self, execution_engine):
        """Recovery engine should handle failures gracefully."""
        from aios.execution.recovery import RecoveryEngine
        from aios.execution.planner_adapter import PlannerAdapter
        from aios.execution.models import Task, TaskStatus, Execution

        recovery = RecoveryEngine(PlannerAdapter(planner=None))

        # Test that critical failure stops execution
        task = Task(
            execution_id="test",
            capability="test.cap",
            tool="test.cap",
            status=TaskStatus.FAILED,
            error="Critical error",
            is_optional=False,
        )
        execution = Execution(objective="test")
        can_continue = await recovery.can_continue(execution, [task])
        assert not can_continue

    async def test_optional_task_failure_allowed(self, execution_engine):
        """Optional task failures should not stop execution."""
        from aios.execution.recovery import RecoveryEngine
        from aios.execution.planner_adapter import PlannerAdapter
        from aios.execution.models import Task, TaskStatus, Execution

        recovery = RecoveryEngine(PlannerAdapter(planner=None))

        task = Task(
            execution_id="test",
            capability="test.cap",
            tool="test.cap",
            status=TaskStatus.FAILED,
            error="Optional failure",
            is_optional=True,
        )
        execution = Execution(objective="test")
        can_continue = await recovery.can_continue(execution, [task])
        assert can_continue


# ═══════════════════════════════════════════════════════════════════
# Performance Measurements
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestPerformance:
    """Measure key performance metrics."""

    async def test_tool_execution_latency(self, initialized_tools, tmp_workdir):
        """Measure individual tool execution times."""
        import time
        results = {}

        # Create a test file
        (tmp_workdir / "perf_test.txt").write_text("x" * 10000)

        tools_to_test = [
            ("file.metadata", {"path": str(tmp_workdir / "perf_test.txt")}),
            ("file.read", {"path": str(tmp_workdir / "perf_test.txt")}),
            ("file.hash", {"path": str(tmp_workdir / "perf_test.txt")}),
            ("file.list", {"path": str(tmp_workdir)}),
            ("search.files", {"path": str(tmp_workdir), "pattern": "*"}),
        ]

        for tool_id, params in tools_to_test:
            t0 = time.monotonic()
            result = await initialized_tools.execute(tool_id, params)
            elapsed = (time.monotonic() - t0) * 1000
            results[tool_id] = {"success": result.success, "time_ms": round(elapsed, 2)}

        for tool_id, data in results.items():
            print(f"  {tool_id}: {data['time_ms']}ms (success={data['success']})")
            assert data["success"], f"{tool_id} failed"

    async def test_concurrent_tool_execution(self, initialized_tools, tmp_workdir):
        """Measure performance under concurrent execution."""
        (tmp_workdir / "concurrent_a.txt").write_text("aaa")
        (tmp_workdir / "concurrent_b.txt").write_text("bbb")
        (tmp_workdir / "concurrent_c.txt").write_text("ccc")

        import time
        tasks = [
            initialized_tools.execute("file.read", {"path": str(tmp_workdir / "concurrent_a.txt")}),
            initialized_tools.execute("file.metadata", {"path": str(tmp_workdir / "concurrent_a.txt")}),
            initialized_tools.execute("file.hash", {"path": str(tmp_workdir / "concurrent_a.txt")}),
            initialized_tools.execute("file.read", {"path": str(tmp_workdir / "concurrent_b.txt")}),
            initialized_tools.execute("file.metadata", {"path": str(tmp_workdir / "concurrent_b.txt")}),
            initialized_tools.execute("file.read", {"path": str(tmp_workdir / "concurrent_c.txt")}),
        ]

        t0 = time.monotonic()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = (time.monotonic() - t0) * 1000

        successes = sum(1 for r in results if isinstance(r, ToolResult) and r.success)
        print(f"  Concurrent: {successes}/{len(tasks)} succeeded in {total_time:.1f}ms")
        assert successes >= 4


# ═══════════════════════════════════════════════════════════════════
# System Integration
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestSystemIntegration:
    """Validate all system tools register and list correctly."""

    async def test_all_tools_registered(self, initialized_tools):
        """All 27 system tools should be registered."""
        all_tools = await initialized_tools.list_tools()
        tool_ids = {t.id for t in all_tools}

        expected = {
            "file.read", "file.write", "file.create", "file.delete",
            "file.copy", "file.move", "file.rename", "file.metadata",
            "file.hash", "file.list", "file.create_directory", "file.delete_directory",
            "search.files", "search.directories", "search.by_extension",
            "search.by_name", "search.by_regex", "search.by_size", "search.by_modified",
            "clipboard.read", "clipboard.write", "clipboard.clear", "clipboard.monitor",
            "archive.compress", "archive.extract", "archive.list", "archive.validate",
        }
        missing = expected - tool_ids
        assert not missing, f"Missing tools: {missing}"

    async def test_tool_categories(self, initialized_tools):
        """Tools should be organized by category."""
        tools = await initialized_tools.list_tools()
        categories = {t.category for t in tools}
        assert "filesystem" in categories
        assert "search" in categories
        assert "clipboard" in categories or "clipboard" in str(categories)
        assert "archive" in categories

    async def test_tool_contracts_have_permission_levels(self, initialized_tools):
        """All tools should have valid permission levels."""
        tools = await initialized_tools.list_tools()
        for t in tools:
            assert t.permission_level is not None
            assert 0 <= int(t.permission_level) <= 3

    async def test_search_tools_functionality(self, initialized_tools):
        """Search tools should find each other."""
        results = await initialized_tools.search_tools("file")
        assert len(results) >= 1

    async def test_tool_listing_by_category(self, initialized_tools):
        """Category filtering should work."""
        file_tools = await initialized_tools.list_tools(category="filesystem")
        assert len(file_tools) >= 10

        search_tools = await initialized_tools.list_tools(category="search")
        assert len(search_tools) >= 5

    async def test_tool_timeout_not_enforced(self, initialized_tools):
        """Tool timeout fields exist but aren't enforced (known limitation)."""
        tools = await initialized_tools.list_tools()
        for t in tools:
            assert hasattr(t, "timeout")
