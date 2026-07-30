"""Tests for launcher configuration."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from launcher.config import LauncherConfig


@pytest.fixture
def temp_config():
    with tempfile.TemporaryDirectory() as tmp:
        config_dir = Path(tmp) / ".eve"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "launcher_config.json"
        yield config_dir, config_file


def test_default_config():
    with patch("launcher.config.CONFIG_DIR", Path(tempfile.mkdtemp())):
        with patch("launcher.config.CONFIG_FILE", Path(tempfile.mkdtemp()) / "config.json"):
            config = LauncherConfig()
            assert config.get("backend_host") == "127.0.0.1"
            assert config.get("backend_port") == 8456
            assert config.get("first_run") is True
            assert config.backend_url == "http://127.0.0.1:8456"
            assert "api/v1/system/health" in config.health_url
            assert config.frontend_url == "http://localhost:5173"


def test_set_get():
    with patch("launcher.config.CONFIG_DIR", Path(tempfile.mkdtemp())):
        with patch("launcher.config.CONFIG_FILE", Path(tempfile.mkdtemp()) / "config.json"):
            config = LauncherConfig()
            config.set("theme", "dark")
            assert config.get("theme") == "dark"


def test_save_load():
    with tempfile.TemporaryDirectory() as tmp:
        config_dir = Path(tmp)
        config_file = config_dir / "config.json"
        with patch("launcher.config.CONFIG_DIR", config_dir):
            with patch("launcher.config.CONFIG_FILE", config_file):
                c1 = LauncherConfig()
                c1.set("theme", "dark")
                c1.set("first_run", False)
                c2 = LauncherConfig()
                assert c2.get("theme") == "dark"
                assert c2.get("first_run") is False


def test_first_run_property():
    with patch("launcher.config.CONFIG_DIR", Path(tempfile.mkdtemp())):
        with patch("launcher.config.CONFIG_FILE", Path(tempfile.mkdtemp()) / "config.json"):
            config = LauncherConfig()
            assert config.is_first_run is True
            config.set("first_run", False)
            assert config.is_first_run is False


def test_all_data():
    with patch("launcher.config.CONFIG_DIR", Path(tempfile.mkdtemp())):
        with patch("launcher.config.CONFIG_FILE", Path(tempfile.mkdtemp()) / "config.json"):
            config = LauncherConfig()
            data = config.all_data
            assert "backend_host" in data
            assert "ai_providers" in data
            assert "api_keys" in data
