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
