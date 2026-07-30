"""Tauri frontend service — placeholder for Tauri-managed frontend.

When Tauri is the native shell, it manages the webview window.
This service exists so that LauncherService can treat the frontend
abstractly — no browser process, no npm run dev.

The Tauri window lifecycle is handled entirely in Rust.
"""

import logging


logger = logging.getLogger("eve.launcher")


class TauriFrontendService:
    def __init__(self, process_service=None):
        self._type = "tauri"
        self._alive = False

    async def start(self, url: str = "") -> int:
        self._alive = True
        logger.info("tauri frontend ready — window manages itself")
        return 0

    async def stop(self, timeout: float = 5.0):
        self._alive = False
        logger.info("tauri frontend stopped")

    async def restart(self, timeout: float = 5.0) -> int:
        return await self.start()

    async def is_alive(self) -> bool:
        return self._alive

    def get_type(self) -> str:
        return self._type
