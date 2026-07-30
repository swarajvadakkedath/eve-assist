"""Plugin repository — persist plugin state and settings."""

import json
from pathlib import Path
from typing import Any


class PluginRepository:
    def __init__(self, base_path: str | None = None):
        self._base_path = Path(base_path or Path.home() / ".aios" / "plugins_data")
        self._base_path.mkdir(parents=True, exist_ok=True)
        self._registry_path = self._base_path / "registry.json"

    async def save_registry(self, data: list[dict]) -> None:
        try:
            with open(self._registry_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception:
            pass

    async def load_registry(self) -> list[dict]:
        try:
            with open(self._registry_path) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    async def save_config(self, plugin_id: str, config: dict) -> None:
        config_path = self._base_path / f"{plugin_id}_config.json"
        try:
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2, default=str)
        except Exception:
            pass

    async def load_config(self, plugin_id: str) -> dict:
        config_path = self._base_path / f"{plugin_id}_config.json"
        try:
            with open(config_path) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    async def save_state(self, plugin_id: str, state: dict) -> None:
        state_path = self._base_path / f"{plugin_id}_state.json"
        try:
            with open(state_path, "w") as f:
                json.dump(state, f, indent=2, default=str)
        except Exception:
            pass

    async def load_state(self, plugin_id: str) -> dict:
        state_path = self._base_path / f"{plugin_id}_state.json"
        try:
            with open(state_path) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    async def remove(self, plugin_id: str) -> None:
        for suffix in ("_config.json", "_state.json"):
            path = self._base_path / f"{plugin_id}{suffix}"
            if path.exists():
                path.unlink()
