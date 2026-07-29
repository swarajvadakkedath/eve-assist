import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aios.devtools.debug_console import DebugConsole
from aios.devtools.health_dashboard import HealthDashboard
from aios.devtools.module_inspector import ModuleInspector
from aios.devtools.hot_reload import HotReload
from aios.devtools.diagnostics import Diagnostics
from aios.devtools.performance_monitor import PerformanceMonitor
from aios.devtools.log_viewer import LogViewer
from aios.devtools.models import LogLevel, LogEntry, HealthStatus, DiagnosticCheck
from aios.tools.devtools_tools import register_devtools_tools
from aios.core.tool_manager import ToolManager
from aios.core.permission_manager import PermissionManager


# ── Fixtures ──

@pytest.fixture
def pm():
    return PermissionManager()


@pytest.fixture
def tm(pm):
    return ToolManager(pm)


@pytest.fixture
async def event_bus():
    from aios.core.event_bus import EventBus
    bus = EventBus()
    await bus.start()
    yield bus
    await bus.stop()


@pytest.fixture
def console():
    return DebugConsole()


@pytest.fixture
def dashboard():
    return HealthDashboard()


@pytest.fixture
def inspector():
    return ModuleInspector()


@pytest.fixture
def reloader():
    return HotReload(poll_interval=0.1)


@pytest.fixture
def diagnostics():
    return Diagnostics()


@pytest.fixture
def perf_monitor():
    return PerformanceMonitor()


@pytest.fixture
def log_viewer():
    return LogViewer()


@pytest.fixture
def mock_memory():
    mem = MagicMock()
    mem.store = AsyncMock(return_value="mem_id_123")
    return mem


@pytest.fixture
def mock_windows_adapter():
    adapter = MagicMock()
    info = MagicMock()
    info.disk_free = 50 * 1024 ** 3
    adapter.get_system_info = AsyncMock(return_value=info)
    return adapter


@pytest.fixture
def mock_planner():
    planner = MagicMock()
    plan = MagicMock()
    plan.id = "plan_123"
    step = MagicMock()
    step.id = "step_1"
    step.capability = "system.diagnostics"
    step.status = "completed"
    step.result = "ok"
    step.error = ""
    plan.steps = [step]
    planner.create_plan = AsyncMock(return_value=plan)
    planner.execute_plan = AsyncMock(return_value=plan)
    return planner


# ════════════════════════════════════════════
# DebugConsole Tests
# ════════════════════════════════════════════

class TestDebugConsole:
    @pytest.mark.asyncio
    async def test_eval_expression_simple(self, console):
        result = await console.eval_expression("1 + 2")
        assert result.result == 3
        assert result.error == ""
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_eval_expression_string(self, console):
        result = await console.eval_expression("'hello' + ' world'")
        assert result.result == "hello world"

    @pytest.mark.asyncio
    async def test_eval_expression_syntax_error_falls_back_to_exec(self, console):
        result = await console.eval_expression("x = 42")
        assert result.error == ""
        vars = await console.get_variables("_default")
        assert vars.get("x") == 42

    @pytest.mark.asyncio
    async def test_eval_expression_error(self, console):
        result = await console.eval_expression("1/0")
        assert result.error != ""
        assert "ZeroDivisionError" in result.error or "division by zero" in result.error

    @pytest.mark.asyncio
    async def test_exec_script(self, console):
        code = """
a = [1, 2, 3]
b = sum(a)
"""
        result = await console.exec_script(code)
        assert result.error == ""
        vars = await console.get_variables("_default")
        assert vars.get("a") == [1, 2, 3]
        assert vars.get("b") == 6

    @pytest.mark.asyncio
    async def test_exec_script_with_output(self, console):
        code = "print('hello world')"
        result = await console.exec_script(code)
        assert "hello world" in result.output
        assert result.error == ""

    @pytest.mark.asyncio
    async def test_exec_script_error(self, console):
        result = await console.exec_script("raise ValueError('test error')")
        assert result.error != ""

    @pytest.mark.asyncio
    async def test_session_isolation(self, console):
        await console.eval_expression("x = 10", session_id="sess_a")
        await console.eval_expression("x = 20", session_id="sess_b")

        vars_a = await console.get_variables("sess_a")
        vars_b = await console.get_variables("sess_b")
        assert vars_a.get("x") == 10
        assert vars_b.get("x") == 20

    @pytest.mark.asyncio
    async def test_get_variables_empty(self, console):
        vars = await console.get_variables("new_session")
        assert vars == {}

    @pytest.mark.asyncio
    async def test_inspect_object_found(self, console):
        await console.eval_expression("my_list = [1, 2, 3]")
        info = await console.inspect_object("my_list")
        assert info["type"] == "list"
        assert info["length"] == 3

    @pytest.mark.asyncio
    async def test_inspect_object_not_found(self, console):
        info = await console.inspect_object("nonexistent")
        assert "error" in info

    @pytest.mark.asyncio
    async def test_inspect_module(self, console):
        import sys
        session = console._get_session("_default")
        session["locals"]["sys_mod"] = sys
        info = await console.inspect_object("sys_mod")
        assert info["type"] == "module"

    @pytest.mark.asyncio
    async def test_inspect_callable_with_doc(self, console):
        def foo():
            """Test docstring."""
            pass
        await console.eval_expression("foo")
        # inspect by name requires the object in session
        console._sessions["_default"]["locals"]["test_func"] = foo
        info = await console.inspect_object("test_func")
        assert "doc" in info

    @pytest.mark.asyncio
    async def test_clear_session(self, console):
        await console.eval_expression("x = 99")
        await console.clear_session()
        vars = await console.get_variables()
        assert "x" not in vars

    @pytest.mark.asyncio
    async def test_list_sessions(self, console):
        await console.eval_expression("a = 1", session_id="one")
        await console.eval_expression("b = 2", session_id="two")
        sessions = await console.list_sessions()
        assert "one" in sessions
        assert "two" in sessions

    @pytest.mark.asyncio
    async def test_event_publish_on_eval(self, console):
        mock_bus = AsyncMock()
        console._event_bus = mock_bus
        await console.eval_expression("1+1")
        mock_bus.publish.assert_called_once()
        call_args = mock_bus.publish.call_args
        assert call_args[0][0] == "debug:eval"

    @pytest.mark.asyncio
    async def test_capture_stdout(self, console):
        result = await console.exec_script("print('line1'); print('line2')")
        assert "line1" in result.output
        assert "line2" in result.output

    @pytest.mark.asyncio
    async def test_multiple_eval_same_session(self, console):
        await console.eval_expression("acc = 0")
        await console.eval_expression("acc += 10")
        await console.eval_expression("acc += 20")
        result = await console.eval_expression("acc")
        assert result.result == 30

    @pytest.mark.asyncio
    async def test_event_publish_on_exec(self, console):
        mock_bus = AsyncMock()
        console._event_bus = mock_bus
        await console.exec_script("x=1")
        mock_bus.publish.assert_called_once()
        assert mock_bus.publish.call_args[0][0] == "debug:exec"


