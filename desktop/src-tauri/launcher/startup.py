"""Backward-compatible startup module.

New code should import from launcher.services.startup_service.
"""

from launcher.services.startup_service import StartupService, wait_for_url, BACKEND_TIMEOUT, FRONTEND_TIMEOUT  # noqa: F401


class StartupOrchestrator(StartupService):
    def __init__(self, pm, hc, config, on_status=None):
        from launcher.services.backend_service import BackendService
        from launcher.services.frontend_service import BrowserFrontendService
        from launcher.services.provider_service import ProviderService
        super().__init__(
            backend=BackendService(pm),
            frontend=BrowserFrontendService(pm),
            health=hc,
            providers=ProviderService(hc, config),
            config=config,
            on_status=on_status,
        )
