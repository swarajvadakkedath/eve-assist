"""Plugin isolator — abstract isolation with multiple strategies."""

import asyncio
import subprocess
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from aios.plugins.models import IsolationStrategy, PluginResult
from aios.plugins.exceptions import PluginIsolationError


class IsolationStrategyBase(ABC):
    @abstractmethod
    async def execute(self, plugin_id: str, tool_id: str, params: dict, timeout: int) -> PluginResult: ...

    @abstractmethod
    async def initialize(self, plugin_id: str, source_path: str) -> None: ...

    @abstractmethod
    async def shutdown(self, plugin_id: str) -> None: ...


class InProcessIsolation(IsolationStrategyBase):
    def __init__(self):
        self._modules: dict[str, Any] = {}

    async def initialize(self, plugin_id: str, source_path: str) -> None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(plugin_id, Path(source_path) / "plugin.py")
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self._modules[plugin_id] = module

    async def execute(self, plugin_id: str, tool_id: str, params: dict, timeout: int) -> PluginResult:
        module = self._modules.get(plugin_id)
        if not module:
            return PluginResult(success=False, error="Plugin module not loaded")
        try:
            handler = getattr(module, "execute", None) or getattr(module, tool_id, None)
            if not handler:
                return PluginResult(success=False, error=f"Tool '{tool_id}' not found in plugin")
            result = await asyncio.wait_for(
                handler(params) if asyncio.iscoroutinefunction(handler) else asyncio.to_thread(handler, params),
                timeout=timeout,
            )
            if isinstance(result, PluginResult):
                return result
            return PluginResult(success=True, data=result)
        except asyncio.TimeoutError:
            return PluginResult(success=False, error="Plugin execution timed out")
        except Exception as e:
            return PluginResult(success=False, error=str(e))

    async def shutdown(self, plugin_id: str) -> None:
        self._modules.pop(plugin_id, None)


class SubprocessIsolation(IsolationStrategyBase):
    def __init__(self, memory_limit_mb: int = 256):
        self._memory_limit_mb = memory_limit_mb
        self._processes: dict[str, subprocess.Popen] = {}

    async def initialize(self, plugin_id: str, source_path: str) -> None:
        pass

    async def execute(self, plugin_id: str, tool_id: str, params: dict, timeout: int) -> PluginResult:
        import json as j
        try:
            code = f"import json, sys; sys.path.insert(0, {repr(str(Path(sys.argv[0]).parent))})"
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-c",
                f"import json, sys; {code}; print(json.dumps({{'success': True, 'data': {j.dumps(params)}}}))",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self._processes[plugin_id] = proc
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                if proc.returncode == 0:
                    data = j.loads(stdout.decode())
                    return PluginResult(success=data.get("success", True), data=data.get("data"))
                return PluginResult(success=False, error=stderr.decode())
            except asyncio.TimeoutError:
                proc.kill()
                return PluginResult(success=False, error="Plugin execution timed out")
        except Exception as e:
            return PluginResult(success=False, error=str(e))
        finally:
            self._processes.pop(plugin_id, None)

    async def shutdown(self, plugin_id: str) -> None:
        proc = self._processes.pop(plugin_id, None)
        if proc:
            proc.kill()


class VirtualEnvIsolation(IsolationStrategyBase):
    async def initialize(self, plugin_id: str, source_path: str) -> None:
        pass

    async def execute(self, plugin_id: str, tool_id: str, params: dict, timeout: int) -> PluginResult:
        return PluginResult(success=False, error="Virtual env isolation not yet implemented")

    async def shutdown(self, plugin_id: str) -> None:
        pass


class PluginIsolator:
    def __init__(self):
        self._strategies: dict[IsolationStrategy, IsolationStrategyBase] = {
            IsolationStrategy.IN_PROCESS: InProcessIsolation(),
            IsolationStrategy.SUBPROCESS: SubprocessIsolation(),
            IsolationStrategy.VIRTUAL_ENV: VirtualEnvIsolation(),
        }

    def get_strategy(self, strategy: IsolationStrategy) -> IsolationStrategyBase:
        return self._strategies.get(strategy, self._strategies[IsolationStrategy.IN_PROCESS])

    async def execute(self, plugin_id: str, tool_id: str, params: dict, timeout: int = 30,
                      strategy: IsolationStrategy = IsolationStrategy.IN_PROCESS) -> PluginResult:
        isolator = self.get_strategy(strategy)
        return await isolator.execute(plugin_id, tool_id, params, timeout)
