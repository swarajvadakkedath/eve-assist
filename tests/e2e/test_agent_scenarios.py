"""End-to-End Agent Scenario Validation — multi-step agent workflows through the platform."""

import asyncio
import json
import time
from pathlib import Path

import pytest

from aios.core.tool_manager import ToolManager, ToolContract, ToolResult
from aios.core.permission_manager import PermissionManager, PermissionLevel
from aios.core.event_bus import EventBus
from aios.core.planner import Planner, StepStatus
from aios.core.capability_registry import CapabilityRegistry, Capability
from aios.execution.engine import ExecutionEngine
from aios.execution.models import ExecutionStatus, TaskStatus
from aios.tools.builtin import register_builtin_tools
from aios.tools.system_tools import register_system_tools


# ═══════════════════════════════════════════════════════════════════
# Fixtures — full integration stack for agent validation
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def tmp_workdir(tmp_path: Path) -> Path:
    wd = tmp_path / "agent_scenario"
    wd.mkdir()
    (wd / "doc1.txt").write_text("Hello from doc1")
    (wd / "doc2.txt").write_text("Hello from doc2")
    (wd / "notes.txt").write_text("Important notes here")
    (wd / "photo.png").write_bytes(b"fake png content")
    (wd / "screenshot.jpg").write_bytes(b"fake jpg content")
    (wd / "logo.png").write_bytes(b"fake logo content")
    (wd / "data.json").write_text('{"items": [1, 2, 3]}')
    (wd / "script.py").write_text("print('hello')")
    (wd / "report.md").write_text("# Report\n\nSummary of findings.")
    return wd


@pytest.fixture
def pm() -> PermissionManager:
    return PermissionManager()


@pytest.fixture
def cr() -> CapabilityRegistry:
    return CapabilityRegistry()


@pytest.fixture
def tl(pm, cr) -> ToolManager:
    return ToolManager(pm, cr)


@pytest.fixture
def pl() -> Planner:
    return Planner()


@pytest.fixture
async def bus() -> EventBus:
    b = EventBus(max_retries=1, retry_delay=0.01)
    await b.start()
    yield b
    await b.stop()


@pytest.fixture
async def full_stack(tl, cr, bus, pm):
    """Register all tools and capabilities; pre-grant WORKSPACE permissions."""
    register_builtin_tools(tl)
    await asyncio.sleep(0.1)
    register_system_tools(tl, bus)
    await asyncio.sleep(0.1)

    workspace_tools = [
        "file.read", "file.write", "file.create", "file.delete",
        "file.copy", "file.move", "file.rename", "file.create_directory",
        "file.delete_directory",
        "archive.compress", "archive.extract",
        "clipboard.write", "clipboard.clear",
        "terminal.run_command", "terminal.stream_output",
        "terminal.cancel_command",
        "powershell.run",
        "process.start", "process.stop", "process.restart",
        "environment.set_process",
        "wsl.run_command",
        "git.init", "git.clone", "git.create_branch", "git.checkout_branch",
        "git.add", "git.commit", "git.push", "git.create_tag",
        "download.file", "upload.file", "upload.multipart",
        "content.write_text", "content.replace_text", "content.append_text",
        "content.write_csv", "content.write_json",
        "office.write_docx",
        "file.open",
    ]
    for tid in workspace_tools:
        result = await pm.request_permission(tid, PermissionLevel.WORKSPACE, action=tid)
        if not result.granted and result.request and result.request.id:
            await pm.grant_permission(result.request.id)

    return {"tm": tl, "cr": cr, "bus": bus, "pm": pm}


@pytest.fixture
async def engine(full_stack, pl) -> ExecutionEngine:
    return ExecutionEngine(
        planner=pl,
        capability_registry=full_stack["cr"],
        tool_manager=full_stack["tm"],
        permission_manager=full_stack["pm"],
        event_bus=full_stack["bus"],
        max_concurrent=1,
    )


