"""Tests for offline mode integration."""

import pytest
from aios.core.cache import ModelCache


@pytest.mark.asyncio
async def test_cache_serves_stale_when_provider_unreachable():
    """Simulate provider going offline — cache serves stale data."""
    cache = ModelCache(default_ttl=0.01, stale_ttl=86400.0)
    await cache.set("provider_models", ["model-a", "model-b"])
    await cache.get("provider_models")  # fresh
    import asyncio
    await asyncio.sleep(0.02)

    # Fetcher raises (provider offline), but stale data available
    async def offline_fetch():
        raise ConnectionError("Provider unreachable")

    result = await cache.get("provider_models", fetcher=offline_fetch)
    assert result == ["model-a", "model-b"]


@pytest.mark.asyncio
async def test_cache_returns_none_for_never_seen():
    """First access to a never-before-fetched provider while offline returns None or raises."""
    cache = ModelCache()
    async def offline_fetch():
        raise ConnectionError("Never connected")
    # No stale data to serve -> should raise
    with pytest.raises(ConnectionError):
        await cache.get("never_seen", fetcher=offline_fetch)
