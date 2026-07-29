import asyncio
import importlib
import os
import sys
import time
from typing import Any

from aios.devtools.models import WatchedModule


class HotReload:
    def __init__(self, event_bus=None, poll_interval: float = 2.0):
        self._event_bus = event_bus
        self._poll_interval = poll_interval
        self._watched: dict[str, WatchedModule] = {}
        self._reload_count: int = 0
        self._reload_history: list[dict] = []
        self._running = False
        self._task: asyncio.Task | None = None

    async def reload_module(self, name: str) -> dict:
        start = time.perf_counter()
        old_mod = sys.modules.get(name)
        old_file = getattr(old_mod, "__file__", "") if old_mod else ""

        try:
            if name in sys.modules:
                importlib.reload(sys.modules[name])
            else:
                importlib.import_module(name)
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            await self._publish("hot_reload:failed", {
                "module": name, "error": str(e),
            })
            return {
                "success": False, "module": name, "error": str(e),
                "duration_ms": round(duration, 2),
            }

        duration = (time.perf_counter() - start) * 1000
        new_mod = sys.modules.get(name)
        new_file = getattr(new_mod, "__file__", "") if new_mod else ""
        self._reload_count += 1
        record = {
            "module": name,
            "timestamp": time.time(),
            "duration_ms": round(duration, 2),
            "old_file": old_file,
            "new_file": new_file,
            "success": True,
        }
        self._reload_history.append(record)
        if len(self._reload_history) > 200:
            self._reload_history = self._reload_history[-200:]

        await self._publish("hot_reload:completed", {
            "module": name, "duration_ms": round(duration, 2),
        })
        return record

    async def reload_all(self) -> list[dict]:
        results = []
        for name in list(self._watched.keys()):
            result = await self.reload_module(name)
            results.append(result)
            await asyncio.sleep(0.05)
        return results

    async def watch_module(self, name: str) -> dict:
        mod = sys.modules.get(name)
        if mod is None:
            try:
                importlib.import_module(name)
                mod = sys.modules.get(name)
            except Exception as e:
                return {"success": False, "module": name, "error": str(e)}

        file_path = getattr(mod, "__file__", "")
        if not file_path or not os.path.isfile(file_path):
            return {"success": False, "module": name, "error": "No file path for module"}

        mtime = os.path.getmtime(file_path)
        self._watched[name] = WatchedModule(
            name=name,
            file_path=file_path,
            last_mtime=mtime,
            auto_reload=True,
        )
        await self._publish("hot_reload:watch_added", {
            "module": name, "file_path": file_path,
        })
        return {"success": True, "module": name, "file_path": file_path, "watching": True}

    async def unwatch_module(self, name: str) -> bool:
        removed = self._watched.pop(name, None) is not None
        if removed:
            await self._publish("hot_reload:watch_removed", {"module": name})
        return removed

    async def get_watched(self) -> list[WatchedModule]:
        return list(self._watched.values())

    async def start_polling(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        await self._publish("hot_reload:polling_started", {
            "interval": self._poll_interval,
        })

    async def stop_polling(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        await self._publish("hot_reload:polling_stopped", {})

    async def get_reload_history(self, limit: int = 50) -> list[dict]:
        return self._reload_history[-limit:]

    async def _poll_loop(self) -> None:
        while self._running:
            for name, watched in list(self._watched.items()):
                try:
                    if os.path.isfile(watched.file_path):
                        current_mtime = os.path.getmtime(watched.file_path)
                        if current_mtime > watched.last_mtime:
                            self._watched[name].last_mtime = current_mtime
                            if watched.auto_reload:
                                await self.reload_module(name)
                except (OSError, IOError):
                    continue
            await asyncio.sleep(self._poll_interval)

    async def _publish(self, event_type: str, payload: dict) -> None:
        if self._event_bus:
            await self._event_bus.publish(event_type, payload, source="hot_reload")