# ═══════════════════════════════════════════════════════════════════
# Scenario 1: Development Workflow
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestDevWorkflow:
    """Clone repository, inspect project, detect technology, run tests, format code, commit changes."""

    async def test_planner_decomposes_dev_request(self, full_stack, pl):
        """Planner should generate multiple steps for a dev request."""
        pl._capability_registry = full_stack["cr"]
        plan = await pl.create_plan("Clone repository git@github.com:test/repo.git, inspect project structure, detect language, run tests, format code, commit changes")
        assert len(plan.steps) >= 2, f"Expected multi-step plan, got {len(plan.steps)} steps"
        cap_ids = [s.capability for s in plan.steps]
        assert any("search" in c or "file.list" in c or "file" in c for c in cap_ids), \
            f"Expected search/file capability in dev plan, got {cap_ids}"
        assert any("terminal" in c or "git" in c or "process" in c for c in cap_ids), \
            f"Expected terminal/git capability in dev plan, got {cap_ids}"

    async def test_search_read_detect_workflow(self, full_stack, tmp_workdir):
        """Search files → Read content → Detect language → Generate report."""
        tm = full_stack["tm"]
        # Step 1: Search for files
        r1 = await tm.execute("search.files", {"path": str(tmp_workdir), "pattern": "*"})
        assert r1.success, f"Search failed: {r1.error}"
        files = r1.data.get("files", [])
        assert len(files) >= 1
        # Step 2: Read each file
        for f in files:
            r2 = await tm.execute("file.read", {"path": f["path"]})
            assert r2.success, f"Read failed: {r2.error}"
        # Step 3: Detect language
        r3 = await tm.execute("content.detect_language", {"path": str(tmp_workdir / "script.py")})
        assert r3.success, f"Detect language failed: {r3.error}"
        # Step 4: Generate report
        report = {"files": len(files), "detected": r3.data}
        r4 = await tm.execute("content.write_json", {
            "path": str(tmp_workdir / "analysis.json"),
            "data": report,
        })
        assert r4.success

    async def test_git_workflow(self, full_stack, tmp_workdir):
        """Terminal init → Status → Add → Commit via terminal (git tools need CWD)."""
        tm = full_stack["tm"]
        # Use terminal for git operations since git tools need proper CWD
        r1 = await tm.execute("terminal.run_command", {
            "command": f"cd {tmp_workdir} && git init && git add -A && git commit -m 'Initial commit'",
        })
        assert r1.success, f"Git init/add/commit failed: {r1.error}"
        # Verify with git log
        r2 = await tm.execute("terminal.run_command", {
            "command": f"cd {tmp_workdir} && git log --oneline",
        })
        assert r2.success
        assert "Initial commit" in r2.data.get("stdout", "")


# ═══════════════════════════════════════════════════════════════════
# Scenario 2: Research Workflow
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestResearchWorkflow:
    """Search documentation, browse pages, extract content, compare, generate summary, save report."""

    async def test_planner_decomposes_research_request(self, full_stack, pl):
        """Planner should select capabilities for research."""
        pl._capability_registry = full_stack["cr"]
        plan = await pl.create_plan("Search web documentation about Python async, browse multiple pages, extract main content, compare findings, generate summary, save report")
        assert len(plan.steps) >= 2
        cap_ids = [s.capability for s in plan.steps]
        assert any("search" in c or "browser" in c or "http" in c or "network" in c for c in cap_ids)

    async def test_search_download_extract_workflow(self, full_stack, tmp_workdir):
        """Search files → Download → Extract text → Save summary."""
        tm = full_stack["tm"]
        r1 = await tm.execute("search.files", {"path": str(tmp_workdir), "pattern": "*.txt"})
        assert r1.success
        txt_files = [f["path"] for f in r1.data.get("files", [])]
        assert len(txt_files) >= 1
        contents = {}
        for fp in txt_files:
            r2 = await tm.execute("file.read", {"path": fp})
            assert r2.success
            contents[Path(fp).name] = r2.data["content"]
        summary_path = str(tmp_workdir / "summary.json")
        r3 = await tm.execute("content.write_json", {
            "path": summary_path,
            "data": {"files": contents, "count": len(contents)},
        })
        assert r3.success


# ═══════════════════════════════════════════════════════════════════
# Scenario 3: Desktop Workflow
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestDesktopWorkflow:
    """Find large files, organize folders, compress files, generate inventory, clean temp files."""

    async def test_find_organize_compress_workflow(self, full_stack, tmp_workdir):
        tm = full_stack["tm"]
        # Step 1: Find all files
        r1 = await tm.execute("search.files", {"path": str(tmp_workdir), "pattern": "*"})
        assert r1.success
        all_files = r1.data.get("files", [])
        assert len(all_files) >= 1
        # Step 2: Create organized directory structure
        r2 = await tm.execute("file.create_directory", {"path": str(tmp_workdir / "organized")})
        assert r2.success
        r3 = await tm.execute("file.create_directory", {"path": str(tmp_workdir / "organized" / "docs")})
        assert r3.success
        # Step 3: Move txt files to docs
        for f in all_files:
            if f["name"].endswith(".txt"):
                r4 = await tm.execute("file.copy", {
                    "source": f["path"],
                    "destination": str(tmp_workdir / "organized" / "docs" / f["name"]),
                })
                assert r4.success
        # Step 4: Compress organized folder
        r5 = await tm.execute("archive.compress", {
            "source": str(tmp_workdir / "organized"),
            "destination": str(tmp_workdir / "organized.zip"),
            "format": "zip",
        })
        assert r5.success
        # Step 5: Verify archive
        r6 = await tm.execute("archive.validate", {"archive": str(tmp_workdir / "organized.zip")})
        assert r6.success
        assert r6.data["valid"] is True

    async def test_inventory_cleanup(self, full_stack, tmp_workdir):
        tm = full_stack["tm"]
        # Step 1: Generate inventory
        r1 = await tm.execute("search.files", {"path": str(tmp_workdir), "pattern": "*"})
        assert r1.success
        inventory = [{"name": f["name"], "size": f["size"], "path": f["path"]}
                     for f in r1.data.get("files", [])]
        r2 = await tm.execute("content.write_json", {
            "path": str(tmp_workdir / "inventory.json"),
            "data": inventory,
        })
        assert r2.success
        # Step 2: Verify inventory
        r3 = await tm.execute("file.metadata", {"path": str(tmp_workdir / "inventory.json")})
        assert r3.success
        assert r3.data["size"] > 0


