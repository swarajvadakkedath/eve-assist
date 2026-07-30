"""Backward-compatible config module.

New code should import from launcher.services.config_service.
"""

from pathlib import Path

from launcher.services.config_service import ConfigService, DEFAULT_CONFIG  # noqa: F401

CONFIG_DIR = Path.home() / ".eve"
CONFIG_FILE = CONFIG_DIR / "launcher_config.json"


class LauncherConfig(ConfigService):
    def __init__(self):
        super().__init__(config_dir=str(CONFIG_DIR), config_file=str(CONFIG_FILE))
