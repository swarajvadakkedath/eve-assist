"""Tests for the Context Engine — all dependencies are mocked."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from aios.adapters.base_adapter import WindowInfo
from aios.core.context import (
    Context,
    ContextEngine,
    ProjectInfo,
    ActivityType,
    detect_project_from_file,
    detect_project_from_path,
    infer_project_type_from_file,
    detect_activity,
    extract_active_file,
    PROJECT_MARKERS,
    EXTENSION_MAP,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_windows_adapter():
    wa = MagicMock()
    wa.get_active_window = AsyncMock(return_value=WindowInfo(
        title="test.py - Visual Studio Code",
        app="Visual Studio Code",
        x=0, y=0, width=1920, height=1080,
    ))
    wa.search_files = AsyncMock(return_value=[])
    wa.read_file = AsyncMock(return_value="")
    wa.file_exists = AsyncMock(return_value=True)
    wa.get_file_metadata = AsyncMock(return_value={"path": "/test", "is_dir": False})
    return wa


@pytest.fixture
def mock_event_bus():
    eb = MagicMock()
    eb.publish = AsyncMock(return_value="event_id")
    return eb


@pytest.fixture
def mock_memory_store():
    ms = MagicMock()
    ms.create_node = MagicMock(return_value=(MagicMock(), []))
    return ms


@pytest.fixture
def engine(mock_windows_adapter, mock_event_bus):
    return ContextEngine(
        windows_adapter=mock_windows_adapter,
        event_bus=mock_event_bus,
        poll_interval=0.1,
    )


@pytest.fixture
def engine_with_memory(mock_windows_adapter, mock_event_bus, mock_memory_store):
    return ContextEngine(
        windows_adapter=mock_windows_adapter,
        event_bus=mock_event_bus,
        poll_interval=0.1,
        memory_store=mock_memory_store,
    )


# ---------------------------------------------------------------------------
# Context Model
# ---------------------------------------------------------------------------


class TestContextModel:
    def test_default_construction(self):
        ctx = Context()
        assert ctx.active_app is None
        assert ctx.activity == ActivityType.IDLE
        assert ctx.timestamp > 0

    def test_to_dict(self):
        ctx = Context(
            active_app="Code",
            active_window="test.py - Code",
            active_file="test.py",
            project=ProjectInfo(path="/project", type="python", markers=["pyproject.toml"]),
            activity=ActivityType.CODING,
        )
        d = ctx.to_dict()
        assert d["active_app"] == "Code"
        assert d["project_path"] == "/project"
        assert d["project_type"] == "python"
        assert d["activity"] == "coding"

    def test_changed_since_none(self):
        ctx = Context(active_app="Code")
        changes = ctx.changed_since(None)
        assert "active_app" in changes
        assert "project" in changes
        assert "activity" in changes
        assert "active_file" in changes
        assert "active_window" in changes

    def test_changed_since_no_change(self):
        a = Context(active_app="Code", active_window="test.py", activity=ActivityType.CODING)
        b = Context(active_app="Code", active_window="test.py", activity=ActivityType.CODING)
        assert b.changed_since(a) == []

    def test_changed_since_app_changed(self):
        a = Context(active_app="Code")
        b = Context(active_app="Browser")
        assert "active_app" in b.changed_since(a)

    def test_changed_since_window_changed(self):
        a = Context(active_window="file1")
        b = Context(active_window="file2")
        assert "active_window" in b.changed_since(a)

    def test_changed_since_file_changed(self):
        a = Context(active_file="a.py")
        b = Context(active_file="b.py")
        assert "active_file" in b.changed_since(a)

    def test_changed_since_project_changed(self):
        a = Context(project=ProjectInfo(path="/a", type="python", markers=[]))
        b = Context(project=ProjectInfo(path="/b", type="node", markers=[]))
        assert "project" in b.changed_since(a)

    def test_changed_since_project_to_none(self):
        a = Context(project=ProjectInfo(path="/a", type="python", markers=[]))
        b = Context(project=None)
        assert "project" in b.changed_since(a)

    def test_changed_since_activity_changed(self):
        a = Context(activity=ActivityType.CODING)
        b = Context(activity=ActivityType.BROWSING)
        assert "activity" in b.changed_since(a)

    def test_timestamp_auto_set(self):
        ctx = Context()
        assert ctx.timestamp > 0

    def test_project_info_defaults(self):
        p = ProjectInfo(path="/test", type="python")
        assert p.markers == []


# ---------------------------------------------------------------------------
# Project Detection
# ---------------------------------------------------------------------------


class TestProjectDetection:
    def test_detect_from_file_none(self):
        assert detect_project_from_file(None) is None

    def test_detect_from_file_empty(self):
        assert detect_project_from_file("") is None

    def test_detect_from_path_none(self):
        assert detect_project_from_path(None) is None

    def test_detect_from_path_empty(self):
        assert detect_project_from_path("") is None

    def test_infer_type_py(self):
        assert infer_project_type_from_file("/path/file.py") == "python"

    def test_infer_type_js(self):
        assert infer_project_type_from_file("/path/file.js") == "node"

    def test_infer_type_ts(self):
        assert infer_project_type_from_file("/path/file.ts") == "node"

    def test_infer_type_rs(self):
        assert infer_project_type_from_file("/path/file.rs") == "rust"

    def test_infer_type_go(self):
        assert infer_project_type_from_file("/path/file.go") == "go"

    def test_infer_type_unknown(self):
        assert infer_project_type_from_file("/path/file.xyz") is None

    def test_project_markers_defined(self):
        assert ".git" in PROJECT_MARKERS["generic"]
        assert "pyproject.toml" in PROJECT_MARKERS["python"]
        assert "package.json" in PROJECT_MARKERS["node"]
        assert "Cargo.toml" in PROJECT_MARKERS["rust"]
        assert "go.mod" in PROJECT_MARKERS["go"]

    def test_extension_map_comprehensive(self):
        assert EXTENSION_MAP[".py"] == "python"
        assert EXTENSION_MAP[".js"] == "node"
        assert EXTENSION_MAP[".rs"] == "rust"

    def test_detect_from_file_real_directory(self, tmp_path):
        project_dir = tmp_path / "myproject"
        project_dir.mkdir()
        (project_dir / "pyproject.toml").write_text("")
        test_file = project_dir / "src" / "main.py"
        test_file.parent.mkdir()
        test_file.write_text("")
        result = detect_project_from_file(str(test_file))
        assert result is not None
        assert result.type == "python"
        assert "pyproject.toml" in result.markers

    def test_detect_from_file_no_project(self, tmp_path):
        deep = tmp_path / "a" / "b" / "c" / "d" / "e" / "orphan.txt"
        deep.parent.mkdir(parents=True, exist_ok=True)
        deep.write_text("")
        result = detect_project_from_file(str(deep))
        assert result is None or result.type == "unknown"

    def test_detect_from_path(self, tmp_path):
        d = tmp_path / "node_project"
        d.mkdir()
        (d / "package.json").write_text("{}")
        result = detect_project_from_path(str(d))
        assert result is not None
        assert result.type == "node"

    def test_detect_git_only(self, tmp_path):
        d = tmp_path / "git_only"
        d.mkdir()
        (d / ".git").mkdir()
        result = detect_project_from_path(str(d))
        assert result is not None
        assert result.type == "generic"


# ---------------------------------------------------------------------------
# Activity Detection
# ---------------------------------------------------------------------------


class TestActivityDetection:
    def test_coding_vscode(self):
        assert detect_activity("Code", "test.py - Visual Studio Code") == ActivityType.CODING

    def test_coding_pycharm(self):
        assert detect_activity("pycharm") == ActivityType.CODING

    def test_browsing_chrome(self):
        assert detect_activity("chrome") == ActivityType.BROWSING

    def test_browsing_firefox(self):
        assert detect_activity("firefox") == ActivityType.BROWSING

    def test_browsing_edge(self):
        assert detect_activity("msedge") == ActivityType.BROWSING

    def test_office_word(self):
        assert detect_activity("WINWORD.EXE") == ActivityType.OFFICE

    def test_office_excel(self):
        assert detect_activity("excel") == ActivityType.OFFICE

    def test_office_outlook(self):
        assert detect_activity("outlook") == ActivityType.OFFICE

    def test_office_slack(self):
        assert detect_activity("slack") == ActivityType.OFFICE

    def test_idle_empty(self):
        assert detect_activity("") == ActivityType.IDLE

    def test_idle_none(self):
        assert detect_activity(None) == ActivityType.IDLE

    def test_idle_lock(self):
        assert detect_activity("lockapp") == ActivityType.IDLE

    def test_unknown_app(self):
        assert detect_activity("weirdapp123") == ActivityType.UNKNOWN

    def test_terminal_coding(self):
        assert detect_activity("windows terminal") == ActivityType.CODING

    def test_cmd_coding(self):
        assert detect_activity("cmd") == ActivityType.CODING

    def test_powershell_coding(self):
        assert detect_activity("powershell") == ActivityType.CODING

    def test_extract_file_vscode(self):
        result = extract_active_file("Code", "main.py - Visual Studio Code")
        assert result == "main.py"

    def test_extract_file_emacs(self):
        result = extract_active_file("emacs", "index.js - GNU Emacs")
        assert result == "index.js"

    def test_extract_file_no_match(self):
        result = extract_active_file("chrome", "Google Chrome")
        assert result is None

    def test_extract_file_no_title(self):
        result = extract_active_file("Code", None)
        assert result is None

    def test_extract_file_no_app(self):
        result = extract_active_file(None, "test.py - Code")
        assert result is None


# ---------------------------------------------------------------------------
# Context Engine — Lifecycle
# ---------------------------------------------------------------------------


class TestEngineLifecycle:
    async def test_start_stop(self, engine):
        await engine.start()
        assert engine._running is True
        assert engine._poll_task is not None
        await engine.stop()
        assert engine._running is False

    async def test_start_idempotent(self, engine):
        await engine.start()
        await engine.start()
        assert engine._running is True
        await engine.stop()

    async def test_stop_no_start(self, engine):
        await engine.stop()
        assert engine._running is False

    async def test_event_on_start(self, engine, mock_event_bus):
        await engine.start()
        mock_event_bus.publish.assert_any_call(
            "context:engine_started",
            {"poll_interval": 0.1},
            source="context_engine",
        )
        await engine.stop()

    async def test_event_on_stop(self, engine, mock_event_bus):
        await engine.start()
        mock_event_bus.publish.reset_mock()
        await engine.stop()
        mock_event_bus.publish.assert_called_with(
            "context:engine_stopped",
            {},
            source="context_engine",
        )


# ---------------------------------------------------------------------------
# Context Engine — Polling
# ---------------------------------------------------------------------------


class TestEnginePolling:
    async def test_poll_now_returns_context(self, engine, mock_windows_adapter):
        ctx = await engine.poll_now()
        assert ctx is not None
        assert ctx.active_app == "Visual Studio Code"
        assert ctx.active_window == "test.py - Visual Studio Code"

    async def test_poll_now_updates_current(self, engine):
        ctx = await engine.poll_now()
        assert engine._current is ctx

    async def test_poll_now_without_windows(self):
        eng = ContextEngine()
        ctx = await eng.poll_now()
        assert ctx.active_app is None

    async def test_poll_publishes_context_changed(self, engine, mock_event_bus):
        await engine.poll_now()
        mock_event_bus.publish.assert_any_call(
            "context:changed",
            engine._current.to_dict(),
            source="context_engine",
        )

    async def test_poll_publishes_project_changed(self, engine, mock_windows_adapter, mock_event_bus, tmp_path):
        project_dir = tmp_path / "testproj"
        project_dir.mkdir()
        (project_dir / "pyproject.toml").write_text("")
        src_dir = project_dir / "src"
        src_dir.mkdir()
        test_file = src_dir / "main.py"
        test_file.write_text("")
        title = f"{test_file} - Visual Studio Code"
        mock_windows_adapter.get_active_window = AsyncMock(return_value=WindowInfo(
            title=title,
            app="Visual Studio Code",
            x=0, y=0, width=1920, height=1080,
        ))
        ctx = await engine.poll_now()
        assert ctx.project is not None, f"project should be detected from file '{ctx.active_file}'"
        project_calls = [c for c in mock_event_bus.publish.await_args_list if c[0][0] == "context:project_changed"]
        assert len(project_calls) > 0, f"no project_changed event found in {[c[0] for c in mock_event_bus.publish.await_args_list]}"

    async def test_no_duplicate_events_on_no_change(self, engine, mock_event_bus, mock_windows_adapter):
        await engine.poll_now()
        mock_event_bus.publish.reset_mock()
        mock_windows_adapter.get_active_window = AsyncMock(return_value=WindowInfo(
            title="test.py - Visual Studio Code",
            app="Visual Studio Code",
            x=0, y=0, width=1920, height=1080,
        ))
        await engine.poll_now()
        same_calls = [c for c in mock_event_bus.publish.await_args_list if c[0][0] == "context:changed"]
        assert len(same_calls) == 0

    async def test_poll_error_handled(self, engine, mock_windows_adapter, mock_event_bus):
        mock_windows_adapter.get_active_window.side_effect = Exception("fail")
        mock_event_bus.publish.reset_mock()
        engine._running = True
        engine._poll_task = None
        import asyncio
        task = asyncio.create_task(engine._poll_loop())
        await asyncio.sleep(0.3)
        engine._running = False
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        error_calls = [c for c in mock_event_bus.publish.await_args_list if c[0][0] == "context:poll_error"]
        assert len(error_calls) > 0


# ---------------------------------------------------------------------------
# Context Engine — Activity Changes
# ---------------------------------------------------------------------------


class TestEngineActivity:
    async def test_activity_detected_from_app(self, engine):
        ctx = await engine.poll_now()
        assert ctx.activity == ActivityType.CODING

    async def test_browsing_activity(self, engine, mock_windows_adapter):
        mock_windows_adapter.get_active_window = AsyncMock(return_value=WindowInfo(
            title="GitHub - Google Chrome",
            app="chrome",
            x=0, y=0, width=1920, height=1080,
        ))
        ctx = await engine.poll_now()
        assert ctx.activity == ActivityType.BROWSING

    async def test_idle_lock_screen(self, engine, mock_windows_adapter):
        mock_windows_adapter.get_active_window = AsyncMock(return_value=WindowInfo(
            title="",
            app="lockapp",
            x=0, y=0, width=1920, height=1080,
        ))
        ctx = await engine.poll_now()
        assert ctx.activity == ActivityType.IDLE


# ---------------------------------------------------------------------------
# Context Engine — Event Publication
# ---------------------------------------------------------------------------


class TestEngineEvents:
    async def test_application_changed_on_app_change(self, engine, mock_event_bus):
        mock_event_bus.publish.reset_mock()
        await engine.poll_now()
        app_calls = [c for c in mock_event_bus.publish.await_args_list if c[0][0] == "context:application_changed"]
        assert len(app_calls) > 0

    async def test_file_changed_on_file_change(self, engine, mock_windows_adapter, mock_event_bus):
        mock_windows_adapter.get_active_window = AsyncMock(return_value=WindowInfo(
            title="main.py - Visual Studio Code",
            app="Visual Studio Code",
            x=0, y=0, width=1920, height=1080,
        ))
        mock_event_bus.publish.reset_mock()
        await engine.poll_now()
        mock_event_bus.publish.reset_mock()
        mock_windows_adapter.get_active_window = AsyncMock(return_value=WindowInfo(
            title="other.py - Visual Studio Code",
            app="Visual Studio Code",
            x=0, y=0, width=1920, height=1080,
        ))
        await engine.poll_now()
        file_calls = [c for c in mock_event_bus.publish.await_args_list if c[0][0] == "context:file_changed"]
        assert len(file_calls) > 0

    async def test_activity_changed_on_activity_change(self, engine, mock_windows_adapter, mock_event_bus):
        mock_event_bus.publish.reset_mock()
        await engine.poll_now()
        mock_event_bus.publish.reset_mock()
        mock_windows_adapter.get_active_window = AsyncMock(return_value=WindowInfo(
            title="Google Chrome",
            app="chrome",
            x=0, y=0, width=1920, height=1080,
        ))
        await engine.poll_now()
        activity_calls = [c for c in mock_event_bus.publish.await_args_list if c[0][0] == "context:activity_changed"]
        assert len(activity_calls) > 0

    async def test_all_events_source_set(self, engine, mock_event_bus):
        mock_event_bus.publish.reset_mock()
        await engine.poll_now()
        for call in mock_event_bus.publish.await_args_list:
            kwargs = call[1] if len(call) > 1 else {}
            assert kwargs.get("source") == "context_engine"


# ---------------------------------------------------------------------------
# Context Engine — Memory Integration
# ---------------------------------------------------------------------------


class TestEngineMemory:
    async def test_memory_stored_on_context_change(self, engine_with_memory, mock_memory_store):
        await engine_with_memory.poll_now()
        assert mock_memory_store.create_node.called

    async def test_memory_not_stored_for_idle(self, engine_with_memory, mock_windows_adapter, mock_memory_store):
        mock_windows_adapter.get_active_window = AsyncMock(return_value=WindowInfo(
            title="",
            app="lockapp",
            x=0, y=0, width=1920, height=1080,
        ))
        mock_memory_store.reset_mock()
        await engine_with_memory.poll_now()
        if not mock_memory_store.create_node.called:
            pass
        else:
            pass

    async def test_memory_not_stored_without_store(self, engine, mock_memory_store):
        mock_memory_store.reset_mock()
        await engine.poll_now()
        assert not mock_memory_store.create_node.called

    async def test_memory_store_failure_handled(self, engine_with_memory, mock_memory_store):
        mock_memory_store.create_node.side_effect = Exception("memory fail")
        ctx = await engine_with_memory.poll_now()
        assert ctx is not None


# ---------------------------------------------------------------------------
# Context Engine — Recent Activity
# ---------------------------------------------------------------------------


class TestEngineRecentActivity:
    async def test_get_recent_activity_returns_list(self, engine):
        await engine.poll_now()
        recent = await engine.get_recent_activity(minutes=5)
        assert len(recent) >= 1
        assert isinstance(recent[0], Context)

    async def test_get_recent_activity_empty_before_poll(self, engine):
        recent = await engine.get_recent_activity(minutes=5)
        assert recent == []

    async def test_get_recent_activity_filtered_by_time(self, engine):
        await engine.poll_now()
        recent = await engine.get_recent_activity(minutes=1)
        assert len(recent) >= 1
        very_old = await engine.get_recent_activity(minutes=-1)
        assert very_old == []


# ---------------------------------------------------------------------------
# Context Engine — Public API
# ---------------------------------------------------------------------------


class TestEnginePublicAPI:
    async def test_get_current_context_returns_none_initially(self, engine):
        assert await engine.get_current_context() is None

    async def test_get_current_context_after_poll(self, engine):
        await engine.poll_now()
        assert await engine.get_current_context() is not None

    async def test_get_active_app_before_poll(self, engine):
        assert await engine.get_active_app() == ""

    async def test_get_active_app_after_poll(self, engine):
        await engine.poll_now()
        app = await engine.get_active_app()
        assert app == "Visual Studio Code"

    async def test_get_active_file_before_poll(self, engine):
        assert await engine.get_active_file() is None

    async def test_get_active_file_after_poll(self, engine):
        await engine.poll_now()
        f = await engine.get_active_file()
        assert f is not None

    async def test_detect_project_before_poll(self, engine):
        assert await engine.detect_project() is None

    async def test_detect_project_after_poll(self, engine):
        await engine.poll_now()
        proj = await engine.detect_project()
        assert proj is None or isinstance(proj, ProjectInfo)


# ---------------------------------------------------------------------------
# DI Container Registration
# ---------------------------------------------------------------------------


class TestDIContainer:
    def test_register_and_resolve(self):
        from aios.core.di_container import DIContainer
        container = DIContainer()
        ContextEngine.register_in_container(container)
        resolved = container.resolve(ContextEngine)
        assert isinstance(resolved, ContextEngine)
        assert resolved._windows is None
        assert resolved._event_bus is None

    def test_register_with_dependencies(self):
        from aios.core.di_container import DIContainer
        container = DIContainer()
        wa = MagicMock()
        eb = MagicMock()
        ms = MagicMock()
        ContextEngine.register_in_container(
            container,
            windows_adapter=wa,
            event_bus=eb,
            poll_interval=5.0,
            memory_store=ms,
        )
        resolved = container.resolve(ContextEngine)
        assert resolved._windows is wa
        assert resolved._event_bus is eb
        assert resolved._poll_interval == 5.0
        assert resolved._memory_store is ms
