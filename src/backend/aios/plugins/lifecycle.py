"""Plugin lifecycle — validated state transitions and stage definitions."""

from enum import Enum
from aios.plugins.models import PluginStatus


class LifecycleStage(str, Enum):
    INITIALIZE = "initialize"
    START = "start"
    REGISTER = "register"
    HEALTH = "health"
    STOP = "stop"
    SHUTDOWN = "shutdown"
    DISPOSE = "dispose"


VALID_TRANSITIONS: dict[PluginStatus, set[PluginStatus]] = {
    PluginStatus.DISCOVERED: {PluginStatus.VALIDATED, PluginStatus.FAILED, PluginStatus.REMOVED},
    PluginStatus.VALIDATED: {PluginStatus.VERIFIED, PluginStatus.FAILED, PluginStatus.REMOVED},
    PluginStatus.VERIFIED: {PluginStatus.LOADING, PluginStatus.FAILED, PluginStatus.REMOVED},
    PluginStatus.LOADING: {PluginStatus.LOADED, PluginStatus.FAILED, PluginStatus.REMOVED},
    PluginStatus.LOADED: {PluginStatus.INITIALIZING, PluginStatus.DISABLED, PluginStatus.FAILED, PluginStatus.REMOVED},
    PluginStatus.INITIALIZING: {PluginStatus.STARTING, PluginStatus.FAILED, PluginStatus.REMOVED},
    PluginStatus.STARTING: {PluginStatus.ACTIVE, PluginStatus.FAILED, PluginStatus.REMOVED},
    PluginStatus.ACTIVE: {PluginStatus.STOPPING, PluginStatus.DEGRADED, PluginStatus.DISABLED, PluginStatus.FAILED, PluginStatus.REMOVED},
    PluginStatus.STOPPING: {PluginStatus.STOPPED, PluginStatus.FAILED, PluginStatus.REMOVED},
    PluginStatus.STOPPED: {PluginStatus.STARTING, PluginStatus.UNLOADED, PluginStatus.FAILED, PluginStatus.REMOVED},
    PluginStatus.DISABLED: {PluginStatus.LOADING, PluginStatus.REMOVED},
    PluginStatus.DEGRADED: {PluginStatus.ACTIVE, PluginStatus.STOPPING, PluginStatus.FAILED, PluginStatus.REMOVED},
    PluginStatus.FAILED: {PluginStatus.LOADING, PluginStatus.REMOVED},
    PluginStatus.UNLOADED: {PluginStatus.REMOVED, PluginStatus.DISCOVERED},
    PluginStatus.REMOVED: set(),
}


class PluginLifecycle:
    def validate_transition(self, current: PluginStatus, target: PluginStatus) -> None:
        """Validates if a transition from current status to target status is allowed."""
        allowed = VALID_TRANSITIONS.get(current)
        if allowed is None:
            raise ValueError(f"Unknown current status: {current}")
        if target not in allowed:
            raise ValueError(f"Invalid transition: {current.value} -> {target.value}")

    def can_transition(self, current: PluginStatus, target: PluginStatus) -> bool:
        """Checks if a transition from current status to target status is allowed."""
        allowed = VALID_TRANSITIONS.get(current)
        return allowed is not None and target in allowed

    def get_allowed_transitions(self, current: PluginStatus) -> set[PluginStatus]:
        """Returns the set of allowed target statuses from the current status."""
        return VALID_TRANSITIONS.get(current, set())
