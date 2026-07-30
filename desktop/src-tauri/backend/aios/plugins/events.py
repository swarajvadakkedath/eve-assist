"""Plugin event publishing — standardized lifecycle events."""

from aios.utils.logger import get_logger

logger = get_logger(__name__)


class PluginEventPublisher:
    def __init__(self, event_bus=None):
        self._event_bus = event_bus

    async def publish(self, event_type: str, payload: dict) -> None:
        if not self._event_bus:
            return
        try:
            await self._event_bus.publish(
                event_type=f"plugin:{event_type}",
                payload=payload,
                source="plugin_system",
            )
        except Exception as e:
            logger.error("plugin.event_publish_failed", event_type=event_type, error=str(e))

    async def discovered(self, plugin_id: str, name: str, source: str) -> None:
        await self.publish("discovered", {"plugin_id": plugin_id, "name": name, "source": source})

    async def validated(self, plugin_id: str, valid: bool, errors: list[str] | None = None) -> None:
        await self.publish("validated", {"plugin_id": plugin_id, "valid": valid, "errors": errors or []})

    async def verified(self, plugin_id: str, verified: bool, message: str = "") -> None:
        await self.publish("verified", {"plugin_id": plugin_id, "verified": verified, "message": message})

    async def loaded(self, plugin_id: str, name: str = "", version: str = "") -> None:
        await self.publish("loaded", {"plugin_id": plugin_id, "name": name, "version": version})

    async def started(self, plugin_id: str) -> None:
        await self.publish("started", {"plugin_id": plugin_id})

    async def stopped(self, plugin_id: str, reason: str = "") -> None:
        await self.publish("stopped", {"plugin_id": plugin_id, "reason": reason})

    async def unloaded(self, plugin_id: str) -> None:
        await self.publish("unloaded", {"plugin_id": plugin_id})

    async def failed(self, plugin_id: str, error: str) -> None:
        await self.publish("failed", {"plugin_id": plugin_id, "error": error})

    async def health_changed(self, plugin_id: str, status: str) -> None:
        await self.publish("health_changed", {"plugin_id": plugin_id, "status": status})

    async def updated(self, plugin_id: str, old_version: str, new_version: str) -> None:
        await self.publish("updated", {"plugin_id": plugin_id, "old_version": old_version, "new_version": new_version})

    async def permission_requested(self, plugin_id: str, permission: str, level: int) -> None:
        await self.publish("permission_requested", {"plugin_id": plugin_id, "permission": permission, "level": level})
