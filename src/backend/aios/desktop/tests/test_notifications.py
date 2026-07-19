import pytest
from aios.desktop.notifications import NotificationService


@pytest.fixture
def service():
    s = NotificationService()
    s._history = []
    return s


@pytest.mark.asyncio
async def test_show_notification(service):
    await service.show("Test Title", "Test Message", "info")
    history = service.get_history()
    assert len(history) == 1
    assert history[0]["title"] == "Test Title"
    assert history[0]["message"] == "Test Message"
    assert history[0]["type"] == "info"


@pytest.mark.asyncio
async def test_notification_history(service):
    await service.show("Title 1", "Message 1", "info")
    await service.show("Title 2", "Message 2", "warning")
    history = service.get_history()
    assert len(history) == 2


@pytest.mark.asyncio
async def test_clear_history(service):
    await service.show("Test", "Message", "info")
    service.clear_history()
    assert len(service.get_history()) == 0


@pytest.mark.asyncio
async def test_notification_types(service):
    await service.show("Perm", "Request", "permission_request")
    await service.show("Task", "Done", "task_completed")
    await service.show("Error", "Failed", "error")
    history = service.get_history()
    assert len(history) == 3
    assert history[0]["type"] == "permission_request"
    assert history[1]["type"] == "task_completed"
    assert history[2]["type"] == "error"
