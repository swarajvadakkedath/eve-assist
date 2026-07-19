"""AI Router — provider abstraction, routing, and failover."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator


@dataclass
class AIRequest:
    messages: list[dict]
    tools: list[dict] | None = None
    stream: bool = False
    max_tokens: int = 4096
    temperature: float = 0.7


@dataclass
class AIResponse:
    content: str
    provider: str
    model: str
    tokens_used: int = 0
    cost: float = 0.0
    tool_calls: list[dict] = field(default_factory=list)


class AIProvider(ABC):
    @abstractmethod
    async def chat(self, request: AIRequest) -> AIResponse:
        ...

    @abstractmethod
    async def chat_stream(self, request: AIRequest) -> AsyncIterator[str]:
        ...

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...

    @property
    @abstractmethod
    def model(self) -> str: ...

    @property
    @abstractmethod
    def capabilities(self) -> set[str]: ...


class AIRouter:
    def __init__(self):
        self._providers: dict[str, AIProvider] = {}
        self._provider_order: list[str] = []

    async def route(self, request: AIRequest) -> AIResponse:
        for provider_name in self._provider_order:
            provider = self._providers[provider_name]
            try:
                return await provider.chat(request)
            except Exception:
                continue
        raise RuntimeError("All AI providers failed")

    async def route_stream(self, request: AIRequest) -> AsyncIterator[str]:
        for provider_name in self._provider_order:
            provider = self._providers[provider_name]
            try:
                async for token in provider.chat_stream(request):
                    yield token
                return
            except Exception:
                continue

    async def register_provider(self, name: str, provider: AIProvider) -> None:
        self._providers[name] = provider
        self._provider_order.append(name)

    async def health_check(self) -> dict[str, bool]:
        results = {}
        for name, provider in self._providers.items():
            try:
                results[name] = await provider.health_check()
            except Exception:
                results[name] = False
        return results

    def get_capabilities(self) -> dict[str, list[str]]:
        caps = {}
        for name, provider in self._providers.items():
            caps[name] = list(provider.capabilities)
        return caps
