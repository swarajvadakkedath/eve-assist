"""Tests for ModelCache — offline mode, stale serving, TTL."""

import asyncio
import pytest
from aios.core.cache import ModelCache


@pytest.mark.asyncio
async def test_cache_get_set():
    cache = ModelCache(default_ttl=60.0)
    await cache.set("key1", {"data": 42})
    result = await cache.get("key1")
    assert result == {"data": 42}


@pytest.mark.asyncio
async def test_cache_fetcher():
    cache = ModelCache(default_ttl=60.0)
    called = 0
    async def fetch():
        nonlocal called
        called += 1
        return {"version": called}
    result = await cache.get("key2", fetcher=fetch)
    assert result == {"version": 1}
    # Second call returns cached
    result = await cache.get("key2", fetcher=fetch)
    assert result == {"version": 1}
    assert called == 1


@pytest.mark.asyncio
async def test_cache_serves_stale_on_failure():
    cache = ModelCache(default_ttl=0.01, stale_ttl=3600.0)
    await cache.set("stale_key", {"stale": True})
    await asyncio.sleep(0.02)
    # Stale, fetcher fails → serve stale
    async def failing_fetch():
        raise ConnectionError("offline")
    result = await cache.get("stale_key", fetcher=failing_fetch)
    assert result == {"stale": True}


@pytest.mark.asyncio
async def test_cache_raises_on_miss_with_failure():
    cache = ModelCache(default_ttl=60.0)
    async def failing_fetch():
        raise ConnectionError("offline")
    with pytest.raises(ConnectionError):
        await cache.get("missing", fetcher=failing_fetch)


@pytest.mark.asyncio
async def test_cache_invalidate():
    cache = ModelCache(default_ttl=60.0)
    await cache.set("inv", 42)
    assert await cache.get("inv") == 42
    await cache.invalidate("inv")
    assert await cache.get("inv") is None


@pytest.mark.asyncio
async def test_cache_clear():
    cache = ModelCache()
    await cache.set("a", 1)
    await cache.set("b", 2)
    await cache.clear()
    assert await cache.get("a") is None
    assert await cache.get("b") is None


@pytest.mark.asyncio
async def test_cache_etag():
    cache = ModelCache()
    assert await cache.get_etag("no_key") == ""
    await cache.set("etag_key", 42)
    # get with fetcher stores etag
    async def fetch():
        return 99
    await cache.get("etag_key_new", fetcher=fetch, etag="abc123")
    assert await cache.get_etag("etag_key_new") == "abc123"


@pytest.mark.asyncio
async def test_cache_stale_ttl():
    """When stale_ttl expires, stale data is not served."""
    cache = ModelCache(default_ttl=0.01, stale_ttl=0.02)
    await cache.set("expired_stale", {"data": "old"})
    await asyncio.sleep(0.05)
    async def fail():
        raise ValueError("gone")
    with pytest.raises(ValueError):
        await cache.get("expired_stale", fetcher=fail)
