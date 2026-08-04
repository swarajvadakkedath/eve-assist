"""Plugin loader — orchestrates discovery, validation, verification, instantiation, and service injection."""

import asyncio
import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from aios.plugins.discovery import PluginDiscovery
from aios.plugins.validator import PluginValidator
from aios.plugins.verifier import PluginVerifier
from aios.plugins.registry import PluginRegistry
from aios.plugins.lifecycle import PluginLifecycle
from aios.plugins.events import PluginEventPublisher
from aios.plugins.models import Plugin, PluginStatus, PluginScope, PluginState, PluginMetadata, PluginDependency, PluginCapability
from aios.plugins.exceptions import PluginLoadError, PluginValidationError, PluginVerificationError, PluginDependencyError
from aios.plugins.repository import PluginRepository
from aios.plugins.sdk import AIOSPlugin
from aios.utils.logger import get_logger
from aios.error_intelligence import get_error_intelligence

logger = get_logger(__name__)


class PluginLoader:
    """
    Orchestrates the process of loading plugins from the filesystem.
    Ensures that plugins are valid, verified, and their dependencies are satisfied.
    Loads the entry point module and instantiates the AIOSPlugin subclass.
    """

    def __init__(
        self,
        registry: PluginRegistry,
        discovery: PluginDiscovery,
        validator: PluginValidator,
        verifier: PluginVerifier,
        lifecycle: PluginLifecycle,
        event_publisher: PluginEventPublisher | None = None,
        repository: PluginRepository | None = None,
        event_bus: Any = None,
        permission_manager: Any = None,
        tool_manager: Any = None,
        capability_registry: Any = None,
        settings: Any = None,
    ):
        self._registry = registry
        self._discovery = discovery
        self._validator = validator
        self._verifier = verifier
        self._lifecycle = lifecycle
        self._events = event_publisher
        self._repo = repository
        self._event_bus = event_bus
        self._permission_manager = permission_manager
        self._tool_manager = tool_manager
        self._capability_registry = capability_registry
        self._settings = settings
        self._loading_lock = asyncio.Lock()

    async def load_all(self) -> List[Plugin]:
        discovered = await self._discovery.discover_all()
        discovery_map = {m.id: (m, p, s) for m, p, s in discovered}
        ordered_ids = self._resolve_load_order(discovery_map)
        loaded_plugins = []
        for plugin_id in ordered_ids:
            manifest, path, scope = discovery_map[plugin_id]
            try:
                plugin = await self._load_single_internal(manifest, path, scope)
                if plugin:
                    loaded_plugins.append(plugin)
            except Exception as e:
                logger.error("loader.failed", plugin_id=plugin_id, error=str(e))
                try:
                    svc = get_error_intelligence()
                    svc.capture_exception(e, module="plugins.loader", message=f"Plugin {plugin_id} failed: {e}")
                except Exception:
                    pass
        return loaded_plugins

    async def load_single(self, plugin_id: str) -> Optional[Plugin]:
        async with self._loading_lock:
            discovered = await self._discovery.discover_all()
            target = next((item for item in discovered if item[0].id == plugin_id), None)
            if not target:
                logger.error("loader.not_found", plugin_id=plugin_id)
                return None
            manifest, path, scope = target
            return await self._load_single_internal(manifest, path, scope)

    async def reload(self, plugin_id: str) -> Optional[Plugin]:
        return await self.load_single(plugin_id)

    async def _load_single_internal(self, manifest, path, scope) -> Optional[Plugin]:
        logger.info("loader.starting", plugin_id=manifest.id, version=manifest.version)

        val_result = self._validator.validate(manifest, path)
        if not val_result.valid:
            raise PluginValidationError(
                f"Validation failed: {'; '.join(val_result.errors)}", manifest.id
            )

        ver_result = await self._verifier.verify(manifest, path)
        if not ver_result.verified:
            raise PluginVerificationError(
                f"Verification failed: {'; '.join(ver_result.messages)}", manifest.id
            )

        available_versions = {p.id: p.manifest.version for p in self._registry.list()}
        dep_result = self._validator.validate_dependencies(manifest, available_versions)
        if not dep_result.valid:
            raise PluginDependencyError(
                f"Dependencies failed: {'; '.join(dep_result.errors)}", manifest.id
            )

        source_path = Path(path) if path else None
        instance = await self._instantiate_plugin(manifest, source_path)

        plugin = Plugin(
            id=manifest.id,
            manifest=manifest,
            scope=scope,
            source=path,
            state=PluginState(status=PluginStatus.LOADING),
            metadata=self._create_metadata(manifest),
            capabilities=[PluginCapability(**c) for c in manifest.capabilities],
            dependencies=[PluginDependency(plugin_id=dep_id, version_spec=spec) for dep_id, spec in manifest.dependencies.items()],
            instance=instance,
        )

        self._registry.register(plugin)
        plugin.state.status = PluginStatus.LOADED
        logger.info("loader.completed", plugin_id=manifest.id)

        if self._events:
            await self._events.loaded(manifest.id, manifest.name, manifest.version)

        return plugin

    async def _instantiate_plugin(self, manifest, source_path: Path | None) -> Optional[AIOSPlugin]:
        if not source_path or not (source_path / manifest.entry_point).exists():
            logger.warning("loader.no_entry_point", plugin_id=manifest.id, entry=manifest.entry_point)
            return None

        try:
            sys.path.insert(0, str(source_path))
            spec = importlib.util.spec_from_file_location(
                f"aios_plugin_{manifest.id}",
                source_path / manifest.entry_point,
            )
            if not spec or not spec.loader:
                raise PluginLoadError(f"Cannot load entry point: {manifest.entry_point}", manifest.id)

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            plugin_class = None
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, AIOSPlugin) and obj is not AIOSPlugin:
                    plugin_class = obj
                    break

            if not plugin_class:
                logger.warning("loader.no_plugin_class", plugin_id=manifest.id)
                return None

            instance = plugin_class()
            instance.metadata = manifest
            instance.logger = logger
            instance._inject_services(
                event_bus=self._event_bus,
                permission_manager=self._permission_manager,
                tool_manager=self._tool_manager,
                capability_registry=self._capability_registry,
                settings=self._settings,
            )

            await instance.initialize()
            await instance.register()

            instance._initialized = True
            logger.info("loader.instantiated", plugin_id=manifest.id, class_name=plugin_class.__name__)
            return instance

        except Exception as e:
            raise PluginLoadError(f"Failed to instantiate plugin: {e}", manifest.id) from e
        finally:
            if source_path:
                sys.path = [p for p in sys.path if p != str(source_path)]

    def _create_metadata(self, manifest) -> PluginMetadata:
        return PluginMetadata(
            id=manifest.id,
            name=manifest.name,
            version=manifest.version,
            author=manifest.author,
            description=manifest.description,
            license=manifest.license,
            homepage=manifest.homepage,
            repository=manifest.repository,
            platforms=manifest.platforms,
            tags=manifest.tags,
            category=manifest.category,
            icon=manifest.icon,
            documentation=manifest.documentation,
        )

    def _resolve_load_order(self, discovery_map: Dict[str, tuple]) -> List[str]:
        adj = {pid: set(manifest.dependencies.keys()) for pid, (manifest, _, _) in discovery_map.items()}
        visited = set()
        stack = []

        def visit(u):
            if u in visited:
                return
            visited.add(u)
            for v in adj.get(u, []):
                if v in discovery_map:
                    visit(v)
            stack.append(u)

        for pid in discovery_map:
            visit(pid)
        return stack
