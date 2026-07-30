"""Plugin permission integration with the existing Permission Manager."""

from aios.core.permission_manager import PermissionLevel


class PluginPermissionManager:
    def __init__(self, permission_manager=None):
        self._pm = permission_manager
        self._granted: dict[str, set[str]] = {}

    async def check_permission(self, plugin_id: str, permission: str, level: int) -> bool:
        if not self._pm:
            return level <= 1
        perm_level = PermissionLevel(level)
        result = await self._pm.check_permission(f"plugin:{plugin_id}:{permission}", perm_level)
        return result.granted

    async def request_permission(self, plugin_id: str, permission: str, level: int, reason: str = "") -> bool:
        if not self._pm:
            return level <= 1
        perm_level = PermissionLevel(level)
        result = await self._pm.request_permission(
            tool_id=f"plugin:{plugin_id}:{permission}",
            level=perm_level,
            action=reason or f"Plugin {plugin_id} requests {permission}",
        )
        if result.granted:
            self._granted.setdefault(plugin_id, set()).add(permission)
        return result.granted

    async def revoke_permission(self, plugin_id: str, permission: str) -> None:
        if plugin_id in self._granted:
            self._granted[plugin_id].discard(permission)

    async def revoke_all(self, plugin_id: str) -> None:
        self._granted.pop(plugin_id, None)

    async def get_granted(self, plugin_id: str) -> list[str]:
        return list(self._granted.get(plugin_id, set()))

    def map_permission_to_level(self, permission: str) -> int:
        safe = {"read", "query", "inspect", "list", "search"}
        protected = {"write", "modify", "execute", "create", "update"}
        restricted = {"delete", "remove", "system", "elevated", "admin"}

        perm_lower = permission.lower()
        if perm_lower in restricted:
            return 3
        if perm_lower in protected:
            return 2
        if perm_lower in safe:
            return 0
        return 1

    async def validate_declared_permissions(self, plugin_id: str, permissions: list[str]) -> list[str]:
        invalid = []
        for perm in permissions:
            if not perm or not perm.strip():
                invalid.append(perm)
            if ".." in perm or "/" in perm or "\\" in perm:
                invalid.append(perm)
        return invalid
