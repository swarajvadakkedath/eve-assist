"""Developer Tools (Sprint 20) — Debug Console, Health Dashboard, Module Inspector, Hot Reload, Diagnostics, Performance Monitor, Log Viewer."""

import asyncio
from typing import Any

from aios.core.tool_manager import ToolContract, ToolResult
from aios.core.permission_manager import PermissionLevel
from aios.devtools.debug_console import DebugConsole
from aios.devtools.health_dashboard import HealthDashboard
from aios.devtools.module_inspector import ModuleInspector
from aios.devtools.hot_reload import HotReload
from aios.devtools.diagnostics import Diagnostics
from aios.devtools.performance_monitor import PerformanceMonitor
from aios.devtools.log_viewer import LogViewer


# ── Debug Console ──

async def _debug_eval(params: dict, console: DebugConsole, event_bus=None) -> ToolResult:
    try:
        result = await console.eval_expression(
            expression=params.get("expression", ""),
            session_id=params.get("session_id", ""),
        )
        return ToolResult(success=not bool(result.error), data={
            "output": result.output, "result": str(result.result) if result.result is not None else None,
            "error": result.error, "duration_ms": result.duration_ms,
            "variables_count": len(result.variables),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _debug_exec(params: dict, console: DebugConsole, event_bus=None) -> ToolResult:
    try:
        result = await console.exec_script(
            code=params.get("code", ""),
            session_id=params.get("session_id", ""),
        )
        return ToolResult(success=not bool(result.error), data={
            "output": result.output, "error": result.error,
            "duration_ms": result.duration_ms, "variables_count": len(result.variables),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _debug_get_vars(params: dict, console: DebugConsole, event_bus=None) -> ToolResult:
    try:
        variables = await console.get_variables(session_id=params.get("session_id", ""))
        return ToolResult(success=True, data={
            "variables": {k: str(type(v).__name__) for k, v in variables.items()},
            "count": len(variables),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _debug_inspect(params: dict, console: DebugConsole, event_bus=None) -> ToolResult:
    try:
        info = await console.inspect_object(
            obj_name=params.get("name", ""),
            session_id=params.get("session_id", ""),
        )
        return ToolResult(success="error" not in info, data=info)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Health Dashboard ──

async def _health_get(params: dict, dashboard: HealthDashboard, event_bus=None) -> ToolResult:
    try:
        report = await dashboard.get_health()
        return ToolResult(success=True, data=report)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _health_get_component(params: dict, dashboard: HealthDashboard, event_bus=None) -> ToolResult:
    try:
        status = await dashboard.get_component_health(params.get("component", ""))
        if status is None:
            return ToolResult(success=False, error=f"Component '{params.get('component', '')}' not found")
        return ToolResult(success=True, data={
            "component": status.component, "healthy": status.healthy,
            "status": status.status, "error": status.error,
            "last_checked": status.last_checked.isoformat(),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _health_history(params: dict, dashboard: HealthDashboard, event_bus=None) -> ToolResult:
    try:
        history = await dashboard.get_health_history(limit=params.get("limit", 100))
        return ToolResult(success=True, data={"history": history, "count": len(history)})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _health_summary(params: dict, dashboard: HealthDashboard, event_bus=None) -> ToolResult:
    try:
        summary = await dashboard.get_health_summary()
        return ToolResult(success=True, data=summary)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Module Inspector ──

async def _module_list(params: dict, inspector: ModuleInspector, event_bus=None) -> ToolResult:
    try:
        modules = await inspector.list_modules(pattern=params.get("pattern", ""))
        return ToolResult(success=True, data={
            "modules": [
                {"name": m.name, "file": m.file, "is_package": m.is_package,
                 "exports_count": len(m.exports), "source_lines": m.source_lines}
                for m in modules
            ],
            "count": len(modules),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _module_info(params: dict, inspector: ModuleInspector, event_bus=None) -> ToolResult:
    try:
        info = await inspector.get_module_info(params.get("name", ""))
        if info is None:
            return ToolResult(success=False, error=f"Module '{params.get('name', '')}' not found")
        return ToolResult(success=True, data={
            "name": info.name, "file": info.file, "size": info.size,
            "is_package": info.is_package, "exports": info.exports,
            "dependencies": info.dependencies, "source_lines": info.source_lines,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _module_state(params: dict, inspector: ModuleInspector, event_bus=None) -> ToolResult:
    try:
        state = await inspector.get_module_state(params.get("name", ""))
        return ToolResult(success="error" not in state, data=state)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _module_search(params: dict, inspector: ModuleInspector, event_bus=None) -> ToolResult:
    try:
        modules = await inspector.search_modules(params.get("query", ""))
        return ToolResult(success=True, data={
            "modules": [{"name": m.name, "file": m.file, "is_package": m.is_package} for m in modules],
            "count": len(modules),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Hot Reload ──

async def _hot_reload(params: dict, reloader: HotReload, event_bus=None) -> ToolResult:
    try:
        result = await reloader.reload_module(params.get("name", ""))
        return ToolResult(success=result.get("success", False), data=result)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _hot_reload_all(params: dict, reloader: HotReload, event_bus=None) -> ToolResult:
    try:
        results = await reloader.reload_all()
        return ToolResult(success=True, data={
            "results": results, "count": len(results),
            "success_count": sum(1 for r in results if r.get("success")),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _hot_watch(params: dict, reloader: HotReload, event_bus=None) -> ToolResult:
    try:
        result = await reloader.watch_module(params.get("name", ""))
        return ToolResult(success=result.get("success", False), data=result)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _hot_unwatch(params: dict, reloader: HotReload, event_bus=None) -> ToolResult:
    try:
        removed = await reloader.unwatch_module(params.get("name", ""))
        return ToolResult(success=removed, data={"removed": removed, "module": params.get("name", "")})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _hot_list(params: dict, reloader: HotReload, event_bus=None) -> ToolResult:
    try:
        watched = await reloader.get_watched()
        return ToolResult(success=True, data={
            "watched": [
                {"name": w.name, "file_path": w.file_path, "auto_reload": w.auto_reload}
                for w in watched
            ],
            "count": len(watched),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _hot_history(params: dict, reloader: HotReload, event_bus=None) -> ToolResult:
    try:
        history = await reloader.get_reload_history(limit=params.get("limit", 50))
        return ToolResult(success=True, data={"history": history, "count": len(history)})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Diagnostics ──

async def _diagnostics_run(params: dict, diag: Diagnostics, event_bus=None) -> ToolResult:
    try:
        result = await diag.run_diagnostics()
        return ToolResult(success=result.all_passed, data={
            "result_id": result.id, "all_passed": result.all_passed,
            "summary": result.summary,
            "checks": [
                {"name": c.name, "passed": c.passed, "detail": c.detail, "duration_ms": c.duration_ms}
                for c in result.checks
            ],
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _diagnostics_check(params: dict, diag: Diagnostics, event_bus=None) -> ToolResult:
    try:
        result = await diag.run_check(params.get("name", ""))
        check = result.checks[0] if result.checks else None
        if check is None:
            return ToolResult(success=False, error="No check returned")
        return ToolResult(success=check.passed, data={
            "name": check.name, "passed": check.passed,
            "detail": check.detail, "duration_ms": check.duration_ms,
            "error": check.error,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _diagnostics_history(params: dict, diag: Diagnostics, event_bus=None) -> ToolResult:
    try:
        history = await diag.get_diagnostic_history(limit=params.get("limit", 50))
        return ToolResult(success=True, data={"history": history, "count": len(history)})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _diagnostics_checks(params: dict, diag: Diagnostics, event_bus=None) -> ToolResult:
    try:
        checks = await diag.get_checks()
        return ToolResult(success=True, data={"checks": checks, "count": len(checks)})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Performance Monitor ──

async def _perf_metrics(params: dict, monitor: PerformanceMonitor, event_bus=None) -> ToolResult:
    try:
        name = params.get("name", "")
        if name:
            metrics = await monitor.get_metric_history(name, limit=params.get("limit", 100))
        else:
            metrics = await monitor.get_metrics()
        return ToolResult(success=True, data={"metrics": metrics, "count": len(metrics)})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _perf_latest(params: dict, monitor: PerformanceMonitor, event_bus=None) -> ToolResult:
    try:
        latest = await monitor.get_latest_metrics()
        return ToolResult(success=True, data={"metrics": latest})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _perf_start(params: dict, monitor: PerformanceMonitor, event_bus=None) -> ToolResult:
    try:
        interval = params.get("interval", 5.0)
        await monitor.start_monitoring(interval=interval)
        return ToolResult(success=True, data={"monitoring": True, "interval": interval})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _perf_stop(params: dict, monitor: PerformanceMonitor, event_bus=None) -> ToolResult:
    try:
        await monitor.stop_monitoring()
        return ToolResult(success=True, data={"monitoring": False})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _perf_summary(params: dict, monitor: PerformanceMonitor, event_bus=None) -> ToolResult:
    try:
        summary = await monitor.get_metric_summary(params.get("name", ""))
        return ToolResult(success=True, data=summary)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Log Viewer ──

async def _log_get(params: dict, viewer: LogViewer, event_bus=None) -> ToolResult:
    try:
        result = await viewer.get_logs(
            level=params.get("level", ""),
            source=params.get("source", ""),
            category=params.get("category", ""),
            search=params.get("search", ""),
            limit=params.get("limit", 200),
            offset=params.get("offset", 0),
        )
        return ToolResult(success=True, data=result)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _log_categories(params: dict, viewer: LogViewer, event_bus=None) -> ToolResult:
    try:
        categories = await viewer.get_log_categories()
        return ToolResult(success=True, data={"categories": categories, "count": len(categories)})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _log_sources(params: dict, viewer: LogViewer, event_bus=None) -> ToolResult:
    try:
        sources = await viewer.get_log_sources()
        return ToolResult(success=True, data={"sources": sources, "count": len(sources)})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _log_clear(params: dict, viewer: LogViewer, event_bus=None) -> ToolResult:
    try:
        await viewer.clear_logs()
        return ToolResult(success=True, data={"cleared": True})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _log_set_level(params: dict, viewer: LogViewer, event_bus=None) -> ToolResult:
    try:
        await viewer.set_log_level(params.get("level", "INFO"))
        return ToolResult(success=True, data={"level": params.get("level", "INFO")})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _log_stats(params: dict, viewer: LogViewer, event_bus=None) -> ToolResult:
    try:
        stats = await viewer.get_stats()
        return ToolResult(success=True, data=stats)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Registration ──

def register_devtools_tools(tm, debug_console=None, health_dashboard=None,
                            module_inspector=None, hot_reload=None,
                            diagnostics=None, performance_monitor=None,
                            log_viewer=None, event_bus=None):
    debug_tools = [
        ToolContract(
            id="debug.eval", name="Debug Eval",
            description="Evaluate a Python expression in the debug console",
            parameters={
                "expression": {"type": "string", "description": "Python expression to evaluate"},
                "session_id": {"type": "string", "description": "Optional session ID", "required": False},
            },
            returns={"output": {"type": "string"}, "result": {"type": "string"},
                     "error": {"type": "string"}, "duration_ms": {"type": "number"}},
            permission_level=PermissionLevel.SENSITIVE,
            requires_confirmation=True,
            category="devtools",
            capabilities=["debug.eval"],
            tags=["debug", "console"],
        ),
        ToolContract(
            id="debug.exec", name="Debug Exec",
            description="Execute a Python script in the debug console",
            parameters={
                "code": {"type": "string", "description": "Python code to execute"},
                "session_id": {"type": "string", "description": "Optional session ID", "required": False},
            },
            returns={"output": {"type": "string"}, "error": {"type": "string"}, "duration_ms": {"type": "number"}},
            permission_level=PermissionLevel.SENSITIVE,
            requires_confirmation=True,
            category="devtools",
            capabilities=["debug.exec"],
            tags=["debug", "console"],
        ),
        ToolContract(
            id="debug.get_variables", name="Debug Get Variables",
            description="List variables in the debug console session",
            parameters={"session_id": {"type": "string", "description": "Optional session ID", "required": False}},
            returns={"variables": {"type": "object"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ,
            category="devtools",
            capabilities=["debug.get_variables"],
            tags=["debug", "variables"],
        ),
        ToolContract(
            id="debug.inspect", name="Debug Inspect Object",
            description="Inspect a Python object in the debug console",
            parameters={
                "name": {"type": "string", "description": "Variable name to inspect"},
                "session_id": {"type": "string", "description": "Optional session ID", "required": False},
            },
            returns={"name": {"type": "string"}, "type": {"type": "string"}, "module": {"type": "string"}},
            permission_level=PermissionLevel.READ,
            category="devtools",
            capabilities=["debug.inspect"],
            tags=["debug", "inspect"],
        ),
    ]

    health_tools = [
        ToolContract(
            id="health.get", name="Get Health",
            description="Get overall system health status",
            parameters={},
            returns={"overall": {"type": "boolean"}, "components": {"type": "object"},
                     "healthy_count": {"type": "integer"}, "unhealthy_count": {"type": "integer"}},
            permission_level=PermissionLevel.READ,
            category="devtools",
            capabilities=["health.get"],
            tags=["health", "dashboard"],
        ),
        ToolContract(
            id="health.get_component", name="Get Component Health",
            description="Get health status of a specific component",
            parameters={"component": {"type": "string", "description": "Component name"}},
            returns={"component": {"type": "string"}, "healthy": {"type": "boolean"},
                     "status": {"type": "string"}, "error": {"type": "string"}},
            permission_level=PermissionLevel.READ,
            category="devtools",
            capabilities=["health.get_component"],
            tags=["health", "component"],
        ),
        ToolContract(
            id="health.history", name="Health History",
            description="Get health check history",
            parameters={"limit": {"type": "integer", "description": "Max entries", "default": 100, "required": False}},
            returns={"history": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ,
            category="devtools",
            capabilities=["health.history"],
            tags=["health", "history"],
        ),
        ToolContract(
            id="health.summary", name="Health Summary",
            description="Get brief health summary",
            parameters={},
            returns={"overall": {"type": "boolean"}, "healthy": {"type": "integer"},
                     "unhealthy": {"type": "integer"}, "total": {"type": "integer"}},
            permission_level=PermissionLevel.READ,
            category="devtools",
            capabilities=["health.summary"],
            tags=["health", "summary"],
        ),
    ]

    module_tools = [
        ToolContract(
            id="module.list", name="List Modules",
            description="List loaded Python modules",
            parameters={"pattern": {"type": "string", "description": "Optional regex pattern filter", "required": False}},
            returns={"modules": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ,
            category="devtools",
            capabilities=["module.list"],
            tags=["module", "inspect"],
        ),
        ToolContract(
            id="module.info", name="Module Info",
            description="Get detailed information about a loaded module",
            parameters={"name": {"type": "string", "description": "Module name"}},
            returns={"name": {"type": "string"}, "file": {"type": "string"},
                     "size": {"type": "integer"}, "exports": {"type": "array"}},
            permission_level=PermissionLevel.READ,
            category="devtools",
            capabilities=["module.info"],
            tags=["module", "info"],
        ),
        ToolContract(
            id="module.state", name="Module State",
            description="Get internal state of a module",
            parameters={"name": {"type": "string", "description": "Module name"}},
            returns={"name": {"type": "string"}, "public_attributes": {"type": "object"},
                     "functions": {"type": "array"}, "classes": {"type": "array"}},
            permission_level=PermissionLevel.READ,
            category="devtools",
            capabilities=["module.state"],
            tags=["module", "state"],
        ),
        ToolContract(
            id="module.search", name="Search Modules",
            description="Search loaded Python modules by name",
            parameters={"query": {"type": "string", "description": "Search query"}},
            returns={"modules": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ,
            category="devtools",
            capabilities=["module.search"],
            tags=["module", "search"],
        ),
    ]

    hot_reload_tools = [
        ToolContract(
            id="hot_reload.reload", name="Reload Module",
            description="Reload a Python module at runtime",
            parameters={"name": {"type": "string", "description": "Module name to reload"}},
            returns={"success": {"type": "boolean"}, "module": {"type": "string"},
                     "duration_ms": {"type": "number"}},
            permission_level=PermissionLevel.SENSITIVE,
            requires_confirmation=True,
            category="devtools",
            capabilities=["hot_reload.reload"],
            tags=["hot_reload", "reload"],
        ),
        ToolContract(
            id="hot_reload.reload_all", name="Reload All Watched",
            description="Reload all watched modules",
            parameters={},
            returns={"results": {"type": "array"}, "count": {"type": "integer"},
                     "success_count": {"type": "integer"}},
            permission_level=PermissionLevel.SENSITIVE,
            requires_confirmation=True,
            category="devtools",
            capabilities=["hot_reload.reload_all"],
            tags=["hot_reload", "reload"],
        ),
        ToolContract(
            id="hot_reload.watch", name="Watch Module",
            description="Start watching a module for changes (auto-reload on file change)",
            parameters={"name": {"type": "string", "description": "Module name to watch"}},
            returns={"success": {"type": "boolean"}, "module": {"type": "string"},
                     "file_path": {"type": "string"}, "watching": {"type": "boolean"}},
            permission_level=PermissionLevel.WORKSPACE,
            category="devtools",
            capabilities=["hot_reload.watch"],
            tags=["hot_reload", "watch"],
        ),
        ToolContract(
            id="hot_reload.unwatch", name="Unwatch Module",
            description="Stop watching a module",
            parameters={"name": {"type": "string", "description": "Module name to unwatch"}},
            returns={"removed": {"type": "boolean"}, "module": {"type": "string"}},
            permission_level=PermissionLevel.WORKSPACE,
            category="devtools",
            capabilities=["hot_reload.unwatch"],
            tags=["hot_reload", "unwatch"],
        ),
        ToolContract(
            id="hot_reload.list", name="List Watched",
            description="List all watched modules",
            parameters={},
            returns={"watched": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ,
            category="devtools",
            capabilities=["hot_reload.list"],
            tags=["hot_reload", "list"],
        ),
        ToolContract(
            id="hot_reload.history", name="Reload History",
            description="Get module reload history",
            parameters={"limit": {"type": "integer", "description": "Max entries", "default": 50, "required": False}},
            returns={"history": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ,
            category="devtools",
            capabilities=["hot_reload.history"],
            tags=["hot_reload", "history"],
        ),
    ]

    diagnostics_tools = [
        ToolContract(
            id="diagnostics.run", name="Run Diagnostics",
            description="Run full system diagnostic checks",
            parameters={},
            returns={"result_id": {"type": "string"}, "all_passed": {"type": "boolean"},
                     "summary": {"type": "string"}, "checks": {"type": "array"}},
            permission_level=PermissionLevel.READ,
            category="devtools",
            capabilities=["diagnostics.run"],
            tags=["diagnostics", "health"],
        ),
        ToolContract(
            id="diagnostics.check", name="Run Check",
            description="Run a specific diagnostic check",
            parameters={"name": {"type": "string", "description": "Check name"}},
            returns={"name": {"type": "string"}, "passed": {"type": "boolean"},
                     "detail": {"type": "string"}, "duration_ms": {"type": "number"}},
            permission_level=PermissionLevel.READ,
            category="devtools",
            capabilities=["diagnostics.check"],
            tags=["diagnostics", "check"],
        ),
        ToolContract(
            id="diagnostics.history", name="Diagnostics History",
            description="Get diagnostic check history",
            parameters={"limit": {"type": "integer", "description": "Max entries", "default": 50, "required": False}},
            returns={"history": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ,
            category="devtools",
            capabilities=["diagnostics.history"],
            tags=["diagnostics", "history"],
        ),
        ToolContract(
            id="diagnostics.checks", name="List Checks",
            description="List available diagnostic checks",
            parameters={},
            returns={"checks": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ,
            category="devtools",
            capabilities=["diagnostics.checks"],
            tags=["diagnostics", "list"],
        ),
    ]

    perf_tools = [
        ToolContract(
            id="perf.metrics", name="Get Metrics",
            description="Get performance metrics",
            parameters={
                "name": {"type": "string", "description": "Optional metric name filter", "required": False},
                "limit": {"type": "integer", "description": "Max results", "default": 100, "required": False},
            },
            returns={"metrics": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ,
            category="devtools",
            capabilities=["perf.metrics"],
            tags=["perf", "metrics"],
        ),
        ToolContract(
            id="perf.latest", name="Latest Metrics",
            description="Get latest performance metric values",
            parameters={},
            returns={"metrics": {"type": "object"}},
            permission_level=PermissionLevel.READ,
            category="devtools",
            capabilities=["perf.latest"],
            tags=["perf", "latest"],
        ),
        ToolContract(
            id="perf.start", name="Start Monitoring",
            description="Start periodic performance monitoring",
            parameters={"interval": {"type": "number", "description": "Polling interval in seconds", "default": 5.0, "required": False}},
            returns={"monitoring": {"type": "boolean"}, "interval": {"type": "number"}},
            permission_level=PermissionLevel.WORKSPACE,
            category="devtools",
            capabilities=["perf.start"],
            tags=["perf", "monitoring"],
        ),
        ToolContract(
            id="perf.stop", name="Stop Monitoring",
            description="Stop periodic performance monitoring",
            parameters={},
            returns={"monitoring": {"type": "boolean"}},
            permission_level=PermissionLevel.WORKSPACE,
            category="devtools",
            capabilities=["perf.stop"],
            tags=["perf", "monitoring"],
        ),
        ToolContract(
            id="perf.summary", name="Metric Summary",
            description="Get statistical summary for a metric",
            parameters={"name": {"type": "string", "description": "Metric name"}},
            returns={"name": {"type": "string"}, "count": {"type": "integer"},
                     "min": {"type": "number"}, "max": {"type": "number"}, "avg": {"type": "number"}},
            permission_level=PermissionLevel.READ,
            category="devtools",
            capabilities=["perf.summary"],
            tags=["perf", "summary"],
        ),
    ]

    log_tools = [
        ToolContract(
            id="log.get", name="Get Logs",
            description="Get log entries with filtering",
            parameters={
                "level": {"type": "string", "description": "Minimum level: DEBUG, INFO, WARNING, ERROR, CRITICAL", "required": False},
                "source": {"type": "string", "description": "Filter by source", "required": False},
                "category": {"type": "string", "description": "Filter by category", "required": False},
                "search": {"type": "string", "description": "Search in message text", "required": False},
                "limit": {"type": "integer", "description": "Max results", "default": 200, "required": False},
                "offset": {"type": "integer", "description": "Result offset", "default": 0, "required": False},
            },
            returns={"logs": {"type": "array"}, "total": {"type": "integer"},
                     "returned": {"type": "integer"}, "limit": {"type": "integer"}},
            permission_level=PermissionLevel.READ,
            category="devtools",
            capabilities=["log.get"],
            tags=["log", "viewer"],
        ),
        ToolContract(
            id="log.categories", name="Log Categories",
            description="Get log entry categories with counts",
            parameters={},
            returns={"categories": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ,
            category="devtools",
            capabilities=["log.categories"],
            tags=["log", "categories"],
        ),
        ToolContract(
            id="log.sources", name="Log Sources",
            description="Get log entry sources with counts",
            parameters={},
            returns={"sources": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ,
            category="devtools",
            capabilities=["log.sources"],
            tags=["log", "sources"],
        ),
        ToolContract(
            id="log.clear", name="Clear Logs",
            description="Clear all log entries",
            parameters={},
            returns={"cleared": {"type": "boolean"}},
            permission_level=PermissionLevel.WORKSPACE,
            category="devtools",
            capabilities=["log.clear"],
            tags=["log", "clear"],
        ),
        ToolContract(
            id="log.set_level", name="Set Log Level",
            description="Set minimum log level for display",
            parameters={"level": {"type": "string", "description": "Level: DEBUG, INFO, WARNING, ERROR, CRITICAL"}},
            returns={"level": {"type": "string"}},
            permission_level=PermissionLevel.WORKSPACE,
            category="devtools",
            capabilities=["log.set_level"],
            tags=["log", "level"],
        ),
        ToolContract(
            id="log.stats", name="Log Stats",
            description="Get log statistics",
            parameters={},
            returns={"total_entries": {"type": "integer"}, "by_level": {"type": "object"},
                     "min_level": {"type": "string"}},
            permission_level=PermissionLevel.READ,
            category="devtools",
            capabilities=["log.stats"],
            tags=["log", "stats"],
        ),
    ]

    all_tools = (debug_tools + health_tools + module_tools + hot_reload_tools
                 + diagnostics_tools + perf_tools + log_tools)

    console = debug_console or DebugConsole(event_bus=event_bus)
    dashboard = health_dashboard or HealthDashboard(event_bus=event_bus)
    inspector = module_inspector or ModuleInspector(event_bus=event_bus)
    reloader = hot_reload or HotReload(event_bus=event_bus)
    diag = diagnostics or Diagnostics(event_bus=event_bus)
    monitor = performance_monitor or PerformanceMonitor(event_bus=event_bus)
    viewer = log_viewer or LogViewer(event_bus=event_bus)

    def _wrap(handler_fn, svc):
        async def wrapped(params: dict) -> ToolResult:
            return await handler_fn(params, svc, event_bus)
        return wrapped

    debug_handlers = [_wrap(_debug_eval, console), _wrap(_debug_exec, console),
                      _wrap(_debug_get_vars, console), _wrap(_debug_inspect, console)]
    health_handlers = [_wrap(_health_get, dashboard), _wrap(_health_get_component, dashboard),
                       _wrap(_health_history, dashboard), _wrap(_health_summary, dashboard)]
    module_handlers = [_wrap(_module_list, inspector), _wrap(_module_info, inspector),
                       _wrap(_module_state, inspector), _wrap(_module_search, inspector)]
    reload_handlers = [_wrap(_hot_reload, reloader), _wrap(_hot_reload_all, reloader),
                       _wrap(_hot_watch, reloader), _wrap(_hot_unwatch, reloader),
                       _wrap(_hot_list, reloader), _wrap(_hot_history, reloader)]
    diag_handlers = [_wrap(_diagnostics_run, diag), _wrap(_diagnostics_check, diag),
                     _wrap(_diagnostics_history, diag), _wrap(_diagnostics_checks, diag)]
    perf_handlers = [_wrap(_perf_metrics, monitor), _wrap(_perf_latest, monitor),
                     _wrap(_perf_start, monitor), _wrap(_perf_stop, monitor),
                     _wrap(_perf_summary, monitor)]
    log_handlers = [_wrap(_log_get, viewer), _wrap(_log_categories, viewer),
                    _wrap(_log_sources, viewer), _wrap(_log_clear, viewer),
                    _wrap(_log_set_level, viewer), _wrap(_log_stats, viewer)]

    all_handlers = (debug_handlers + health_handlers + module_handlers + reload_handlers
                    + diag_handlers + perf_handlers + log_handlers)

    for contract, handler in zip(all_tools, all_handlers):
        asyncio.create_task(tm.register_tool(contract, handler))