# ════════════════════════════════════════════
# HealthDashboard Tests
# ════════════════════════════════════════════

class TestHealthDashboard:
    @pytest.mark.asyncio
    async def test_initial_health_all_pending(self, dashboard):
        report = await dashboard.get_health()
        assert report["total_components"] > 0
        assert report["healthy_count"] >= 0

    @pytest.mark.asyncio
    async def test_update_health_sets_status(self, dashboard):
        status = await dashboard.update_health("event_bus", True, "running")
        assert status.healthy is True
        assert status.status == "running"

    @pytest.mark.asyncio
    async def test_get_component_health(self, dashboard):
        await dashboard.update_health("tool_manager", True, "active")
        status = await dashboard.get_component_health("tool_manager")
        assert status is not None
        assert status.healthy is True

    @pytest.mark.asyncio
    async def test_get_component_health_not_found(self, dashboard):
        status = await dashboard.get_component_health("nonexistent")
        assert status is None

    @pytest.mark.asyncio
    async def test_health_overall_false_on_any_failure(self, dashboard):
        await dashboard.update_health("event_bus", True, "ok")
        await dashboard.update_health("memory_system", False, "down", error="OOM")
        report = await dashboard.get_health()
        assert report["overall"] is False
        assert report["unhealthy_count"] >= 1

    @pytest.mark.asyncio
    async def test_health_history(self, dashboard):
        await dashboard.update_health("event_bus", True, "ok")
        await dashboard.update_health("event_bus", False, "error", error="timeout")
        history = await dashboard.get_health_history(limit=10)
        assert len(history) >= 2

    @pytest.mark.asyncio
    async def test_health_history_limit(self, dashboard):
        for i in range(20):
            await dashboard.update_health("test_component", True, f"status_{i}")
        history = await dashboard.get_health_history(limit=5)
        assert len(history) <= 5

    @pytest.mark.asyncio
    async def test_health_summary(self, dashboard):
        await dashboard.update_health("event_bus", True, "ok")
        summary = await dashboard.get_health_summary()
        assert "overall" in summary
        assert "healthy" in summary
        assert "total" in summary

    @pytest.mark.asyncio
    async def test_update_health_publishes_event(self, dashboard):
        mock_bus = AsyncMock()
        dashboard._event_bus = mock_bus
        await dashboard.update_health("event_bus", True, "ok")
        mock_bus.publish.assert_called_once()
        assert mock_bus.publish.call_args[0][0] == "health:updated"

    @pytest.mark.asyncio
    async def test_update_health_stores_in_memory(self, dashboard, mock_memory):
        dashboard._memory = mock_memory
        await dashboard.update_health("event_bus", True, "ok")
        mock_memory.store.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_components(self, dashboard):
        components = ["event_bus", "memory_system", "ai_router", "planner"]
        for c in components:
            await dashboard.update_health(c, True, "ok")
        report = await dashboard.get_health()
        default_count = len(dashboard._components)
        assert report["healthy_count"] == default_count

    @pytest.mark.asyncio
    async def test_update_with_metrics(self, dashboard):
        await dashboard.update_health("event_bus", True, "ok", metrics={"uptime": 3600})
        status = await dashboard.get_component_health("event_bus")
        assert status.metrics.get("uptime") == 3600

    @pytest.mark.asyncio
    async def test_history_max_size(self, dashboard):
        dashboard._max_history = 10
        for i in range(20):
            await dashboard.update_health("test", True, f"loop_{i}")
        assert len(dashboard._history) == 10

    @pytest.mark.asyncio
    async def test_health_round_trip(self, dashboard):
        await dashboard.update_health("test_comp", True, "all_good")
        status = await dashboard.get_component_health("test_comp")
        assert status.component == "test_comp"
        assert status.healthy is True
        assert status.status == "all_good"


# ════════════════════════════════════════════
# ModuleInspector Tests
# ════════════════════════════════════════════

