"""Plugin SDK — official developer API for building AIOS plugins."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from aios.plugins.manifest import PluginManifest
from aios.plugins.models import PluginResult, PluginCapability


class AIOSPlugin(ABC):
    """
    Base class for all AIOS plugins.
    Plugin authors should inherit from this class and implement the required methods.
    """
    
    metadata: Optional[PluginManifest] = None
    logger: Any = None
    
    def __init__(self):
        self._initialized = False
        self._event_bus = None
        self._permission_manager = None
        self._tool_manager = None
        self._capability_registry = None
        self._settings = None
        self._context = {}

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the plugin, load resources, etc."""
        ...

    @abstractmethod
    async def register(self) -> None:
        """Register tools, capabilities, and event listeners."""
        ...

    async def start(self) -> None:
        """Start plugin execution/background tasks."""
        pass

    async def health(self) -> Dict[str, Any]:
        """Return the current health status of the plugin."""
        return {"status": "alive"}

    async def stop(self) -> None:
        """Stop background tasks."""
        pass

    async def shutdown(self) -> None:
        """Cleanup resources before unloading."""
        pass

    async def dispose(self) -> None:
        """Final cleanup when the plugin is removed."""
        pass

    # Helper methods for plugin authors

    async def publish_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Publish an event to the AIOS Event Bus."""
        if self._event_bus and self.metadata:
            await self._event_bus.publish(f"plugin:{self.metadata.id}:{event_type}", payload)

    async def request_permission(self, permission: str, level: int = 1, reason: str = "") -> bool:
        """Request a permission from the AIOS Permission Manager."""
        if self._permission_manager and self.metadata:
            return await self._permission_manager.request_permission(
                plugin_id=self.metadata.id,
                permission=permission,
                level=level,
                reason=reason
            )
        return False

    async def register_tool(self, tool_definition: Dict[str, Any]) -> bool:
        """Register a tool with the AIOS Tool Manager."""
        if self._tool_manager and self.metadata:
            tool_definition["plugin_id"] = self.metadata.id
            return await self._tool_manager.register_tool(tool_definition)
        return False

    async def register_capability(self, capability: PluginCapability) -> bool:
        """Register a capability with the AIOS Capability Registry."""
        if self._capability_registry and self.metadata:
            from aios.core.capability_registry import Capability
            cap = Capability(
                id=capability.id,
                name=capability.name,
                description=capability.description,
                provider_type="plugin",
                provider_id=self.metadata.id,
                parameters=capability.parameters,
                returns=capability.returns,
                permission_level=capability.permission_level,
                tags=capability.tags
            )
            await self._capability_registry.register_capability(cap)
            return True
        return False

    async def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a plugin-specific setting."""
        if self._settings:
            return await self._settings.get(key, default)
        return default

    def log_info(self, message: str, **kwargs) -> None:
        """Log an informational message."""
        if self.logger:
            self.logger.info(message, plugin_id=self.plugin_id, **kwargs)

    def log_error(self, message: str, **kwargs) -> None:
        """Log an error message."""
        if self.logger:
            self.logger.error(message, plugin_id=self.plugin_id, **kwargs)

    def log_warning(self, message: str, **kwargs) -> None:
        """Log a warning message."""
        if self.logger:
            self.logger.warning(message, plugin_id=self.plugin_id, **kwargs)

    def log_debug(self, message: str, **kwargs) -> None:
        """Log a debug message."""
        if self.logger:
            self.logger.debug(message, plugin_id=self.plugin_id, **kwargs)

    @property
    def plugin_id(self) -> str:
        """Return the unique plugin identifier."""
        return self.metadata.id if self.metadata else "unknown"

    @property
    def plugin_name(self) -> str:
        """Return the human-readable plugin name."""
        return self.metadata.name if self.metadata else "Unknown Plugin"

    def _inject_services(self, event_bus, permission_manager, tool_manager, capability_registry, settings):
        """Internal method to inject AIOS services into the plugin instance."""
        self._event_bus = event_bus
        self._permission_manager = permission_manager
        self._tool_manager = tool_manager
        self._capability_registry = capability_registry
        self._settings = settings
