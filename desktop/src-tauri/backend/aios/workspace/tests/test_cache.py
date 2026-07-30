import pytest
from aios.workspace.cache import WorkspaceCache
from aios.workspace.models import WorkspaceSnapshot


@pytest.fixture
def cache():
    return WorkspaceCache(ttl_seconds=60)


@pytest.mark.asyncio
async def test_cache_miss(cache):
    result = await cache.get_snapshot()
    assert result is None


@pytest.mark.asyncio
async def test_cache_hit(cache):
    snapshot = WorkspaceSnapshot(active_window="test")
    await cache.update_snapshot(snapshot)
    result = await cache.get_snapshot()
    assert result is not None
    assert result.active_window == "test"


@pytest.mark.asyncio
async def test_cache_history(cache):
    for i in range(5):
        await cache.update_snapshot(WorkspaceSnapshot(active_window=f"window-{i}"))
    history = await cache.get_history(limit=3)
    assert len(history) == 3


@pytest.mark.asyncio
async def test_cache_invalidate(cache):
    await cache.update_snapshot(WorkspaceSnapshot())
    await cache.invalidate()
    result = await cache.get_snapshot()
    assert result is None


@pytest.mark.asyncio
async def test_cache_expiry():
    cache = WorkspaceCache(ttl_seconds=0)
    await cache.update_snapshot(WorkspaceSnapshot())
    import asyncio
    await asyncio.sleep(0.01)
    result = await cache.get_snapshot()
    assert result is None


@pytest.mark.asyncio
async def test_cache_age(cache):
    await cache.update_snapshot(WorkspaceSnapshot())
    age = await cache.get_cache_age_seconds()
    assert age >= 0


@pytest.mark.asyncio
async def test_cache_snapshot_count(cache):
    for i in range(10):
        await cache.update_snapshot(WorkspaceSnapshot())
    count = await cache.get_cached_snapshot_count()
    assert count == 10