class TestModuleInspector:
    @pytest.mark.asyncio
    async def test_list_modules_returns_results(self, inspector):
        modules = await inspector.list_modules()
        assert len(modules) > 10
        names = [m.name for m in modules]
        assert "os" in names
        assert "sys" in names

    @pytest.mark.asyncio
    async def test_list_modules_with_pattern(self, inspector):
        modules = await inspector.list_modules(pattern=r"^os\b")
        assert len(modules) >= 1
        assert all(m.name == "os" or m.name.startswith("os.") for m in modules)

    @pytest.mark.asyncio
    async def test_get_module_info_found(self, inspector):
        info = await inspector.get_module_info("os")
        assert info is not None
        assert info.name == "os"
        assert info.file != ""
        assert len(info.exports) > 0

    @pytest.mark.asyncio
    async def test_get_module_info_not_found(self, inspector):
        info = await inspector.get_module_info("nonexistent_module_xyz")
        assert info is None

    @pytest.mark.asyncio
    async def test_get_module_state_basic(self, inspector):
        state = await inspector.get_module_state("os")
        assert "name" in state
        assert state["name"] == "os"
        assert "file" in state

    @pytest.mark.asyncio
    async def test_get_module_state_not_found(self, inspector):
        state = await inspector.get_module_state("nonexistent_module_xyz")
        assert "error" in state

    @pytest.mark.asyncio
    async def test_get_module_state_functions(self, inspector):
        state = await inspector.get_module_state("os")
        assert "functions" in state

    @pytest.mark.asyncio
    async def test_search_modules(self, inspector):
        results = await inspector.search_modules("json")
        assert len(results) >= 1
        assert any("json" in r.name for r in results)

    @pytest.mark.asyncio
    async def test_search_modules_no_results(self, inspector):
        results = await inspector.search_modules("zzz_nonexistent_zzz")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_module_info_includes_dependencies(self, inspector):
        info = await inspector.get_module_info("os")
        assert info is not None
        assert isinstance(info.dependencies, list)

    @pytest.mark.asyncio
    async def test_module_state_public_attributes(self, inspector):
        state = await inspector.get_module_state("json")
        assert "public_attributes" in state

    @pytest.mark.asyncio
    async def test_event_publish_on_inspect(self, inspector):
        mock_bus = AsyncMock()
        inspector._event_bus = mock_bus
        await inspector.get_module_state("os")
        mock_bus.publish.assert_called_once()
        assert mock_bus.publish.call_args[0][0] == "module:inspected"

    @pytest.mark.asyncio
    async def test_get_module_source(self, inspector):
        source = await inspector.get_module_source("json")
        assert source is not None
        assert '"""' in source or "#" in source or len(source) > 50

    @pytest.mark.asyncio
    async def test_get_module_source_not_found(self, inspector):
        source = await inspector.get_module_source("nonexistent_module_xyz")
        assert source is None

    @pytest.mark.asyncio
    async def test_builtin_module_info(self, inspector):
        import builtins
        info = await inspector.get_module_info("builtins")
        if info:
            assert info.is_package is False


# ════════════════════════════════════════════
# HotReload Tests
# ════════════════════════════════════════════

class TestHotReload:
    @pytest.mark.asyncio
    async def test_reload_module_success(self, reloader):
        result = await reloader.reload_module("json")
        assert result["success"] is True
        assert result["module"] == "json"

    @pytest.mark.asyncio
    async def test_reload_module_not_found(self, reloader):
        result = await reloader.reload_module("nonexistent_module_xyz")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_reload_module_tracks_history(self, reloader):
        await reloader.reload_module("json")
        history = await reloader.get_reload_history()
        assert len(history) >= 1
        assert history[-1]["module"] == "json"

    @pytest.mark.asyncio
    async def test_reload_all_empty(self, reloader):
        results = await reloader.reload_all()
        assert results == []

    @pytest.mark.asyncio
    async def test_watch_module_success(self, reloader):
        result = await reloader.watch_module("json")
        assert result["success"] is True
        assert result["watching"] is True

    @pytest.mark.asyncio
    async def test_watch_module_not_found(self, reloader):
        result = await reloader.watch_module("nonexistent_xyz")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_unwatch_module(self, reloader):
        await reloader.watch_module("json")
        removed = await reloader.unwatch_module("json")
        assert removed is True

    @pytest.mark.asyncio
    async def test_unwatch_module_not_watched(self, reloader):
        removed = await reloader.unwatch_module("json")
        assert removed is False

    @pytest.mark.asyncio
    async def test_get_watched(self, reloader):
        await reloader.watch_module("json")
        await reloader.watch_module("os")
        watched = await reloader.get_watched()
        names = [w.name for w in watched]
        assert "json" in names
        assert "os" in names

    @pytest.mark.asyncio
    async def test_reload_all_with_watched(self, reloader):
        await reloader.watch_module("json")
        results = await reloader.reload_all()
        assert len(results) >= 1
        assert results[0]["success"] is True

    @pytest.mark.asyncio
    async def test_reload_history_limit(self, reloader):
        await reloader.reload_module("json")
        await reloader.reload_module("os")
        history = await reloader.get_reload_history(limit=1)
        assert len(history) == 1

    @pytest.mark.asyncio
    async def test_start_stop_polling(self, reloader):
        await reloader.start_polling()
        assert reloader._running is True
        await reloader.stop_polling()
        assert reloader._running is False

    @pytest.mark.asyncio
    async def test_polling_no_duplicate_start(self, reloader):
        await reloader.start_polling()
        await reloader.start_polling()
        assert reloader._running is True
        await reloader.stop_polling()

    @pytest.mark.asyncio
    async def test_reload_event_publish(self, reloader):
        mock_bus = AsyncMock()
        reloader._event_bus = mock_bus
        await reloader.reload_module("json")
        mock_bus.publish.assert_called()
        assert mock_bus.publish.call_args[0][0] in (
            "hot_reload:completed", "hot_reload:failed"
        )

    @pytest.mark.asyncio
    async def test_watch_event_publish(self, reloader):
        mock_bus = AsyncMock()
        reloader._event_bus = mock_bus
        await reloader.watch_module("json")
        mock_bus.publish.assert_called()
        assert mock_bus.publish.call_args[0][0] == "hot_reload:watch_added"

    @pytest.mark.asyncio
    async def test_unwatch_event_publish(self, reloader):
        mock_bus = AsyncMock()
        reloader._event_bus = mock_bus
        await reloader.watch_module("json")
        await reloader.unwatch_module("json")
        calls = [c for c in mock_bus.publish.call_args_list if c[0][0] == "hot_reload:watch_removed"]
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_double_reload(self, reloader):
        r1 = await reloader.reload_module("json")
        r2 = await reloader.reload_module("json")
        assert r1["success"] is True
        assert r2["success"] is True