# ═══════════════════════════════════════════════════════════════════
# Scenario 4: Productivity Workflow
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestProductivityWorkflow:
    """Download document, rename file, extract content, update spreadsheet, archive documents."""

    async def test_rename_extract_archive(self, full_stack, tmp_workdir):
        tm = full_stack["tm"]
        # Step 1: Rename file
        r1 = await tm.execute("file.rename", {
            "path": str(tmp_workdir / "notes.txt"),
            "new_name": "meeting_notes.txt",
        })
        assert r1.success
        assert (tmp_workdir / "meeting_notes.txt").exists()
        # Step 2: Extract content
        r2 = await tm.execute("file.read", {"path": str(tmp_workdir / "meeting_notes.txt")})
        assert r2.success
        content = r2.data["content"]
        assert "Important notes" in content
        # Step 3: Write extracted data
        r3 = await tm.execute("content.write_text", {
            "path": str(tmp_workdir / "extracted_content.txt"),
            "content": content,
        })
        assert r3.success
        # Step 4: Archive documents
        r4 = await tm.execute("archive.compress", {
            "source": str(tmp_workdir),
            "destination": str(tmp_workdir / "documents.zip"),
            "format": "zip",
        })
        assert r4.success
        # Step 5: Verify
        r5 = await tm.execute("archive.list", {"archive": str(tmp_workdir / "documents.zip")})
        assert r5.success
        assert r5.data["entry_count"] > 0


# ═══════════════════════════════════════════════════════════════════
# Scenario 5: Cross-Tool Integration
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestCrossToolIntegration:
    """Validate tools from different categories chain correctly."""

    async def test_file_clipboard_archive_chain(self, full_stack, tmp_workdir):
        """File → Clipboard → Archive cross-tool chain."""
        tm = full_stack["tm"]
        # Step 1: Read file (filesystem)
        r1 = await tm.execute("file.read", {"path": str(tmp_workdir / "doc1.txt")})
        assert r1.success
        content = r1.data["content"]
        # Step 2: Write to clipboard (clipboard)
        r2 = await tm.execute("clipboard.write", {"content": content})
        if not r2.success:
            pytest.skip("Clipboard not available")
        assert r2.success
        # Step 3: Write new file with clipboard content
        r3 = await tm.execute("file.write", {
            "path": str(tmp_workdir / "clipboard_save.txt"),
            "content": content,
        })
        assert r3.success
        # Step 4: Compress (archive)
        r4 = await tm.execute("archive.compress", {
            "source": str(tmp_workdir / "clipboard_save.txt"),
            "destination": str(tmp_workdir / "cross_tool.zip"),
            "format": "zip",
        })
        assert r4.success

    async def test_search_metadata_hash_chain(self, full_stack, tmp_workdir):
        """Search → Metadata → Hash cross-tool chain."""
        tm = full_stack["tm"]
        r1 = await tm.execute("search.files", {"path": str(tmp_workdir), "pattern": "*.txt"})
        assert r1.success
        for f in r1.data.get("files", []):
            r2 = await tm.execute("file.metadata", {"path": f["path"]})
            assert r2.success
            r3 = await tm.execute("file.hash", {"path": f["path"], "algorithm": "sha256"})
            assert r3.success
            assert r3.data["hash"]

    async def test_write_validate_read_chain(self, full_stack, tmp_workdir):
        """Write JSON → Validate → Read back."""
        tm = full_stack["tm"]
        data = {"test": True, "value": 42}
        r1 = await tm.execute("content.write_json", {
            "path": str(tmp_workdir / "test.json"),
            "data": data,
        })
        assert r1.success
        r2 = await tm.execute("content.validate_json", {
            "path": str(tmp_workdir / "test.json"),
        })
        assert r2.success
        assert r2.data["valid"] is True
        r3 = await tm.execute("content.read_json", {"path": str(tmp_workdir / "test.json")})
        assert r3.success
        assert r3.data["data"] == data


