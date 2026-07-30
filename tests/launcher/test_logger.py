"""Tests for launcher logging."""

import logging
import tempfile
from pathlib import Path
from unittest.mock import patch

from launcher.logger import setup_launcher_logging


def _close_logger():
    root = logging.getLogger("eve.launcher")
    for h in root.handlers[:]:
        h.close()
        root.removeHandler(h)
    root.handlers.clear()


def test_setup_launcher_logging():
    _close_logger()
    with tempfile.TemporaryDirectory() as tmp:
        log_dir = Path(tmp) / "logs"
        with patch("launcher.logger.LOG_DIR", log_dir):
            with patch("launcher.logger.LOG_FILE", log_dir / "launcher.log"):
                logger = setup_launcher_logging("DEBUG")
                assert logger is not None
                assert logger.level == logging.DEBUG
                logger.info("test message")
                assert log_dir.exists()
                log_file = log_dir / "launcher.log"
                assert log_file.exists()
                _close_logger()


def test_log_levels():
    _close_logger()
    with tempfile.TemporaryDirectory() as tmp:
        log_dir = Path(tmp) / "logs"
        with patch("launcher.logger.LOG_DIR", log_dir):
            with patch("launcher.logger.LOG_FILE", log_dir / "launcher.log"):
                logger = setup_launcher_logging("ERROR")
                assert logger.level == logging.ERROR
                _close_logger()


def test_logger_singleton():
    _close_logger()
    with tempfile.TemporaryDirectory() as tmp:
        log_dir = Path(tmp) / "logs"
        with patch("launcher.logger.LOG_DIR", log_dir):
            with patch("launcher.logger.LOG_FILE", log_dir / "launcher.log"):
                l1 = setup_launcher_logging()
                l2 = setup_launcher_logging()
                assert l1 is l2
                _close_logger()
