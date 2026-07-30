import pytest
import tempfile
import os
import json
from aios.desktop.settings_store import SettingsStore


@pytest.fixture
async def store():
    s = SettingsStore()
    s._settings = dict(s._settings)
    return s


@pytest.mark.asyncio
async def test_get_default(store):
    val = await store.get("theme")
    assert val == "dark"


@pytest.mark.asyncio
async def test_get_nested(store):
    val = await store.get("global_shortcuts.toggle_eve")
    assert val == "ctrl+space"


@pytest.mark.asyncio
async def test_set(store):
    await store.set("theme", "light")
    assert await store.get("theme") == "light"


@pytest.mark.asyncio
async def test_set_nested(store):
    await store.set("global_shortcuts.toggle_eve", "ctrl+alt+space")
    assert await store.get("global_shortcuts.toggle_eve") == "ctrl+alt+space"


@pytest.mark.asyncio
async def test_get_all(store):
    all_settings = await store.get_all()
    assert "theme" in all_settings
    assert "global_shortcuts" in all_settings


@pytest.mark.asyncio
async def test_update(store):
    await store.update({"theme": "light", "ui": {"accent_color": "#ff0000"}})
    assert await store.get("theme") == "light"
    assert await store.get("ui.accent_color") == "#ff0000"


@pytest.mark.asyncio
async def test_persistence(tmp_path):
    from aios.desktop.settings_store import SettingsStore
    s = SettingsStore()
    s._settings = dict(s._settings)
    file_path = tmp_path / "test_settings.json"
    await s.initialize(str(file_path))
    await s.set("theme", "light")
    s2 = SettingsStore()
    s2._settings = dict(s2._settings)
    await s2.initialize(str(file_path))
    assert await s2.get("theme") == "light"
