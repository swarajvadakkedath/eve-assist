"""Event data models for the Event Bus."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class Event:
    id: str = ""
    type: str = ""
    source: str = ""
    timestamp: datetime = None
    payload: dict = field(default_factory=dict)
    correlation_id: str = ""
    retry_count: int = 0
    priority: int = 0

    def __post_init__(self):
        if not self.id:
            self.id = uuid4().hex
        if not self.timestamp:
            self.timestamp = datetime.utcnow()
        if not self.correlation_id:
            self.correlation_id = self.id


@dataclass
class Subscription:
    id: str
    event_type: str
    handler: callable

    def __post_init__(self):
        if not self.id:
            self.id = uuid4().hex
