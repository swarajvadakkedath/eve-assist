"""Backward-compatible shutdown module.

New code should import from launcher.services.shutdown_service.
"""

from launcher.services.shutdown_service import ShutdownService  # noqa: F401


class ShutdownManager(ShutdownService):
    def __init__(self, pm, hc):
        from launcher.services.backend_service import BackendService
        from launcher.services.frontend_service import BrowserFrontendService
        super().__init__(
            backend=BackendService(pm),
            frontend=BrowserFrontendService(pm),
            health=hc,
        )
