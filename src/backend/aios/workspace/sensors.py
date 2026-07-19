"""Workspace Sensors — modular information collectors."""

import os
import psutil
from datetime import datetime
from typing import Any
from aios.workspace.models import Application, AppCategory
from aios.workspace.interfaces import IWorkspaceSensor
from aios.utils.logger import get_logger

logger = get_logger(__name__)

DEV_TOOL_PATTERNS = {
    "code.exe": AppCategory.IDE,
    "Code.exe": AppCategory.IDE,
    "cursor.exe": AppCategory.IDE,
    "windsurf.exe": AppCategory.IDE,
    "rider64.exe": AppCategory.IDE,
    "idea64.exe": AppCategory.IDE,
    "devenv.exe": AppCategory.IDE,
    "WindowsTerminal.exe": AppCategory.TERMINAL,
    "Windowsterminal.exe": AppCategory.TERMINAL,
    "cmd.exe": AppCategory.TERMINAL,
    "powershell.exe": AppCategory.TERMINAL,
    "pwsh.exe": AppCategory.TERMINAL,
    "wt.exe": AppCategory.TERMINAL,
    "git-bash.exe": AppCategory.TERMINAL,
    "bash.exe": AppCategory.TERMINAL,
    "chrome.exe": AppCategory.BROWSER,
    "msedge.exe": AppCategory.BROWSER,
    "firefox.exe": AppCategory.BROWSER,
    "Postman.exe": AppCategory.API_CLIENT,
    "DBeaver.exe": AppCategory.DB_CLIENT,
    "slack.exe": AppCategory.COMM_TOOL,
    "discord.exe": AppCategory.COMM_TOOL,
}


class ActiveWindowSensor(IWorkspaceSensor):
    def __init__(self):
        self._running = False
        self._last_title = ""

    async def start(self) -> None:
        self._running = True
        logger.info("sensor.active_window.started")

    async def stop(self) -> None:
        self._running = False
        logger.info("sensor.active_window.stopped")

    async def collect(self) -> dict:
        try:
            import pygetwindow as gw
            window = gw.getActiveWindow()
            if window and window.title:
                title = window.title
                return {
                    "active_window": title,
                    "active_app": title.split(" - ")[-1] if " - " in title else title,
                    "changed": title != self._last_title,
                }
            return {"active_window": "", "active_app": "", "changed": False}
        except Exception as e:
            logger.error("sensor.active_window.failed", error=str(e))
            return {"active_window": "", "active_app": "", "changed": False}


class ProcessSensor(IWorkspaceSensor):
    def __init__(self):
        self._running = False

    async def start(self) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False

    async def collect(self) -> dict:
        dev_apps = []
        try:
            for proc in psutil.process_iter(["pid", "name", "exe", "create_time"]):
                try:
                    name = proc.info.get("name", "")
                    if name not in DEV_TOOL_PATTERNS:
                        continue
                    category = DEV_TOOL_PATTERNS.get(name, AppCategory.UNKNOWN)
                    app = Application(
                        process_name=name,
                        executable=proc.info.get("exe", ""),
                        pid=proc.info["pid"],
                        category=category,
                        launched_at=datetime.fromtimestamp(proc.info.get("create_time", 0)) if proc.info.get("create_time") else datetime.utcnow(),
                    )
                    dev_apps.append(app)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            terminals = [a for a in dev_apps if a.category == AppCategory.TERMINAL]
            ides = [a for a in dev_apps if a.category == AppCategory.IDE]
            return {
                "applications": dev_apps,
                "terminals": terminals,
                "ides": ides,
            }
        except Exception as e:
            logger.error("sensor.process.failed", error=str(e))
            return {"applications": [], "terminals": [], "ides": []}


class FileSystemSensor(IWorkspaceSensor):
    def __init__(self):
        self._running = False

    async def start(self) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False

    async def collect(self) -> dict:
        return {}
