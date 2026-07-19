"""Tests for Configuration module."""

from aios.config.settings import AiosSettings


def test_default_settings():
    settings = AiosSettings()
    assert settings.ai_provider == "ollama"
    assert settings.log_level == "INFO"
    assert settings.permission_default_level == 1
    assert settings.ui_theme in ("light", "dark", "system")


def test_env_override(monkeypatch):
    monkeypatch.setenv("AIOS_AI_PROVIDER", "openai")
    settings = AiosSettings()
    assert settings.ai_provider == "openai"


def test_db_path_default():
    settings = AiosSettings()
    assert settings.db_path.endswith("aios.db")


def test_permission_levels():
    settings = AiosSettings()
    assert 0 <= settings.permission_default_level <= 3
