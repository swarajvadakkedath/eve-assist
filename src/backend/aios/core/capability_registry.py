"""Capability Registry — capability-based discovery layer with intelligence."""

from dataclasses import dataclass, field
from typing import Any
from difflib import SequenceMatcher


def _word_score(text: str, query: str) -> float:
    """Word-level relevance score between 0 and 1.
    
    Scores based on exact word overlap, not substring/sequence matching.
    A capability should only match if its words are relevant to the query.
    """
    if not query or not text:
        return 0.0
    q_words = set(query.lower().split())
    t_words = set(text.lower().split())
    if not q_words or not t_words:
        return 0.0
    # Exact word overlap
    overlap = q_words & t_words
    if overlap:
        return len(overlap) / max(len(q_words), len(t_words))
    # Partial word match (prefix/suffix)
    partial = 0
    for qw in q_words:
        for tw in t_words:
            if len(qw) >= 3 and len(tw) >= 3:
                if qw.startswith(tw[:3]) or tw.startswith(qw[:3]):
                    partial += 0.3
    return min(partial / max(len(q_words), 1), 0.5)


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
    version: str = "1.2.1"
    quality: float = 1.0
    supported_interfaces: list[str] = field(default_factory=lambda: ["chat"])
    supports_streaming: bool = False
    supports_cancellation: bool = False
    estimated_latency: float = 0.0
    estimated_cost: float = 0.0
    reliability_score: float = 1.0
    requires_confirmation: bool = False
    related_capabilities: list[str] = field(default_factory=list)


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

    async def search_by_category(self, category: str) -> list[Capability]:
        """Search capabilities by category (matched against id prefix)."""
        prefix = f"{category}."
        return [v[0] for v in self._capabilities.values() if v[0].id.startswith(prefix)]

    async def filter_by_permission(self, min_level: int = 0, max_level: int | None = None) -> list[Capability]:
        """Filter capabilities by permission level range."""
        results = []
        for versions in self._capabilities.values():
            c = versions[0]
            if c.permission_level >= min_level:
                if max_level is None or c.permission_level <= max_level:
                    results.append(c)
        return results

    async def filter_by_interface(self, interface: str) -> list[Capability]:
        """Filter capabilities by supported interface (chat, voice, vision)."""
        return [
            v[0] for v in self._capabilities.values()
            if interface in v[0].supported_interfaces
        ]

    async def rank_for_task(self, task_description: str, context: dict | None = None) -> list[tuple[Capability, float]]:
        """Rank all capabilities by relevance to a task description. Returns (capability, score) pairs."""
        scored: list[tuple[Capability, float]] = []
        for versions in self._capabilities.values():
            c = versions[0]
            score = (
                _word_score(c.id, task_description) * 1.5
                + _word_score(c.name, task_description) * 1.2
                + _word_score(c.description, task_description) * 1.0
                + max((_word_score(tag, task_description) for tag in c.tags), default=0.0) * 0.8
            )
            score *= c.quality
            scored.append((c, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    async def recommend_alternatives(self, capability_id: str, max_results: int = 5) -> list[Capability]:
        """Recommend alternative capabilities based on related_capabilities and tags."""
        versions = self._capabilities.get(capability_id)
        if not versions:
            return []
        source = versions[0]
        seen = {capability_id}
        recommended: list[Capability] = []

        related_ids = source.related_capabilities or []
        for rid in related_ids:
            if rid in seen:
                continue
            if rid in self._capabilities:
                recommended.append(self._capabilities[rid][0])
                seen.add(rid)

        source_tags = set(source.tags)
        for cap_id, versions in self._capabilities.items():
            if cap_id in seen:
                continue
            c = versions[0]
            if source_tags & set(c.tags):
                recommended.append(c)
                seen.add(cap_id)

        return recommended[:max_results]
