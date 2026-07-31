"""Plugin manifest parsing with JSON and YAML support."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PluginManifest:
    id: str
    name: str
    version: str
    sdk_version: str = "1.2.0-rc.2"
    author: str = ""
    description: str = ""
    license: str = "MIT"
    homepage: str = ""
    repository: str = ""
    platforms: list[str] = field(default_factory=lambda: ["windows"])
    capabilities: list[dict] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    dependencies: dict[str, str] = field(default_factory=dict)
    entry_point: str = "plugin.py"
    minimum_aios_version: str = "1.2.0-rc.2"
    icon: str = ""
    tags: list[str] = field(default_factory=list)
    category: str = "general"
    documentation: str = ""
    configuration_schema: dict = field(default_factory=dict)
    tools: list[dict] = field(default_factory=list)
    events: dict = field(default_factory=dict)
    hooks: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "sdk_version": self.sdk_version,
            "author": self.author,
            "description": self.description,
            "license": self.license,
            "homepage": self.homepage,
            "repository": self.repository,
            "platforms": self.platforms,
            "capabilities": self.capabilities,
            "permissions": self.permissions,
            "dependencies": self.dependencies,
            "entry_point": self.entry_point,
            "minimum_aios_version": self.minimum_aios_version,
            "icon": self.icon,
            "tags": self.tags,
            "category": self.category,
            "documentation": self.documentation,
            "configuration_schema": self.configuration_schema,
            "tools": self.tools,
            "events": self.events,
            "hooks": self.hooks,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PluginManifest":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_json(cls, path: Path | str) -> "PluginManifest":
        path = Path(path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_yaml(cls, path: Path | str) -> "PluginManifest":
        import yaml
        path = Path(path)
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    @classmethod
    def load(cls, path: Path | str) -> "PluginManifest":
        path = Path(path)
        if path.suffix in (".yaml", ".yml"):
            return cls.from_yaml(path)
        if path.suffix == ".json":
            return cls.from_json(path)
        raise ValueError(f"Unsupported manifest format: {path.suffix}. Use .json, .yaml, or .yml")
