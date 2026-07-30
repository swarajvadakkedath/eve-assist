"""Tests for launcher service modules."""

import logging
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from launcher.services.config_service import ConfigService
from launcher.services.logger_service import LoggerService
from launcher.services.process_service import ProcessService
from launcher.services.backend_service import BackendService
from launcher.services.frontend_service import BrowserFrontendService
from launcher.services.health_service import HealthService, ServiceHealth, ProviderStatus
from launcher.services.provider_service import ProviderService
from launcher.services.startup_service import StartupService, wait_for_url
from launcher.services.shutdown_service import ShutdownService
from launcher.launcher_api import LauncherAPI, LauncherStatus


class TestConfigService:
    def test_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc = ConfigService(config_dir=tmp, config_file=str(Path(tmp) / "config.json"))
            assert svc.get("backend_host") == "127.0.0.1"
            assert svc.get("first_run") is True
            assert "api/v1/system/health" in svc.health_url

    def test_set_get(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc = ConfigService(config_dir=tmp, config_file=str(Path(tmp) / "config.json"))
            svc.set("theme", "dark")
            assert svc.get("theme") == "dark"

    def test_save_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            cf = str(Path(tmp) / "config.json")
            c1 = ConfigService(config_dir=tmp, config_file=cf)
            c1.set("theme", "dark")
            c1.set("first_run", False)
            c2 = ConfigService(config_dir=tmp, config_file=cf)
            assert c2.get("theme") == "dark"
            assert c2.get("first_run") is False

    def test_properties(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc = ConfigService(config_dir=tmp, config_file=str(Path(tmp) / "config.json"))
            assert svc.frontend_type == "browser"
            assert svc.api_keys == {}
            assert svc.ai_providers_config is not None


class TestLoggerService:
    def _close(self):
        root = logging.getLogger("eve.launcher")
        for h in root.handlers[:]:
            h.close()
            root.removeHandler(h)
        root.handlers.clear()

    def test_setup(self):
        self._close()
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = str(Path(tmp) / "logs")
            log_file = str(Path(tmp) / "logs" / "launcher.log")
            svc = LoggerService(log_dir=log_dir, log_file=log_file)
            logger = svc.setup("DEBUG")
            assert logger is not None
            self._close()


class TestProcessService:
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
    async def test_start(self):
        ps = ProcessService()
        with patch("asyncio.create_subprocess_exec", return_value=self.FakeProcess()):
            mp = await ps.start("test", "python", "-c", "pass")
            assert mp.name == "test"
            assert mp.pid == 12345
            assert mp.is_running is True

    @pytest.mark.asyncio
    async def test_stop_all(self):
        ps = ProcessService()
        with patch("asyncio.create_subprocess_exec", return_value=self.FakeProcess()):
            await ps.start("t1", "python", "-c", "pass")
            await ps.start("t2", "python", "-c", "pass")
            assert len(ps.list_processes()) == 2
            await ps.stop_all()
            assert len(ps.list_processes()) == 0

    @pytest.mark.asyncio
    async def test_get_and_is_alive(self):
        ps = ProcessService()
        with patch("asyncio.create_subprocess_exec", return_value=self.FakeProcess()):
            await ps.start("test", "python", "-c", "pass")
            assert ps.get("test") is not None
            assert ps.get("nonexistent") is None
            assert await ps.is_alive("test") is True


class TestBackendService:
    @pytest.mark.asyncio
    async def test_start_stop(self):
        ps = MagicMock(spec=ProcessService)
        backend = BackendService(ps)
        mp = MagicMock()
        mp.pid = 999
        ps.start = AsyncMock(return_value=mp)
        pid = await backend.start()
        assert pid == 999


class TestFrontendService:
    @pytest.mark.asyncio
    async def test_start(self):
        ps = MagicMock(spec=ProcessService)
        fe = BrowserFrontendService(ps)
        mp = MagicMock()
        mp.pid = 888
        ps.start = AsyncMock(return_value=mp)
        pid = await fe.start()
        assert pid == 888
        assert fe.get_type() == "browser"


class TestHealthService:
    @pytest.fixture
    def hs(self):
        return HealthService(
            backend_url="http://127.0.0.1:8456",
            health_url="http://127.0.0.1:8456/api/v1/system/health",
        )

    def test_init_services(self, hs):
        assert "backend" in hs.services
        assert "frontend" in hs.services
        assert "gemini" in hs.providers

    def test_init_providers(self, hs):
        assert "ollama" in hs.providers

    def test_service_health_defaults(self):
        sh = ServiceHealth(name="test")
        assert sh.status == "unknown"

    def test_provider_status_defaults(self):
        ps = ProviderStatus(name="test")
        assert ps.connected is False

    @pytest.mark.asyncio
    async def test_check_backend_down(self, hs):
        with patch("httpx.AsyncClient.get", side_effect=Exception("refused")):
            await hs.check_backend()
            assert hs.services["backend"].status == "down"

    @pytest.mark.asyncio
    async def test_check_ai_missing_key(self, hs):
        ps = await hs.check_ai_provider("gemini", key="", url="")
        assert ps.connected is False
        assert "Missing API Key" in ps.error

    @pytest.mark.asyncio
    async def test_check_ai_ollama_offline(self, hs):
        ps = await hs.check_ai_provider("ollama", url="http://127.0.0.1:99999")
        assert ps.connected is False


class TestProviderService:
    @pytest.mark.asyncio
    async def test_check_all(self):
        hs = MagicMock(spec=HealthService)
        cs = MagicMock(spec=ConfigService)
        cs.api_keys = {}
        cs.ai_providers_config = {"ollama": {"url": "http://127.0.0.1:11434"}}
        ps = ProviderService(hs, cs)
        await ps.check_all()
        assert hs.check_all_ai_providers.called

    def test_get_status(self):
        hs = MagicMock(spec=HealthService)
        cs = MagicMock(spec=ConfigService)
        hs.providers = {"gemini": ProviderStatus(name="gemini")}
        ps = ProviderService(hs, cs)
        status = ps.get_status()
        assert "gemini" in status


class TestStartupService:
    @pytest.mark.asyncio
    async def test_wait_for_url_timeout(self):
        ok, data = await wait_for_url("http://127.0.0.1:1", timeout=0.5, interval=0.1)
        assert ok is False

    @pytest.mark.asyncio
    async def test_run_backend_fails(self):
        backend = MagicMock(spec=BackendService)
        frontend = MagicMock(spec=BrowserFrontendService)
        health = MagicMock(spec=HealthService)
        providers = MagicMock(spec=ProviderService)
        config = MagicMock(spec=ConfigService)
        config.health_url = "http://127.0.0.1:1"
        backend.start = AsyncMock(return_value=999)
        with patch("launcher.services.startup_service.wait_for_url", AsyncMock(return_value=(False, None))):
            startup = StartupService(backend, frontend, health, providers, config)
            ok = await startup.run()
            assert ok is False


class TestShutdownService:
    @pytest.mark.asyncio
    async def test_shutdown(self):
        backend = MagicMock(spec=BackendService)
        frontend = MagicMock(spec=BrowserFrontendService)
        health = MagicMock(spec=HealthService)
        sd = ShutdownService(backend, frontend, health)
        await sd.shutdown()
        assert health.stop_monitoring.called
        assert frontend.stop.called
        assert backend.stop.called


class TestLauncherAPI:
    def test_status(self):
        api = LauncherAPI(
            get_status_fn=lambda: LauncherStatus(state="running", version="1.1.0"),
            get_health_fn=AsyncMock(return_value={}),
            get_log_dir_fn=lambda: "/tmp/logs",
        )
        status = api.status()
        assert status.state == "running"

    @pytest.mark.asyncio
    async def test_health(self):
        api = LauncherAPI(
            get_status_fn=lambda: LauncherStatus(),
            get_health_fn=AsyncMock(return_value={"backend": "healthy"}),
            get_log_dir_fn=lambda: "/tmp/logs",
        )
        health = await api.health()
        assert health["backend"] == "healthy"

    def test_log_dir(self):
        api = LauncherAPI(
            get_status_fn=lambda: LauncherStatus(),
            get_health_fn=AsyncMock(return_value={}),
            get_log_dir_fn=lambda: "/tmp/logs",
        )
        assert api.log_dir() == "/tmp/logs"
