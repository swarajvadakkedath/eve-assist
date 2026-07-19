"""Project & Framework Detection — discover projects and frameworks."""

import os
from typing import Any
from aios.workspace.models import Project, FrameworkType
from aios.workspace.interfaces import IProjectDetector
from aios.workspace.providers import (
    PackageJsonDetector, PythonDetector, RustDetector, GoDetector,
    DotnetDetector, JavaDetector, FlutterDetector,
)
from aios.utils.logger import get_logger

logger = get_logger(__name__)


class ProjectDetector:
    def __init__(self):
        self._providers: list[IProjectDetector] = [
            PackageJsonDetector(),
            PythonDetector(),
            RustDetector(),
            GoDetector(),
            DotnetDetector(),
            JavaDetector(),
            FlutterDetector(),
        ]

    async def detect_project(self, path: str) -> Project | None:
        if not os.path.isdir(path):
            return None
        for provider in self._providers:
            try:
                project = await provider.detect(path)
                if project:
                    logger.info("detector.project_found", path=path, framework=project.framework.value)
                    return project
            except Exception as e:
                logger.error("detector.provider_failed", provider=type(provider).__name__, error=str(e))
        return None

    async def scan_directory(self, root_path: str, max_depth: int = 3) -> list[Project]:
        projects = []
        root_path = os.path.abspath(root_path)
        root_project = await self.detect_project(root_path)
        if root_project:
            projects.append(root_project)
        base_depth = root_path.rstrip(os.sep).count(os.sep)
        for dirpath, dirnames, filenames in os.walk(root_path):
            depth = dirpath.count(os.sep) - base_depth
            if depth > max_depth:
                dirnames.clear()
                continue
            if dirpath == root_path:
                continue
            project = await self.detect_project(dirpath)
            if project:
                projects.append(project)
                dirnames.clear()
        return projects


class FrameworkDetector:
    async def detect_framework(self, file_list: list[str]) -> FrameworkType:
        files = " ".join(f.lower() for f in file_list)
        if "package.json" in files:
            return FrameworkType.NODE_JS
        if "requirements.txt" in files or "setup.py" in files:
            return FrameworkType.PYTHON
        if "cargo.toml" in files or "cargo.lock" in files:
            return FrameworkType.RUST
        if "go.mod" in files:
            return FrameworkType.GO
        if any(f.endswith(".csproj") for f in file_list):
            return FrameworkType.DOTNET
        if "pubspec.yaml" in files:
            return FrameworkType.FLUTTER
        if "pom.xml" in files or "build.gradle" in files:
            return FrameworkType.JAVA
        return FrameworkType.UNKNOWN

    def detect_language(self, framework: FrameworkType) -> str:
        mapping = {
            FrameworkType.NEXT_JS: "typescript",
            FrameworkType.REACT: "typescript",
            FrameworkType.VUE: "typescript",
            FrameworkType.ANGULAR: "typescript",
            FrameworkType.NODE_JS: "javascript",
            FrameworkType.FASTAPI: "python",
            FrameworkType.DJANGO: "python",
            FrameworkType.FLASK: "python",
            FrameworkType.PYTHON: "python",
            FrameworkType.RUST: "rust",
            FrameworkType.GO: "go",
            FrameworkType.DOTNET: "csharp",
            FrameworkType.JAVA: "java",
            FrameworkType.FLUTTER: "dart",
        }
        return mapping.get(framework, "")
