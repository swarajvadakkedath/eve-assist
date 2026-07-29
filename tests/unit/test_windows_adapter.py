"""Tests for the Windows Adapter — all Windows APIs are mocked."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from aios.adapters.base_adapter import FileInfo, ProcessInfo, SystemInfo, WindowInfo
from aios.core.windows import WindowsAdapter
from aios.core.permission_manager import PermissionLevel
from aios.core.windows.exceptions import (
    ActiveWindowError,
    ClipboardError,
    FileNotFoundError_,
    FileOperationError,
    MonitorError,
    ProcessError,
    ProcessNotFoundError,
    SystemInfoError,
    UIAutomationError,
    ValidationError,
    WindowsAdapterError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_services():
    clip = MagicMock()
    fs = MagicMock()
    proc = MagicMock()
    aw = MagicMock()
    mon = MagicMock()
    uia = MagicMock()
    si = MagicMock()
    return clip, fs, proc, aw, mon, uia, si


@pytest.fixture
def adapter(mock_services):
    clip, fs, proc, aw, mon, uia, si = mock_services
    return WindowsAdapter(
        clipboard=clip,
        filesystem=fs,
        process=proc,
        active_window=aw,
        monitor=mon,
        ui_automation=uia,
        system_info=si,
    )


@pytest.fixture
def adapter_with_permissions(mock_services):
    clip, fs, proc, aw, mon, uia, si = mock_services
    pm = MagicMock()
    pm.check_permission = AsyncMock(return_value=MagicMock(granted=True))
    eb = MagicMock()
    eb.publish = AsyncMock()
    return WindowsAdapter(
        clipboard=clip,
        filesystem=fs,
        process=proc,
        active_window=aw,
        monitor=mon,
        ui_automation=uia,
        system_info=si,
        permission_manager=pm,
        event_bus=eb,
    )


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestConstructor:
    def test_default_constructs(self):
        adapter = WindowsAdapter()
        assert adapter.clipboard is not None
        assert adapter.filesystem is not None
        assert adapter.process is not None
        assert adapter.active_window is not None
        assert adapter.monitor is not None
        assert adapter.ui_automation is not None
        assert adapter.system_info is not None

    def test_di_registration(self):
        from aios.core.di_container import DIContainer
        container = DIContainer()
        WindowsAdapter.register_in_container(container)
        resolved = container.resolve(WindowsAdapter)
        assert isinstance(resolved, WindowsAdapter)


# ---------------------------------------------------------------------------
# Clipboard
# ---------------------------------------------------------------------------


class TestClipboard:
    async def test_get_text(self, adapter):
        adapter.clipboard.get_text.return_value = "hello"
        result = await adapter.clipboard_get_text()
        assert result == "hello"
        adapter.clipboard.get_text.assert_called_once()

    async def test_get_text_error(self, adapter):
        adapter.clipboard.get_text.side_effect = ClipboardError("fail")
        with pytest.raises(ClipboardError):
            await adapter.clipboard_get_text()

    async def test_set_text(self, adapter):
        await adapter.clipboard_set_text("world")
        adapter.clipboard.set_text.assert_called_once_with("world")

    async def test_clear(self, adapter):
        await adapter.clipboard_clear()
        adapter.clipboard.clear.assert_called_once()


# ---------------------------------------------------------------------------
# Filesystem
# ---------------------------------------------------------------------------


class TestFilesystem:
    async def test_search_files(self, adapter):
        adapter.filesystem.search_files.return_value = [
            {"path": "/a.txt", "name": "a.txt", "size": 10, "is_dir": False, "modified": "2024-01-01", "created": "2024-01-01"},
        ]
        results = await adapter.search_files("*.txt")
        assert len(results) == 1
        assert isinstance(results[0], FileInfo)
        assert results[0].name == "a.txt"

    async def test_read_file(self, adapter):
        adapter.filesystem.read_file.return_value = "content"
        result = await adapter.read_file("/test.txt")
        assert result == "content"

    async def test_read_file_not_found(self, adapter):
        adapter.filesystem.read_file.side_effect = FileNotFoundError_("not found")
        with pytest.raises(FileNotFoundError_):
            await adapter.read_file("/missing.txt")

    async def test_write_file(self, adapter):
        await adapter.write_file("/test.txt", "data")
        adapter.filesystem.write_file.assert_called_once_with("/test.txt", "data")

    async def test_delete_file(self, adapter):
        await adapter.delete_file("/test.txt")
        adapter.filesystem.delete_file.assert_called_once_with("/test.txt")

    async def test_create_directory(self, adapter):
        await adapter.create_directory("/newdir")
        adapter.filesystem.create_directory.assert_called_once_with("/newdir")

    async def test_move_file(self, adapter):
        await adapter.move_file("/src.txt", "/dst.txt")
        adapter.filesystem.move_file.assert_called_once_with("/src.txt", "/dst.txt")

    async def test_copy_file(self, adapter):
        await adapter.copy_file("/src.txt", "/dst.txt")
        adapter.filesystem.copy_file.assert_called_once_with("/src.txt", "/dst.txt")

    async def test_get_file_metadata(self, adapter):
        adapter.filesystem.get_metadata.return_value = {"path": "/a.txt", "name": "a.txt"}
        result = await adapter.get_file_metadata("/a.txt")
        assert result["name"] == "a.txt"

    async def test_file_exists(self, adapter):
        adapter.filesystem.exists.return_value = True
        result = await adapter.file_exists("/a.txt")
        assert result is True

    async def test_search_files_error(self, adapter):
        adapter.filesystem.search_files.side_effect = FileOperationError("fail")
        with pytest.raises(FileOperationError):
            await adapter.search_files("*.txt")


# ---------------------------------------------------------------------------
# Process
# ---------------------------------------------------------------------------


class TestProcess:
    async def test_list_processes(self, adapter):
        adapter.process.list_processes.return_value = [
            {"pid": 1, "name": "proc1", "cpu_percent": 0.5, "memory_mb": 10.0, "create_time": "2024-01-01", "status": "running"},
        ]
        results = await adapter.list_processes()
        assert len(results) == 1
        assert isinstance(results[0], ProcessInfo)
        assert results[0].pid == 1

    async def test_get_process_info(self, adapter):
        adapter.process.get_process_info.return_value = {"pid": 1, "name": "proc1"}
        result = await adapter.get_process_info(1)
        assert result["pid"] == 1

    async def test_find_process(self, adapter):
        adapter.process.find_process.return_value = [{"pid": 1, "name": "proc1"}]
        result = await adapter.find_process("proc1")
        assert len(result) == 1

    async def test_start_process(self, adapter):
        adapter.process.start_process.return_value = 42
        pid = await adapter.start_process("notepad.exe")
        assert pid == 42

    async def test_kill_process(self, adapter):
        await adapter.kill_process(123)
        adapter.process.terminate_process.assert_called_once_with(123, force=True)

    async def test_terminate_process(self, adapter):
        await adapter.terminate_process(456)
        adapter.process.terminate_process.assert_called_once_with(456, force=False)

    async def test_process_not_found(self, adapter):
        adapter.process.get_process_info.side_effect = ProcessNotFoundError("not found")
        with pytest.raises(ProcessNotFoundError):
            await adapter.get_process_info(999)

    async def test_process_error(self, adapter):
        adapter.process.list_processes.side_effect = ProcessError("fail")
        with pytest.raises(ProcessError):
            await adapter.list_processes()


# ---------------------------------------------------------------------------
# Active Window
# ---------------------------------------------------------------------------


class TestActiveWindow:
    async def test_get_active_window(self, adapter):
        adapter.active_window.get_active_window.return_value = {
            "title": "Test - Notepad", "app": "Notepad",
            "x": 0, "y": 0, "width": 800, "height": 600,
            "process_id": 0, "process_name": "",
        }
        result = await adapter.get_active_window()
        assert isinstance(result, WindowInfo)
        assert result.title == "Test - Notepad"

    async def test_search_windows(self, adapter):
        adapter.active_window.get_window_by_title.return_value = [{"title": "Test"}]
        result = await adapter.search_windows("Test")
        assert len(result) == 1

    async def test_list_window_titles(self, adapter):
        adapter.active_window.get_all_window_titles.return_value = ["A", "B"]
        result = await adapter.list_window_titles()
        assert result == ["A", "B"]

    async def test_active_window_error(self, adapter):
        adapter.active_window.get_active_window.side_effect = ActiveWindowError("fail")
        with pytest.raises(ActiveWindowError):
            await adapter.get_active_window()


# ---------------------------------------------------------------------------
# Monitor / Screen
# ---------------------------------------------------------------------------


class TestMonitor:
    async def test_get_monitors(self, adapter):
        adapter.monitor.get_monitors.return_value = [{"name": "Monitor1", "width": 1920, "height": 1080}]
        result = await adapter.get_monitors()
        assert len(result) == 1

    async def test_get_cursor_position(self, adapter):
        adapter.monitor.get_cursor_position.return_value = {"x": 100, "y": 200}
        result = await adapter.get_cursor_position()
        assert result["x"] == 100

    async def test_get_screen_size(self, adapter):
        adapter.monitor.get_screen_size.return_value = {"width": 1920, "height": 1080}
        result = await adapter.get_screen_size()
        assert result["width"] == 1920

    async def test_get_active_monitor(self, adapter):
        adapter.monitor.get_active_monitor.return_value = {"name": "Primary", "width": 1920}
        result = await adapter.get_active_monitor()
        assert result["name"] == "Primary"

    async def test_monitor_error(self, adapter):
        adapter.monitor.get_monitors.side_effect = MonitorError("fail")
        with pytest.raises(MonitorError):
            await adapter.get_monitors()


# ---------------------------------------------------------------------------
# UI Automation
# ---------------------------------------------------------------------------


class TestUIAutomation:
    async def test_click(self, adapter):
        await adapter.click(100, 200)
        adapter.ui_automation.click.assert_called_once_with(100, 200, "left", 1)

    async def test_double_click(self, adapter):
        await adapter.double_click(100, 200)
        adapter.ui_automation.double_click.assert_called_once_with(100, 200)

    async def test_right_click(self, adapter):
        await adapter.right_click(100, 200)
        adapter.ui_automation.right_click.assert_called_once_with(100, 200)

    async def test_type_text(self, adapter):
        await adapter.type_text("hello", 0.1)
        adapter.ui_automation.type_text.assert_called_once_with("hello", 0.1)

    async def test_press_key(self, adapter):
        await adapter.press_key("enter")
        adapter.ui_automation.press_key.assert_called_once_with("enter")

    async def test_hotkey(self, adapter):
        await adapter.hotkey("ctrl", "c")
        adapter.ui_automation.hotkey.assert_called_once_with("ctrl", "c")

    async def test_move_mouse(self, adapter):
        await adapter.move_mouse(300, 400, 0.5)
        adapter.ui_automation.move_mouse.assert_called_once_with(300, 400, 0.5)

    async def test_scroll(self, adapter):
        await adapter.scroll(3, 100, 200)
        adapter.ui_automation.scroll.assert_called_once_with(3, 100, 200)

    async def test_drag(self, adapter):
        await adapter.drag(0, 0, 100, 100, 0.3)
        adapter.ui_automation.drag.assert_called_once_with(0, 0, 100, 100, 0.3)

    async def test_get_screenshot(self, adapter):
        adapter.ui_automation.get_screenshot.return_value = b"pngdata"
        result = await adapter.get_screenshot()
        assert result == b"pngdata"

    async def test_ui_error(self, adapter):
        adapter.ui_automation.click.side_effect = UIAutomationError("fail")
        with pytest.raises(UIAutomationError):
            await adapter.click(0, 0)


# ---------------------------------------------------------------------------
# System Info
# ---------------------------------------------------------------------------


class TestSystemInfo:
    async def test_get_system_info(self, adapter):
        adapter.system_info.get_system_info.return_value = {
            "os": "Windows", "os_version": "10", "cpu": "8",
            "cpu_percent": 25.0, "ram_total_gb": 16.0, "ram_used_gb": 8.0,
            "ram_percent": 50.0, "hostname": "pc", "os_release": "10",
            "username": "user", "disk_total_gb": 256.0, "disk_used_gb": 128.0,
            "disk_free_gb": 128.0, "disk_percent": 50.0,
            "uptime_seconds": 3600, "architecture": "x64", "processor": "Intel",
            "ram_available_gb": 8.0,
        }
        result = await adapter.get_system_info()
        assert isinstance(result, SystemInfo)
        assert result.os == "Windows"
        assert result.ram_total_gb == 16.0

    async def test_get_disk_usage(self, adapter):
        adapter.system_info.get_disk_usage.return_value = [{"device": "C:", "total_gb": 256}]
        result = await adapter.get_disk_usage()
        assert len(result) == 1

    async def test_get_network_info(self, adapter):
        adapter.system_info.get_network_info.return_value = {"bytes_sent": 1000}
        result = await adapter.get_network_info()
        assert result["bytes_sent"] == 1000

    async def test_system_info_error(self, adapter):
        adapter.system_info.get_system_info.side_effect = SystemInfoError("fail")
        with pytest.raises(SystemInfoError):
            await adapter.get_system_info()


# ---------------------------------------------------------------------------
# Permission Manager & Event Bus Integration
# ---------------------------------------------------------------------------


class TestPermissions:
    async def test_permission_denied(self, adapter):
        pm = MagicMock()
        pm.check_permission = AsyncMock(return_value=MagicMock(granted=False))
        adapter._permission_manager = pm
        with pytest.raises(WindowsAdapterError, match="Permission denied"):
            await adapter.read_file("/test.txt")

    async def test_event_published_on_clipboard_read(self, adapter_with_permissions):
        adapter = adapter_with_permissions
        adapter.clipboard.get_text.return_value = "data"
        await adapter.clipboard_get_text()
        adapter._event_bus.publish.assert_called_once()
        args = adapter._event_bus.publish.await_args[0]
        assert args[0] == "clipboard:read"

    async def test_event_published_on_file_write(self, adapter_with_permissions):
        adapter = adapter_with_permissions
        await adapter.write_file("/test.txt", "data")
        adapter._event_bus.publish.assert_called_once()
        args = adapter._event_bus.publish.await_args[0]
        assert args[0] == "file:changed"

    async def test_event_published_on_process_start(self, adapter_with_permissions):
        adapter = adapter_with_permissions
        adapter.process.start_process.return_value = 42
        await adapter.start_process("calc.exe")
        adapter._event_bus.publish.assert_called()
        events = [str(c) for c in adapter._event_bus.publish.await_args_list]
        assert any("process:started" in e for e in events)

    async def test_no_event_bus_does_not_crash(self, adapter):
        adapter.clipboard.get_text.return_value = "data"
        result = await adapter.clipboard_get_text()
        assert result == "data"

    async def test_no_permission_manager_grants_all(self, adapter):
        adapter.filesystem.read_file.return_value = "data"
        result = await adapter.read_file("/test.txt")
        assert result == "data"

    async def test_permission_checked_for_sensitive_action(self, adapter_with_permissions):
        adapter = adapter_with_permissions
        adapter.ui_automation.get_screenshot.return_value = b"png"
        await adapter.get_screenshot()
        adapter._permission_manager.check_permission.assert_called_with(
            "get_screenshot", PermissionLevel.SENSITIVE
        )

    async def test_permission_checked_for_clipboard(self, adapter_with_permissions):
        adapter = adapter_with_permissions
        adapter.clipboard.get_text.return_value = ""
        await adapter.clipboard_get_text()
        adapter._permission_manager.check_permission.assert_called_with(
            "clipboard_get_text", PermissionLevel.READ
        )


# ---------------------------------------------------------------------------
# Di Container Integration
# ---------------------------------------------------------------------------


class TestDIContainer:
    def test_register_and_resolve(self):
        from aios.core.di_container import DIContainer
        from aios.core.permission_manager import PermissionManager
        from aios.core.event_bus import EventBus

        container = DIContainer()
        eb = EventBus()
        pm = PermissionManager()
        PermissionManager.register_in_container(container, event_bus=eb)
        WindowsAdapter.register_in_container(container, permission_manager=pm, event_bus=eb)

        resolved = container.resolve(WindowsAdapter)
        assert isinstance(resolved, WindowsAdapter)
        assert resolved._permission_manager is pm
        assert resolved._event_bus is eb

    def test_register_and_resolve_defaults(self):
        from aios.core.di_container import DIContainer

        container = DIContainer()
        WindowsAdapter.register_in_container(container)

        resolved = container.resolve(WindowsAdapter)
        assert isinstance(resolved, WindowsAdapter)
        assert resolved._permission_manager is None
        assert resolved._event_bus is None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_importable(self):
        from aios.core.windows.validation import validate_path, validate_pid, validate_process_name
        assert callable(validate_path)
        assert callable(validate_pid)
        assert callable(validate_process_name)

    def test_validate_pid_valid(self):
        from aios.core.windows.validation import validate_pid
        assert validate_pid(1) == 1
        assert validate_pid(99999) == 99999

    def test_validate_pid_invalid(self):
        from aios.core.windows.validation import validate_pid
        with pytest.raises(ValidationError):
            validate_pid(-1)
        with pytest.raises(ValidationError):
            validate_pid(0)

    def test_validate_process_name_valid(self):
        from aios.core.windows.validation import validate_process_name
        assert validate_process_name("notepad.exe") == "notepad.exe"
        assert validate_process_name("chrome") == "chrome"

    def test_validate_process_name_invalid(self):
        from aios.core.windows.validation import validate_process_name
        with pytest.raises(ValidationError):
            validate_process_name("")
        with pytest.raises(ValidationError):
            validate_process_name("a" * 261)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TestExceptions:
    def test_all_exceptions_are_typed(self):
        from aios.core.windows.exceptions import (
            WindowsAdapterError,
            ClipboardError,
            FileOperationError,
            FileNotFoundError_,
            PathTraversalError,
            ProcessError,
            ProcessNotFoundError,
            ProcessTerminationError,
            ActiveWindowError,
            MonitorError,
            UIAutomationError,
            SystemInfoError,
            ValidationError,
        )
        assert issubclass(ClipboardError, WindowsAdapterError)
        assert issubclass(FileOperationError, WindowsAdapterError)
        assert issubclass(FileNotFoundError_, WindowsAdapterError)
        assert issubclass(PathTraversalError, WindowsAdapterError)
        assert issubclass(ProcessError, WindowsAdapterError)
        assert issubclass(ProcessNotFoundError, WindowsAdapterError)
        assert issubclass(ProcessTerminationError, WindowsAdapterError)
        assert issubclass(ActiveWindowError, WindowsAdapterError)
        assert issubclass(MonitorError, WindowsAdapterError)
        assert issubclass(UIAutomationError, WindowsAdapterError)
        assert issubclass(SystemInfoError, WindowsAdapterError)
        assert issubclass(ValidationError, WindowsAdapterError)
