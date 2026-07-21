"""Tests for AIOS launcher (__main__.py)."""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aios.__main__ import (
    LauncherError,
    _build_proc_env,
    check_node,
    check_python,
    fetch_runtime_info,
    main,
    ok,
    print_banner,
    run,
    start_process,
    wait_for_backend,
)


class FakeProc:
    """Non-awaitable subprocess mock (avoids AsyncMock double-await)."""

    def __init__(self, returncode=None, pid=12345):
        self.returncode = returncode
        self.pid = pid
        self.stdout = AsyncMock()
        self.stdout.readline = AsyncMock(return_value=b"")

    async def wait(self):
        return 0

    def terminate(self):
        pass

    def kill(self):
        pass


# ── Output helpers ────────────────────────────────────────

class TestOutputHelpers:
    def test_ok_prints_checkmark(self, capsys):
        ok("Test Message")
        captured = capsys.readouterr()
        assert "\u2713" in captured.out
        assert "Test Message" in captured.out

    def test_print_banner_contains_header(self, capsys):
        print_banner()
        captured = capsys.readouterr()
        assert "\u2550" in captured.out
        assert "AIOS (Eve)" in captured.out


# ── Environment checks ────────────────────────────────────

class TestCheckPython:
    @patch("aios.__main__.sys.version_info")
    def test_ok(self, mock_vi):
        mock_vi.major = 3
        mock_vi.minor = 12
        assert check_python() is True

    @patch("aios.__main__.sys.version_info")
    def test_too_old(self, mock_vi):
        mock_vi.major = 3
        mock_vi.minor = 11
        with pytest.raises(LauncherError, match="Python >= 3.12"):
            check_python()

    @patch("aios.__main__.sys.version_info")
    def test_aios_not_importable(self, mock_vi):
        mock_vi.major = 3
        mock_vi.minor = 12
        import sys as _sys
        saved = _sys.modules.pop("aios", None)
        try:
            with patch("builtins.__import__", side_effect=ImportError("No module named aios")):
                with pytest.raises(LauncherError, match="aios package not installed"):
                    check_python()
        finally:
            if saved is not None:
                _sys.modules["aios"] = saved


class TestCheckNode:
    @patch("aios.__main__.shutil.which", return_value="/usr/bin/node")
    def test_ok(self, mock_which):
        assert check_node() is True

    @patch("aios.__main__.shutil.which", side_effect=[None, "/usr/bin/npm"])
    def test_node_missing(self, mock_which):
        with pytest.raises(LauncherError, match="Node.js not found"):
            check_node()

    @patch("aios.__main__.shutil.which", side_effect=["/usr/bin/node", None])
    def test_npm_missing(self, mock_which):
        with pytest.raises(LauncherError, match="npm not found"):
            check_node()


# ── Backend health check ──────────────────────────────────

class TestWaitForBackend:
    @patch("aios.__main__.httpx.AsyncClient")
    def test_healthy(self, mock_client_cls):
        resp = MagicMock()
        resp.status_code = 200
        resp.json = MagicMock(return_value={"status": "healthy", "modules": {}})
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.get = AsyncMock(return_value=resp)
        mock_client_cls.return_value = client

        ok, data = asyncio.run(wait_for_backend(timeout=1))
        assert ok is True
        assert data["status"] == "healthy"

    @patch("aios.__main__.httpx.AsyncClient")
    def test_timeout(self, mock_client_cls):
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.get = AsyncMock(side_effect=ConnectionError)
        mock_client_cls.return_value = client

        ok, data = asyncio.run(wait_for_backend(timeout=1))
        assert ok is False
        assert data is None


# ── Subprocess management ─────────────────────────────────

class TestStartProcess:
    @patch("aios.__main__._build_proc_env", return_value={"PATH": "/usr/bin"})
    @patch("aios.__main__.asyncio.create_subprocess_exec", new_callable=AsyncMock)
    async def test_starts_subprocess(self, mock_create, mock_build):
        proc = FakeProc()
        mock_create.return_value = proc

        result_proc, buffer, reader = await start_process("python", "-c", "pass")
        assert result_proc is proc


