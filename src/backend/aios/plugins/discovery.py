"""Plugin discovery — scans directories for plugin packages."""

import os
from pathlib import Path
from typing import List, Tuple, Optional

from aios.plugins.manifest import PluginManifest
from aios.plugins.models import PluginScope
from aios.utils.logger import get_logger

logger = get_logger(__name__)


class PluginDiscovery:
    """
    Discovers plugin packages in specified directories.
    Supports built-in, user, and system plugin locations.
    """

    def __init__(
        self,
        builtin_dirs: List[str] | None = None,
        user_dir: str | None = None,
        system_dir: str | None = None,
    ):
        self._builtin_dirs = [Path(d) for d in (builtin_dirs or [])]
        self._user_dir = Path(user_dir) if user_dir else None
        self._system_dir = Path(system_dir) if system_dir else None
        self._extra_dirs: List[Path] = []

    def add_search_directory(self, path: str) -> None:
        """Add an additional directory to scan for plugins."""
        p = Path(path)
        if p.exists() and p.is_dir() and p not in self._extra_dirs:
            self._extra_dirs.append(p)

    async def discover_all(self) -> List[Tuple[PluginManifest, str, PluginScope]]:
        """
        Discover all plugins in all configured directories.
        Returns a list of (manifest, path, scope) tuples.
        """
        results = []

        # 1. Discover built-in plugins
        for d in self._builtin_dirs:
            results.extend(await self._scan_directory(d, PluginScope.BUILTIN))

        # 2. Discover system plugins
        if self._system_dir:
            results.extend(await self._scan_directory(self._system_dir, PluginScope.SYSTEM))

        # 3. Discover user plugins
        if self._user_dir:
            results.extend(await self._scan_directory(self._user_dir, PluginScope.USER))

        # 4. Discover from extra directories
        for d in self._extra_dirs:
            results.extend(await self._scan_directory(d, PluginScope.USER))

        return results

    async def _scan_directory(self, path: Path, scope: PluginScope) -> List[Tuple[PluginManifest, str, PluginScope]]:
        """Scan a single directory for plugin packages."""
        found = []
        if not path.exists() or not path.is_dir():
            return found

        logger.debug(f"Scanning directory for plugins: {path} (scope: {scope})")

        for item in path.iterdir():
            if item.is_dir():
                manifest = await self._try_load_manifest(item)
                if manifest:
                    found.append((manifest, str(item), scope))
            elif item.is_file() and item.suffix in (".json", ".yaml", ".yml"):
                # Potential standalone manifest? usually plugins are in folders
                pass

        return found

    async def _try_load_manifest(self, plugin_dir: Path) -> Optional[PluginManifest]:
        """Attempt to load a manifest from a plugin directory."""
        manifest_files = ["plugin.yaml", "plugin.yml", "plugin.json"]
        for filename in manifest_files:
            manifest_path = plugin_dir / filename
            if manifest_path.exists():
                try:
                    return PluginManifest.load(manifest_path)
                except Exception as e:
                    logger.error(f"Failed to load manifest at {manifest_path}: {e}")
        return None

    def get_search_paths(self) -> List[str]:
        """Return all directories currently being scanned."""
        paths = [str(d) for d in self._builtin_dirs]
        if self._system_dir:
            paths.append(str(self._system_dir))
        if self._user_dir:
            paths.append(str(self._user_dir))
        paths.extend([str(d) for d in self._extra_dirs])
        return paths
