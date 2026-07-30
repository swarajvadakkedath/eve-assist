"""Context Engine — event-driven observer for workspace, app, and file context."""

from .models import Context, ProjectInfo, ActivityType
from .engine import ContextEngine
from .project_detector import (
    detect_project_from_file,
    detect_project_from_path,
    infer_project_type_from_file,
    PROJECT_MARKERS,
    EXTENSION_MAP,
)
from .activity_detector import detect_activity, extract_active_file

__all__ = [
    "Context",
    "ProjectInfo",
    "ActivityType",
    "ContextEngine",
    "detect_project_from_file",
    "detect_project_from_path",
    "infer_project_type_from_file",
    "detect_activity",
    "extract_active_file",
    "PROJECT_MARKERS",
    "EXTENSION_MAP",
]