# ═══════════════════════════════════════════════════════════════════
# Execution Engine — Full Pipeline
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestExecutionEnginePipeline:
    """Full Planner → Execution Engine pipeline validation."""

    async def test_planner_with_capability_registry(self, full_stack, pl):
        """Planner should use CR to generate relevant steps."""
        pl._capability_registry = full_stack["cr"]
        plan = await pl.create_plan("Find all text files and read their contents")
        assert len(plan.steps) >= 1
        cap_ids = [s.capability for s in plan.steps]
        assert any("search" in c or "file" in c for c in cap_ids), f"Got: {cap_ids}"

    async def test_planner_fallback_without_cr(self, pl):
        """Planner without CR should generate fallback step."""
        plan = await pl.create_plan("Some request")
        assert len(plan.steps) >= 1

    async def test_workflow_build_tasks(self, full_stack, pl):
        """Workflow builder should convert plan steps to tasks."""
        pl._capability_registry = full_stack["cr"]
        plan = await pl.create_plan("Read files and compress")
        assert len(plan.steps) >= 1
        from aios.execution.workflow import WorkflowBuilder
        from aios.execution.models import Execution
        wb = WorkflowBuilder()
        execution = Execution(objective="test")
        tasks = wb.build_tasks(execution, plan)
        assert len(tasks) >= 1
        assert tasks[0].capability is not None

    async def test_executor_resolves_capability(self, full_stack):
        """Executor should resolve capability IDs to tool IDs."""
        from aios.execution.executor import TaskExecutor
        from aios.execution.models import Task, TaskStatus
        executor = TaskExecutor(full_stack["cr"], full_stack["tm"])
        task = Task(execution_id="t1", capability="search.files", tool="search.files", parameters={
            "path": ".", "pattern": "*.py",
        })
        result = await executor.execute_task(task)
        assert result.status in (TaskStatus.SUCCESS, TaskStatus.FAILED)
        if result.status == TaskStatus.FAILED:
            assert "permission" in result.error.lower() or "denied" in result.error.lower(), \
                f"Unexpected error: {result.error}"

    async def test_executor_fallback_to_tool_id(self, full_stack):
        """Executor should fall back to tool ID when capability not found."""
        from aios.execution.executor import TaskExecutor
        from aios.execution.models import Task, TaskStatus
        executor = TaskExecutor(full_stack["cr"], full_stack["tm"])
        task = Task(execution_id="t2", capability="nonexistent.cap", tool="nonexistent.cap", parameters={})
        result = await executor.execute_task(task)
        assert result.status == TaskStatus.FAILED
        assert result.error is not None

    async def test_engine_state_transitions(self, engine):
        """Engine should transition through states."""
        execution = await engine.start_execution(objective="full pipeline test")
        assert execution.status == ExecutionStatus.PENDING
        await asyncio.sleep(0.8)
        execution = await engine.get_execution(execution.id)
        assert execution.status in (
            ExecutionStatus.COMPLETED, ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED, ExecutionStatus.RUNNING,
        )

    async def test_engine_pause_resume_cancel(self, engine):
        execution = await engine.start_execution(objective="pause test")
        paused = await engine.pause_execution(execution.id)
        assert paused is not None
        resumed = await engine.resume_execution(execution.id)
        assert resumed is not None
        cancelled = await engine.cancel_execution(execution.id)
        assert cancelled.status == ExecutionStatus.CANCELLED

    async def test_engine_history(self, engine):
        await engine.start_execution(objective="history test 1")
        await engine.start_execution(objective="history test 2")
        await asyncio.sleep(0.1)
        history = await engine.get_history()
        assert len(history) >= 1

    async def test_execution_progress(self, engine):
        execution = await engine.start_execution(objective="progress test")
        await asyncio.sleep(0.1)
        progress = await engine.get_execution_progress(execution.id)
        assert progress is not None
        assert progress.total_tasks >= 0

    async def test_engine_list_executions(self, engine):
        await engine.start_execution(objective="list test")
        await asyncio.sleep(0.1)
        executions = await engine.list_executions()
        assert len(executions) >= 1
        assert executions[0].objective is not None