class TestBuildProcEnv:
    @patch("aios.__main__.ENSURE_PATH", "C:\\backend")
    @patch("aios.__main__.os.environ.copy", return_value={})
    def test_adds_ensure_path_when_empty(self, mock_copy):
        env = _build_proc_env()
        assert "PYTHONPATH" in env
        assert "C:\\backend" in env["PYTHONPATH"]

    @patch("aios.__main__.ENSURE_PATH", "C:\\backend")
    @patch("aios.__main__.os.environ.copy", return_value={"PYTHONPATH": "C:\\other"})
    def test_appends_to_existing(self, mock_copy):
        env = _build_proc_env()
        assert "C:\\backend;C:\\other" in env["PYTHONPATH"]

    @patch("aios.__main__.ENSURE_PATH", "C:\\backend")
    @patch("aios.__main__.os.environ.copy", return_value={"PYTHONPATH": "C:\\backend"})
    def test_no_duplicate(self, mock_copy):
        env = _build_proc_env()
        assert env["PYTHONPATH"] == "C:\\backend"


# ── Runtime info fetching ─────────────────────────────────

class TestFetchRuntimeInfo:
    @patch("aios.__main__.httpx.AsyncClient")
    async def test_fetches_all_endpoints(self, mock_client_cls):
        client = AsyncMock()
        client.__aenter__.return_value = client

        async def mock_get(url, **kw):
            resp = AsyncMock()
            resp.raise_for_status = MagicMock()
            if "tools" in str(url):
                resp.json = MagicMock(return_value={"tools": [{"id": "t1"}, {"id": "t2"}]})
                return resp
            if "capabilities" in str(url):
                resp.json = MagicMock(return_value={"capabilities": [{"id": c} for c in range(5)]})
                return resp
            if "settings" in str(url):
                resp.json = MagicMock(return_value={"settings": {"ai.provider": "test", "ai.model": "gpt-4", "log.level": "INFO"}})
                return resp
            if "plugins/health" in str(url):
                resp.json = MagicMock(return_value={"total": 3, "active": 2})
                return resp
            return None

        client.get = AsyncMock(side_effect=mock_get)
        mock_client_cls.return_value = client

        info = await fetch_runtime_info()
        assert info["tools"] == 2
        assert info["capabilities"] == 5
        assert info["plugins"] == 3
        assert info["ai_provider"] == "test"

    @patch("aios.__main__.httpx.AsyncClient")
    async def test_handles_api_failure(self, mock_client_cls):
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.get = AsyncMock(side_effect=ConnectionError)
        mock_client_cls.return_value = client

        info = await fetch_runtime_info()
        assert info["tools"] == 0
        assert info["capabilities"] == 0
        assert info["ai_provider"] == "unknown"


# ── Full run flow ─────────────────────────────────────────

