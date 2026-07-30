"""Desktop API routes — expose desktop integration features to frontend."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from aios.utils.tracer import trace_async
from aios.desktop.status_service import StatusService, AppStatus
from aios.desktop.settings_store import SettingsStore
from aios.desktop.hotkeys import HotkeyManager
from aios.desktop.notifications import NotificationService
from aios.desktop.startup import StartupManager
from aios.desktop.window_manager import WindowManager

router = APIRouter(prefix="/api/v1/desktop", tags=["desktop"])


class HotkeyUpdateRequest(BaseModel):
    action: str
    combination: str


class NotificationRequest(BaseModel):
    title: str
    message: str
    notification_type: str = "info"
    timeout: int = 5


class SettingsUpdateRequest(BaseModel):
    settings: dict


@router.get("/status")
async def get_status():
    service = StatusService()
    return {
        "status": service.get_status().value,
        "metadata": service.get_metadata(),
    }


@router.get("/status/history")
async def get_status_history(limit: int = 50):
    service = StatusService()
    return {"history": service.get_history(limit)}


@router.get("/settings")
@trace_async
async def get_settings():
    store = SettingsStore()
    return await store.get_all()


@router.put("/settings")
@trace_async
async def update_settings(request: SettingsUpdateRequest):
    store = SettingsStore()
    await store.update(request.settings)
    return {"status": "ok"}


@router.get("/hotkeys")
async def get_hotkeys():
    manager = HotkeyManager()
    bindings = manager.get_all_bindings()
    return {
        "hotkeys": [
            {"action": b.action, "combination": b.combination, "enabled": b.enabled}
            for b in bindings
        ]
    }


@router.put("/hotkeys")
async def update_hotkey(request: HotkeyUpdateRequest):
    manager = HotkeyManager()
    conflicts = manager.check_conflicts(request.combination)
    return {"status": "ok", "conflicts": conflicts}


@router.get("/notifications/history")
async def get_notification_history(limit: int = 50):
    service = NotificationService()
    return {"notifications": service.get_history(limit)}


@router.delete("/notifications/history")
async def clear_notification_history():
    service = NotificationService()
    service.clear_history()
    return {"status": "ok"}


@router.get("/window/state")
async def get_window_state():
    manager = WindowManager()
    rect = manager.get_window_rect()
    return {
        "visible": manager.is_window_visible(),
        "rect": rect,
    }


@router.post("/window/show")
async def show_window():
    manager = WindowManager()
    manager.show_window()
    return {"status": "ok"}


@router.post("/window/hide")
async def hide_window():
    manager = WindowManager()
    manager.hide_window()
    return {"status": "ok"}


@router.post("/window/minimize")
async def minimize_window():
    manager = WindowManager()
    manager.minimize_window()
    return {"status": "ok"}


@router.post("/window/restore")
async def restore_window():
    manager = WindowManager()
    manager.restore_window()
    return {"status": "ok"}


@router.get("/startup")
async def get_startup_status():
    manager = StartupManager()
    return {
        "enabled": manager.is_startup_enabled(),
        "path": manager.get_startup_path(),
    }


@router.post("/startup/enable")
async def enable_startup():
    manager = StartupManager()
    success = manager.enable_startup()
    return {"status": "ok" if success else "failed"}


@router.post("/startup/disable")
async def disable_startup():
    manager = StartupManager()
    success = manager.disable_startup()
    return {"status": "ok" if success else "failed"}
