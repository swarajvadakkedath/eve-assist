from datetime import datetime, timezone
from typing import Any

from aios.devtools.models import HealthStatus


COMPONENT_CAPABILITIES: dict[str, list[str]] = {
    "event_bus": ["event_bus.publish", "event_bus.subscribe"],
    "memory_system": ["memory.store", "memory.search", "memory.recall"],
    "ai_router": ["ai_router.route", "ai_router.health_check"],
    "planner": ["planner.create_plan", "planner.execute_plan", "planner.validate_plan"],
    "plugin_system": ["plugin.load", "plugin.unload", "plugin.list"],
    "tool_manager": ["tool_manager.register", "tool_manager.execute", "tool_manager.list"],
    "conversation_manager": ["conversation.manage", "conversation.list"],
}


class HealthDashboard:
    def __init__(self, event_bus=None, memory=None, tool_manager=None):
        self._event_bus = event_bus
        self._memory = memory
        self._tool_manager = tool_manager
        self._history: list[dict] = []
        self._max_history = 500
        self._components: dict[str, HealthStatus] = {}

        for name in COMPONENT_CAPABILITIES:
            self._components[name] = HealthStatus(
                component=name, healthy=True, status="pending"
            )

    async def get_health(self) -> dict:
        report = {
            "overall": True,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "components": {},
            "healthy_count": 0,
            "unhealthy_count": 0,
            "pending_count": 0,
        }

        for name, status in self._components.items():
            entry = {
                "component": name,
                "healthy": status.healthy,
                "status": status.status,
                "last_checked": status.last_checked.isoformat(),
                "metrics": status.metrics,
            }
            if status.error:
                entry["error"] = status.error
            report["components"][name] = entry
            if status.healthy:
                report["healthy_count"] += 1
            else:
                report["unhealthy_count"] += 1
                report["overall"] = False

        report["total_components"] = len(self._components)
        return report

    async def get_component_health(self, component: str) -> HealthStatus | None:
        return self._components.get(component)

    async def update_health(self, component: str, healthy: bool, status: str = "",
                            metrics: dict | None = None, error: str = "") -> HealthStatus:
        entry = HealthStatus(
            component=component,
            healthy=healthy,
            status=status,
            metrics=metrics or {},
            last_checked=datetime.now(timezone.utc),
            error=error,
        )
        self._components[component] = entry

        snapshot = {
            "timestamp": entry.last_checked.isoformat(),
            "component": component,
            "healthy": healthy,
            "status": status,
            "error": error,
        }
        self._history.append(snapshot)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        await self._publish("health:updated", {
            "component": component,
            "healthy": healthy,
            "status": status,
            "error": error,
        })

        if self._memory:
            try:
                from aios.core.memory_system import Memory
                mem = Memory(
                    type="health_snapshot",
                    content=f"Health {component}: {'OK' if healthy else 'FAIL'} - {status}",
                    source="health_dashboard",
                )
                await self._memory.store(mem)
            except Exception:
                pass

        return entry

    async def get_health_history(self, limit: int = 100) -> list[dict]:
        return self._history[-limit:]

    async def get_health_summary(self) -> dict:
        report = await self.get_health()
        summary = {
            "overall": report["overall"],
            "healthy": report["healthy_count"],
            "unhealthy": report["unhealthy_count"],
            "total": report["total_components"],
            "checked_at": report["checked_at"],
        }
        return summary

    async def _publish(self, event_type: str, payload: dict) -> None:
        if self._event_bus:
            await self._event_bus.publish(event_type, payload, source="health_dashboard")
