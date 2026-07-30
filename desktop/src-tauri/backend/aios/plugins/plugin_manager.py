"""Plugin Manager — orchestrates discovery, loading, lifecycle, and runtime."""

from pathlib import Path

from aios.plugins.models import Plugin, PluginStatus, PluginScope
from aios.plugins.manifest import PluginManifest
from aios.plugins.discovery import PluginDiscovery
from aios.plugins.validator import PluginValidator
from aios.plugins.verifier import PluginVerifier
from aios.plugins.registry import PluginRegistry
from aios.plugins.loader import PluginLoader
from aios.plugins.runtime import PluginRuntime
from aios.plugins.health import PluginHealthMonitor
from aios.plugins.lifecycle import PluginLifecycle
from aios.plugins.events import PluginEventPublisher
from aios.plugins.repository import PluginRepository
from aios.plugins.isolator import PluginIsolator
from aios.plugins.permissions import PluginPermissionManager
from aios.plugins.exceptions import PluginError, PluginNotFoundError


class PluginManager:
    def __init__(
        self,
        tool_manager=None,
        capability_registry=None,
        event_bus=None,
        permission_manager=None,
        settings=None,
        base_path: str | None = None,
    ):
        self._event_bus = event_bus
        self._event_publisher = PluginEventPublisher(event_bus)
        self._lifecycle = PluginLifecycle()
        self._registry = PluginRegistry()
        self._health = PluginHealthMonitor()
        self._isolator = PluginIsolator()
        self._perm_mgr = PluginPermissionManager(permission_manager)
        self._repo = PluginRepository(base_path)
        self._discovery = PluginDiscovery(
            builtin_dirs=[],
            user_dir=str(Path(base_path or Path.home() / ".aios" / "plugins")),
        )
        self._validator = PluginValidator()
        self._verifier = PluginVerifier()
        self._loader = PluginLoader(
            registry=self._registry,
            discovery=self._discovery,
            validator=self._validator,
            verifier=self._verifier,
            lifecycle=self._lifecycle,
            event_publisher=self._event_publisher,
            repository=self._repo,
            event_bus=event_bus,
            permission_manager=permission_manager,
            tool_manager=tool_manager,
            capability_registry=capability_registry,
            settings=settings,
        )
        self._runtime = PluginRuntime(
            registry=self._registry,
            lifecycle=self._lifecycle,
            health=self._health,
            event_publisher=self._event_publisher,
            permission_manager=permission_manager,
            tool_manager=tool_manager,
            capability_registry=capability_registry,
            event_bus=event_bus,
        )

    async def initialize(self) -> None:
        loaded = await self._loader.load_all()
        for plugin in loaded:
            if plugin.state.status == PluginStatus.LOADED:
                await self._runtime.initialize_plugin(plugin.id)
                await self._runtime.start_plugin(plugin.id)

    async def scan_plugins(self, plugins_path: str | None = None) -> list[PluginManifest]:
        if plugins_path:
            if str(Path(plugins_path).resolve()) not in self._discovery.get_search_paths():
                self._discovery.add_search_directory(plugins_path)
        discovered = await self._discovery.discover_all()
        seen = set()
        unique = []
        for m, p, s in discovered:
            if m.id not in seen:
                seen.add(m.id)
                unique.append(m)
        return unique

    async def load_plugin(self, manifest: PluginManifest) -> bool:
        try:
            plugin = await self._loader.load_single(manifest.id)
            if plugin:
                await self._runtime.initialize_plugin(plugin.id)
                await self._runtime.start_plugin(plugin.id)
            return plugin is not None
        except Exception:
            return False

    async def unload_plugin(self, plugin_id: str) -> bool:
        try:
            await self._runtime.stop_plugin(plugin_id)
            await self._runtime.unload_plugin(plugin_id)
            return True
        except Exception:
            return False

    async def enable_plugin(self, plugin_id: str) -> bool:
        try:
            plugin = self._registry.get_safe(plugin_id)
            if not plugin:
                return False
            if plugin.state.status == PluginStatus.DISABLED:
                plugin.state.status = PluginStatus.LOADED
                await self._runtime.initialize_plugin(plugin_id)
                await self._runtime.start_plugin(plugin_id)
            return True
        except Exception:
            return False

    async def disable_plugin(self, plugin_id: str) -> bool:
        try:
            await self._runtime.stop_plugin(plugin_id)
            plugin = self._registry.get_safe(plugin_id)
            if plugin:
                plugin.state.status = PluginStatus.DISABLED
            return True
        except Exception:
            return False

    async def reload_plugin(self, plugin_id: str) -> bool:
        try:
            await self._runtime.stop_plugin(plugin_id)
            await self._runtime.unload_plugin(plugin_id)
            await self._loader.reload(plugin_id)
            plugin = self._registry.get_safe(plugin_id)
            if plugin:
                await self._runtime.initialize_plugin(plugin_id)
                await self._runtime.start_plugin(plugin_id)
            return True
        except Exception:
            return False

    async def get_plugin(self, plugin_id: str) -> Plugin | None:
        return self._registry.get_safe(plugin_id)

    async def list_plugins(self) -> list[Plugin]:
        return self._registry.list()

    async def get_plugin_health(self, plugin_id: str):
        return await self._runtime.get_plugin_health(plugin_id)

    async def get_plugin_manifest(self, plugin_id: str):
        plugin = self._registry.get_safe(plugin_id)
        if plugin and plugin.manifest:
            return plugin.manifest.to_dict()
        return None

    async def get_plugin_capabilities(self, plugin_id: str) -> list:
        plugin = self._registry.get_safe(plugin_id)
        return [c.to_dict() for c in plugin.capabilities] if plugin else []

    async def get_plugin_permissions(self, plugin_id: str) -> dict:
        granted = await self._perm_mgr.get_granted(plugin_id)
        plugin = self._registry.get_safe(plugin_id)
        declared = list(plugin.manifest.permissions) if plugin and plugin.manifest else []
        return {"declared": declared, "granted": granted}

    async def get_plugin_config(self, plugin_id: str) -> dict:
        return await self._repo.load_config(plugin_id)

    async def update_plugin_config(self, plugin_id: str, config: dict) -> None:
        await self._repo.save_config(plugin_id, config)

    async def get_health_summary(self) -> dict:
        plugins = self._registry.list()
        return {
            "total": len(plugins),
            "active": len([p for p in plugins if p.is_active]),
            "failed": len([p for p in plugins if p.is_failed]),
            "loaded": len([p for p in plugins if p.state.status == PluginStatus.LOADED]),
            "degraded": len([p for p in plugins if p.state.status == PluginStatus.DEGRADED]),
            "disabled": len([p for p in plugins if p.state.status == PluginStatus.DISABLED]),
        }

    async def search_plugins(self, query: str) -> list[Plugin]:
        plugins = self._registry.list()
        q = query.lower()
        return [
            p for p in plugins
            if q in p.id.lower()
            or (p.manifest and q in p.manifest.name.lower())
            or (p.manifest and q in p.manifest.description.lower())
            or any(q in t for t in (p.manifest.tags if p.manifest else []))
        ]

    async def shutdown(self) -> None:
        for plugin in self._registry.list():
            if plugin.is_active:
                await self._runtime.stop_plugin(plugin.id)
                await self._runtime.unload_plugin(plugin.id)
