import re
from collections import deque
from datetime import datetime
from typing import Any

from aios.devtools.models import LogEntry, LogLevel


class LogViewer:
    def __init__(self, event_bus=None):
        self._event_bus = event_bus
        self._logs: deque[LogEntry] = deque(maxlen=10000)
        self._min_level = LogLevel.DEBUG
        self._subscriptions: dict[str, list[str]] = {}
        self._level_order = {
            LogLevel.DEBUG: 0,
            LogLevel.INFO: 1,
            LogLevel.WARNING: 2,
            LogLevel.ERROR: 3,
            LogLevel.CRITICAL: 4,
        }

    async def get_logs(self, level: str = "", source: str = "",
                       category: str = "", search: str = "",
                       limit: int = 200, offset: int = 0) -> dict:
        filtered = list(self._logs)

        if level:
            min_order = self._level_order.get(LogLevel(level.upper()), 0)
            filtered = [e for e in filtered
                        if self._level_order.get(e.level, 0) >= min_order]
        else:
            min_order = self._level_order.get(self._min_level, 0)
            filtered = [e for e in filtered
                        if self._level_order.get(e.level, 0) >= min_order]

        if source:
            filtered = [e for e in filtered if source.lower() in e.source.lower()]
        if category:
            filtered = [e for e in filtered if category.lower() in e.category.lower()]
        if search:
            pattern = re.compile(re.escape(search), re.IGNORECASE)
            filtered = [e for e in filtered if pattern.search(e.message)]

        total = len(filtered)
        page = filtered[offset:offset + limit]

        return {
            "logs": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "level": e.level.value,
                    "message": e.message,
                    "source": e.source,
                    "category": e.category,
                    "metadata": e.metadata,
                }
                for e in page
            ],
            "total": total,
            "offset": offset,
            "limit": limit,
            "returned": len(page),
        }

    async def get_log_categories(self) -> list[dict]:
        cats: dict[str, dict] = {}
        for entry in self._logs:
            cat = entry.category or "uncategorized"
            if cat not in cats:
                cats[cat] = {"category": cat, "count": 0, "levels": set()}
            cats[cat]["count"] += 1
            cats[cat]["levels"].add(entry.level.value)
        return [
            {"category": k, "count": v["count"], "levels": sorted(v["levels"])}
            for k, v in sorted(cats.items())
        ]

    async def get_log_sources(self) -> list[dict]:
        sources: dict[str, int] = {}
        for entry in self._logs:
            src = entry.source or "unknown"
            sources[src] = sources.get(src, 0) + 1
        return [
            {"source": k, "count": v}
            for k, v in sorted(sources.items(), key=lambda x: -x[1])
        ]

    async def add_log(self, level: LogLevel, message: str, source: str = "",
                      category: str = "", metadata: dict | None = None) -> LogEntry:
        entry = LogEntry(
            timestamp=datetime.utcnow(),
            level=level,
            message=message,
            source=source,
            category=category,
            metadata=metadata or {},
        )
        self._logs.append(entry)

        min_order = self._level_order.get(self._min_level, 0)
        if self._level_order.get(level, 0) >= min_order:
            await self._publish("log:entry", {
                "timestamp": entry.timestamp.isoformat(),
                "level": level.value,
                "message": message,
                "source": source,
                "category": category,
            })

        return entry

    async def clear_logs(self) -> None:
        count = len(self._logs)
        self._logs.clear()
        await self._publish("log:cleared", {"cleared_count": count})

    async def set_log_level(self, level: str) -> None:
        self._min_level = LogLevel(level.upper())
        await self._publish("log:level_changed", {
            "new_level": self._min_level.value,
        })

    async def get_log_level(self) -> str:
        return self._min_level.value

    async def get_stats(self) -> dict:
        levels = {lv: 0 for lv in LogLevel}
        for entry in self._logs:
            if entry.level in levels:
                levels[entry.level] += 1
        return {
            "total_entries": len(self._logs),
            "by_level": {k.value: v for k, v in levels.items()},
            "min_level": self._min_level.value,
        }

    async def subscribe_to_events(self, event_bus) -> None:
        if not event_bus:
            return
        sub_id = await event_bus.subscribe("*", self._on_event)
        self._subscriptions.setdefault("*", []).append(sub_id)

    async def _on_event(self, event) -> None:
        try:
            level = LogLevel.INFO
            if event.type.startswith("error") or event.type.startswith("diagnostics:failed"):
                level = LogLevel.ERROR
            elif event.type.startswith("warning"):
                level = LogLevel.WARNING
            elif event.type.startswith("debug"):
                level = LogLevel.DEBUG
            elif event.type.startswith("health") and hasattr(event, "payload"):
                payload = event.payload if isinstance(event.payload, dict) else {}
                if not payload.get("healthy", True):
                    level = LogLevel.WARNING

            message = str(event.payload) if event.payload else event.type
            if isinstance(event.payload, dict):
                message = event.payload.get("message", event.payload.get("error", str(event.payload)))

            await self.add_log(
                level=level,
                message=str(message)[:500],
                source=event.source or event.type.split(":")[0],
                category=event.type,
                metadata={"event_id": getattr(event, "id", ""), "event_type": event.type},
            )
        except Exception:
            pass

    async def unsubscribe_all(self) -> None:
        if not self._event_bus:
            return
        for et, sub_ids in self._subscriptions.items():
            for sid in sub_ids:
                await self._event_bus.unsubscribe(sid)
        self._subscriptions.clear()

    async def _publish(self, event_type: str, payload: dict) -> None:
        if self._event_bus:
            await self._event_bus.publish(event_type, payload, source="log_viewer")
