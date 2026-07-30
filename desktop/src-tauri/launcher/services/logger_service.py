"""Logging service — centralized log management."""

import logging
import sys
from pathlib import Path

LOG_DIR = Path.home() / ".eve" / "logs"
LOG_FILE = LOG_DIR / "launcher.log"


class LoggerService:
    def __init__(self, log_dir: str | None = None, log_file: str | None = None):
        self._log_dir = Path(log_dir) if log_dir else Path(LOG_DIR)
        self._log_file = Path(log_file) if log_file else Path(LOG_FILE)
        self._logger: logging.Logger | None = None

    def setup(self, level: str = "INFO") -> logging.Logger:
        self._log_dir.mkdir(parents=True, exist_ok=True)
        logger = logging.getLogger("eve.launcher")
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        if logger.handlers:
            self._logger = logger
            return logger
        fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler = logging.FileHandler(str(self._log_file), encoding="utf-8")
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S",
        ))
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)
        self._logger = logger
        return logger

    def open_log_folder(self):
        import subprocess
        subprocess.Popen(["explorer", str(self._log_dir)])

    @property
    def logger(self) -> logging.Logger:
        if self._logger is None:
            return self.setup()
        return self._logger

    @property
    def log_dir(self) -> Path:
        return self._log_dir
