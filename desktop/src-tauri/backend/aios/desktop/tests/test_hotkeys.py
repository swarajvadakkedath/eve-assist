import pytest
from aios.desktop.hotkeys import HotkeyManager, HotkeyBinding


@pytest.fixture
def manager():
    m = HotkeyManager()
    m._bindings = {}
    m._registered = set()
    return m


@pytest.mark.asyncio
async def test_register_binding(manager):
    manager.register("toggle_eve", "ctrl+space", lambda: None)
    binding = manager.get_binding("toggle_eve")
    assert binding is not None
    assert binding.action == "toggle_eve"
    assert binding.combination == "ctrl+space"


@pytest.mark.asyncio
async def test_get_all_bindings(manager):
    manager.register("toggle_eve", "ctrl+space", lambda: None)
    manager.register("new_conversation", "ctrl+alt+e", lambda: None)
    bindings = manager.get_all_bindings()
    assert len(bindings) == 2


@pytest.mark.asyncio
async def test_conflict_detection(manager):
    manager.register("toggle_eve", "ctrl+space", lambda: None)
    conflicts = manager.check_conflicts("ctrl+space")
    assert "toggle_eve" in conflicts


@pytest.mark.asyncio
async def test_no_conflict(manager):
    manager.register("toggle_eve", "ctrl+space", lambda: None)
    conflicts = manager.check_conflicts("ctrl+alt+e")
    assert len(conflicts) == 0


@pytest.mark.asyncio
async def test_unregister(manager):
    manager.register("toggle_eve", "ctrl+space", lambda: None)
    manager.unregister("toggle_eve")
    assert manager.get_binding("toggle_eve") is not None
    assert not manager.is_registered("toggle_eve")
