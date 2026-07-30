"""Provider service — AI provider detection and connectivity."""

import logging

from launcher.services.health_service import HealthService
from launcher.services.config_service import ConfigService

logger = logging.getLogger("eve.launcher")


class ProviderService:
    def __init__(self, health_service: HealthService, config_service: ConfigService):
        self._health = health_service
        self._config = config_service

    async def check_all(self):
        api_keys = self._config.api_keys
        providers_cfg = self._config.ai_providers_config
        ollama_url = ""
        if isinstance(providers_cfg, dict) and "ollama" in providers_cfg:
            ollama_url = providers_cfg["ollama"].get("url", "http://127.0.0.1:11434")
        await self._health.check_all_ai_providers(api_keys, ollama_url)

    def get_status(self) -> dict[str, dict]:
        return {
            name: {"connected": ps.connected, "error": ps.error}
            for name, ps in self._health.providers.items()
        }

    def connected_providers(self) -> list[str]:
        return [name for name, ps in self._health.providers.items() if ps.connected]
