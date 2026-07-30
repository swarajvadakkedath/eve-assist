import pytest
from aios.desktop.status_service import StatusService, AppStatus


@pytest.fixture
def service():
    s = StatusService()
    s._history = []
    s._observers = []
    s._status = AppStatus.STARTING
    return s


@pytest.mark.asyncio
async def test_initial_status(service):
    assert service.get_status() == AppStatus.STARTING


@pytest.mark.asyncio
async def test_set_status(service):
    await service.set_status(AppStatus.READY)
    assert service.get_status() == AppStatus.READY


@pytest.mark.asyncio
async def test_status_history(service):
    await service.set_status(AppStatus.READY)
    await service.set_status(AppStatus.THINKING)
    await service.set_status(AppStatus.READY)
    history = service.get_history()
    assert len(history) == 3
    assert history[0]["new_status"] == "ready"
    assert history[1]["new_status"] == "thinking"
    assert history[2]["new_status"] == "ready"


@pytest.mark.asyncio
async def test_status_metadata(service):
    await service.set_status(AppStatus.READY, {"reason": "startup_complete"})
    assert service.get_metadata()["reason"] == "startup_complete"


@pytest.mark.asyncio
async def test_status_observer(service):
    observed = []
    def observer(status, metadata):
        observed.append((status, metadata))
    service.subscribe(observer)
    await service.set_status(AppStatus.READY)
    assert len(observed) == 1
    assert observed[0][0] == AppStatus.READY


@pytest.mark.asyncio
async def test_status_history_limit(service):
    for i in range(10):
        await service.set_status(AppStatus.READY)
    history = service.get_history(limit=5)
    assert len(history) == 5


# ── Regression: async observer support (Defect 3) ─────────────────

@pytest.mark.asyncio
async def test_status_async_observer_awaited(service):
    """Async observers are properly awaited — no RuntimeWarning."""
    results = []

    async def async_observer(status, metadata):
        results.append((status, metadata))

    service.subscribe(async_observer)
    await service.set_status(AppStatus.READY)
    assert len(results) == 1
    assert results[0][0] == AppStatus.READY


@pytest.mark.asyncio
async def test_status_async_observer_exception_handling(service):
    """Async observer exceptions are caught without crashing."""
    async def bad_observer(status, metadata):
        raise ValueError("boom")

    ok_results = []
    async def good_observer(status, metadata):
        ok_results.append(status)

    service.subscribe(bad_observer)
    service.subscribe(good_observer)

    await service.set_status(AppStatus.READY)
    assert len(ok_results) == 1
    assert ok_results[0] == AppStatus.READY


@pytest.mark.asyncio
async def test_status_mixed_sync_async_observers(service):
    """Sync and async observers work together."""
    results = []

    def sync_observer(status, metadata):
        results.append(("sync", status))

    async def async_observer(status, metadata):
        results.append(("async", status))

    service.subscribe(sync_observer)
    service.subscribe(async_observer)
    await service.set_status(AppStatus.THINKING)

    assert len(results) == 2
    assert results[0] == ("sync", AppStatus.THINKING)
    assert results[1] == ("async", AppStatus.THINKING)