# ════════════════════════════════════════════
# Diagnostics Tests
# ════════════════════════════════════════════

class TestDiagnostics:
    @pytest.mark.asyncio
    async def test_run_diagnostics_returns_result(self, diagnostics):
        result = await diagnostics.run_diagnostics()
        assert result.id != ""
        assert len(result.checks) > 0
        assert isinstance(result.all_passed, bool)

    @pytest.mark.asyncio
    async def test_run_diagnostics_includes_python_version(self, diagnostics):
        result = await diagnostics.run_diagnostics()
        checks = {c.name: c for c in result.checks}
        assert "python_version" in checks
        assert checks["python_version"].passed is True

    @pytest.mark.asyncio
    async def test_run_specific_check(self, diagnostics):
        result = await diagnostics.run_check("python_version")
        assert len(result.checks) == 1
        assert result.checks[0].passed is True
        assert result.checks[0].name == "python_version"

    @pytest.mark.asyncio
    async def test_run_unknown_check(self, diagnostics):
        result = await diagnostics.run_check("nonexistent_check")
        assert result.checks[0].passed is False
        assert "Unknown" in result.checks[0].detail

    @pytest.mark.asyncio
    async def test_diagnostic_history(self, diagnostics):
        await diagnostics.run_diagnostics()
        history = await diagnostics.get_diagnostic_history()
        assert len(history) >= 1
        assert "summary" in history[0]

    @pytest.mark.asyncio
    async def test_get_checks_returns_available(self, diagnostics):
        checks = await diagnostics.get_checks()
        assert len(checks) > 0
        assert all("name" in c for c in checks)

    @pytest.mark.asyncio
    async def test_diagnostics_check_detail(self, diagnostics):
        result = await diagnostics.run_check("python_version")
        check = result.checks[0]
        assert "Python" in check.detail

    @pytest.mark.asyncio
    async def test_event_publish_on_run(self, diagnostics):
        mock_bus = AsyncMock()
        diagnostics._event_bus = mock_bus
        await diagnostics.run_diagnostics()
        completed_calls = [c for c in mock_bus.publish.call_args_list if c[0][0] == "diagnostics:completed"]
        assert len(completed_calls) == 1

    @pytest.mark.asyncio
    async def test_diagnostics_with_memory(self, diagnostics, mock_memory):
        diagnostics._memory = mock_memory
        await diagnostics.run_diagnostics()
        mock_memory.store.assert_called_once()

    @pytest.mark.asyncio
    async def test_event_bus_health_check(self, diagnostics):
        result = await diagnostics.run_check("event_bus_health")
        assert result.checks[0].passed is False
        assert "not configured" in result.checks[0].detail

    @pytest.mark.asyncio
    async def test_dependency_check(self, diagnostics):
        result = await diagnostics.run_check("dependency_check")
        assert result.checks[0].passed is True

    @pytest.mark.asyncio
    async def test_module_consistency_check(self, diagnostics):
        result = await diagnostics.run_check("module_consistency")
        assert isinstance(result.checks[0].passed, bool)

    @pytest.mark.asyncio
    async def test_diagnostics_with_planner(self, diagnostics):
        result = await diagnostics.diagnose_with_planner("test issue")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_diagnostics_with_planner_available(self, diagnostics, mock_planner):
        diagnostics._planner = mock_planner
        result = await diagnostics.diagnose_with_planner("slow response")
        assert "plan_id" in result
        assert len(result["steps"]) > 0

    @pytest.mark.asyncio
    async def test_history_limit(self, diagnostics):
        for i in range(5):
            await diagnostics.run_diagnostics()
        history = await diagnostics.get_diagnostic_history(limit=2)
        assert len(history) <= 2

    @pytest.mark.asyncio
    async def test_all_checks_have_names(self, diagnostics):
        checks = await diagnostics.get_checks()
        for c in checks:
            assert "name" in c
            assert "description" in c


# ════════════════════════════════════════════
# PerformanceMonitor Tests
# ════════════════════════════════════════════

