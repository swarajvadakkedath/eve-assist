"""Workspace Exceptions."""


class WorkspaceBaseError(Exception):
    message = "A workspace error occurred"


class WorkspaceNotFoundError(WorkspaceBaseError):
    def __init__(self, workspace_id: str):
        super().__init__(f"Workspace not found: {workspace_id}")


class SensorNotRunningError(WorkspaceBaseError):
    def __init__(self, sensor_name: str):
        super().__init__(f"Sensor not running: {sensor_name}")


class DetectionError(WorkspaceBaseError):
    def __init__(self, path: str, reason: str = ""):
        super().__init__(f"Detection failed for path {path}: {reason}")


class CacheExpiredError(WorkspaceBaseError):
    def __init__(self, key: str):
        super().__init__(f"Cache entry expired: {key}")
