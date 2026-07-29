"""Filesystem operations — safe wrappers for file and directory operations."""

import os
import shutil
import stat
from datetime import datetime
from glob import glob
from pathlib import Path

from .exceptions import FileOperationError, FileNotFoundError_
from .validation import validate_path, validate_file_extension, validate_search_pattern


class FileSystemService:
    def search_files(self, pattern: str, search_path: str | None = None) -> list[dict]:
        safe_pattern = validate_search_pattern(pattern)
        root = search_path or os.path.expanduser("~")
        resolved_root = validate_path(root)
        results = []
        full_pattern = os.path.join(resolved_root, safe_pattern)
        for filepath in glob(full_pattern, recursive=True):
            try:
                stat_result = os.stat(filepath)
                results.append({
                    "path": filepath,
                    "name": os.path.basename(filepath),
                    "size": stat_result.st_size,
                    "is_dir": os.path.isdir(filepath),
                    "modified": datetime.fromtimestamp(stat_result.st_mtime).isoformat(),
                    "created": datetime.fromtimestamp(stat_result.st_ctime).isoformat(),
                })
            except OSError:
                continue
        return results

    def read_file(self, path: str, encoding: str = "utf-8") -> str:
        resolved = validate_path(path)
        validate_file_extension(resolved)
        if not os.path.isfile(resolved):
            raise FileNotFoundError_(f"File not found: {path}")
        try:
            with open(resolved, "r", encoding=encoding, errors="replace") as f:
                return f.read()
        except PermissionError:
            raise FileOperationError(f"Permission denied reading file: {path}")
        except OSError as e:
            raise FileOperationError(f"Failed to read file: {path}: {e}")

    def write_file(self, path: str, content: str, encoding: str = "utf-8") -> None:
        resolved = validate_path(path, allow_write=True)
        validate_file_extension(resolved)
        parent = os.path.dirname(resolved)
        try:
            os.makedirs(parent, exist_ok=True)
        except PermissionError:
            raise FileOperationError(f"Permission denied creating directory: {parent}")
        try:
            with open(resolved, "w", encoding=encoding) as f:
                f.write(content)
        except PermissionError:
            raise FileOperationError(f"Permission denied writing file: {path}")
        except OSError as e:
            raise FileOperationError(f"Failed to write file: {path}: {e}")

    def delete_file(self, path: str) -> None:
        resolved = validate_path(path, allow_write=True)
        if not os.path.exists(resolved):
            raise FileNotFoundError_(f"Path not found: {path}")
        try:
            if os.path.isdir(resolved):
                shutil.rmtree(resolved)
            else:
                os.chmod(resolved, stat.S_IWRITE)
                os.remove(resolved)
        except PermissionError:
            raise FileOperationError(f"Permission denied deleting: {path}")
        except OSError as e:
            raise FileOperationError(f"Failed to delete: {path}: {e}")

    def create_directory(self, path: str) -> None:
        resolved = validate_path(path, allow_write=True)
        try:
            os.makedirs(resolved, exist_ok=True)
        except PermissionError:
            raise FileOperationError(f"Permission denied creating directory: {path}")
        except OSError as e:
            raise FileOperationError(f"Failed to create directory: {path}: {e}")

    def move_file(self, src: str, dst: str) -> None:
        resolved_src = validate_path(src, allow_write=True)
        resolved_dst = validate_path(dst, allow_write=True)
        if not os.path.exists(resolved_src):
            raise FileNotFoundError_(f"Source not found: {src}")
        try:
            os.makedirs(os.path.dirname(resolved_dst), exist_ok=True)
            shutil.move(resolved_src, resolved_dst)
        except PermissionError:
            raise FileOperationError(f"Permission denied moving: {src} -> {dst}")
        except OSError as e:
            raise FileOperationError(f"Failed to move: {src} -> {dst}: {e}")

    def copy_file(self, src: str, dst: str) -> None:
        resolved_src = validate_path(src)
        resolved_dst = validate_path(dst, allow_write=True)
        if not os.path.exists(resolved_src):
            raise FileNotFoundError_(f"Source not found: {src}")
        try:
            os.makedirs(os.path.dirname(resolved_dst), exist_ok=True)
            if os.path.isdir(resolved_src):
                shutil.copytree(resolved_src, resolved_dst, dirs_exist_ok=True)
            else:
                shutil.copy2(resolved_src, resolved_dst)
        except PermissionError:
            raise FileOperationError(f"Permission denied copying: {src} -> {dst}")
        except OSError as e:
            raise FileOperationError(f"Failed to copy: {src} -> {dst}: {e}")

    def get_metadata(self, path: str) -> dict:
        resolved = validate_path(path)
        if not os.path.exists(resolved):
            raise FileNotFoundError_(f"Path not found: {path}")
        try:
            stat_result = os.stat(resolved)
            return {
                "path": resolved,
                "name": os.path.basename(resolved),
                "size": stat_result.st_size,
                "is_dir": os.path.isdir(resolved),
                "is_file": os.path.isfile(resolved),
                "is_symlink": os.path.islink(resolved),
                "modified": datetime.fromtimestamp(stat_result.st_mtime).isoformat(),
                "created": datetime.fromtimestamp(stat_result.st_ctime).isoformat(),
                "accessed": datetime.fromtimestamp(stat_result.st_atime).isoformat(),
                "mode": stat_result.st_mode,
                "extension": Path(resolved).suffix.lower() if os.path.isfile(resolved) else "",
            }
        except PermissionError:
            raise FileOperationError(f"Permission denied reading metadata: {path}")
        except OSError as e:
            raise FileOperationError(f"Failed to read metadata: {path}: {e}")

    def exists(self, path: str) -> bool:
        try:
            resolved = validate_path(path)
            return os.path.exists(resolved)
        except Exception:
            return False

    def directory_exists(self, path: str) -> bool:
        try:
            resolved = validate_path(path)
            return os.path.isdir(resolved)
        except Exception:
            return False
