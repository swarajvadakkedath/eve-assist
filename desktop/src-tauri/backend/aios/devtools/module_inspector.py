import importlib
import inspect
import os
import re
import sys
import types
from typing import Any

from aios.devtools.models import ModuleInfo


class ModuleInspector:
    def __init__(self, event_bus=None):
        self._event_bus = event_bus

    async def list_modules(self, pattern: str = "") -> list[ModuleInfo]:
        results = []
        seen = set()
        for module_name in sorted(sys.modules.keys()):
            if pattern and not re.search(pattern, module_name, re.IGNORECASE):
                continue
            if module_name in seen:
                continue
            seen.add(module_name)
            mod = sys.modules[module_name]
            if mod is None:
                continue
            info = self._build_info(module_name, mod)
            if info:
                results.append(info)
        return results

    async def get_module_info(self, name: str) -> ModuleInfo | None:
        mod = sys.modules.get(name)
        if mod is None:
            return None
        return self._build_info(name, mod)

    async def get_module_state(self, name: str) -> dict:
        mod = sys.modules.get(name)
        if mod is None:
            return {"error": f"Module '{name}' not found"}
        state = {
            "name": name,
            "file": getattr(mod, "__file__", ""),
            "doc": getattr(mod, "__doc__", "")[:500] if getattr(mod, "__doc__", "") else "",
        }
        if hasattr(mod, "__dict__"):
            public = {}
            for k, v in mod.__dict__.items():
                if not k.startswith("_"):
                    public[k] = self._summarize(v)
            state["public_attributes"] = public

        if inspect.getmembers(mod, inspect.isfunction):
            funcs = [(n, f) for n, f in inspect.getmembers(mod, inspect.isfunction)
                     if f.__module__ == name or getattr(f, "__module__", "") == name]
            state["functions"] = [
                {"name": n, "signature": str(inspect.signature(f))[:200]}
                for n, f in funcs
            ]

        if inspect.getmembers(mod, inspect.isclass):
            classes = [(n, c) for n, c in inspect.getmembers(mod, inspect.isclass)
                       if c.__module__ == name]
            state["classes"] = [
                {
                    "name": n,
                    "bases": [b.__name__ for b in c.__bases__],
                    "methods": [
                        m for m in dir(c)
                        if not m.startswith("_") or m in ("__init__",)
                    ],
                }
                for n, c in classes
            ]

        await self._publish("module:inspected", {
            "module": name,
            "has_state": True,
        })
        return state

    async def search_modules(self, query: str) -> list[ModuleInfo]:
        query_lower = query.lower()
        results = []
        seen = set()
        for module_name in sorted(sys.modules.keys()):
            if query_lower not in module_name.lower():
                continue
            if module_name in seen:
                continue
            seen.add(module_name)
            mod = sys.modules[module_name]
            if mod is None:
                continue
            info = self._build_info(module_name, mod)
            if info:
                results.append(info)
        return results

    async def get_module_source(self, name: str) -> str | None:
        mod = sys.modules.get(name)
        if mod is None:
            return None
        try:
            return inspect.getsource(mod)
        except (TypeError, OSError):
            return None

    def _build_info(self, name: str, mod: types.ModuleType) -> ModuleInfo | None:
        try:
            file = getattr(mod, "__file__", "") or ""
            size = 0
            source_lines = 0
            if file and os.path.isfile(file):
                try:
                    size = os.path.getsize(file)
                    with open(file, "r", encoding="utf-8", errors="replace") as f:
                        source_lines = sum(1 for _ in f)
                except (OSError, IOError):
                    pass

            doc = getattr(mod, "__doc__", "") or ""
            exports = [
                n for n in dir(mod)
                if not n.startswith("_")
            ]
            deps = self._get_dependencies(name, mod)

            return ModuleInfo(
                name=name,
                file=file,
                size=size,
                exports=exports,
                dependencies=deps,
                is_package=hasattr(mod, "__path__"),
                docstring=doc[:500] if doc else "",
                source_lines=source_lines,
            )
        except Exception:
            return None

    def _get_dependencies(self, module_name: str, mod: types.ModuleType) -> list[str]:
        deps = []
        if hasattr(mod, "__dict__"):
            for k, v in list(mod.__dict__.items())[:200]:
                if isinstance(v, types.ModuleType):
                    dep_name = getattr(v, "__name__", "")
                    if dep_name and dep_name != module_name and not dep_name.startswith("_"):
                        deps.append(dep_name)
        return sorted(set(deps))[:50]

    def _summarize(self, v: Any) -> str:
        if isinstance(v, (int, float, str, bool, type(None))):
            return repr(v)[:200]
        if isinstance(v, (list, tuple, set)):
            return f"{type(v).__name__}[{len(v)}]"
        if isinstance(v, dict):
            return f"dict[{len(v)}]"
        if isinstance(v, types.ModuleType):
            return f"module<{getattr(v, '__name__', '?')}>"
        if isinstance(v, types.FunctionType):
            return f"function<{v.__name__}>"
        if isinstance(v, types.BuiltinFunctionType):
            return f"builtin<{v.__name__}>"
        if inspect.isclass(v):
            return f"class<{v.__name__}>"
        return type(v).__name__

    async def _publish(self, event_type: str, payload: dict) -> None:
        if self._event_bus:
            await self._event_bus.publish(event_type, payload, source="module_inspector")
