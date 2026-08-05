"""Audio routing — connects sources to destinations through the pipeline."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from .buffer import AudioBuffer
from .exceptions import AudioRoutingError


class RouteType(Enum):
    """Audio route type."""
    RECORD = "record"          # Microphone → Buffer
    PLAYBACK = "playback"      # Buffer → Speaker
    PIPELINE = "pipeline"      # Microphone → Buffer → Pipeline
    MONITOR = "monitor"        # Buffer → Diagnostics (non-destructive)


class RouteStatus(Enum):
    """Audio route status."""
    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class AudioRoute:
    """Represents an audio route from source to destination."""
    id: str
    route_type: RouteType
    source_id: str
    destination_id: str
    buffer: AudioBuffer
    status: RouteStatus = RouteStatus.INACTIVE
    sample_rate: int = 16000
    channels: int = 1
    sample_width: int = 2
    created_at: float = field(default_factory=time.monotonic)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "route_type": self.route_type.value,
            "source_id": self.source_id,
            "destination_id": self.destination_id,
            "status": self.status.value,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "sample_width": self.sample_width,
            "buffer_usage": self.buffer.count,
            "buffer_capacity": self.buffer.capacity,
        }


class AudioRouter:
    """Routes audio streams between sources, buffers, and destinations.

    Central hub for all audio data flow. No component accesses
    hardware directly — everything goes through routes managed here.
    """

    def __init__(self, *, event_bus: Optional[object] = None):
        self._event_bus = event_bus
        self._routes: dict[str, AudioRoute] = {}
        self._source_buffers: dict[str, AudioBuffer] = {}
        self._dest_buffers: dict[str, AudioBuffer] = {}
        self._forwarding_tasks: dict[str, asyncio.Task] = {}
        self._stream_handlers: dict[str, Callable] = {}
        self._created_at = time.monotonic()
        self._next_route_id = 0

    @property
    def routes(self) -> dict[str, AudioRoute]:
        return dict(self._routes)

    @property
    def active_routes(self) -> list[AudioRoute]:
        return [r for r in self._routes.values() if r.status == RouteStatus.ACTIVE]

    def _generate_route_id(self) -> str:
        self._next_route_id += 1
        return f"route_{self._next_route_id}"

    def create_route(self, route_type: RouteType, source_id: str,
                     destination_id: str, *, buffer_size: int = 8192,
                     sample_rate: int = 16000, channels: int = 1,
                     sample_width: int = 2) -> AudioRoute:
        """Create a new audio route."""
        route_id = self._generate_route_id()
        buffer = AudioBuffer(capacity=buffer_size)

        route = AudioRoute(
            id=route_id,
            route_type=route_type,
            source_id=source_id,
            destination_id=destination_id,
            buffer=buffer,
            sample_rate=sample_rate,
            channels=channels,
            sample_width=sample_width,
        )
        self._routes[route_id] = route
        self._source_buffers[source_id] = buffer
        self._dest_buffers[destination_id] = buffer
        return route

    def remove_route(self, route_id: str) -> None:
        """Remove a route and stop forwarding."""
        if route_id not in self._routes:
            raise AudioRoutingError(f"Route not found: {route_id}")

        route = self._routes[route_id]
        route.buffer.close()

        if route_id in self._forwarding_tasks:
            self._forwarding_tasks[route_id].cancel()
            del self._forwarding_tasks[route_id]

        self._source_buffers.pop(route.source_id, None)
        self._dest_buffers.pop(route.destination_id, None)
        del self._routes[route_id]

    def start_route(self, route_id: str) -> None:
        """Activate a route."""
        if route_id not in self._routes:
            raise AudioRoutingError(f"Route not found: {route_id}")
        self._routes[route_id].status = RouteStatus.ACTIVE

    def pause_route(self, route_id: str) -> None:
        """Pause a route."""
        if route_id not in self._routes:
            raise AudioRoutingError(f"Route not found: {route_id}")
        self._routes[route_id].status = RouteStatus.PAUSED

    def stop_route(self, route_id: str) -> None:
        """Stop a route."""
        if route_id not in self._routes:
            raise AudioRoutingError(f"Route not found: {route_id}")
        self._routes[route_id].status = RouteStatus.INACTIVE

    def write_to_route(self, route_id: str, data: bytes) -> int:
        """Write audio data into a route's buffer."""
        if route_id not in self._routes:
            raise AudioRoutingError(f"Route not found: {route_id}")
        route = self._routes[route_id]
        if route.status != RouteStatus.ACTIVE:
            return 0
        return route.buffer.write(data, block=False)

    def read_from_route(self, route_id: str, length: int) -> bytes:
        """Read audio data from a route's buffer."""
        if route_id not in self._routes:
            raise AudioRoutingError(f"Route not found: {route_id}")
        route = self._routes[route_id]
        return route.buffer.read(length, block=False)

    def get_buffer_for_source(self, source_id: str) -> Optional[AudioBuffer]:
        """Get the buffer associated with a source."""
        return self._source_buffers.get(source_id)

    def get_buffer_for_destination(self, dest_id: str) -> Optional[AudioBuffer]:
        """Get the buffer associated with a destination."""
        return self._dest_buffers.get(dest_id)

    def register_stream_handler(self, route_id: str, handler: Callable) -> None:
        """Register a handler to receive audio from a route.

        The handler receives (route_id, data) and can process audio
        in real-time (e.g., for STT, wake word detection, diagnostics).
        """
        self._stream_handlers[route_id] = handler

    def unregister_stream_handler(self, route_id: str) -> None:
        """Remove a stream handler."""
        self._stream_handlers.pop(route_id, None)

    async def start_forwarding(self, route_id: str) -> None:
        """Start forwarding audio from source buffer to destination."""
        if route_id not in self._forwarding_tasks:
            task = asyncio.create_task(self._forwarding_loop(route_id))
            self._forwarding_tasks[route_id] = task

    async def stop_forwarding(self, route_id: str) -> None:
        """Stop forwarding audio for a route."""
        if route_id in self._forwarding_tasks:
            self._forwarding_tasks[route_id].cancel()
            try:
                await self._forwarding_tasks[route_id]
            except asyncio.CancelledError:
                pass
            del self._forwarding_tasks[route_id]

    async def _forwarding_loop(self, route_id: str) -> None:
        """Forward audio data from route buffer, calling handlers."""
        try:
            while True:
                if route_id not in self._routes:
                    break
                route = self._routes[route_id]
                if route.status != RouteStatus.ACTIVE:
                    await asyncio.sleep(0.01)
                    continue

                data = route.buffer.read(1024, block=False)
                if data:
                    handler = self._stream_handlers.get(route_id)
                    if handler:
                        try:
                            if asyncio.iscoroutinefunction(handler):
                                await handler(route_id, data)
                            else:
                                handler(route_id, data)
                        except Exception:
                            pass
                else:
                    await asyncio.sleep(0.005)
        except asyncio.CancelledError:
            return

    def get_route(self, route_id: str) -> Optional[AudioRoute]:
        """Get a route by ID."""
        return self._routes.get(route_id)

    def to_dict(self) -> dict:
        """Serialize router state."""
        return {
            "route_count": len(self._routes),
            "active_route_count": len(self.active_routes),
            "routes": {k: v.to_dict() for k, v in self._routes.items()},
        }
