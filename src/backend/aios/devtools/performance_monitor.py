import asyncio
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Any

from aios.devtools.models import MetricPoint


class PerformanceMonitor:
    def __init__(self, event_bus=None, memory=None):
        self._event_bus = event_bus
        self._memory = memory
        self._metrics: dict[str, deque[MetricPoint]] = defaultdict(
            lambda: deque(maxlen=10000)
        )
        self._running = False
        self._task: asyncio.Task | None = None
        self._interval: float = 5.0
        self._max_history = 10000
        self._labels: dict[str, dict] = {}

    async def get_metrics(self, name: str = "") -> list[dict]:
        if name:
            points = list(self._metrics.get(name, []))
        else:
            points = []
            for pts in self._metrics.values():
                points.extend(pts)
            points.sort(key=lambda p: p.timestamp)

        return [
            {
                "timestamp": p.timestamp.isoformat(),
                "name": p.name,
                "value": p.value,
                "labels": p.labels,
            }
            for p in points[-500:]
        ]

    async def get_metric_history(self, name: str, limit: int = 100) -> list[dict]:
        points = list(self._metrics.get(name, []))
        return [
            {
                "timestamp": p.timestamp.isoformat(),
                "value": p.value,
                "labels": p.labels,
            }
            for p in points[-limit:]
        ]

    async def get_latest_metrics(self) -> dict:
        result = {}
        for name, points in self._metrics.items():
            if points:
                last = points[-1]
                result[name] = {
                    "value": last.value,
                    "timestamp": last.timestamp.isoformat(),
                    "labels": last.labels,
                }
        return result

    async def record_metric(self, name: str, value: float,
                            labels: dict | None = None) -> MetricPoint:
        point = MetricPoint(
            timestamp=datetime.utcnow(),
            name=name,
            value=value,
            labels=labels or {},
        )
        self._metrics[name].append(point)
        return point

    async def start_monitoring(self, interval: float = 5.0) -> None:
        if self._running:
            return
        self._running = True
        self._interval = interval
        self._task = asyncio.create_task(self._monitor_loop())
        await self._publish("perf:monitoring_started", {
            "interval": interval,
        })

    async def stop_monitoring(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        await self._publish("perf:monitoring_stopped", {})

    async def get_metric_summary(self, name: str) -> dict:
        points = list(self._metrics.get(name, []))
        if not points:
            return {"name": name, "count": 0}

        values = [p.value for p in points]
        import statistics
        return {
            "name": name,
            "count": len(values),
            "min": round(min(values), 2),
            "max": round(max(values), 2),
            "avg": round(statistics.mean(values), 2),
            "latest": round(values[-1], 2),
            "latest_timestamp": points[-1].timestamp.isoformat(),
        }

    async def _monitor_loop(self) -> None:
        while self._running:
            try:
                cpu = await self._get_cpu_percent()
                await self.record_metric("cpu_percent", cpu)

                mem = await self._get_memory_percent()
                await self.record_metric("memory_percent", mem)

                await self._publish("perf:metrics", {
                    "cpu_percent": cpu,
                    "memory_percent": mem,
                    "timestamp": datetime.utcnow().isoformat(),
                })
            except Exception:
                pass
            await asyncio.sleep(self._interval)

    async def _get_cpu_percent(self) -> float:
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1)
        except ImportError:
            return 0.0

    async def _get_memory_percent(self) -> float:
        try:
            import psutil
            return psutil.virtual_memory().percent
        except ImportError:
            return 0.0

    async def _publish(self, event_type: str, payload: dict) -> None:
        if self._event_bus:
            await self._event_bus.publish(event_type, payload, source="performance_monitor")