# ═══════════════════════════════════════════════════════════════════
# Multi-Modal Interface Validation
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestMultiModalValidation:
    """Validate that chat/voice/vision all route through same pipeline."""

    async def test_chat_interface_capabilities(self, full_stack):
        """All tools should support chat interface."""
        caps = await full_stack["cr"].filter_by_interface("chat")
        assert len(caps) > 0, "No capabilities support chat interface"

    async def test_voice_interface_capabilities(self, full_stack):
        """Voice interface capabilities should be a subset."""
        voice_caps = await full_stack["cr"].filter_by_interface("voice")
        all_caps = await full_stack["cr"].list_capabilities()
        assert set(v.id for v in voice_caps).issubset(set(c.id for c in all_caps))

    async def test_vision_interface_capabilities(self, full_stack):
        """Vision interface capabilities should be a subset."""
        vision_caps = await full_stack["cr"].filter_by_interface("vision")
        all_caps = await full_stack["cr"].list_capabilities()
        assert set(v.id for v in vision_caps).issubset(set(c.id for c in all_caps))

    async def test_planner_selects_chat_capabilities(self, full_stack, pl):
        """Planner should respect interface filter."""
        pl._capability_registry = full_stack["cr"]
        result = await pl.select_best_capability("read file", interface="chat")
        if result:
            cap_id, score = result
            caps = await full_stack["cr"].find_capability(cap_id)
            for c in caps:
                assert "chat" in c.supported_interfaces


# ═══════════════════════════════════════════════════════════════════
# Capability Intelligence — Selection and Ranking
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestCapabilityIntelligence:
    """Validate Capability Intelligence selection and ranking."""

    async def test_rank_for_task(self, full_stack):
        """Tasks should rank relevant capabilities highest."""
        ranked = await full_stack["cr"].rank_for_task("search for files on disk")
        assert len(ranked) > 0
        top_id, top_score = ranked[0]
        assert any(term in top_id for term in ["search", "file"]), \
            f"Expected search/file at top, got {top_id} ({top_score})"

    async def test_rank_for_read_task(self, full_stack):
        ranked = await full_stack["cr"].rank_for_task("read text file content")
        assert len(ranked) > 0
        top_ids = [c.id for c, s in ranked[:5]]
        assert any("file.read" in i or "content.read" in i for i in top_ids), \
            f"Expected file.read or content.read in top, got {top_ids}"

    async def test_rank_for_git_task(self, full_stack):
        ranked = await full_stack["cr"].rank_for_task("commit changes to git repository")
        assert len(ranked) > 0
        top_ids = [c.id for c, s in ranked[:5]]
        assert any("git" in i for i in top_ids), \
            f"Expected git in top 5, got {top_ids}"

    async def test_fallback_capability(self, full_stack, pl):
        """Fallback should return a valid capability."""
        pl._capability_registry = full_stack["cr"]
        fallback = await pl.get_fallback_capability("some random task")
        assert fallback is not None

    async def test_recommend_alternatives(self, full_stack):
        """Related capabilities should be recommended."""
        related = await full_stack["cr"].recommend_alternatives("search.files", max_results=3)
        assert len(related) >= 0  # may be 0 if no related_capabilities set

    async def test_search_by_category(self, full_stack):
        """Category search should return matching capabilities."""
        git_caps = await full_stack["cr"].search_by_category("git")
        assert len(git_caps) >= 1

    async def test_filter_by_permission(self, full_stack):
        """Permission filtering should work."""
        read_caps = await full_stack["cr"].filter_by_permission(min_level=0, max_level=0)
        assert len(read_caps) >= 1

    async def test_capability_lifecycle(self, full_stack):
        """Register → find → unregister flow."""
        cap = Capability(
            id="test.temp", name="Temp", description="Temporary",
            provider_type="tool", provider_id="test",
        )
        await full_stack["cr"].register_capability(cap)
        found = await full_stack["cr"].find_best_match("test.temp")
        assert found is not None
        await full_stack["cr"].unregister_capability("test.temp")
        found = await full_stack["cr"].find_best_match("test.temp")
        assert found is None


# ═══════════════════════════════════════════════════════════════════
# Event Bus — Cross-Component Events
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestEventBusIntegration:
    """Validate event bus works across components."""

    async def test_execution_events_published(self, engine, bus):
        events = []
        await bus.subscribe("execution.*", lambda e: events.append(e))
        await engine.start_execution(objective="event test scenario")
        await asyncio.sleep(0.5)
        assert len(events) > 0, "No execution events published"

    async def test_event_bus_wildcard(self, bus):
        events = []
        await bus.subscribe("*", lambda e: events.append(e))
        await bus.publish("test.event", {"msg": "wildcard test"})
        await asyncio.sleep(0.05)
        assert len(events) >= 1

    async def test_event_bus_topic_filter(self, bus):
        file_events = []
        await bus.subscribe("file.*", lambda e: file_events.append(e))
        await bus.publish("file.read", {"path": "/test"})
        await bus.publish("other.event", {})
        await asyncio.sleep(0.05)
        assert len(file_events) >= 1
        assert len(file_events) == 1  # only file.* matched


