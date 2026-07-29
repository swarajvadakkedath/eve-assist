"""Project Detector — scans parent directories for project markers."""

from pathlib import Path

from .models import ProjectInfo


PROJECT_MARKERS: dict[str, list[str]] = {
    "python": ["pyproject.toml", "setup.py", "setup.cfg", "Pipfile", "requirements.txt"],
    "node": ["package.json", "yarn.lock", "pnpm-lock.yaml"],
    "rust": ["Cargo.toml"],
    "go": ["go.mod"],
    "dotnet": ["*.csproj", "*.sln", "*.fsproj"],
    "ruby": ["Gemfile"],
    "java": ["pom.xml", "build.gradle", "build.gradle.kts"],
    "elixir": ["mix.exs"],
    "php": ["composer.json"],
    "dart": ["pubspec.yaml"],
    "swift": ["Package.swift"],
    "generic": [".git"],
}

EXTENSION_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "node", ".jsx": "node", ".ts": "node", ".tsx": "node",
    ".rs": "rust",
    ".go": "go",
    ".cs": "dotnet", ".vb": "dotnet", ".fs": "dotnet",
    ".rb": "ruby",
    ".java": "java", ".kt": "java",
    ".ex": "elixir", ".exs": "elixir",
    ".php": "php",
    ".dart": "dart",
    ".swift": "swift",
}


def detect_project_from_file(file_path: str | None, max_depth: int = 10) -> ProjectInfo | None:
    if not file_path:
        return None
    try:
        current = Path(file_path).resolve().parent
    except (OSError, ValueError):
        return None
    depth = 0
    while depth < max_depth:
        project_type = _scan_directory(current)
        if project_type is not None:
            return project_type
        parent = current.parent
        if parent == current:
            break
        current = parent
        depth += 1
    return None


def detect_project_from_path(path: str, max_depth: int = 10) -> ProjectInfo | None:
    if not path:
        return None
    try:
        current = Path(path).resolve()
    except (OSError, ValueError):
        return None
    if not current.is_dir():
        current = current.parent
    depth = 0
    while depth < max_depth:
        project_type = _scan_directory(current)
        if project_type is not None:
            return project_type
        parent = current.parent
        if parent == current:
            break
        current = parent
        depth += 1
    return None


def infer_project_type_from_file(file_path: str) -> str | None:
    ext = Path(file_path).suffix.lower()
    return EXTENSION_MAP.get(ext)


def _scan_directory(directory: Path) -> ProjectInfo | None:
    try:
        entries = {e.name for e in directory.iterdir() if e.is_file() or e.is_dir()}
    except (PermissionError, OSError):
        return None
    for project_type, markers in PROJECT_MARKERS.items():
        found = [m for m in markers if _marker_exists(directory, m, entries)]
        if found:
            return ProjectInfo(path=str(directory), type=project_type, markers=found)
    return None


def _marker_exists(directory: Path, marker: str, entries: set[str]) -> bool:
    if marker.startswith("*."):
        ext = marker[1:]
        return any(e.endswith(ext) for e in entries)
    return marker in entries
