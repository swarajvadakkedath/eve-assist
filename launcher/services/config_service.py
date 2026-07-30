"""Configuration service — centralized settings management."""

from pathlib import Path
from typing import Any
import json

CONFIG_DIR = Path.home() / ".eve"
CONFIG_FILE = CONFIG_DIR / "launcher_config.json"

DEFAULT_CONFIG = {
    "backend_host": "127.0.0.1",
    "backend_port": 8456,
    "frontend_port": 5173,
    "frontend_type": "browser",
    "api_keys": {},
    "theme": "system",
    "auto_start": False,
    "auto_update": True,
    "developer_mode": False,
    "first_run": True,
    "ai_providers": {
        "gemini": {"enabled": False, "key": ""},
        "groq": {"enabled": False, "key": ""},
        "openrouter": {"enabled": False, "key": ""},
        "ollama": {"enabled": True, "url": "http://127.0.0.1:11434"},
        "github_models": {"enabled": False, "key": ""},
        "z_ai": {"enabled": False, "key": ""},
    },
}


class ConfigService:
    def __init__(self, config_dir: str | None = None, config_file: str | None = None):
        self._config_dir = Path(config_dir) if config_dir else Path(CONFIG_DIR)
        self._config_file = Path(config_file) if config_file else Path(CONFIG_FILE)
        self._data = dict(DEFAULT_CONFIG)
        self._load()

    def _load(self):
        self._config_dir.mkdir(parents=True, exist_ok=True)
        if self._config_file.exists():
            try:
                with open(str(self._config_file), "r", encoding="utf-8") as f:
                    stored = json.load(f)
                for k, v in stored.items():
                    if k in self._data:
                        self._data[k] = v
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        self._config_dir.mkdir(parents=True, exist_ok=True)
        with open(str(self._config_file), "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        self._data[key] = value
        self.save()

    @property
    def backend_url(self) -> str:
        return f"http://{self._data['backend_host']}:{self._data['backend_port']}"

    @property
    def health_url(self) -> str:
        return f"{self.backend_url}/api/v1/system/health"

    @property
    def frontend_url(self) -> str:
        return f"http://localhost:{self._data['frontend_port']}"

    @property
    def frontend_type(self) -> str:
        return self._data.get("frontend_type", "browser")

    @property
    def is_first_run(self) -> bool:
        return self._data.get("first_run", True)

    @property
    def all_data(self) -> dict:
        return dict(self._data)

    @property
    def api_keys(self) -> dict:
        return self._data.get("api_keys", {})

    @property
    def ai_providers_config(self) -> dict:
        return self._data.get("ai_providers", {})