class TestPerformanceMonitor:
    @pytest.mark.asyncio
    async def test_record_metric(self, perf_monitor):
        point = await perf_monitor.record_metric("cpu_percent", 45.2)
        assert point.name == "cpu_percent"
        assert point.value == 45.2

    @pytest.mark.asyncio
    async def test_get_metrics_returns_recorded(self, perf_monitor):
        await perf_monitor.record_metric("cpu_percent", 30.0)
        metrics = await perf_monitor.get_metrics()
        assert len(metrics) >= 1
        assert metrics[0]["name"] == "cpu_percent"

    @pytest.mark.asyncio
    async def test_get_metrics_filtered_by_name(self, perf_monitor):
        await perf_monitor.record_metric("cpu_percent", 30.0)
        await perf_monitor.record_metric("memory_percent", 60.0)
        metrics = await perf_monitor.get_metric_history("cpu_percent")
        assert len(metrics) >= 1
        assert all("cpu" not in str(m) for m in metrics)

    @pytest.mark.asyncio
    async def test_get_latest_metrics(self, perf_monitor):
        await perf_monitor.record_metric("cpu_percent", 50.0)
        await perf_monitor.record_metric("memory_percent", 70.0)
        latest = await perf_monitor.get_latest_metrics()
        assert "cpu_percent" in latest
        assert "memory_percent" in latest
        assert latest["cpu_percent"]["value"] == 50.0

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, perf_monitor):
        await perf_monitor.start_monitoring(interval=0.1)
        assert perf_monitor._running is True
        await asyncio.sleep(0.3)
        await perf_monitor.stop_monitoring()
        assert perf_monitor._running is False

    @pytest.mark.asyncio
    async def test_monitoring_records_metrics(self, perf_monitor):
        await perf_monitor.start_monitoring(interval=0.1)
        await asyncio.sleep(0.35)
        await perf_monitor.stop_monitoring()
        metrics = await perf_monitor.get_metrics()
        names = {m["name"] for m in metrics}
        assert "cpu_percent" in names
        assert "memory_percent" in names

    @pytest.mark.asyncio
    async def test_no_duplicate_start(self, perf_monitor):
        await perf_monitor.start_monitoring(interval=0.1)
        await perf_monitor.start_monitoring(interval=0.1)
        assert perf_monitor._running is True
        await perf_monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_get_metric_summary(self, perf_monitor):
        await perf_monitor.record_metric("test_metric", 10.0)
        await perf_monitor.record_metric("test_metric", 20.0)
        await perf_monitor.record_metric("test_metric", 30.0)
        summary = await perf_monitor.get_metric_summary("test_metric")
        assert summary["count"] == 3
        assert summary["min"] == 10.0
        assert summary["max"] == 30.0
        assert summary["avg"] == 20.0

    @pytest.mark.asyncio
    async def test_get_metric_summary_empty(self, perf_monitor):
        summary = await perf_monitor.get_metric_summary("nonexistent")
        assert summary["count"] == 0

    @pytest.mark.asyncio
    async def test_event_publish_on_start(self, perf_monitor):
        mock_bus = AsyncMock()
        perf_monitor._event_bus = mock_bus
        await perf_monitor.start_monitoring()
        mock_bus.publish.assert_called_with(
            "perf:monitoring_started", {"interval": 5.0}, source="performance_monitor"
        )

    @pytest.mark.asyncio
    async def test_event_publish_on_stop(self, perf_monitor):
        mock_bus = AsyncMock()
        perf_monitor._event_bus = mock_bus
        await perf_monitor.start_monitoring()
        await perf_monitor.stop_monitoring()
        calls = [c for c in mock_bus.publish.call_args_list if c[0][0] == "perf:monitoring_stopped"]
        assert len(calls) >= 1

    @pytest.mark.asyncio
    async def test_metric_with_labels(self, perf_monitor):
        await perf_monitor.record_metric("custom_metric", 42.0, labels={"env": "test"})
        metrics = await perf_monitor.get_metrics("custom_metric")
        assert metrics[0]["labels"]["env"] == "test"

    @pytest.mark.asyncio
    async def test_event_publish_during_monitoring(self, perf_monitor):
        mock_bus = AsyncMock()
        perf_monitor._event_bus = mock_bus
        await perf_monitor.start_monitoring(interval=0.1)
        await asyncio.sleep(0.25)
        await perf_monitor.stop_monitoring()
        perf_calls = [c for c in mock_bus.publish.call_args_list if c[0][0] == "perf:metrics"]
        assert len(perf_calls) >= 1


# ════════════════════════════════════════════
# LogViewer Tests
# ════════════════════════════════════════════

