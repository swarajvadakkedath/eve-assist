"""Unit tests for PluginIsolator."""

import pytest
import tempfile
from pathlib import Path
from aios.plugins.isolator import PluginIsolator, InProcessIsolation, SubprocessIsolation
from aios.plugins.models import IsolationStrategy, PluginResult


@pytest.mark.asyncio
class TestInProcessIsolation:
    async def test_execute_without_init_returns_error(self):
        isolator = InProcessIsolation()
        result = await isolator.execute("p1", "tool1", {}, timeout=5)
        assert result.success is False
        assert "not loaded" in result.error.lower()

    async def test_initialize_and_execute(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_py = Path(tmpdir) / "plugin.py"
            plugin_py.write_text(
                "from aios.plugins.models import PluginResult\n"
                "async def execute(params):\n"
                "    return PluginResult(success=True, data={'echo': params})\n"
            )
            isolator = InProcessIsolation()
            await isolator.initialize("p1", tmpdir)
            result = await isolator.execute("p1", "execute", {"key": "val"}, timeout=5)
            assert result.success is True
            assert result.data["echo"]["key"] == "val"

    async def test_tool_not_found_returns_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_py = Path(tmpdir) / "plugin.py"
            plugin_py.write_text("# no execute function\n")
            isolator = InProcessIsolation()
            await isolator.initialize("p1", tmpdir)
            result = await isolator.execute("p1", "nonexistent_tool", {}, timeout=5)
            assert result.success is False
            assert "not found" in result.error.lower()

    async def test_shutdown_removes_module(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_py = Path(tmpdir) / "plugin.py"
            plugin_py.write_text("# plugin\n")
            isolator = InProcessIsolation()
            await isolator.initialize("p1", tmpdir)
            await isolator.shutdown("p1")
            # After shutdown, execute should return "not loaded"
            result = await isolator.execute("p1", "execute", {}, timeout=5)
            assert result.success is False


@pytest.mark.asyncio
class TestPluginIsolator:
    async def test_get_strategy_in_process(self):
        isolator = PluginIsolator()
        strategy = isolator.get_strategy(IsolationStrategy.IN_PROCESS)
        assert isinstance(strategy, InProcessIsolation)

    async def test_get_strategy_subprocess(self):
        isolator = PluginIsolator()
        strategy = isolator.get_strategy(IsolationStrategy.SUBPROCESS)
        assert isinstance(strategy, SubprocessIsolation)

    async def test_get_strategy_fallback_for_unknown(self):
        isolator = PluginIsolator()
        # DOCKER and REMOTE are not implemented → should fall back to IN_PROCESS
        strategy = isolator.get_strategy(IsolationStrategy.DOCKER)
        assert isinstance(strategy, InProcessIsolation)

    async def test_execute_dispatches_to_strategy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_py = Path(tmpdir) / "plugin.py"
            plugin_py.write_text(
                "from aios.plugins.models import PluginResult\n"
                "async def execute(params):\n"
                "    return PluginResult(success=True, data='ok')\n"
            )
            isolator = PluginIsolator()
            # Initialize in-process first
            await isolator.get_strategy(IsolationStrategy.IN_PROCESS).initialize("p1", tmpdir)
            result = await isolator.execute(
                "p1", "execute", {}, timeout=5, strategy=IsolationStrategy.IN_PROCESS
            )
            assert result.success is True
