"""MemoryEventBus — typed pub/sub for memory events."""

from datetime import datetime
from typing import Any, Callable
from uuid import uuid4


class MemoryEventBus:
    def __init__(self, history_limit: int = 100):
        self._subscriptions: dict[str, list[dict]] = {}
        self._history: list[dict] = []
        self._history_limit = history_limit

    def subscribe(self, event_type: str, callback: Callable, event_filter: Callable | None = None) -> Callable:
        sub_id = uuid4().hex
        sub = {"id": sub_id, "event_type": event_type, "callback": callback, "filter": event_filter}
        self._subscriptions.setdefault(event_type, []).append(sub)
        return lambda: self._unsubscribe(sub_id)

    def _unsubscribe(self, sub_id: str) -> bool:
        for event_type, subs in self._subscriptions.items():
            for sub in subs:
                if sub["id"] == sub_id:
                    subs.remove(sub)
                    return True
        return False

    def publish(self, event_type: str, payload: Any):
        event = {"type": event_type, "payload": payload, "timestamp": int(datetime.now().timestamp() * 1000)}
        self._history.append(event)
        if len(self._history) > self._history_limit:
            self._history = self._history[-self._history_limit:]
        subs = list(self._subscriptions.get(event_type, []))
        wildcard_subs = list(self._subscriptions.get("*", []))
        for sub in subs + wildcard_subs:
            if sub.get("filter") and not sub["filter"](event):
                continue
            try:
                sub["callback"](event)
            except Exception:
                pass

    def on_any(self, callback: Callable) -> Callable:
        return self.subscribe("*", callback)

    def get_history(self, event_type: str | None = None, limit: int = 100) -> list[dict]:
        if event_type:
            return [e for e in self._history if e["type"] == event_type][-limit:]
        return self._history[-limit:]

    def clear_history(self):
        self._history.clear()

    def subscriber_count(self) -> int:
        return sum(len(subs) for subs in self._subscriptions.values())
