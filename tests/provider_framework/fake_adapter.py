"""Reusable FakeAdapter for provider framework tests.

Replaces the 3 copies in test_provider_manager.py, test_providers_api.py,
and test_routing_engine.py.
"""

from __future__ import annotations

from typing import Any, AsyncIterator

from aios.core.adapters.base import AIProviderAdapter, ChatRequest, ChatResponse, ProviderStatus
from aios.core.model_info import ModelInfo
from aios.core.streaming_manager import StreamingManager
from aios.core.timeout_retry import TimeoutConfig


class FakeAdapter(AIProviderAdapter):
    """Minimal in-memory adapter for unit tests.

    Usage:
        adapter = FakeAdapter(provider_type="test", api_key="fake-key")
        status = await adapter.connect()
        assert status == ProviderStatus.CONNECTED
    """

    def __init__(
        self,
        provider_type: str = "test",
        provider_name: str = "Test Provider",
        api_key: str = "",
        base_url: str = "http://fake.test",
        timeout_config: TimeoutConfig | None = None,
        streaming_manager: StreamingManager | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self._provider_type = provider_type
        self._provider_name = provider_name
        self._api_key = api_key
        self._base_url = base_url
        self._timeout_config = timeout_config or TimeoutConfig()
        self._streaming = streaming_manager or StreamingManager()
        self._metadata = metadata or {}
        self._connected = False

    @property
    def provider_id(self) -> str:
        return self._provider_type

    @property
    def provider_name(self) -> str:
        return self._provider_name

    async def connect(self) -> ProviderStatus:
        self._connected = True
        return ProviderStatus.CONNECTED

    async def disconnect(self) -> None:
        self._connected = False

    async def validate_api_key(self) -> bool:
        return bool(self._api_key)

    async def list_models(self) -> list[ModelInfo]:
        return []

    async def get_model(self, model_id: str) -> ModelInfo | None:
        return None

    async def chat(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            content="Fake response",
            model=request.model,
            provider=self._provider_type,
        )

    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        yield "Fake "

    async def health(self) -> ProviderStatus:
        return ProviderStatus.CONNECTED if self._connected else ProviderStatus.OFFLINE
