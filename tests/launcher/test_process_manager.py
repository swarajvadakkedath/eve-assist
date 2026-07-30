"""Tests for process manager."""

import sys
from unittest.mock import patch, AsyncMock

import pytest

from launcher.process_manager import ProcessManager, ManagedProcess


@pytest.fixture
def pm():
    return ProcessManager()


class FakeProcess:
    def __init__(self):
        self.returncode = None
        self.pid = 12345
        self.stdout = AsyncMock()
        self.stdout.readline = AsyncMock(side_effect=[b"", b""])

    def terminate(self):
        self.returncode = -1

    wait = AsyncMock(return_value=0)


@pytest.mark.asyncio
async def test_start_process_creates_managed(pm):
    with patch("asyncio.create_subprocess_exec", return_value=FakeProcess()):
        mp = await pm.start("test", sys.executable, "-c", "pass")
        assert mp.name == "test"
        assert mp.pid == 12345
        assert mp.is_running is True


@pytest.mark.asyncio
async def test_get_process(pm):
    with patch("asyncio.create_subprocess_exec", return_value=FakeProcess()):
        await pm.start("test", sys.executable, "-c", "pass")
        mp = pm.get("test")
        assert mp is not None
        assert mp.name == "test"
        assert pm.get("nonexistent") is None


@pytest.mark.asyncio
async def test_stop_nonexistent(pm):
    await pm.stop("nonexistent")


@pytest.mark.asyncio
async def test_stop_all(pm):
    with patch("asyncio.create_subprocess_exec", return_value=FakeProcess()):
        await pm.start("test1", sys.executable, "-c", "pass")
        await pm.start("test2", sys.executable, "-c", "pass")
        assert len(pm._processes) == 2
        await pm.stop_all()
        assert len(pm._processes) == 0


def test_managed_process_properties():
    fp = FakeProcess()
    mp = ManagedProcess("test", fp, [], None)
    assert mp.name == "test"
    assert mp.pid == 12345
    assert mp.is_running is True


@pytest.mark.asyncio
async def test_is_alive(pm):
    with patch("asyncio.create_subprocess_exec", return_value=FakeProcess()):
        await pm.start("test", sys.executable, "-c", "pass")
        assert await pm.is_alive("test") is True
        assert await pm.is_alive("nonexistent") is False
