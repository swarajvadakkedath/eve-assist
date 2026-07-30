"""Backward-compatible re-export of process manager.

New code should import from launcher.services.process_service.
"""

from launcher.services.process_service import ProcessService, ManagedProcess  # noqa: F401

ProcessManager = ProcessService
