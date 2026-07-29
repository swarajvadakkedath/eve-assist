"""Windows Adapter facade — permission-gated, event-publishing Windows API wrapper."""

from aios.adapters.base_adapter import (
    BaseAdapter,
    FileInfo,
    ProcessInfo,
    SystemInfo,
    WindowInfo,
)
from aios.core.di_container import DIContainer
from aios.core.event_bus import EventBus
from aios.core.permission_manager import PermissionManager, PermissionLevel

from .clipboard import ClipboardService
from .filesystem import FileSystemService
from .process import ProcessService
from .active_window import ActiveWindowService
from .monitor import MonitorService
from .ui_automation import UIAutomationService
from .system_info import SystemInfoService
from .exceptions import WindowsAdapterError


class WindowsAdapter(BaseAdapter):
    def __init__(
        self,
        clipboard: ClipboardService | None = None,
        filesystem: FileSystemService | None = None,
        process: ProcessService | None = None,
        active_window: ActiveWindowService | None = None,
        monitor: MonitorService | None = None,
        ui_automation: UIAutomationService | None = None,
        system_info: SystemInfoService | None = None,
        permission_manager: PermissionManager | None = None,
        event_bus: EventBus | None = None,
    ):
        self.clipboard = clipboard or ClipboardService()
        self.filesystem = filesystem or FileSystemService()
        self.process = process or ProcessService()
        self.active_window = active_window or ActiveWindowService()
        self.monitor = monitor or MonitorService()
        self.ui_automation = ui_automation or UIAutomationService()
        self.system_info = system_info or SystemInfoService()
        self._permission_manager = permission_manager
        self._event_bus = event_bus

    # ------------------------------------------------------------------
    # DI registration
    # ------------------------------------------------------------------

    @staticmethod
    def register_in_container(
        container: DIContainer,
        permission_manager: PermissionManager | None = None,
        event_bus: EventBus | None = None,
    ) -> DIContainer:
        def factory() -> WindowsAdapter:
            return WindowsAdapter(
                permission_manager=permission_manager,
                event_bus=event_bus,
            )
        container.register(WindowsAdapter, factory=factory)
        return container

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _check(self, tool_id: str, level: PermissionLevel = PermissionLevel.READ) -> None:
        if self._permission_manager is None:
            return
        result = await self._permission_manager.check_permission(tool_id, level)
        if not result.granted:
            raise WindowsAdapterError(f"Permission denied for {tool_id}: requires {level.name}")

    async def _publish(self, event_type: str, payload: dict) -> None:
        if self._event_bus is not None:
            await self._event_bus.publish(event_type, payload, source="windows_adapter")

    def _check_permission_sync(self, tool_id: str, level: PermissionLevel = PermissionLevel.READ) -> None:
        if self._permission_manager is None:
            return
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self._check(tool_id, level), loop
                )
                future.result(timeout=10)
                return
        except RuntimeError:
            pass
        raise WindowsAdapterError(f"Permission check unavailable for {tool_id}")

    # ------------------------------------------------------------------
    # Clipboard
    # ------------------------------------------------------------------

    async def clipboard_get_text(self) -> str:
        await self._check("clipboard_get_text")
        result = self.clipboard.get_text()
        await self._publish("clipboard:read", {"text_length": len(result)})
        return result

    async def clipboard_set_text(self, text: str) -> None:
        await self._check("clipboard_set_text", PermissionLevel.SAFE)
        self.clipboard.set_text(text)
        await self._publish("clipboard:changed", {"text_length": len(text)})

    async def clipboard_clear(self) -> None:
        await self._check("clipboard_clear", PermissionLevel.SAFE)
        self.clipboard.clear()
        await self._publish("clipboard:changed", {"text_length": 0})

    # ------------------------------------------------------------------
    # Filesystem
    # ------------------------------------------------------------------

    async def search_files(self, pattern: str, path: str | None = None) -> list[FileInfo]:
        await self._check("search_files")
        results = self.filesystem.search_files(pattern, path)
        return [FileInfo(path=r["path"], name=r["name"], size=r["size"], is_dir=r["is_dir"], modified=r["modified"]) for r in results]

    async def read_file(self, path: str) -> str:
        await self._check("read_file")
        content = self.filesystem.read_file(path)
        await self._publish("file:read", {"path": path})
        return content

    async def write_file(self, path: str, content: str) -> None:
        await self._check("write_file", PermissionLevel.WORKSPACE)
        self.filesystem.write_file(path, content)
        await self._publish("file:changed", {"path": path, "action": "write"})

    async def delete_file(self, path: str) -> None:
        await self._check("delete_file", PermissionLevel.WORKSPACE)
        self.filesystem.delete_file(path)
        await self._publish("file:changed", {"path": path, "action": "delete"})

    async def create_directory(self, path: str) -> None:
        await self._check("create_directory", PermissionLevel.WORKSPACE)
        self.filesystem.create_directory(path)
        await self._publish("file:changed", {"path": path, "action": "create_directory"})

    async def move_file(self, src: str, dst: str) -> None:
        await self._check("move_file", PermissionLevel.WORKSPACE)
        self.filesystem.move_file(src, dst)
        await self._publish("file:changed", {"path": src, "action": "move", "destination": dst})

    async def copy_file(self, src: str, dst: str) -> None:
        await self._check("copy_file", PermissionLevel.SAFE)
        self.filesystem.copy_file(src, dst)
        await self._publish("file:changed", {"path": src, "action": "copy", "destination": dst})

    async def get_file_metadata(self, path: str) -> dict:
        await self._check("get_file_metadata")
        return self.filesystem.get_metadata(path)

    async def file_exists(self, path: str) -> bool:
        await self._check("file_exists")
        return self.filesystem.exists(path)

    # ------------------------------------------------------------------
    # Process
    # ------------------------------------------------------------------

    async def list_processes(self) -> list[ProcessInfo]:
        await self._check("list_processes")
        results = self.process.list_processes()
        return [ProcessInfo(pid=r["pid"], name=r["name"], cpu_percent=r["cpu_percent"], memory_mb=r["memory_mb"]) for r in results]

    async def get_process_info(self, pid: int) -> dict:
        await self._check("get_process_info")
        return self.process.get_process_info(pid)

    async def find_process(self, name: str) -> list[dict]:
        await self._check("find_process")
        return self.process.find_process(name)

    async def start_process(self, command: str) -> int:
        await self._check("start_process", PermissionLevel.SENSITIVE)
        pid = self.process.start_process(command)
        await self._publish("process:started", {"pid": pid, "command": command})
        return pid

    async def kill_process(self, pid: int) -> None:
        await self._check("kill_process", PermissionLevel.SENSITIVE)
        self.process.terminate_process(pid, force=True)
        await self._publish("process:stopped", {"pid": pid})

    async def terminate_process(self, pid: int) -> None:
        await self._check("terminate_process", PermissionLevel.SENSITIVE)
        self.process.terminate_process(pid, force=False)
        await self._publish("process:stopped", {"pid": pid})

    # ------------------------------------------------------------------
    # Active Window
    # ------------------------------------------------------------------

    async def get_active_window(self) -> WindowInfo:
        await self._check("get_active_window")
        result = self.active_window.get_active_window()
        await self._publish("active_window:changed", result)
        return WindowInfo(
            title=result["title"],
            app=result["app"],
            x=result["x"],
            y=result["y"],
            width=result["width"],
            height=result["height"],
        )

    async def search_windows(self, title_substring: str) -> list[dict]:
        await self._check("search_windows")
        return self.active_window.get_window_by_title(title_substring)

    async def list_window_titles(self) -> list[str]:
        await self._check("list_window_titles")
        return self.active_window.get_all_window_titles()

    # ------------------------------------------------------------------
    # Monitor / Screen
    # ------------------------------------------------------------------

    async def get_monitors(self) -> list[dict]:
        await self._check("get_monitors")
        return self.monitor.get_monitors()

    async def get_cursor_position(self) -> dict:
        await self._check("get_cursor_position")
        return self.monitor.get_cursor_position()

    async def get_screen_size(self) -> dict:
        await self._check("get_screen_size")
        return self.monitor.get_screen_size()

    async def get_active_monitor(self) -> dict:
        await self._check("get_active_monitor")
        return self.monitor.get_active_monitor()

    # ------------------------------------------------------------------
    # UI Automation
    # ------------------------------------------------------------------

    async def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> None:
        await self._check("ui_click", PermissionLevel.SENSITIVE)
        self.ui_automation.click(x, y, button, clicks)

    async def double_click(self, x: int, y: int) -> None:
        await self._check("ui_double_click", PermissionLevel.SENSITIVE)
        self.ui_automation.double_click(x, y)

    async def right_click(self, x: int, y: int) -> None:
        await self._check("ui_right_click", PermissionLevel.SENSITIVE)
        self.ui_automation.right_click(x, y)

    async def type_text(self, text: str, interval: float = 0.0) -> None:
        await self._check("ui_type_text", PermissionLevel.SENSITIVE)
        self.ui_automation.type_text(text, interval)

    async def press_key(self, key: str) -> None:
        await self._check("ui_press_key", PermissionLevel.SENSITIVE)
        self.ui_automation.press_key(key)

    async def hotkey(self, *keys: str) -> None:
        await self._check("ui_hotkey", PermissionLevel.SENSITIVE)
        self.ui_automation.hotkey(*keys)

    async def move_mouse(self, x: int, y: int, duration: float = 0.0) -> None:
        await self._check("ui_move_mouse", PermissionLevel.SENSITIVE)
        self.ui_automation.move_mouse(x, y, duration)

    async def scroll(self, clicks: int, x: int | None = None, y: int | None = None) -> None:
        await self._check("ui_scroll", PermissionLevel.SENSITIVE)
        self.ui_automation.scroll(clicks, x, y)

    async def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.2) -> None:
        await self._check("ui_drag", PermissionLevel.SENSITIVE)
        self.ui_automation.drag(start_x, start_y, end_x, end_y, duration)

    async def get_screenshot(self) -> bytes:
        await self._check("get_screenshot", PermissionLevel.SENSITIVE)
        return self.ui_automation.get_screenshot()

    # ------------------------------------------------------------------
    # System Info
    # ------------------------------------------------------------------

    async def get_system_info(self) -> SystemInfo:
        await self._check("get_system_info")
        result = self.system_info.get_system_info()
        return SystemInfo(
            os=result["os"],
            os_version=result["os_version"],
            cpu=result["cpu"],
            cpu_percent=result["cpu_percent"],
            ram_total_gb=result["ram_total_gb"],
            ram_used_gb=result["ram_used_gb"],
            ram_percent=result["ram_percent"],
        )

    async def get_disk_usage(self) -> list[dict]:
        await self._check("get_disk_usage")
        return self.system_info.get_disk_usage()

    async def get_network_info(self) -> dict:
        await self._check("get_network_info")
        return self.system_info.get_network_info()
