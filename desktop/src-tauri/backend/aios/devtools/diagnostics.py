import asyncio
import os
import platform
import sys
import time
import traceback
from datetime import datetime
from typing import Any
from uuid import uuid4

from aios.devtools.models import DiagnosticCheck, DiagnosticResult


class Diagnostics:
    def __init__(self, event_bus=None, memory=None, planner=None,
                 windows_adapter=None, ai_router=None):
        self._event_bus = event_bus
        self._memory = memory
        self._planner = planner
        self._windows_adapter = windows_adapter
        self._ai_router = ai_router
        self._history: list[DiagnosticResult] = []
        self._max_history = 100
        self._checks = self._get_default_checks()

    def _get_default_checks(self) -> list[dict]:
        return [
            {"name": "python_version", "description": "Check Python version meets minimum requirements"},
            {"name": "disk_space", "description": "Check available disk space"},
            {"name": "memory_usage", "description": "Check current memory usage"},
            {"name": "cpu_load", "description": "Check current CPU load"},
            {"name": "event_bus_health", "description": "Check if event bus is operational"},
            {"name": "module_consistency", "description": "Check for module import errors"},
            {"name": "dependency_check", "description": "Verify critical dependencies are installed"},
        ]

    async def run_diagnostics(self) -> DiagnosticResult:
        result_id = uuid4().hex
        checks: list[DiagnosticCheck] = []
        all_passed = True

        for check_def in self._checks:
            check = await self._run_check(check_def["name"])
            checks.append(check)
            if not check.passed:
                all_passed = False

        result = DiagnosticResult(
            id=result_id,
            checks=checks,
            summary=f"Ran {len(checks)} checks, "
                    f"{sum(1 for c in checks if c.passed)} passed, "
                    f"{sum(1 for c in checks if not c.passed)} failed",
            all_passed=all_passed,
        )
        self._history.append(result)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        await self._publish("diagnostics:completed", {
            "result_id": result_id,
            "all_passed": all_passed,
            "checks": [
                {"name": c.name, "passed": c.passed, "duration_ms": c.duration_ms}
                for c in checks
            ],
        })

        if self._memory:
            try:
                from aios.core.memory_system import Memory
                mem = Memory(
                    type="diagnostic_result",
                    content=result.summary,
                    source="diagnostics",
                )
                await self._memory.store(mem)
            except Exception:
                pass

        return result

    async def run_check(self, name: str) -> DiagnosticResult:
        check = await self._run_check(name)
        result_id = uuid4().hex
        result = DiagnosticResult(
            id=result_id,
            checks=[check],
            summary=f"Check '{name}': {'PASSED' if check.passed else 'FAILED'}",
            all_passed=check.passed,
        )
        return result

    async def get_diagnostic_history(self, limit: int = 50) -> list[dict]:
        return [
            {
                "id": r.id,
                "timestamp": r.timestamp.isoformat(),
                "summary": r.summary,
                "all_passed": r.all_passed,
                "check_count": len(r.checks),
            }
            for r in self._history[-limit:]
        ]

    async def get_checks(self) -> list[dict]:
        return self._checks

    async def diagnose_with_planner(self, issue: str) -> dict:
        if not self._planner:
            return {"error": "Planner not available"}

        diagnostic_steps = [
            {"capability": "system.diagnostics", "params": {"check": "python_version"}},
            {"capability": "system.diagnostics", "params": {"check": "memory_usage"}},
            {"capability": "system.diagnostics", "params": {"check": "disk_space"}},
            {"capability": "system.search_logs", "params": {"query": issue}},
        ]

        plan = await self._planner.create_plan(
            request=f"Diagnose issue: {issue}",
            context={"steps": diagnostic_steps},
        )

        executed = await self._planner.execute_plan(plan)
        return {
            "plan_id": executed.id if hasattr(executed, "id") else "",
            "steps": [
                {
                    "id": s.id,
                    "capability": s.capability,
                    "status": s.status.value if hasattr(s.status, "value") else str(s.status),
                    "result": s.result,
                    "error": s.error,
                }
                for s in executed.steps
            ],
        }

    async def _run_check(self, name: str) -> DiagnosticCheck:
        start = time.perf_counter()
        check_map = {
            "python_version": self._check_python_version,
            "disk_space": self._check_disk_space,
            "memory_usage": self._check_memory_usage,
            "cpu_load": self._check_cpu_load,
            "event_bus_health": self._check_event_bus_health,
            "module_consistency": self._check_module_consistency,
            "dependency_check": self._check_dependencies,
        }

        handler = check_map.get(name)
        if handler is None:
            return DiagnosticCheck(
                name=name, status="error", passed=False,
                detail=f"Unknown check: {name}", duration_ms=0.0,
            )

        try:
            passed, detail = await handler()
            duration = (time.perf_counter() - start) * 1000
            return DiagnosticCheck(
                name=name, status="passed" if passed else "failed",
                passed=passed, detail=detail,
                duration_ms=round(duration, 2),
            )
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return DiagnosticCheck(
                name=name, status="error", passed=False,
                detail=str(e), error=traceback.format_exc(),
                duration_ms=round(duration, 2),
            )

    async def _check_python_version(self) -> tuple[bool, str]:
        v = sys.version_info
        ok = v.major >= 3 and v.minor >= 10
        detail = f"Python {v.major}.{v.minor}.{v.micro} ({platform.architecture()[0]})"
        return ok, detail

    async def _check_disk_space(self) -> tuple[bool, str]:
        try:
            if self._windows_adapter:
                info = await self._windows_adapter.get_system_info()
                disk = getattr(info, "disk_free", 0) if hasattr(info, "disk_free") else 0
            else:
                if hasattr(os, "statvfs"):
                    stat = os.statvfs("/")
                    disk = stat.f_frsize * stat.f_bavail
                else:
                    import ctypes
                    free_bytes = ctypes.c_ulonglong(0)
                    ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                        ctypes.c_wchar_p(os.getcwd()), None, None, ctypes.byref(free_bytes)
                    )
                    disk = free_bytes.value

            free_gb = disk / (1024 ** 3)
            ok = free_gb > 0.5
            detail = f"Free disk space: {free_gb:.2f} GB"
            return ok, detail
        except Exception as e:
            return True, f"Could not check: {e}"

    async def _check_memory_usage(self) -> tuple[bool, str]:
        try:
            import psutil
            mem = psutil.virtual_memory()
            percent = mem.percent
            ok = percent < 90
            detail = f"Memory: {mem.used / (1024**3):.1f} GB / {mem.total / (1024**3):.1f} GB ({percent:.1f}%)"
            return ok, detail
        except ImportError:
            return True, "psutil not available"

    async def _check_cpu_load(self) -> tuple[bool, str]:
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.1)
            ok = cpu < 90
            detail = f"CPU usage: {cpu:.1f}%"
            return ok, detail
        except ImportError:
            return True, "psutil not available"

    async def _check_event_bus_health(self) -> tuple[bool, str]:
        if not self._event_bus:
            return False, "Event bus not configured"
        try:
            event_id = await self._event_bus.publish("diagnostics:ping", {})
            detail = f"Event bus operational (test event: {event_id})"
            return True, detail
        except Exception as e:
            return False, f"Event bus error: {e}"

    async def _check_module_consistency(self) -> tuple[bool, str]:
        errors = []
        for name in sorted(sys.modules.keys()):
            mod = sys.modules[name]
            if mod is None:
                errors.append(f"{name} is None")
                continue
            if hasattr(mod, "__file__") and getattr(mod, "__file__") is None:
                if not hasattr(mod, "__path__"):
                    errors.append(f"{name} has no __file__")
        ok = len(errors) == 0
        detail = f"{len(errors)} module issues found" if errors else "All modules consistent"
        if errors:
            detail += f": {errors[:5]}"
        return ok, detail

    async def _check_dependencies(self) -> tuple[bool, str]:
        critical = ["asyncio", "json", "os", "sys", "datetime"]
        missing = [d for d in critical if d not in sys.modules]
        ok = len(missing) == 0
        detail = "All critical dependencies present" if ok else f"Missing: {missing}"
        return ok, detail

    async def _publish(self, event_type: str, payload: dict) -> None:
        if self._event_bus:
            await self._event_bus.publish(event_type, payload, source="diagnostics")