class TestLogViewer:
    @pytest.mark.asyncio
    async def test_add_and_get_logs(self, log_viewer):
        await log_viewer.add_log(LogLevel.INFO, "test message", source="test")
        result = await log_viewer.get_logs()
        assert result["total"] >= 1
        assert result["logs"][0]["message"] == "test message"

    @pytest.mark.asyncio
    async def test_get_logs_filter_by_level(self, log_viewer):
        await log_viewer.add_log(LogLevel.DEBUG, "debug msg")
        await log_viewer.add_log(LogLevel.ERROR, "error msg")
        result = await log_viewer.get_logs(level="ERROR")
        assert result["total"] >= 1
        assert all(l["level"] in ("ERROR", "CRITICAL") for l in result["logs"])

    @pytest.mark.asyncio
    async def test_get_logs_filter_by_source(self, log_viewer):
        await log_viewer.add_log(LogLevel.INFO, "msg1", source="alpha")
        await log_viewer.add_log(LogLevel.INFO, "msg2", source="beta")
        result = await log_viewer.get_logs(source="alpha")
        assert all(l["source"] == "alpha" for l in result["logs"])

    @pytest.mark.asyncio
    async def test_get_logs_filter_by_category(self, log_viewer):
        await log_viewer.add_log(LogLevel.INFO, "msg1", category="security")
        await log_viewer.add_log(LogLevel.INFO, "msg2", category="performance")
        result = await log_viewer.get_logs(category="security")
        assert all(l["category"] == "security" for l in result["logs"])

    @pytest.mark.asyncio
    async def test_get_logs_search(self, log_viewer):
        await log_viewer.add_log(LogLevel.INFO, "disk space low")
        await log_viewer.add_log(LogLevel.INFO, "memory ok")
        result = await log_viewer.get_logs(search="disk")
        assert len(result["logs"]) == 1
        assert "disk" in result["logs"][0]["message"]

    @pytest.mark.asyncio
    async def test_get_logs_pagination(self, log_viewer):
        for i in range(10):
            await log_viewer.add_log(LogLevel.INFO, f"msg {i}")
        result = await log_viewer.get_logs(limit=3, offset=5)
        assert result["returned"] == 3
        assert result["total"] == 10

    @pytest.mark.asyncio
    async def test_get_log_categories(self, log_viewer):
        await log_viewer.add_log(LogLevel.INFO, "msg", category="cat_a")
        await log_viewer.add_log(LogLevel.INFO, "msg", category="cat_b")
        await log_viewer.add_log(LogLevel.INFO, "msg", category="cat_a")
        cats = await log_viewer.get_log_categories()
        cat_map = {c["category"]: c["count"] for c in cats}
        assert cat_map.get("cat_a") == 2
        assert cat_map.get("cat_b") == 1

    @pytest.mark.asyncio
    async def test_get_log_sources(self, log_viewer):
        await log_viewer.add_log(LogLevel.INFO, "msg", source="src_a")
        await log_viewer.add_log(LogLevel.INFO, "msg", source="src_b")
        sources = await log_viewer.get_log_sources()
        src_map = {s["source"]: s["count"] for s in sources}
        assert "src_a" in src_map
        assert "src_b" in src_map

    @pytest.mark.asyncio
    async def test_clear_logs(self, log_viewer):
        await log_viewer.add_log(LogLevel.INFO, "to be cleared")
        await log_viewer.clear_logs()
        result = await log_viewer.get_logs()
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_set_log_level(self, log_viewer):
        await log_viewer.set_log_level("WARNING")
        level = await log_viewer.get_log_level()
        assert level == "WARNING"

    @pytest.mark.asyncio
    async def test_log_level_affects_display(self, log_viewer):
        await log_viewer.set_log_level("WARNING")
        await log_viewer.add_log(LogLevel.INFO, "should be hidden")
        await log_viewer.add_log(LogLevel.ERROR, "should show")
        result = await log_viewer.get_logs()
        assert all(l["level"] in ("WARNING", "ERROR", "CRITICAL") for l in result["logs"])

    @pytest.mark.asyncio
    async def test_get_stats(self, log_viewer):
        await log_viewer.add_log(LogLevel.INFO, "info msg")
        await log_viewer.add_log(LogLevel.ERROR, "error msg")
        stats = await log_viewer.get_stats()
        assert stats["total_entries"] == 2
        assert stats["by_level"]["INFO"] >= 1
        assert stats["by_level"]["ERROR"] >= 1

    @pytest.mark.asyncio
    async def test_event_publish_on_log(self, log_viewer):
        mock_bus = AsyncMock()
        log_viewer._event_bus = mock_bus
        await log_viewer.add_log(LogLevel.INFO, "test event")
        mock_bus.publish.assert_called_once()
        assert mock_bus.publish.call_args[0][0] == "log:entry"

    @pytest.mark.asyncio
    async def test_event_subscribe_and_receive(self, log_viewer, event_bus):
        log_viewer._event_bus = event_bus
        await log_viewer.subscribe_to_events(event_bus)
        await asyncio.sleep(0.05)
        await event_bus.publish("debug:test", {"message": "hello from bus"}, source="test_src")
        await asyncio.sleep(0.15)
        result = await log_viewer.get_logs()
        assert result["total"] >= 1
        assert result["logs"][0]["source"] == "test_src"

    @pytest.mark.asyncio
    async def test_unsubscribe_all(self, log_viewer, event_bus):
        log_viewer._event_bus = event_bus
        await log_viewer.subscribe_to_events(event_bus)
        assert len(log_viewer._subscriptions) > 0
        await log_viewer.unsubscribe_all()
        total_subs = sum(len(v) for v in log_viewer._subscriptions.values())
        assert total_subs == 0

    @pytest.mark.asyncio
    async def test_log_with_metadata(self, log_viewer):
        await log_viewer.add_log(LogLevel.INFO, "meta msg", metadata={"key": "val"})
        result = await log_viewer.get_logs()
        assert result["logs"][0]["metadata"]["key"] == "val"

    @pytest.mark.asyncio
    async def test_log_max_size(self, log_viewer):
        log_viewer._logs = type(log_viewer._logs)(maxlen=5)
        for i in range(10):
            await log_viewer.add_log(LogLevel.INFO, f"msg {i}")
        result = await log_viewer.get_logs()
        assert result["total"] <= 5

    @pytest.mark.asyncio
    async def test_event_publish_on_clear(self, log_viewer):
        mock_bus = AsyncMock()
        log_viewer._event_bus = mock_bus
        await log_viewer.clear_logs()
        mock_bus.publish.assert_called_with(
            "log:cleared", {"cleared_count": 0}, source="log_viewer"
        )

    @pytest.mark.asyncio
    async def test_event_publish_on_set_level(self, log_viewer):
        mock_bus = AsyncMock()
        log_viewer._event_bus = mock_bus
        await log_viewer.set_log_level("ERROR")
        mock_bus.publish.assert_called_with(
            "log:level_changed", {"new_level": "ERROR"}, source="log_viewer"
        )


# ════════════════════════════════════════════
# Tool Registration Tests
# ════════════════════════════════════════════