class TestRun:
    @patch("aios.__main__.check_python", return_value=True)
    @patch("aios.__main__.check_node", return_value=True)
    @patch("aios.__main__.wait_for_backend",
           return_value=(True, {"modules": {
               "event_bus": "healthy", "tool_manager": "healthy",
               "capability_registry": "healthy", "ai_router": "healthy",
               "memory_system": "healthy",
           }}))
    @patch("aios.__main__.fetch_runtime_info",
           return_value={"tools": 33, "capabilities": 153, "plugins": 0,
                         "ai_provider": "ollama", "ai_model": "gpt-4",
                         "log_level": "INFO"})
    @patch("aios.__main__.webbrowser.open")
    @patch("aios.__main__._build_proc_env", return_value={})
    async def test_full_flow(self, mock_build, mock_browser, mock_runtime,
                             mock_health, mock_node, mock_py):
        proc = FakeProc()
        with patch("aios.__main__.asyncio.create_subprocess_exec",
                   new_callable=AsyncMock, return_value=proc):
            with patch.object(Path, "exists", return_value=True):
                await run()
        mock_browser.assert_called_once_with("http://localhost:5173")

    @patch("aios.__main__.check_python", return_value=True)
    @patch("aios.__main__.check_node", return_value=True)
    @patch("aios.__main__._build_proc_env", return_value={})
    async def test_backend_timeout(self, mock_build, mock_node, mock_py):
        proc = FakeProc()
        proc.stdout.readline = AsyncMock(
            side_effect=[b"Error binding to port 8456\n", b""])

        with patch("aios.__main__.asyncio.create_subprocess_exec",
                   new_callable=AsyncMock, return_value=proc):
            with patch("aios.__main__.wait_for_backend",
                       return_value=(False, None)):
                with patch.object(Path, "exists", return_value=True):
                    with pytest.raises(LauncherError):
                        await run()

    @patch("aios.__main__.check_python", return_value=True)
    @patch("aios.__main__.check_node", return_value=True)
    @patch("aios.__main__._build_proc_env", return_value={})
    async def test_health_validation_fails(self, mock_build, mock_node, mock_py):
        proc = FakeProc()
        with patch("aios.__main__.asyncio.create_subprocess_exec",
                   new_callable=AsyncMock, return_value=proc):
            with patch("aios.__main__.wait_for_backend",
                       return_value=(True, {"modules": {"event_bus": "unhealthy"}})):
                with patch.object(Path, "exists", return_value=True):
                    with pytest.raises(LauncherError, match="health validation"):
                        await run()

    @patch("aios.__main__.check_python", return_value=True)
    @patch("aios.__main__.check_node", return_value=True)
    @patch("aios.__main__._build_proc_env", return_value={})
    async def test_npm_install_on_missing_modules(self, mock_build, mock_node, mock_py):
        proc = FakeProc()
        installer = FakeProc(returncode=0)
        installer.wait = AsyncMock(return_value=0)

        async def fake_create(*args, **kwargs):
            if "install" in str(args):
                return installer
            return proc

        with patch("aios.__main__.wait_for_backend",
                   return_value=(True, {"modules": {
                       "event_bus": "healthy", "tool_manager": "healthy",
                   }})):
            with patch("aios.__main__.fetch_runtime_info",
                       return_value={"tools": 0, "capabilities": 0, "plugins": 0,
                                     "ai_provider": "", "ai_model": "", "log_level": ""}):
                with patch("aios.__main__.webbrowser.open"):
                    with patch("aios.__main__.asyncio.create_subprocess_exec",
                               side_effect=fake_create):
                        with patch.object(Path, "exists", return_value=False):
                            await run()

    @patch("aios.__main__.check_python", return_value=True)
    @patch("aios.__main__.check_node", return_value=True)
    @patch("aios.__main__._build_proc_env", return_value={})
    async def test_graceful_shutdown_on_cancel(self, mock_build, mock_node, mock_py):
        proc = FakeProc()

        with patch("aios.__main__.wait_for_backend",
                   return_value=(True, {"modules": {
                       "event_bus": "healthy", "tool_manager": "healthy",
                   }})):
            with patch("aios.__main__.fetch_runtime_info",
                       return_value={"tools": 0, "capabilities": 0, "plugins": 0,
                                     "ai_provider": "", "ai_model": "", "log_level": ""}):
                with patch("aios.__main__.webbrowser.open"):
                    with patch("aios.__main__.asyncio.create_subprocess_exec",
                               new_callable=AsyncMock, return_value=proc):
                        with patch.object(Path, "exists", return_value=True):
                            with patch("aios.__main__.logger"):
                                await run()

    def test_output_includes_progress_markers(self, capsys):
        ok("Test Step")
        captured = capsys.readouterr()
        assert "\u2713" in captured.out


# ── Main entry point ──────────────────────────────────────

class TestMain:
    @patch("aios.__main__.run")
    def test_main_calls_run(self, mock_run):
        main()
        mock_run.assert_called_once()

    @patch("aios.__main__.run", side_effect=KeyboardInterrupt)
    def test_keyboard_interrupt(self, mock_run):
        main()

    @patch("aios.__main__.run", side_effect=LauncherError("test error"))
    def test_launcher_error_exits(self, mock_run):
        with pytest.raises(SystemExit):
            main()


# ── Launcher scripts exist ────────────────────────────────

class TestLauncherScripts:
    ROOT = Path(__file__).resolve().parent.parent.parent

    def test_start_eve_ps1_exists(self):
        assert (self.ROOT / "start_eve.ps1").exists()

    def test_start_eve_bat_exists(self):
        assert (self.ROOT / "start_eve.bat").exists()

    def test_start_eve_ps1_calls_python(self):
        content = (self.ROOT / "start_eve.ps1").read_text(encoding="utf-8")
        assert "python -m aios" in content
        assert "PYTHONPATH" in content

    def test_start_eve_bat_calls_python(self):
        content = (self.ROOT / "start_eve.bat").read_text(encoding="utf-8")
        assert "python -m aios" in content
        assert "PYTHONPATH" in content
