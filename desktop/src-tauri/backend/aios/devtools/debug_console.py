import asyncio
import io
import os
import sys
import traceback
import types
import time
from typing import Any

from aios.devtools.models import DebugResult


class DebugConsole:
    def __init__(self, event_bus=None):
        self._event_bus = event_bus
        self._locals: dict[str, Any] = {}
        self._sessions: dict[str, dict] = {}

    async def eval_expression(self, expression: str, session_id: str = "") -> DebugResult:
        if not os.environ.get("EVE_DEBUG_CONSOLE", "").lower() in ("1", "true", "yes"):
            raise RuntimeError("Debug console is disabled")
        start = time.perf_counter()
        session = self._get_session(session_id)
        output = io.StringIO()
        error = ""
        result = None

        old_stdout = sys.stdout
        sys.stdout = output
        try:
            compiled = compile(expression, "<debug>", "eval")
            result = eval(compiled, session["globals"], session["locals"])
        except SyntaxError:
            try:
                compiled = compile(expression, "<debug>", "exec")
                exec(compiled, session["globals"], session["locals"])
                result = None
            except Exception as e:
                error = traceback.format_exc()
        except Exception as e:
            error = traceback.format_exc()
        finally:
            sys.stdout = old_stdout

        duration = (time.perf_counter() - start) * 1000
        debug_result = DebugResult(
            output=output.getvalue(),
            error=error,
            result=result,
            duration_ms=round(duration, 2),
            variables=dict(session["locals"]),
        )
        await self._publish("debug:eval", {
            "expression": expression,
            "session_id": session_id,
            "duration_ms": debug_result.duration_ms,
            "error": bool(error),
            "has_result": result is not None,
        })
        return debug_result

    async def exec_script(self, code: str, session_id: str = "") -> DebugResult:
        if not os.environ.get("EVE_DEBUG_CONSOLE", "").lower() in ("1", "true", "yes"):
            raise RuntimeError("Debug console is disabled")
        start = time.perf_counter()
        session = self._get_session(session_id)
        output = io.StringIO()
        error = ""

        old_stdout = sys.stdout
        sys.stdout = output
        try:
            compiled = compile(code, "<debug>", "exec")
            exec(compiled, session["globals"], session["locals"])
        except Exception as e:
            error = traceback.format_exc()
        finally:
            sys.stdout = old_stdout

        duration = (time.perf_counter() - start) * 1000
        debug_result = DebugResult(
            output=output.getvalue(),
            error=error,
            duration_ms=round(duration, 2),
            variables=dict(session["locals"]),
        )
        await self._publish("debug:exec", {
            "code_length": len(code),
            "session_id": session_id,
            "duration_ms": debug_result.duration_ms,
            "error": bool(error),
        })
        return debug_result

    async def get_variables(self, session_id: str = "") -> dict:
        session = self._get_session(session_id)
        return dict(session["locals"])

    async def inspect_object(self, obj_name: str, session_id: str = "") -> dict:
        session = self._get_session(session_id)
        obj = session["locals"].get(obj_name) or session["globals"].get(obj_name)
        if obj is None:
            return {"error": f"Object '{obj_name}' not found"}

        info = {
            "name": obj_name,
            "type": type(obj).__name__,
            "module": getattr(type(obj), "__module__", ""),
        }
        if isinstance(obj, (int, float, str, bool, bytes)):
            info["value"] = repr(obj)
        if hasattr(obj, "__len__"):
            try:
                info["length"] = len(obj)
            except (TypeError, ValueError):
                pass
        if isinstance(obj, types.ModuleType):
            info["file"] = getattr(obj, "__file__", "")
            info["exports"] = [n for n in dir(obj) if not n.startswith("_")]
        if callable(obj):
            try:
                sig = obj.__doc__
                info["doc"] = sig[:500] if sig else ""
            except Exception:
                pass
        if hasattr(obj, "__dict__"):
            info["attributes"] = list(getattr(obj, "__dict__", {}).keys())
        if isinstance(obj, (list, tuple, set, frozenset)):
            info["element_types"] = list({type(e).__name__ for e in obj})
        await self._publish("debug:inspect", {
            "object_name": obj_name,
            "obj_type": info["type"],
        })
        return info

    def _get_session(self, session_id: str) -> dict:
        if not session_id:
            session_id = "_default"
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "globals": {"__builtins__": __builtins__},
                "locals": {},
            }
        return self._sessions[session_id]

    async def clear_session(self, session_id: str = "") -> None:
        sid = session_id or "_default"
        self._sessions.pop(sid, None)
        await self._publish("debug:session_cleared", {"session_id": sid})

    async def list_sessions(self) -> list[str]:
        return [k for k in self._sessions.keys()]

    async def _publish(self, event_type: str, payload: dict) -> None:
        if self._event_bus:
            await self._event_bus.publish(event_type, payload, source="debug_console")
