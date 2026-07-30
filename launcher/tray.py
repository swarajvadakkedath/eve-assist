"""Backward-compatible re-export of tray.

New code should import from launcher.services.tray_service.
"""

from launcher.services.tray_service import TrayService, HAS_TRAY  # noqa: F401

TrayManager = TrayService
