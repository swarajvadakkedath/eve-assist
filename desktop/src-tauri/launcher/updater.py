"""Auto-update placeholder — architecture for future updates."""

from dataclasses import dataclass


@dataclass
class UpdateInfo:
    version: str = ""
    available: bool = False
    download_url: str = ""
    changelog: str = ""
    mandatory: bool = False


class Updater:
    def __init__(self):
        self._update_check_url = "https://updates.eveos.ai/latest"
        self._current_version = "1.0.0"
        self._info = UpdateInfo()

    async def check_for_update(self) -> UpdateInfo:
        return UpdateInfo(available=False)

    async def download_update(self, info: UpdateInfo) -> bool:
        return False

    async def apply_update(self, info: UpdateInfo) -> bool:
        return False

    @property
    def update_available(self) -> bool:
        return self._info.available

    @property
    def update_info(self) -> UpdateInfo:
        return self._info
