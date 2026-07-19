"""Unit tests for PluginPermissionManager."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from aios.plugins.permissions import PluginPermissionManager
from aios.core.permission_manager import PermissionResult, PermissionRequest, PermissionLevel


def make_granted_result() -> PermissionResult:
    return PermissionResult(
        granted=True,
        request=PermissionRequest(tool_id="test", level=PermissionLevel.SAFE, status="granted"),
        auto_approved=True,
    )


def make_denied_result() -> PermissionResult:
    return PermissionResult(
        granted=False,
        request=PermissionRequest(tool_id="test", level=PermissionLevel.SENSITIVE),
    )


@pytest.mark.asyncio
class TestPluginPermissionManager:
    async def test_check_permission_without_pm_allows_level_0(self):
        mgr = PluginPermissionManager(permission_manager=None)
        result = await mgr.check_permission("p1", "read", level=0)
        assert result is True

    async def test_check_permission_without_pm_allows_level_1(self):
        mgr = PluginPermissionManager(permission_manager=None)
        result = await mgr.check_permission("p1", "write", level=1)
        assert result is True

    async def test_check_permission_without_pm_denies_level_2(self):
        mgr = PluginPermissionManager(permission_manager=None)
        result = await mgr.check_permission("p1", "admin", level=2)
        assert result is False

    async def test_request_permission_without_pm_allows_level_1(self):
        mgr = PluginPermissionManager(permission_manager=None)
        result = await mgr.request_permission("p1", "read", level=1)
        assert result is True

    async def test_request_permission_without_pm_denies_level_3(self):
        mgr = PluginPermissionManager(permission_manager=None)
        result = await mgr.request_permission("p1", "system", level=3)
        assert result is False

    async def test_request_permission_with_pm_granted(self):
        mock_pm = MagicMock()
        mock_pm.request_permission = AsyncMock(return_value=make_granted_result())
        mgr = PluginPermissionManager(permission_manager=mock_pm)
        result = await mgr.request_permission("p1", "filesystem.read", level=1, reason="need it")
        assert result is True
        # Should be tracked in granted
        granted = await mgr.get_granted("p1")
        assert "filesystem.read" in granted

    async def test_request_permission_with_pm_denied(self):
        mock_pm = MagicMock()
        mock_pm.request_permission = AsyncMock(return_value=make_denied_result())
        mgr = PluginPermissionManager(permission_manager=mock_pm)
        result = await mgr.request_permission("p1", "system.delete", level=3)
        assert result is False
        granted = await mgr.get_granted("p1")
        assert "system.delete" not in granted

    async def test_revoke_permission(self):
        mock_pm = MagicMock()
        mock_pm.request_permission = AsyncMock(return_value=make_granted_result())
        mock_pm.check_permission = AsyncMock(return_value=make_granted_result())
        mgr = PluginPermissionManager(permission_manager=mock_pm)
        await mgr.request_permission("p1", "read", level=1)
        await mgr.revoke_permission("p1", "read")
        granted = await mgr.get_granted("p1")
        assert "read" not in granted

    async def test_revoke_all(self):
        mock_pm = MagicMock()
        mock_pm.request_permission = AsyncMock(return_value=make_granted_result())
        mgr = PluginPermissionManager(permission_manager=mock_pm)
        await mgr.request_permission("p1", "read", level=1)
        await mgr.request_permission("p1", "write", level=1)
        await mgr.revoke_all("p1")
        granted = await mgr.get_granted("p1")
        assert granted == []

    async def test_get_granted_empty_by_default(self):
        mgr = PluginPermissionManager()
        result = await mgr.get_granted("p1")
        assert result == []

    def test_map_permission_to_level_safe(self):
        mgr = PluginPermissionManager()
        assert mgr.map_permission_to_level("read") == 0
        assert mgr.map_permission_to_level("search") == 0

    def test_map_permission_to_level_protected(self):
        mgr = PluginPermissionManager()
        assert mgr.map_permission_to_level("write") == 2
        assert mgr.map_permission_to_level("execute") == 2

    def test_map_permission_to_level_restricted(self):
        mgr = PluginPermissionManager()
        assert mgr.map_permission_to_level("delete") == 3
        assert mgr.map_permission_to_level("admin") == 3

    def test_map_permission_to_level_unknown(self):
        mgr = PluginPermissionManager()
        assert mgr.map_permission_to_level("unknown-perm") == 1

    async def test_validate_declared_permissions_valid(self):
        mgr = PluginPermissionManager()
        invalid = await mgr.validate_declared_permissions("p1", ["read", "write", "execute"])
        assert invalid == []

    async def test_validate_declared_permissions_path_traversal(self):
        mgr = PluginPermissionManager()
        invalid = await mgr.validate_declared_permissions("p1", ["../etc/passwd"])
        assert len(invalid) > 0

    async def test_validate_declared_permissions_empty(self):
        mgr = PluginPermissionManager()
        invalid = await mgr.validate_declared_permissions("p1", [])
        assert invalid == []