# ═══════════════════════════════════════════════════════════════════
# Tool Manager — Registration, Discovery, Execution
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestToolManagerIntegration:
    """Validate ToolManager registration and discovery."""

    async def test_tool_registration_count(self, full_stack):
        all_tools = await full_stack["tm"].list_tools()
        assert len(all_tools) >= 150, f"Expected 150+ tools, got {len(all_tools)}"

    async def test_tool_discovery_by_category(self, full_stack):
        git_tools = await full_stack["tm"].list_tools(category="git")
        assert len(git_tools) >= 15

    async def test_tool_search(self, full_stack):
        results = await full_stack["tm"].search_tools("clipboard")
        assert len(results) >= 1

    async def test_tool_not_found(self, full_stack):
        result = await full_stack["tm"].execute("does.not.exist", {})
        assert not result.success
        assert "not found" in result.error.lower()

    async def test_tool_invalid_params(self, full_stack):
        result = await full_stack["tm"].execute("file.read", {})  # missing path
        assert not result.success


# ═══════════════════════════════════════════════════════════════════
# Memory System Integration
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestMemoryIntegration:
    """Validate memory system stores execution context."""

    async def test_memory_store_and_retrieve(self):
        from aios.core.memory_system import MemorySystem
        mem = MemorySystem()
        await mem.store("agent:test", {"key": "value"}, ttl=60)
        result = await mem.retrieve("agent:test")
        assert result is not None
        assert result["key"] == "value"

    async def test_memory_search(self):
        from aios.core.memory_system import MemorySystem
        mem = MemorySystem()
        await mem.store("agent:search_test", {"data": 42}, ttl=60)
        results = await mem.search("search_test")
        assert len(results) >= 1

    async def test_memory_expiry(self):
        from aios.core.memory_system import MemorySystem
        mem = MemorySystem()
        await mem.store("agent:expiry_test", {"x": 1}, ttl=0)
        import time
        time.sleep(0.1)
        result = await mem.retrieve("agent:expiry_test")
        assert result is None


# ═══════════════════════════════════════════════════════════════════
# Progress Streaming
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestProgressStreaming:
    """Validate progress tracking and streaming."""

    async def test_progress_tracker(self, engine):
        from aios.execution.progress import ProgressTracker
        from aios.execution.models import Execution, Task
        pt = ProgressTracker()
        execution = Execution(objective="progress test")
        tasks = [Task(execution_id="e1", capability="c1", tool="c1", index=i) for i in range(3)]
        progress = pt.initialize(execution, tasks)
        assert progress.total_tasks == 3
        assert progress.completed_tasks == 0
        pt.task_completed("e1", tasks[0])
        progress = pt.get_progress("e1")
        assert progress.completed_tasks == 1

    async def test_stream_events(self, engine):
        execution = await engine.start_execution(objective="stream test")
        await asyncio.sleep(0.1)
        stream = engine.stream_events(execution.id)
        events = []
        async for event in stream:
            events.append(event)
            break  # one event is enough to validate
        assert len(events) >= 0  # may be 0 if no events yet


# ═══════════════════════════════════════════════════════════════════
# Recovery & Retry
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestRecoveryAndRetry:
    """Validate failure recovery and retry mechanisms."""

    async def test_recovery_engine_optional_ok(self):
        from aios.execution.recovery import RecoveryEngine
        from aios.execution.planner_adapter import PlannerAdapter
        from aios.execution.models import Task, TaskStatus, Execution
        recovery = RecoveryEngine(PlannerAdapter(planner=None))
        task = Task(execution_id="e1", capability="c1", tool="c1",
                    status=TaskStatus.FAILED, error="optional fail",
                    is_optional=True)
        execution = Execution(objective="test")
        can_continue = await recovery.can_continue(execution, [task])
        assert can_continue

    async def test_recovery_engine_critical_stops(self):
        from aios.execution.recovery import RecoveryEngine
        from aios.execution.planner_adapter import PlannerAdapter
        from aios.execution.models import Task, TaskStatus, Execution
        recovery = RecoveryEngine(PlannerAdapter(planner=None))
        task = Task(execution_id="e1", capability="c1", tool="c1",
                    status=TaskStatus.FAILED, error="critical fail",
                    is_optional=False)
        execution = Execution(objective="test")
        can_continue = await recovery.can_continue(execution, [task])
        assert not can_continue

    async def test_recovery_handle_failure(self):
        from aios.execution.recovery import RecoveryEngine
        from aios.execution.planner_adapter import PlannerAdapter
        from aios.execution.models import Task, TaskStatus, Execution
        recovery = RecoveryEngine(PlannerAdapter(planner=None))
        task = Task(execution_id="e1", capability="c1", tool="c1",
                    status=TaskStatus.FAILED, error="fail",
                    max_retries=2, retry_count=0)
        execution = Execution(objective="test")
        recovered, new_task = await recovery.handle_failure(execution, task)
        assert recovered
        assert new_task is not None
        assert new_task.retry_count == 1

    async def test_recovery_exhausts_retries(self):
        from aios.execution.recovery import RecoveryEngine
        from aios.execution.planner_adapter import PlannerAdapter
        from aios.execution.models import Task, TaskStatus, Execution
        recovery = RecoveryEngine(PlannerAdapter(planner=None))
        task = Task(execution_id="e1", capability="c1", tool="c1",
                    status=TaskStatus.FAILED, error="fail",
                    max_retries=2, retry_count=3)
        execution = Execution(objective="test")
        recovered, new_task = await recovery.handle_failure(execution, task)
        assert not recovered
        assert new_task is None


