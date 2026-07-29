"""Tests for Permission Manager — core logic, audit, events, config, DI."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from aios.core.permission_manager import (
    AuditEntry,
    PermissionLevel,
    PermissionManager,
)


@pytest.fixture
def pm():
    return PermissionManager()


@pytest.fixture
def config():
    c = MagicMock()
    c.permission_default_level = 1
    c.permission_sensitive_actions = []
    c.session_timeout_seconds = 300
    return c


@pytest.fixture
def event_bus():
    eb = AsyncMock()
    eb.publish = AsyncMock(return_value="evt_001")
    return eb


# ---------------------------------------------------------------------------
# Existing baseline tests (kept intact)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_read_auto_approve(pm):
    result = await pm.check_permission("read_tool", PermissionLevel.READ)
    assert result.granted
    assert result.auto_approved


@pytest.mark.asyncio
async def test_safe_auto_approve(pm):
    result = await pm.check_permission("safe_tool", PermissionLevel.SAFE)
    assert result.granted
    assert result.auto_approved


@pytest.mark.asyncio
async def test_sensitive_requires_approval(pm):
    result = await pm.check_permission("delete_tool", PermissionLevel.SENSITIVE)
    assert not result.granted


@pytest.mark.asyncio
async def test_grant_permission(pm):
    req = await pm.request_permission("delete_tool", PermissionLevel.SENSITIVE, "delete file")
    approved = await pm.grant_permission(req.request.id)
    assert approved.status == "granted"


@pytest.mark.asyncio
async def test_deny_permission(pm):
    req = await pm.request_permission("delete_tool", PermissionLevel.SENSITIVE, "delete file")
    denied = await pm.deny_permission(req.request.id, "not now")
    assert denied.status == "denied"
    assert denied.reason == "not now"


@pytest.mark.asyncio
async def test_pending_requests(pm):
    await pm.request_permission("tool_a", PermissionLevel.SENSITIVE)
    await pm.request_permission("tool_b", PermissionLevel.SENSITIVE)
    pending = await pm.get_pending_requests()
    assert len(pending) == 2


# ---------------------------------------------------------------------------
# Session expiry with monotonic timing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_workspace_session_grant(pm):
    await pm.request_permission("workspace_tool", PermissionLevel.WORKSPACE, "access workspace")
    pending = await pm.get_pending_requests()
    await pm.grant_permission(pending[0].id)
    result = await pm.check_permission("workspace_tool", PermissionLevel.WORKSPACE)
    assert result.granted
    assert result.session_approved


@pytest.mark.asyncio
async def test_session_expiry(pm):
    pm._session_timeout = -1.0
    await pm.request_permission("ws_tool", PermissionLevel.WORKSPACE)
    pending = await pm.get_pending_requests()
    await pm.grant_permission(pending[0].id)
    result = await pm.check_permission("ws_tool", PermissionLevel.WORKSPACE)
    assert not result.granted


@pytest.mark.asyncio
async def test_session_uses_monotonic_clock(pm):
    from time import monotonic

    await pm.request_permission("mono_tool", PermissionLevel.WORKSPACE)
    pending = await pm.get_pending_requests()
    await pm.grant_permission(pending[0].id)
    entry = pm._session_approvals.get("mono_tool")
    assert entry is not None
    assert isinstance(entry, float)
    assert abs(entry - monotonic()) < 5.0


# ---------------------------------------------------------------------------
# Audit persistence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_tracks_requested(pm):
    await pm.request_permission("tool", PermissionLevel.SENSITIVE, "do something")
    history = await pm.get_audit_history()
    decisions = [e.decision for e in history]
    assert "requested" in decisions


@pytest.mark.asyncio
async def test_audit_tracks_granted(pm):
    req = await pm.request_permission("tool", PermissionLevel.SENSITIVE)
    await pm.grant_permission(req.request.id)
    history = await pm.get_audit_history()
    decisions = [e.decision for e in history]
    assert "granted" in decisions


@pytest.mark.asyncio
async def test_audit_tracks_denied(pm):
    req = await pm.request_permission("tool", PermissionLevel.SENSITIVE)
    await pm.deny_permission(req.request.id, "rejected")
    history = await pm.get_audit_history()
    decisions = [e.decision for e in history]
    assert "denied" in decisions


@pytest.mark.asyncio
async def test_audit_filter_by_tool(pm):
    await pm.request_permission("find_me", PermissionLevel.SENSITIVE, "op")
    await pm.request_permission("other", PermissionLevel.SENSITIVE, "op")
    history = await pm.get_audit_history(tool_id="find_me")
    assert all(e.tool_id == "find_me" for e in history)


@pytest.mark.asyncio
async def test_audit_filter_by_decision(pm):
    req = await pm.request_permission("tool", PermissionLevel.SENSITIVE)
    await pm.grant_permission(req.request.id)
    denied = await pm.get_audit_history(decision="denied")
    assert len(denied) == 0
    granted = await pm.get_audit_history(decision="granted")
    assert len(granted) >= 1


@pytest.mark.asyncio
async def test_audit_limit(pm):
    for i in range(10):
        await pm.request_permission(f"tool_{i}", PermissionLevel.SENSITIVE)
    history = await pm.get_audit_history(limit=3)
    assert len(history) == 3


@pytest.mark.asyncio
async def test_audit_entry_structure(pm):
    await pm.request_permission("my_tool", PermissionLevel.SENSITIVE, "action_x")
    history = await pm.get_audit_history()
    entry = history[0]
    assert isinstance(entry, AuditEntry)
    assert entry.tool_id == "my_tool"
    assert entry.action == "action_x"
    assert entry.level == int(PermissionLevel.SENSITIVE)
    assert entry.decision == "requested"


# ---------------------------------------------------------------------------
# Default-deny policy
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_sensitive_default_deny(pm):
    result = await pm.check_permission("delete_tool", PermissionLevel.SENSITIVE)
    assert not result.granted


@pytest.mark.asyncio
async def test_request_sensitive_default_deny(pm):
    result = await pm.request_permission("delete_tool", PermissionLevel.SENSITIVE, "delete")
    assert not result.granted


@pytest.mark.asyncio
async def test_grant_nonexistent_raises(pm):
    with pytest.raises(ValueError, match="No pending request"):
        await pm.grant_permission("nonexistent")


@pytest.mark.asyncio
async def test_deny_nonexistent_raises(pm):
    with pytest.raises(ValueError, match="No pending request"):
        await pm.deny_permission("nonexistent")


# ---------------------------------------------------------------------------
# Event publication
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_publishes_event(pm, event_bus):
    pm._event_bus = event_bus
    await pm.request_permission("tool", PermissionLevel.SENSITIVE, "action")
    event_bus.publish.assert_awaited_once()
    call_args = event_bus.publish.await_args
    assert call_args[0][0] == "permission:requested"


@pytest.mark.asyncio
async def test_grant_publishes_event(pm, event_bus):
    pm._event_bus = event_bus
    req = await pm.request_permission("tool", PermissionLevel.SENSITIVE)
    event_bus.publish.reset_mock()
    await pm.grant_permission(req.request.id)
    event_bus.publish.assert_awaited_once()
    call_args = event_bus.publish.await_args
    assert call_args[0][0] == "permission:granted"


@pytest.mark.asyncio
async def test_deny_publishes_event(pm, event_bus):
    pm._event_bus = event_bus
    req = await pm.request_permission("tool", PermissionLevel.SENSITIVE)
    event_bus.publish.reset_mock()
    await pm.deny_permission(req.request.id, "nope")
    event_bus.publish.assert_awaited_once()
    call_args = event_bus.publish.await_args
    assert call_args[0][0] == "permission:denied"


@pytest.mark.asyncio
async def test_expiry_publishes_event(pm, event_bus):
    pm._event_bus = event_bus
    pm._session_timeout = -1.0
    await pm.request_permission("expiry_tool", PermissionLevel.WORKSPACE)
    pending = await pm.get_pending_requests()
    await pm.grant_permission(pending[0].id)
    event_bus.publish.reset_mock()
    await pm.check_permission("expiry_tool", PermissionLevel.WORKSPACE)
    event_bus.publish.assert_awaited_once()
    call_args = event_bus.publish.await_args
    assert call_args[0][0] == "permission:expired"


# ---------------------------------------------------------------------------
# Config integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_configure_sensitive_actions(pm, config):
    config.permission_sensitive_actions = ["super_tool"]
    pm.configure(sensitive_actions=["super_tool"])
    result = await pm.check_permission("super_tool", PermissionLevel.SAFE)
    assert not result.granted


@pytest.mark.asyncio
async def test_configure_session_timeout(pm):
    pm._session_timeout = 0.0
    assert pm._session_timeout == 0.0


@pytest.mark.asyncio
async def test_configure_default_level(pm, config):
    config.permission_default_level = 3
    pm._config = config
    result = await pm.check_permission("tool", PermissionLevel.READ)
    assert not result.granted


# ---------------------------------------------------------------------------
# DI registration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_in_container():
    container = MagicMock()
    result = PermissionManager.register_in_container(container)
    assert result is container
    container.register.assert_called_once()
    args, _ = container.register.call_args
    assert args[0] is PermissionManager


@pytest.mark.asyncio
async def test_factory_produces_permission_manager():
    container = MagicMock()
    PermissionManager.register_in_container(container)
    args, kwargs = container.register.call_args
    factory = kwargs.get("factory")
    instance = factory()
    assert isinstance(instance, PermissionManager)
    assert instance._event_bus is None


@pytest.mark.asyncio
async def test_factory_with_event_bus(event_bus):
    container = MagicMock()
    PermissionManager.register_in_container(container, event_bus=event_bus)
    args, kwargs = container.register.call_args
    factory = kwargs.get("factory")
    instance = factory()
    assert instance._event_bus is event_bus


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_approved_not_sensitive(pm):
    result = await pm.check_permission("tool", PermissionLevel.READ)
    assert result.auto_approved
    assert not result.session_approved


@pytest.mark.asyncio
async def test_session_approved_not_auto(pm):
    await pm.request_permission("ws", PermissionLevel.WORKSPACE)
    pending = await pm.get_pending_requests()
    await pm.grant_permission(pending[0].id)
    result = await pm.check_permission("ws", PermissionLevel.WORKSPACE)
    assert result.session_approved
    assert not result.auto_approved


@pytest.mark.asyncio
async def test_no_event_bus_no_crash(pm):
    await pm.request_permission("tool", PermissionLevel.SENSITIVE)
    pending = await pm.get_pending_requests()
    await pm.grant_permission(pending[0].id)
    with pytest.raises(ValueError):
        await pm.deny_permission("nonexistent", "nope")
    history = await pm.get_audit_history()
    assert len(history) >= 2


@pytest.mark.asyncio
async def test_load_config_no_config(pm):
    pm._config = None
    pm._load_config()
    assert pm._session_timeout == 300.0


@pytest.mark.asyncio
async def test_load_config_with_config(pm, config):
    pm._config = config
    pm._load_config()
    assert pm._session_timeout == 300.0
    assert len(pm._sensitive_actions) == 0


@pytest.mark.asyncio
async def test_audit_entry_dataclass():
    from datetime import datetime, timezone

    entry = AuditEntry(
        timestamp=datetime.now(timezone.utc),
        tool_id="tool",
        action="act",
        level=3,
        decision="granted",
        session_id="s1",
        reason="ok",
        request_id="r1",
    )
    assert entry.decision == "granted"
    assert entry.tool_id == "tool"


@pytest.mark.asyncio
async def test_configure_sensitive_actions_list(pm):
    pm.configure(sensitive_actions=["alpha", "beta"])
    assert "alpha" in pm._sensitive_actions
    assert "beta" in pm._sensitive_actions


@pytest.mark.asyncio
async def test_session_approval_expired_clears_entry(pm):
    pm._session_timeout = -1.0
    await pm.request_permission("ex_tool", PermissionLevel.WORKSPACE)
    pending = await pm.get_pending_requests()
    await pm.grant_permission(pending[0].id)
    pm._session_timeout = -1.0
    assert "ex_tool" in pm._session_approvals
    await pm.check_permission("ex_tool", PermissionLevel.WORKSPACE)
    assert "ex_tool" not in pm._session_approvals
