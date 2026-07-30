"""Backward-compatible logger module.

New code should import from launcher.services.logger_service.
"""

from pathlib import Path

from launcher.services.logger_service import LoggerService

LOG_DIR = Path.home() / ".eve" / "logs"
LOG_FILE = LOG_DIR / "launcher.log"


def setup_launcher_logging(level: str = "INFO"):
    svc = LoggerService(log_dir=str(LOG_DIR), log_file=str(LOG_FILE))
    return svc.setup(level)


def open_log_folder():
    svc = LoggerService(log_dir=str(LOG_DIR), log_file=str(LOG_FILE))
    svc.open_log_folder()