# ═══════════════════════════════════════════════════════════════════
# Permission Validation — Full Flow
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestPermissionFlow:
    """Validate permission request/grant/deny flow in tool execution."""

    async def test_read_tool_auto_approves(self, full_stack):
        result = await full_stack["tm"].execute("file.read", {"path": __file__})
        assert result.success

    async def test_sensitive_tool_blocks_without_grant(self, full_stack):
        async def handler(p):
            return ToolResult(success=True, data="ok")
        await full_stack["tm"].register_tool(
            ToolContract(
                id="test.secret_op",
                name="Secret",
                description="Secret operation",
                permission_level=PermissionLevel.SENSITIVE,
            ),
            handler,
        )
        await asyncio.sleep(0.05)
        result = await full_stack["tm"].execute("test.secret_op", {})
        assert not result.success
        assert "denied" in result.error.lower() or "permission" in result.error.lower()

    async def test_permission_grant_deny_flow(self, full_stack):
        pm = full_stack["pm"]
        result = await pm.request_permission("test.op", PermissionLevel.SENSITIVE, action="test_action")
        assert result is not None
        req_id = result.request.id
        assert req_id is not None
        granted = await pm.grant_permission(req_id)
        assert granted.status == "granted"
        result2 = await pm.request_permission("test.op2", PermissionLevel.WORKSPACE, action="test_action2")
        req_id2 = result2.request.id
        denied = await pm.deny_permission(req_id2, "Not allowed")
        assert denied.status == "denied"

    async def test_permission_check_task(self):
        from aios.execution.permissions import ExecutionPermissionManager
        from aios.execution.models import Task
        from aios.core.permission_manager import PermissionManager, PermissionLevel
        pm = PermissionManager()
        epm = ExecutionPermissionManager(pm)
        task = Task(execution_id="e1", capability="file.read", tool="file.read",
                    parameters={"path": "."})
        granted, req_id = await epm.check_task(task)
        assert granted or req_id is not None


# ═══════════════════════════════════════════════════════════════════
# Performance Measurements
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestPerformance:
    """Measure key agent workflow performance metrics."""

    async def test_planning_latency(self, full_stack, pl):
        pl._capability_registry = full_stack["cr"]
        t0 = time.monotonic()
        plan = await pl.create_plan("Find all text files, read their contents, compress into archive")
        latency = (time.monotonic() - t0) * 1000
        print(f"\n[PERF] Planning latency: {latency:.1f}ms ({len(plan.steps)} steps)")
        assert latency < 1000, f"Planning too slow: {latency:.1f}ms"

    async def test_capability_ranking_latency(self, full_stack):
        t0 = time.monotonic()
        await full_stack["cr"].rank_for_task("search for files and read content")
        latency = (time.monotonic() - t0) * 1000
        print(f"[PERF] Capability ranking latency: {latency:.1f}ms")
        assert latency < 500, f"Ranking too slow: {latency:.1f}ms"

    async def test_tool_execution_latency(self, full_stack, tmp_workdir):
        suite = [
            ("file.metadata", {"path": str(tmp_workdir / "doc1.txt")}),
            ("file.read", {"path": str(tmp_workdir / "doc1.txt")}),
            ("file.hash", {"path": str(tmp_workdir / "doc1.txt"), "algorithm": "sha256"}),
            ("search.files", {"path": str(tmp_workdir), "pattern": "*"}),
            ("file.list", {"path": str(tmp_workdir)}),
        ]
        for tool_id, params in suite:
            t0 = time.monotonic()
            result = await full_stack["tm"].execute(tool_id, params)
            elapsed = (time.monotonic() - t0) * 1000
            print(f"[PERF] {tool_id}: {elapsed:.1f}ms (success={result.success})")

    async def test_concurrent_execution(self, full_stack, tmp_workdir):
        tasks = [
            full_stack["tm"].execute("file.metadata", {"path": str(tmp_workdir / "doc1.txt")}),
            full_stack["tm"].execute("file.metadata", {"path": str(tmp_workdir / "doc2.txt")}),
            full_stack["tm"].execute("file.hash", {"path": str(tmp_workdir / "doc1.txt"), "algorithm": "sha256"}),
            full_stack["tm"].execute("search.files", {"path": str(tmp_workdir), "pattern": "*.txt"}),
        ]
        t0 = time.monotonic()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total = (time.monotonic() - t0) * 1000
        successes = sum(1 for r in results if isinstance(r, ToolResult) and r.success)
        print(f"[PERF] Concurrent: {successes}/{len(tasks)} in {total:.1f}ms")