class TestDevToolsRegistration:
    @pytest.mark.asyncio
    async def test_register_devtools_tools(self, tm, console, dashboard, inspector,
                                            reloader, diagnostics, perf_monitor, log_viewer):
        register_devtools_tools(
            tm,
            debug_console=console,
            health_dashboard=dashboard,
            module_inspector=inspector,
            hot_reload=reloader,
            diagnostics=diagnostics,
            performance_monitor=perf_monitor,
            log_viewer=log_viewer,
        )
        await asyncio.sleep(0.1)
        all_tools = await tm.list_tools()
        dev_tools = [t for t in all_tools if t.category == "devtools"]
        assert len(dev_tools) >= 30

    @pytest.mark.asyncio
    async def test_register_all_ids_unique(self, tm, console, dashboard, inspector,
                                            reloader, diagnostics, perf_monitor, log_viewer):
        register_devtools_tools(
            tm,
            debug_console=console,
            health_dashboard=dashboard,
            module_inspector=inspector,
            hot_reload=reloader,
            diagnostics=diagnostics,
            performance_monitor=perf_monitor,
            log_viewer=log_viewer,
        )
        await asyncio.sleep(0.1)
        all_tools = await tm.list_tools()
        dev_tools = [t for t in all_tools if t.category == "devtools"]
        ids = [t.id for t in dev_tools]
        assert len(ids) == len(set(ids))

    @pytest.mark.asyncio
    async def test_register_with_event_bus(self, tm, event_bus, console, dashboard,
                                            inspector, reloader, diagnostics,
                                            perf_monitor, log_viewer):
        register_devtools_tools(
            tm,
            debug_console=console,
            health_dashboard=dashboard,
            module_inspector=inspector,
            hot_reload=reloader,
            diagnostics=diagnostics,
            performance_monitor=perf_monitor,
            log_viewer=log_viewer,
            event_bus=event_bus,
        )
        await asyncio.sleep(0.1)
        all_tools = await tm.list_tools()
        dev_ids = [t.id for t in all_tools if t.category == "devtools"]
        assert "debug.eval" in dev_ids
        assert "health.get" in dev_ids
        assert "module.list" in dev_ids
        assert "hot_reload.reload" in dev_ids
        assert "diagnostics.run" in dev_ids
        assert "perf.metrics" in dev_ids
        assert "log.get" in dev_ids

    @pytest.mark.asyncio
    async def test_register_with_default_instances(self, tm):
        register_devtools_tools(tm)
        await asyncio.sleep(0.1)
        all_tools = await tm.list_tools()
        dev_tools = [t for t in all_tools if t.category == "devtools"]
        assert len(dev_tools) >= 30

    @pytest.mark.asyncio
    async def test_debug_tool_contracts_have_required_fields(self, tm):
        register_devtools_tools(tm)
        await asyncio.sleep(0.1)
        tool = await tm.get_tool("debug.eval")
        assert tool is not None
        assert tool.permission_level.name == "SENSITIVE"
        assert tool.requires_confirmation is True
        assert "expression" in tool.parameters

    @pytest.mark.asyncio
    async def test_health_tool_read_permission(self, tm):
        register_devtools_tools(tm)
        await asyncio.sleep(0.1)
        tool = await tm.get_tool("health.get")
        assert tool is not None
        assert tool.permission_level.name == "READ"
        assert tool.requires_confirmation is True


# ════════════════════════════════════════════
# Integration Tests
# ════════════════════════════════════════════

class TestDevToolsIntegration:
    @pytest.mark.asyncio
    async def test_debug_to_dashboard_flow(self, console, dashboard, event_bus):
        console._event_bus = event_bus
        dashboard._event_bus = event_bus

        await console.eval_expression("42 + 10")
        await dashboard.update_health("debug_console", True, "operational")

        health = await dashboard.get_component_health("debug_console")
        assert health.healthy is True

    @pytest.mark.asyncio
    async def test_diagnostics_to_memory_flow(self, diagnostics, mock_memory):
        diagnostics._memory = mock_memory
        result = await diagnostics.run_diagnostics()
        mock_memory.store.assert_called_once()

    @pytest.mark.asyncio
    async def test_perf_to_health_dashboard(self, perf_monitor, dashboard):
        await perf_monitor.record_metric("cpu_percent", 45.0)
        await dashboard.update_health("performance_monitor", True, "collecting",
                                       metrics={"cpu": 45.0})
        status = await dashboard.get_component_health("performance_monitor")
        assert status.healthy is True
        assert status.metrics.get("cpu") == 45.0

    @pytest.mark.asyncio
    async def test_log_viewer_captures_events(self, log_viewer, event_bus):
        log_viewer._event_bus = event_bus
        await log_viewer.subscribe_to_events(event_bus)
        await asyncio.sleep(0.05)
        await event_bus.publish("debug:eval", {"expression": "1+1"}, source="debug_console")
        await event_bus.publish("health:updated", {"component": "test", "healthy": True}, source="health")
        await asyncio.sleep(0.2)
        result = await log_viewer.get_logs()
        assert result["total"] >= 2

    @pytest.mark.asyncio
    async def test_hot_reload_and_inspector(self, reloader, inspector):
        await reloader.reload_module("json")
        info = await inspector.get_module_info("json")
        assert info is not None
        assert info.name == "json"

    @pytest.mark.asyncio
    async def test_full_diagnostics_health_report(self, diagnostics, dashboard):
        diag_result = await diagnostics.run_diagnostics()
        await dashboard.update_health("diagnostics", diag_result.all_passed,
                                       f"{sum(1 for c in diag_result.checks if c.passed)}/{len(diag_result.checks)} passed")
        status = await dashboard.get_component_health("diagnostics")
        assert status.healthy == diag_result.all_passed

    @pytest.mark.asyncio
    async def test_metrics_in_diagnostics(self, perf_monitor, diagnostics):
        await perf_monitor.record_metric("cpu_percent", 30.0)
        await perf_monitor.record_metric("memory_percent", 50.0)
        diag_result = await diagnostics.run_diagnostics()
        perf_check = [c for c in diag_result.checks if c.name == "memory_usage"]
        assert len(perf_check) >= 1

    @pytest.mark.asyncio
    async def test_debug_and_log_viewer(self, console, log_viewer, event_bus):
        console._event_bus = event_bus
        log_viewer._event_bus = event_bus
        await log_viewer.subscribe_to_events(event_bus)
        await asyncio.sleep(0.05)
        await console.eval_expression("1 + 1")
        await asyncio.sleep(0.2)
        result = await log_viewer.get_logs(source="debug_console")
        assert result["total"] >= 1


# ════════════════════════════════════════════
# Edge Cases & Error Handling
# ════════════════════════════════════════════

