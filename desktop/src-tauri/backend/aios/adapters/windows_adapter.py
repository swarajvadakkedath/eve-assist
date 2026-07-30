"""Windows Adapter — safe OS abstraction layer."""

import os
import platform
import shutil
import subprocess
from glob import glob

import psutil

from aios.adapters.base_adapter import (
    BaseAdapter,
    FileInfo,
    ProcessInfo,
    SystemInfo,
    WindowInfo,
)


class WindowsAdapter(BaseAdapter):
    async def search_files(self, pattern: str, path: str | None = None) -> list[FileInfo]:
        search_path = path or os.path.expanduser("~")
        results = []
        for filepath in glob(os.path.join(search_path, pattern), recursive=True):
            try:
                stat = os.stat(filepath)
                results.append(FileInfo(
                    path=filepath,
                    name=os.path.basename(filepath),
                    size=stat.st_size,
                    is_dir=os.path.isdir(filepath),
                    modified=str(stat.st_mtime),
                ))
            except OSError:
                continue
        return results

    async def read_file(self, path: str) -> str:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    async def write_file(self, path: str, content: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    async def delete_file(self, path: str) -> None:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

    async def create_directory(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)

    async def list_processes(self) -> list[ProcessInfo]:
        processes = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
            try:
                processes.append(ProcessInfo(
                    pid=proc.info["pid"],
                    name=proc.info["name"],
                    cpu_percent=proc.info["cpu_percent"] or 0.0,
                    memory_mb=(proc.info["memory_info"].rss / 1024 / 1024) if proc.info["memory_info"] else 0.0,
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return sorted(processes, key=lambda p: p.memory_mb, reverse=True)

    async def start_process(self, command: str) -> int:
        import shlex
        args = shlex.split(command)
        proc = subprocess.Popen(args, shell=False)
        return proc.pid

    async def kill_process(self, pid: int) -> None:
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            proc.wait(timeout=5)
        except psutil.NoSuchProcess:
            pass
        except psutil.TimeoutExpired:
            proc.kill()

    async def get_system_info(self) -> SystemInfo:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        return SystemInfo(
            os="Windows",
            os_version=platform.version(),
            cpu=psutil.cpu_count(),
            cpu_percent=cpu_percent,
            ram_total_gb=round(memory.total / (1024**3), 1),
            ram_used_gb=round(memory.used / (1024**3), 1),
            ram_percent=memory.percent,
        )

    async def get_active_window(self) -> WindowInfo:
        try:
            import pygetwindow as gw
            window = gw.getActiveWindow()
            if window:
                return WindowInfo(
                    title=window.title,
                    app=window.title.split(" - ")[-1] if " - " in window.title else window.title,
                    x=window.left,
                    y=window.top,
                    width=window.width,
                    height=window.height,
                )
        except ImportError:
            pass
        return WindowInfo(title="", app="", x=0, y=0, width=0, height=0)

    async def get_screenshot(self) -> bytes:
        import pyautogui
        screenshot = pyautogui.screenshot()
        import io
        buf = io.BytesIO()
        screenshot.save(buf, format="PNG")
        return buf.getvalue()
