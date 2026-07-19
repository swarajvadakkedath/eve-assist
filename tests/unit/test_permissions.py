"""Tests for Permission Manager."""

import pytest
from aios.core.permission_manager import PermissionManager, PermissionLevel


@pytest.fixture
def pm():
    return PermissionManager()


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
