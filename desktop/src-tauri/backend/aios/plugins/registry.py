"""Plugin registry — thread-safe storage and lookup for loaded plugins."""

import asyncio
from typing import Dict, List, Optional

from aios.plugins.models import Plugin, PluginStatus
from aios.plugins.exceptions import PluginNotFoundError


class PluginRegistry:
    """
    Maintains the collection of loaded plugins.
    Provides thread-safe access for registration, lookup, and removal.
    """

    def __init__(self):
        self._plugins: Dict[str, Plugin] = {}
        self._lock = asyncio.Lock()

    def register(self, plugin: Plugin) -> None:
        """Add a plugin to the registry."""
        if not plugin.id:
            raise ValueError("Plugin must have an ID")
        self._plugins[plugin.id] = plugin

    def get(self, plugin_id: str) -> Plugin:
        """Get a plugin by its ID. Raises PluginNotFoundError if not found."""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            raise PluginNotFoundError(f"Plugin '{plugin_id}' not found", plugin_id)
        return plugin

    def get_safe(self, plugin_id: str) -> Optional[Plugin]:
        """Get a plugin by its ID. Returns None if not found."""
        return self._plugins.get(plugin_id)

    def list(self) -> List[Plugin]:
        """Return a list of all registered plugins."""
        return list(self._plugins.values())

    def list_active(self) -> List[Plugin]:
        """Return a list of all active plugins."""
        return [p for p in self._plugins.values() if p.is_active]

    def remove(self, plugin_id: str) -> Optional[Plugin]:
        """Remove a plugin from the registry."""
        return self._plugins.pop(plugin_id, None)

    def exists(self, plugin_id: str) -> bool:
        """Check if a plugin exists in the registry."""
        return plugin_id in self._plugins

    def clear(self) -> None:
        """Clear all plugins from the registry."""
        self._plugins.clear()

    @property
    def count(self) -> int:
        """Return the total number of registered plugins."""
        return len(self._plugins)
