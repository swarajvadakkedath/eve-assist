"""Capability Registry — capability-based discovery layer."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Capability:
    id: str
    name: str
    description: str
    provider_type: str
    provider_id: str
    parameters: dict = field(default_factory=dict)
    returns: dict = field(default_factory=dict)
    permission_level: int = 0
    tags: list[str] = field(default_factory=list)
    version: str = "1.0.0"
    quality: float = 1.0


class CapabilityRegistry:
    def __init__(self):
        self._capabilities: dict[str, list[Capability]] = {}
        self._providers: dict[str, Any] = {}

    async def register_capability(self, capability: Capability) -> None:
        self._capabilities.setdefault(capability.id, []).append(capability)

    async def unregister_capability(self, capability_id: str) -> None:
        self._capabilities.pop(capability_id, None)

    async def register_provider(self, provider_type: str, provider: Any) -> None:
        self._providers[provider_type] = provider

    async def find_capability(self, query: str, context: dict | None = None) -> list[Capability]:
        results = []
        for cap_id, versions in self._capabilities.items():
            if query in cap_id or any(query in tag for tag in versions[0].tags):
                results.append(versions[0])
        return results

    async def find_best_match(self, query: str, context: dict | None = None) -> Capability | None:
        best: Capability | None = None
        for cap_id, versions in self._capabilities.items():
            if query in cap_id or any(query in tag for tag in versions[0].tags):
                for v in versions:
                    if best is None or v.quality > best.quality:
                        best = v
        return best

    async def list_capabilities(self, tag: str | None = None) -> list[Capability]:
        if tag:
            return [v[0] for v in self._capabilities.values() if tag in v[0].tags]
        return [v[0] for v in self._capabilities.values()]

    async def search_capabilities(self, query: str) -> list[Capability]:
        return await self.find_capability(query)
