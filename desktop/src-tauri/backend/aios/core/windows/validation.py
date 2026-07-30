"""Input and path validation for the Windows Adapter."""

import os
import re
from pathlib import Path

from .exceptions import ValidationError, PathTraversalError


ALLOWED_FILE_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".jsx", ".tsx",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".csv", ".xml", ".html", ".css", ".scss", ".less",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".tar", ".gz", ".7z", ".rar",
    ".mp3", ".wav", ".mp4", ".avi", ".mkv",
    ".exe", ".dll", ".bat", ".ps1",
    ".log", ".env", ".gitignore",
}

BLOCKED_DIRECTORIES = {
    "C:\\Windows",
    "C:\\Windows\\System32",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
    "C:\\ProgramData",
    os.path.expandvars("%SYSTEMROOT%"),
    os.path.expandvars("%WINDIR%"),
}

BLOCKED_DIR_PREFIXES = [
    os.path.normpath(p).lower()
    for p in BLOCKED_DIRECTORIES if os.path.isabs(p) or "$" not in p
]


def validate_path(path: str, allow_write: bool = False) -> str:
    if not path or not path.strip():
        raise ValidationError("Path must not be empty")
    normalized = os.path.normpath(path.strip())
    resolved = str(Path(normalized).resolve())
    if not os.path.isabs(resolved):
        raise PathTraversalError(f"Relative paths are not allowed: {path}")
    lowered = resolved.lower()
    for blocked in BLOCKED_DIR_PREFIXES:
        if lowered.startswith(blocked):
            raise PathTraversalError(f"Access to system directory is blocked: {path}")
    if ".." in normalized.split(os.sep):
        raise PathTraversalError(f"Directory traversal detected in path: {path}")
    return resolved


def validate_file_extension(path: str) -> bool:
    ext = Path(path).suffix.lower()
    if ext and ext not in ALLOWED_FILE_EXTENSIONS:
        raise ValidationError(f"File extension not allowed: {ext}")
    return True


def validate_process_name(name: str) -> str:
    if not name or not name.strip():
        raise ValidationError("Process name must not be empty")
    cleaned = name.strip()
    if len(cleaned) > 260:
        raise ValidationError("Process name too long")
    if re.search(r'[<>"|?*]', cleaned):
        raise ValidationError(f"Process name contains invalid characters: {cleaned}")
    return cleaned


def validate_pid(pid: int) -> int:
    pid_int = int(pid)
    if pid_int <= 0:
        raise ValidationError(f"Invalid PID: {pid}")
    return pid_int


def validate_clipboard_text(text: str) -> str:
    if not isinstance(text, str):
        raise ValidationError("Clipboard content must be a string")
    return text


def validate_coordinates(x: int, y: int):
    try:
        x_val = int(x)
        y_val = int(y)
    except (TypeError, ValueError):
        raise ValidationError(f"Invalid coordinates: ({x}, {y})")
    if x_val < 0 or y_val < 0:
        raise ValidationError(f"Coordinates must be non-negative: ({x_val}, {y_val})")
    return x_val, y_val


def validate_search_pattern(pattern: str) -> str:
    if not pattern or not pattern.strip():
        raise ValidationError("Search pattern must not be empty")
    cleaned = pattern.strip()
    if len(cleaned) > 500:
        raise ValidationError("Search pattern too long")
    if re.search(r'[<>"|?*\x00-\x1f]', cleaned):
        bad = re.findall(r'[<>"|]', cleaned)
        if bad:
            raise ValidationError(f"Search pattern contains invalid characters: {set(bad)}")
    return cleaned