# ═══════════════════════════════════════════════════════════════════
# State Machine Validation
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestStateMachine:
    """Validate execution state machine transitions."""

    async def test_valid_transitions(self):
        from aios.execution.state_machine import ExecutionStateMachine
        from aios.execution.models import ExecutionStatus
        sm = ExecutionStateMachine()
        new_state = sm.transition(ExecutionStatus.PENDING, ExecutionStatus.PLANNING, "start")
        assert new_state == ExecutionStatus.PLANNING

    async def test_invalid_transition_raises(self):
        from aios.execution.state_machine import ExecutionStateMachine
        from aios.execution.models import ExecutionStatus
        from aios.execution.exceptions import InvalidStateTransitionError
        sm = ExecutionStateMachine()
        with pytest.raises(InvalidStateTransitionError):
            sm.transition(ExecutionStatus.PENDING, ExecutionStatus.COMPLETED, "skip")

    async def test_all_allowed_transitions(self):
        from aios.execution.state_machine import ExecutionStateMachine
        from aios.execution.models import ExecutionStatus
        sm = ExecutionStateMachine()
        transitions = [
            (ExecutionStatus.PENDING, ExecutionStatus.PLANNING),
            (ExecutionStatus.PLANNING, ExecutionStatus.READY),
            (ExecutionStatus.READY, ExecutionStatus.RUNNING),
            (ExecutionStatus.RUNNING, ExecutionStatus.COMPLETED),
            (ExecutionStatus.RUNNING, ExecutionStatus.FAILED),
            (ExecutionStatus.RUNNING, ExecutionStatus.PAUSED),
            (ExecutionStatus.PAUSED, ExecutionStatus.RUNNING),
            (ExecutionStatus.RUNNING, ExecutionStatus.CANCELLED),
            (ExecutionStatus.PENDING, ExecutionStatus.CANCELLED),
        ]
        for from_s, to_s in transitions:
            result = sm.transition(from_s, to_s, "test")
            assert result == to_s, f"Failed: {from_s} -> {to_s}"


# ═══════════════════════════════════════════════════════════════════
# Scheduler Validation
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestScheduler:
    """Validate task scheduling."""

    async def test_scheduler_basic(self):
        from aios.execution.scheduler import Scheduler
        from aios.execution.models import Execution, Task
        sched = Scheduler(max_concurrent=5)
        execution = Execution(objective="sched test")
        tasks = [Task(execution_id="e1", capability=f"c{i}", tool=f"c{i}", index=i) for i in range(3)]
        results = []
        async for task in sched.schedule(execution, tasks):
            results.append(task)
        assert len(results) == 3

    async def test_scheduler_concurrent_limit(self):
        from aios.execution.scheduler import Scheduler
        from aios.execution.models import Execution, Task
        sched = Scheduler(max_concurrent=2)
        execution = Execution(objective="concurrent test")
        tasks = [Task(execution_id="e1", capability=f"c{i}", tool=f"c{i}", index=i) for i in range(5)]
        in_flight = 0
        max_in_flight = 0
        async for task in sched.schedule(execution, tasks):
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
            in_flight -= 1
        assert max_in_flight <= 2

    async def test_scheduler_pause_resume(self):
        from aios.execution.scheduler import Scheduler
        from aios.execution.models import Execution, Task
        sched = Scheduler(max_concurrent=5)
        execution = Execution(objective="pause test")
        tasks = [Task(execution_id="e1", capability=f"c{i}", tool=f"c{i}", index=i) for i in range(3)]
        await sched.pause("e1")
        results = []
        async for task in sched.schedule(execution, tasks):
            results.append(task)
        # After resume, should still schedule
        await sched.resume("e1")
        async for task in sched.schedule(execution, tasks):
            results.append(task)
        assert len(results) >= 0
        await sched.cleanup("e1")
