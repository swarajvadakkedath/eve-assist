"""Workspace Registry — registers sensors, providers, and detectors."""

from typing import Any
from aios.workspace.interfaces import IWorkspaceSensor, IProjectDetector
from aios.utils.logger import get_logger

logger = get_logger(__name__)


class WorkspaceRegistry:
    def __init__(self):
        self._sensors: dict[str, IWorkspaceSensor] = {}
        self._project_detectors: dict[str, IProjectDetector] = {}

    def register_sensor(self, name: str, sensor: IWorkspaceSensor) -> None:
        self._sensors[name] = sensor
        logger.info("registry.sensor_registered", name=name)

    def unregister_sensor(self, name: str) -> None:
        self._sensors.pop(name, None)

    def get_sensor(self, name: str) -> IWorkspaceSensor | None:
        return self._sensors.get(name)

    def list_sensors(self) -> list[str]:
        return list(self._sensors.keys())

    def register_project_detector(self, name: str, detector: IProjectDetector) -> None:
        self._project_detectors[name] = detector
        logger.info("registry.detector_registered", name=name)

    def unregister_project_detector(self, name: str) -> None:
        self._project_detectors.pop(name, None)

    def list_project_detectors(self) -> list[str]:
        return list(self._project_detectors.keys())