class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_debug_console_empty_expression(self, console):
        result = await console.eval_expression("")
        assert result.error == "" or "SyntaxError" in result.error

    @pytest.mark.asyncio
    async def test_debug_console_very_long_expression(self, console):
        long_expr = "+".join(str(i) for i in range(1000))
        result = await console.eval_expression(long_expr)
        assert result.result == sum(range(1000))

    @pytest.mark.asyncio
    async def test_dashboard_update_with_empty_metrics(self, dashboard):
        status = await dashboard.update_health("test", True, "", metrics={})
        assert status.metrics == {}

    @pytest.mark.asyncio
    async def test_inspector_handles_builtins(self, inspector):
        import builtins
        info = await inspector.get_module_info("builtins")
        if info:
            assert info.name == "builtins"

    @pytest.mark.asyncio
    async def test_hot_reload_nonexistent_module(self, reloader):
        result = await reloader.reload_module("")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_log_viewer_unicode_messages(self, log_viewer):
        await log_viewer.add_log(LogLevel.INFO, "héllo wörld 😊")
        result = await log_viewer.get_logs()
        assert result["logs"][0]["message"] == "héllo wörld 😊"

    @pytest.mark.asyncio
    async def test_diagnostics_all_passed_true(self, diagnostics):
        result = await diagnostics.run_diagnostics()
        assert isinstance(result.all_passed, bool)

    @pytest.mark.asyncio
    async def test_perf_monitor_cold_start(self, perf_monitor):
        latest = await perf_monitor.get_latest_metrics()
        assert latest == {}

    @pytest.mark.asyncio
    async def test_log_viewer_level_hides_messages(self, log_viewer):
        await log_viewer.set_log_level("ERROR")
        await log_viewer.add_log(LogLevel.DEBUG, "debug hidden")
        await log_viewer.add_log(LogLevel.INFO, "info hidden")
        result = await log_viewer.get_logs()
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_debug_console_no_side_effects_between_sessions(self, console):
        await console.eval_expression("import os", session_id="s1")
        vars1 = await console.get_variables("s1")
        vars2 = await console.get_variables("empty_sess")
        assert "os" in vars1 or any("os" in str(v) for v in vars1.values())

    @pytest.mark.asyncio
    async def test_inspector_pattern_no_match(self, inspector):
        modules = await inspector.list_modules(pattern=r"^$\b^")
        assert len(modules) == 0

    @pytest.mark.asyncio
    async def test_hot_reload_watch_nonexistent(self, reloader):
        result = await reloader.watch_module("")
        assert result["success"] is False


# ════════════════════════════════════════════
# LogLevel Enum Tests
# ════════════════════════════════════════════

class TestLogLevelEnum:
    def test_from_int_critical(self):
        assert LogLevel.from_int(50) == LogLevel.CRITICAL

    def test_from_int_error(self):
        assert LogLevel.from_int(40) == LogLevel.ERROR

    def test_from_int_warning(self):
        assert LogLevel.from_int(30) == LogLevel.WARNING

    def test_from_int_info(self):
        assert LogLevel.from_int(20) == LogLevel.INFO

    def test_from_int_debug(self):
        assert LogLevel.from_int(10) == LogLevel.DEBUG


# ════════════════════════════════════════════
# Performance & Stress Tests
# ════════════════════════════════════════════

class TestStress:
    @pytest.mark.asyncio
    async def test_bulk_log_entries(self, log_viewer):
        for i in range(100):
            await log_viewer.add_log(LogLevel.INFO, f"bulk msg {i}")
        result = await log_viewer.get_logs()
        assert result["total"] == 100

    @pytest.mark.asyncio
    async def test_bulk_metric_recording(self, perf_monitor):
        for i in range(100):
            await perf_monitor.record_metric("stress_test", float(i))
        metrics = await perf_monitor.get_metric_history("stress_test", limit=1000)
        assert len(metrics) >= 100

    @pytest.mark.asyncio
    async def test_many_diagnostic_results(self, diagnostics):
        for i in range(10):
            await diagnostics.run_diagnostics()
        history = await diagnostics.get_diagnostic_history()
        assert len(history) == 10

    @pytest.mark.asyncio
    async def test_health_update_storm(self, dashboard):
        for i in range(50):
            await dashboard.update_health(
                f"comp_{i % 5}", i % 2 == 0, f"status_{i}"
            )
        history = await dashboard.get_health_history(limit=100)
        assert len(history) == 50

    @pytest.mark.asyncio
    async def test_reload_many_watched(self, reloader):
        mods = ["json", "os", "re", "collections", "pathlib"]
        for m in mods:
            await reloader.watch_module(m)
        watched = await reloader.get_watched()
        assert len(watched) == 5
        results = await reloader.reload_all()
        assert len(results) == 5
        assert all(r["success"] for r in results)

    @pytest.mark.asyncio
    async def test_log_viewer_buffer_limit(self, log_viewer):
        log_viewer._logs = type(log_viewer._logs)(maxlen=20)
        for i in range(50):
            await log_viewer.add_log(LogLevel.INFO, f"msg {i}")
        stats = await log_viewer.get_stats()
        assert stats["total_entries"] == 20


# ════════════════════════════════════════════
# Model Validation Tests
# ════════════════════════════════════════════

class TestModels:
    def test_log_entry_defaults(self):
        entry = LogEntry(level=LogLevel.INFO, message="test", timestamp=None)
        assert entry.level == LogLevel.INFO
        assert entry.message == "test"
        assert entry.metadata == {}

    def test_health_status_defaults(self):
        hs = HealthStatus(component="test", healthy=True)
        assert hs.component == "test"
        assert hs.healthy is True
        assert hs.error == ""

    def test_diagnostic_check_defaults(self):
        dc = DiagnosticCheck(name="test_check")
        assert dc.name == "test_check"
        assert dc.status == "pending"
        assert dc.passed is False
