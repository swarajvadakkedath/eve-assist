"""System Tool Pack — File, Search, Clipboard, Archive toolkits for AIOS Phase 5.1."""

import asyncio
import gzip
import hashlib
import io
import os
import re
import shutil
import tarfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator

from aios.core.tool_manager import ToolContract, ToolResult
from aios.core.permission_manager import PermissionLevel
from aios.core.event_bus import EventBus


# ──────────────────────────────────────────────
# Sprint 1 — File Toolkit
# ──────────────────────────────────────────────

async def _read_file(params: dict) -> ToolResult:
    try:
        path = Path(params["path"])
        encoding = params.get("encoding", "utf-8")
        offset = params.get("offset")
        limit = params.get("limit")
        if not path.exists():
            return ToolResult(success=False, error=f"File not found: {path}")
        if path.is_dir():
            return ToolResult(success=False, error=f"Path is a directory: {path}")
        if offset is not None or limit is not None:
            with path.open("r", encoding=encoding, errors="replace") as f:
                lines = f.readlines()
            start = offset or 0
            end = start + limit if limit else len(lines)
            content = "".join(lines[start:end])
            return ToolResult(success=True, data={
                "content": content, "path": str(path),
                "total_lines": len(lines), "offset": start, "lines_returned": end - start,
            })
        content = path.read_text(encoding=encoding, errors="replace")
        return ToolResult(success=True, data={
            "content": content, "path": str(path), "size": len(content),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _write_file(params: dict) -> ToolResult:
    try:
        path = Path(params["path"])
        content = params.get("content", "")
        mode = params.get("mode", "w")
        encoding = params.get("encoding", "utf-8")
        path.parent.mkdir(parents=True, exist_ok=True)
        if mode == "a":
            with path.open("a", encoding=encoding) as f:
                f.write(content)
        else:
            path.write_text(content, encoding=encoding)
        stat = path.stat()
        return ToolResult(success=True, data={
            "path": str(path), "size": stat.st_size,
            "mode": mode, "written": len(content),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _create_file(params: dict) -> ToolResult:
    try:
        path = Path(params["path"])
        if path.exists():
            return ToolResult(success=False, error=f"File already exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        content = params.get("content", "")
        path.write_text(content, encoding="utf-8")
        return ToolResult(success=True, data={"path": str(path), "size": len(content)})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _delete_file(params: dict) -> ToolResult:
    try:
        path = Path(params["path"])
        permanent = params.get("permanent", True)
        if not path.exists():
            return ToolResult(success=False, error=f"File not found: {path}")
        if path.is_dir():
            return ToolResult(success=False, error=f"Path is a directory, use delete_directory: {path}")
        if not permanent:
            import send2trash
            send2trash.send2trash(str(path))
        else:
            path.unlink()
        return ToolResult(success=True, data={"path": str(path), "permanent": permanent})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _copy_file(params: dict) -> ToolResult:
    try:
        src = Path(params["source"])
        dst = Path(params["destination"])
        overwrite = params.get("overwrite", False)
        if not src.exists():
            return ToolResult(success=False, error=f"Source not found: {src}")
        if dst.exists() and not overwrite:
            return ToolResult(success=False, error=f"Destination exists: {dst} (use overwrite=true)")
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=overwrite)
        else:
            shutil.copy2(src, dst)
        dst_stat = dst.stat()
        return ToolResult(success=True, data={
            "source": str(src), "destination": str(dst),
            "size": dst_stat.st_size, "is_dir": src.is_dir(),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _move_file(params: dict) -> ToolResult:
    try:
        src = Path(params["source"])
        dst = Path(params["destination"])
        overwrite = params.get("overwrite", False)
        if not src.exists():
            return ToolResult(success=False, error=f"Source not found: {src}")
        if dst.exists() and not overwrite:
            return ToolResult(success=False, error=f"Destination exists: {dst} (use overwrite=true)")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return ToolResult(success=True, data={"source": str(src), "destination": str(dst)})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _rename_file(params: dict) -> ToolResult:
    try:
        path = Path(params["path"])
        new_name = params["new_name"]
        if not path.exists():
            return ToolResult(success=False, error=f"Path not found: {path}")
        new_path = path.parent / new_name
        if new_path.exists():
            return ToolResult(success=False, error=f"Target already exists: {new_path}")
        path.rename(new_path)
        return ToolResult(success=True, data={"source": str(path), "destination": str(new_path)})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _file_metadata(params: dict) -> ToolResult:
    try:
        path = Path(params["path"])
        if not path.exists():
            return ToolResult(success=False, error=f"Path not found: {path}")
        stat = path.stat()
        return ToolResult(success=True, data={
            "path": str(path), "name": path.name, "extension": path.suffix,
            "size": stat.st_size, "is_dir": path.is_dir(), "is_file": path.is_file(),
            "is_symlink": path.is_symlink(), "created": datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "accessed": datetime.fromtimestamp(stat.st_atime, tz=timezone.utc).isoformat(),
            "mode": oct(stat.st_mode), "permissions": stat.st_mode & 0o777,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _file_hash(params: dict) -> ToolResult:
    try:
        path = Path(params["path"])
        algorithm = params.get("algorithm", "sha256")
        if not path.exists() or not path.is_file():
            return ToolResult(success=False, error=f"File not found: {path}")
        h = hashlib.new(algorithm)
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return ToolResult(success=True, data={
            "path": str(path), "algorithm": algorithm, "hash": h.hexdigest(),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _list_directory(params: dict) -> ToolResult:
    try:
        path = Path(params["path"])
        recursive = params.get("recursive", False)
        include_hidden = params.get("include_hidden", False)
        sort_by = params.get("sort_by", "name")
        if not path.exists():
            return ToolResult(success=False, error=f"Path not found: {path}")
        if not path.is_dir():
            return ToolResult(success=False, error=f"Not a directory: {path}")
        entries = []
        iterator = path.rglob("*") if recursive else path.iterdir()
        for entry in iterator:
            if not include_hidden and entry.name.startswith("."):
                continue
            try:
                stat = entry.stat()
                entries.append({
                    "name": entry.name, "path": str(entry), "is_dir": entry.is_dir(),
                    "size": stat.st_size, "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                })
            except OSError:
                entries.append({"name": entry.name, "path": str(entry), "is_dir": entry.is_dir(), "size": 0, "modified": ""})
        reverse = False
        if sort_by.startswith("-"):
            reverse = True
            sort_by = sort_by[1:]
        key_fn = {"name": lambda e: e["name"].lower(), "size": lambda e: e["size"], "modified": lambda e: e["modified"]}.get(sort_by, lambda e: e["name"].lower())
        entries.sort(key=key_fn, reverse=reverse)
        return ToolResult(success=True, data={
            "path": str(path), "entries": entries, "count": len(entries), "recursive": recursive,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _create_directory(params: dict) -> ToolResult:
    try:
        path = Path(params["path"])
        exist_ok = params.get("exist_ok", True)
        path.mkdir(parents=True, exist_ok=exist_ok)
        return ToolResult(success=True, data={"path": str(path), "created": path.exists()})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _delete_directory(params: dict) -> ToolResult:
    try:
        path = Path(params["path"])
        recursive = params.get("recursive", True)
        if not path.exists():
            return ToolResult(success=False, error=f"Directory not found: {path}")
        if not path.is_dir():
            return ToolResult(success=False, error=f"Not a directory: {path}")
        if recursive:
            shutil.rmtree(path)
        else:
            path.rmdir()
        return ToolResult(success=True, data={"path": str(path), "recursive": recursive})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ──────────────────────────────────────────────
# Sprint 2 — Search Toolkit
# ──────────────────────────────────────────────

async def _search_files(params: dict) -> ToolResult:
    try:
        root = Path(params.get("path", "."))
        pattern = params.get("pattern", "*")
        recursive = params.get("recursive", True)
        max_results = params.get("max_results", 1000)
        include_hidden = params.get("include_hidden", False)
        if not root.exists():
            return ToolResult(success=False, error=f"Path not found: {root}")
        results = []
        iterator = root.rglob(pattern) if recursive else root.glob(pattern)
        for entry in iterator:
            if not include_hidden and entry.name.startswith("."):
                continue
            if entry.is_file():
                try:
                    stat = entry.stat()
                    results.append({
                        "path": str(entry), "name": entry.name, "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                    })
                except OSError:
                    results.append({"path": str(entry), "name": entry.name, "size": 0, "modified": ""})
            if len(results) >= max_results:
                break
        return ToolResult(success=True, data={"files": results, "count": len(results), "path": str(root), "pattern": pattern})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _search_directories(params: dict) -> ToolResult:
    try:
        root = Path(params.get("path", "."))
        pattern = params.get("pattern", "*")
        recursive = params.get("recursive", True)
        max_results = params.get("max_results", 500)
        include_hidden = params.get("include_hidden", False)
        if not root.exists():
            return ToolResult(success=False, error=f"Path not found: {root}")
        results = []
        iterator = root.rglob(pattern) if recursive else root.glob(pattern)
        for entry in iterator:
            if not include_hidden and entry.name.startswith("."):
                continue
            if entry.is_dir():
                results.append({"path": str(entry), "name": entry.name})
            if len(results) >= max_results:
                break
        return ToolResult(success=True, data={
            "directories": results, "count": len(results), "path": str(root), "pattern": pattern,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _search_by_extension(params: dict) -> ToolResult:
    try:
        root = Path(params.get("path", "."))
        extension = params.get("extension", "")
        if extension and not extension.startswith("."):
            extension = "." + extension
        recursive = params.get("recursive", True)
        max_results = params.get("max_results", 1000)
        pattern = f"*{extension}" if extension else "*"
        if not root.exists():
            return ToolResult(success=False, error=f"Path not found: {root}")
        results = []
        iterator = root.rglob(pattern) if recursive else root.glob(pattern)
        for entry in iterator:
            if entry.is_file():
                try:
                    stat = entry.stat()
                    results.append({
                        "path": str(entry), "name": entry.name, "size": stat.st_size,
                        "extension": entry.suffix,
                        "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                    })
                except OSError:
                    results.append({"path": str(entry), "name": entry.name, "extension": entry.suffix, "size": 0, "modified": ""})
            if len(results) >= max_results:
                break
        return ToolResult(success=True, data={
            "files": results, "count": len(results), "extension": extension,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _search_by_name(params: dict) -> ToolResult:
    try:
        root = Path(params.get("path", "."))
        query = params.get("query", "")
        recursive = params.get("recursive", True)
        max_results = params.get("max_results", 1000)
        case_sensitive = params.get("case_sensitive", False)
        if not root.exists():
            return ToolResult(success=False, error=f"Path not found: {root}")
        results = []
        iterator = root.rglob("*") if recursive else root.glob("*")
        q = query if case_sensitive else query.lower()
        for entry in iterator:
            name = entry.name if case_sensitive else entry.name.lower()
            if q in name:
                is_dir = entry.is_dir()
                try:
                    stat = entry.stat()
                    results.append({
                        "path": str(entry), "name": entry.name, "is_dir": is_dir,
                        "size": stat.st_size if not is_dir else 0,
                        "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                    })
                except OSError:
                    results.append({"path": str(entry), "name": entry.name, "is_dir": is_dir, "size": 0, "modified": ""})
            if len(results) >= max_results:
                break
        return ToolResult(success=True, data={
            "results": results, "count": len(results), "query": query,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _search_by_regex(params: dict) -> ToolResult:
    try:
        root = Path(params.get("path", "."))
        regex = params.get("regex", "")
        recursive = params.get("recursive", True)
        max_results = params.get("max_results", 1000)
        search_content = params.get("search_content", False)
        if not root.exists():
            return ToolResult(success=False, error=f"Path not found: {root}")
        try:
            pattern = re.compile(regex)
        except re.error as e:
            return ToolResult(success=False, error=f"Invalid regex: {e}")
        results = []
        iterator = root.rglob("*") if recursive else root.glob("*")
        for entry in iterator:
            if entry.is_dir() and not search_content:
                if pattern.search(entry.name):
                    results.append({"path": str(entry), "name": entry.name, "is_dir": True, "match": entry.name})
            elif entry.is_file():
                if pattern.search(entry.name):
                    try:
                        stat = entry.stat()
                        results.append({
                            "path": str(entry), "name": entry.name, "is_dir": False,
                            "size": stat.st_size, "match": entry.name,
                            "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                        })
                    except OSError:
                        results.append({"path": str(entry), "name": entry.name, "is_dir": False, "size": 0, "match": entry.name, "modified": ""})
                elif search_content:
                    try:
                        text = entry.read_text(encoding="utf-8", errors="replace")
                        for lineno, line in enumerate(text.splitlines(), 1):
                            if pattern.search(line):
                                results.append({
                                    "path": str(entry), "name": entry.name, "line": lineno,
                                    "content": line.strip()[:200], "is_dir": False,
                                })
                                break
                    except Exception:
                        pass
            if len(results) >= max_results:
                break
        return ToolResult(success=True, data={
            "results": results, "count": len(results), "regex": regex, "search_content": search_content,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _search_by_size(params: dict) -> ToolResult:
    try:
        root = Path(params.get("path", "."))
        min_size = params.get("min_size", 0)
        max_size = params.get("max_size", float("inf"))
        unit = params.get("unit", "b")
        recursive = params.get("recursive", True)
        max_results = params.get("max_results", 1000)
        multipliers = {"b": 1, "kb": 1024, "mb": 1024**2, "gb": 1024**3}
        mult = multipliers.get(unit.lower(), 1)
        min_bytes = min_size * mult
        max_bytes = max_size * mult if max_size != float("inf") else float("inf")
        if not root.exists():
            return ToolResult(success=False, error=f"Path not found: {root}")
        results = []
        iterator = root.rglob("*") if recursive else root.glob("*")
        for entry in iterator:
            if entry.is_file():
                try:
                    size = entry.stat().st_size
                    if min_bytes <= size <= max_bytes:
                        results.append({
                            "path": str(entry), "name": entry.name, "size": size,
                            "size_hr": _format_size(size),
                            "modified": datetime.fromtimestamp(entry.stat().st_mtime, tz=timezone.utc).isoformat(),
                        })
                except OSError:
                    pass
            if len(results) >= max_results:
                break
        return ToolResult(success=True, data={
            "files": results, "count": len(results),
            "min_size": min_size, "max_size": max_size if max_size != float("inf") else None, "unit": unit,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _search_by_modified_date(params: dict) -> ToolResult:
    try:
        root = Path(params.get("path", "."))
        after = params.get("after")
        before = params.get("before")
        recursive = params.get("recursive", True)
        max_results = params.get("max_results", 1000)
        if not root.exists():
            return ToolResult(success=False, error=f"Path not found: {root}")
        after_ts = datetime.fromisoformat(after).timestamp() if after else 0
        before_ts = datetime.fromisoformat(before).timestamp() if before else float("inf")
        results = []
        iterator = root.rglob("*") if recursive else root.glob("*")
        for entry in iterator:
            try:
                mtime = entry.stat().st_mtime
                if after_ts <= mtime <= before_ts:
                    is_dir = entry.is_dir()
                    results.append({
                        "path": str(entry), "name": entry.name, "is_dir": is_dir,
                        "size": entry.stat().st_size if not is_dir else 0,
                        "modified": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
                    })
            except OSError:
                pass
            if len(results) >= max_results:
                break
        return ToolResult(success=True, data={
            "results": results, "count": len(results), "after": after, "before": before,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ──────────────────────────────────────────────
# Sprint 3 — Clipboard Toolkit
# ──────────────────────────────────────────────

_clipboard_monitors: dict[str, asyncio.Task] = {}
_clipboard_last_content: str = ""


async def _clipboard_read(params: dict) -> ToolResult:
    try:
        import pyperclip
        text = pyperclip.paste()
        return ToolResult(success=True, data={
            "content": text, "length": len(text), "has_content": len(text) > 0,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _clipboard_write(params: dict) -> ToolResult:
    try:
        import pyperclip
        text = params.get("content", "")
        pyperclip.copy(text)
        global _clipboard_last_content
        _clipboard_last_content = text
        return ToolResult(success=True, data={"length": len(text), "content": text[:100]})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _clipboard_clear(params: dict) -> ToolResult:
    try:
        import pyperclip
        pyperclip.copy("")
        global _clipboard_last_content
        _clipboard_last_content = ""
        return ToolResult(success=True, data={"cleared": True})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _clipboard_monitor(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    try:
        import pyperclip
        interval = params.get("interval", 1.0)
        action = params.get("action", "start")
        monitor_id = params.get("monitor_id", "default")

        if action == "stop":
            task = _clipboard_monitors.pop(monitor_id, None)
            if task:
                task.cancel()
                return ToolResult(success=True, data={"monitoring": False, "monitor_id": monitor_id})
            return ToolResult(success=True, data={"monitoring": False, "message": "Monitor not running"})

        if action == "status":
            return ToolResult(success=True, data={
                "monitoring": monitor_id in _clipboard_monitors,
                "active_monitors": len(_clipboard_monitors),
            })

        if monitor_id in _clipboard_monitors:
            return ToolResult(success=False, error=f"Monitor already running: {monitor_id}")

        global _clipboard_last_content
        _clipboard_last_content = pyperclip.paste()

        async def _poll():
            global _clipboard_last_content
            try:
                while True:
                    await asyncio.sleep(interval)
                    current = pyperclip.paste()
                    if current != _clipboard_last_content:
                        old = _clipboard_last_content
                        _clipboard_last_content = current
                        if event_bus:
                            await event_bus.publish(
                                "clipboard:changed",
                                {"content": current[:500], "length": len(current),
                                 "previous_length": len(old), "monitor_id": monitor_id},
                                source="system_tools",
                            )
            except asyncio.CancelledError:
                pass

        task = asyncio.create_task(_poll())
        _clipboard_monitors[monitor_id] = task
        return ToolResult(success=True, data={
            "monitoring": True, "monitor_id": monitor_id, "interval": interval,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ──────────────────────────────────────────────
# Sprint 4 — Archive Toolkit
# ──────────────────────────────────────────────

SUPPORTED_ARCHIVE_FORMATS = {"zip", "tar", "gzip", "tar.gz", "tgz"}


async def _compress(params: dict) -> ToolResult:
    try:
        source = Path(params["source"])
        destination = Path(params.get("destination", ""))
        format = params.get("format", "zip").lower()
        compression_level = params.get("compression_level", 6)
        include_root = params.get("include_root", True)
        if not source.exists():
            return ToolResult(success=False, error=f"Source not found: {source}")
        if format not in SUPPORTED_ARCHIVE_FORMATS:
            return ToolResult(success=False, error=f"Unsupported format: {format}. Use: {', '.join(sorted(SUPPORTED_ARCHIVE_FORMATS))}")
        if not destination:
            destination = source.parent / f"{source.name}.{format.replace('tar.gz', 'tar.gz').replace('tgz', 'tgz')}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if format == "zip":
            _create_zip(source, destination, compression_level, include_root)
        elif format in ("tar", "tar.gz", "tgz"):
            _create_tar(source, destination, format, include_root)
        elif format == "gzip":
            _create_gzip(source, destination, compression_level)
        result_size = destination.stat().st_size if destination.exists() else 0
        return ToolResult(success=True, data={
            "source": str(source), "destination": str(destination),
            "format": format, "size": result_size,
            "size_hr": _format_size(result_size),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _extract(params: dict) -> ToolResult:
    try:
        archive = Path(params["archive"])
        destination = Path(params.get("destination", ""))
        format = params.get("format", "").lower()
        if not archive.exists():
            return ToolResult(success=False, error=f"Archive not found: {archive}")
        if not destination:
            destination = archive.parent / archive.stem
        destination.mkdir(parents=True, exist_ok=True)
        if not format:
            format = _detect_archive_format(archive)
        if format == "zip":
            with zipfile.ZipFile(archive, "r") as zf:
                zf.extractall(destination)
        elif format in ("tar", "tar.gz", "tgz"):
            mode = "r:gz" if format in ("tar.gz", "tgz") else "r:"
            with tarfile.open(archive, mode) as tf:
                tf.extractall(destination)
        elif format == "gzip":
            output = destination / archive.stem.replace(".gz", "").replace(".gzip", "")
            with gzip.open(archive, "rb") as gf:
                data = gf.read()
            output.write_bytes(data)
        else:
            return ToolResult(success=False, error=f"Unsupported format: {format}")
        extracted = sum(1 for _ in destination.rglob("*"))
        return ToolResult(success=True, data={
            "archive": str(archive), "destination": str(destination),
            "format": format, "extracted_items": extracted,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _list_contents(params: dict) -> ToolResult:
    try:
        archive = Path(params["archive"])
        format = params.get("format", "").lower()
        if not archive.exists():
            return ToolResult(success=False, error=f"Archive not found: {archive}")
        if not format:
            format = _detect_archive_format(archive)
        entries = []
        if format == "zip":
            with zipfile.ZipFile(archive, "r") as zf:
                for info in zf.infolist():
                    entries.append({
                        "name": info.filename, "size": info.file_size,
                        "compressed_size": info.compress_size, "is_dir": info.filename.endswith("/"),
                        "modified": datetime(*info.date_time, tzinfo=timezone.utc).isoformat() if info.date_time else "",
                    })
        elif format in ("tar", "tar.gz", "tgz"):
            mode = "r:gz" if format in ("tar.gz", "tgz") else "r:"
            with tarfile.open(archive, mode) as tf:
                for info in tf.getmembers():
                    entries.append({
                        "name": info.name, "size": info.size,
                        "is_dir": info.isdir(), "is_file": info.isfile(),
                        "modified": datetime.fromtimestamp(info.mtime, tz=timezone.utc).isoformat() if info.mtime else "",
                    })
        elif format == "gzip":
            stat = archive.stat()
            entries.append({
                "name": archive.name, "size": stat.st_size,
                "compressed": True, "original_name": archive.stem,
            })
        return ToolResult(success=True, data={
            "archive": str(archive), "format": format,
            "entries": entries, "count": len(entries),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _validate(params: dict) -> ToolResult:
    try:
        archive = Path(params["archive"])
        format = params.get("format", "").lower()
        if not archive.exists():
            return ToolResult(success=False, error=f"Archive not found: {archive}")
        if not format:
            format = _detect_archive_format(archive)
        valid = False
        issues = []
        if format == "zip":
            with zipfile.ZipFile(archive, "r") as zf:
                bad = zf.testzip()
                valid = bad is None
                if bad:
                    issues.append(f"Corrupted file in archive: {bad}")
        elif format in ("tar", "tar.gz", "tgz"):
            try:
                mode = "r:gz" if format in ("tar.gz", "tgz") else "r:"
                with tarfile.open(archive, mode) as tf:
                    members = tf.getmembers()
                    valid = True
            except Exception as e:
                valid = False
                issues.append(str(e))
        elif format == "gzip":
            try:
                with gzip.open(archive, "rb") as gf:
                    gf.read(1)
                valid = True
            except Exception as e:
                valid = False
                issues.append(str(e))
        else:
            return ToolResult(success=False, error=f"Unsupported format: {format}")
        return ToolResult(success=True, data={
            "archive": str(archive), "format": format,
            "valid": valid, "issues": issues,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _format_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def _detect_archive_format(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".zip"):
        return "zip"
    if name.endswith(".tar.gz") or name.endswith(".tgz"):
        return "tar.gz"
    if name.endswith(".tar"):
        return "tar"
    if name.endswith(".gz") or name.endswith(".gzip"):
        return "gzip"
    return ""


def _create_zip(source: Path, destination: Path, compression_level: int, include_root: bool):
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=compression_level) as zf:
        if source.is_file():
            zf.write(source, source.name)
        else:
            base = source.parent if not include_root else source
            for entry in source.rglob("*"):
                if entry.is_file():
                    zf.write(entry, str(entry.relative_to(base)))


def _create_tar(source: Path, destination: Path, format: str, include_root: bool):
    mode = "w:gz" if format in ("tar.gz", "tgz") else "w"
    with tarfile.open(destination, mode) as tf:
        if source.is_file():
            tf.add(source, source.name)
        else:
            arcname = source.name if include_root else "."
            tf.add(source, arcname)


def _create_gzip(source: Path, destination: Path, compression_level: int):
    data = source.read_bytes()
    with gzip.open(destination, "wb", compresslevel=compression_level) as gf:
        gf.write(data)


# ──────────────────────────────────────────────
# Registration
# ──────────────────────────────────────────────

def register_system_tools(tm, event_bus=None):
    import asyncio
    from aios.tools.developer_tools import register_developer_tools
    from aios.tools.git_tools import register_git_tools
    from aios.tools.content_tools import register_content_tools

    register_developer_tools(tm, event_bus)
    register_git_tools(tm, event_bus)
    register_content_tools(tm, event_bus)

    file_tools = [
        ToolContract(
            id="file.read", name="Read File",
            description="Read contents of a file with optional offset/limit",
            parameters={
                "path": {"type": "string", "description": "Path to the file"},
                "encoding": {"type": "string", "description": "File encoding", "default": "utf-8"},
                "offset": {"type": "integer", "description": "Start line", "required": False},
                "limit": {"type": "integer", "description": "Max lines to read", "required": False},
            },
            returns={"content": {"type": "string"}, "path": {"type": "string"}, "size": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="filesystem",
            capabilities=["file.read"], tags=["file", "read"],
        ),
        ToolContract(
            id="file.write", name="Write File",
            description="Write content to a file (creates parent directories)",
            parameters={
                "path": {"type": "string", "description": "Path to the file"},
                "content": {"type": "string", "description": "Content to write"},
                "mode": {"type": "string", "description": "Write mode: w (overwrite) or a (append)", "default": "w"},
            },
            returns={"path": {"type": "string"}, "size": {"type": "integer"}, "written": {"type": "integer"}},
            permission_level=PermissionLevel.WORKSPACE, category="filesystem",
            capabilities=["file.write"], tags=["file", "write"],
        ),
        ToolContract(
            id="file.create", name="Create File",
            description="Create a new empty file (fails if exists)",
            parameters={
                "path": {"type": "string", "description": "Path for the new file"},
                "content": {"type": "string", "description": "Optional initial content", "required": False},
            },
            returns={"path": {"type": "string"}, "size": {"type": "integer"}},
            permission_level=PermissionLevel.WORKSPACE, category="filesystem",
            capabilities=["file.create"], tags=["file", "create"],
        ),
        ToolContract(
            id="file.delete", name="Delete File",
            description="Delete a file (requires SENSITIVE permission)",
            parameters={
                "path": {"type": "string", "description": "Path to the file"},
                "permanent": {"type": "boolean", "description": "Permanently delete (vs move to trash)", "default": True},
            },
            returns={"path": {"type": "string"}, "permanent": {"type": "boolean"}},
            permission_level=PermissionLevel.SENSITIVE, category="filesystem",
            requires_confirmation=True,
            capabilities=["file.delete"], tags=["file", "delete"],
        ),
        ToolContract(
            id="file.copy", name="Copy File",
            description="Copy a file or directory to a new location",
            parameters={
                "source": {"type": "string", "description": "Source path"},
                "destination": {"type": "string", "description": "Destination path"},
                "overwrite": {"type": "boolean", "description": "Overwrite if exists", "default": False},
            },
            returns={"source": {"type": "string"}, "destination": {"type": "string"}, "size": {"type": "integer"}},
            permission_level=PermissionLevel.WORKSPACE, category="filesystem",
            capabilities=["file.copy"], tags=["file", "copy"],
        ),
        ToolContract(
            id="file.move", name="Move File",
            description="Move a file or directory to a new location",
            parameters={
                "source": {"type": "string", "description": "Source path"},
                "destination": {"type": "string", "description": "Destination path"},
                "overwrite": {"type": "boolean", "description": "Overwrite if exists", "default": False},
            },
            returns={"source": {"type": "string"}, "destination": {"type": "string"}},
            permission_level=PermissionLevel.WORKSPACE, category="filesystem",
            capabilities=["file.move"], tags=["file", "move"],
        ),
        ToolContract(
            id="file.rename", name="Rename File",
            description="Rename a file or directory within the same parent",
            parameters={
                "path": {"type": "string", "description": "Path to the file/directory"},
                "new_name": {"type": "string", "description": "New name (not full path)"},
            },
            returns={"source": {"type": "string"}, "destination": {"type": "string"}},
            permission_level=PermissionLevel.WORKSPACE, category="filesystem",
            capabilities=["file.rename"], tags=["file", "rename"],
        ),
        ToolContract(
            id="file.metadata", name="File Metadata",
            description="Get detailed metadata about a file or directory",
            parameters={"path": {"type": "string", "description": "Path to inspect"}},
            returns={
                "path": {"type": "string"}, "size": {"type": "integer"},
                "is_dir": {"type": "boolean"}, "modified": {"type": "string"},
                "created": {"type": "string"}, "permissions": {"type": "integer"},
            },
            permission_level=PermissionLevel.READ, category="filesystem",
            capabilities=["file.metadata"], tags=["file", "metadata"],
        ),
        ToolContract(
            id="file.hash", name="File Hash",
            description="Calculate cryptographic hash of a file",
            parameters={
                "path": {"type": "string", "description": "Path to the file"},
                "algorithm": {"type": "string", "description": "Hash algorithm (md5, sha1, sha256, sha512)", "default": "sha256"},
            },
            returns={"path": {"type": "string"}, "algorithm": {"type": "string"}, "hash": {"type": "string"}},
            permission_level=PermissionLevel.READ, category="filesystem",
            capabilities=["file.hash"], tags=["file", "hash"],
        ),
        ToolContract(
            id="file.list", name="List Directory",
            description="List contents of a directory with sorting and filtering",
            parameters={
                "path": {"type": "string", "description": "Directory path"},
                "recursive": {"type": "boolean", "description": "List recursively", "default": False},
                "include_hidden": {"type": "boolean", "description": "Include hidden files", "default": False},
                "sort_by": {"type": "string", "description": "Sort field: name, size, modified (prefix - for reverse)", "default": "name"},
            },
            returns={"path": {"type": "string"}, "entries": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="filesystem",
            capabilities=["file.list"], tags=["file", "list", "directory"],
        ),
        ToolContract(
            id="file.create_directory", name="Create Directory",
            description="Create a directory (creates parent directories)",
            parameters={
                "path": {"type": "string", "description": "Directory path"},
                "exist_ok": {"type": "boolean", "description": "Don't error if exists", "default": True},
            },
            returns={"path": {"type": "string"}, "created": {"type": "boolean"}},
            permission_level=PermissionLevel.WORKSPACE, category="filesystem",
            capabilities=["file.create_directory"], tags=["file", "directory"],
        ),
        ToolContract(
            id="file.delete_directory", name="Delete Directory",
            description="Delete a directory (requires SENSITIVE permission)",
            parameters={
                "path": {"type": "string", "description": "Directory path"},
                "recursive": {"type": "boolean", "description": "Delete recursively", "default": True},
            },
            returns={"path": {"type": "string"}, "recursive": {"type": "boolean"}},
            permission_level=PermissionLevel.SENSITIVE, category="filesystem",
            requires_confirmation=True,
            capabilities=["file.delete_directory"], tags=["file", "directory", "delete"],
        ),
    ]

    search_tools = [
        ToolContract(
            id="search.files", name="Search Files",
            description="Search for files matching a glob pattern recursively",
            parameters={
                "path": {"type": "string", "description": "Root directory", "default": "."},
                "pattern": {"type": "string", "description": "Glob pattern (e.g. **/*.py)", "default": "*"},
                "recursive": {"type": "boolean", "description": "Search recursively", "default": True},
                "max_results": {"type": "integer", "description": "Maximum results", "default": 1000},
            },
            returns={"files": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="search",
            capabilities=["search.files"], tags=["search", "file"],
        ),
        ToolContract(
            id="search.directories", name="Search Directories",
            description="Search for directories matching a glob pattern",
            parameters={
                "path": {"type": "string", "description": "Root directory", "default": "."},
                "pattern": {"type": "string", "description": "Glob pattern", "default": "*"},
                "recursive": {"type": "boolean", "description": "Search recursively", "default": True},
                "max_results": {"type": "integer", "description": "Maximum results", "default": 500},
            },
            returns={"directories": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="search",
            capabilities=["search.directories"], tags=["search", "directory"],
        ),
        ToolContract(
            id="search.by_extension", name="Search by Extension",
            description="Search files by their extension",
            parameters={
                "path": {"type": "string", "description": "Root directory", "default": "."},
                "extension": {"type": "string", "description": "File extension (e.g. py, .txt)"},
                "recursive": {"type": "boolean", "description": "Search recursively", "default": True},
                "max_results": {"type": "integer", "description": "Maximum results", "default": 1000},
            },
            returns={"files": {"type": "array"}, "count": {"type": "integer"}, "extension": {"type": "string"}},
            permission_level=PermissionLevel.READ, category="search",
            capabilities=["search.by_extension"], tags=["search", "extension"],
        ),
        ToolContract(
            id="search.by_name", name="Search by Name",
            description="Search files and directories by name substring",
            parameters={
                "path": {"type": "string", "description": "Root directory", "default": "."},
                "query": {"type": "string", "description": "Name substring to search for"},
                "recursive": {"type": "boolean", "description": "Search recursively", "default": True},
                "case_sensitive": {"type": "boolean", "description": "Case sensitive search", "default": False},
                "max_results": {"type": "integer", "description": "Maximum results", "default": 1000},
            },
            returns={"results": {"type": "array"}, "count": {"type": "integer"}, "query": {"type": "string"}},
            permission_level=PermissionLevel.READ, category="search",
            capabilities=["search.by_name"], tags=["search", "name"],
        ),
        ToolContract(
            id="search.by_regex", name="Search by Regex",
            description="Search files/directories by regex pattern (optionally in content)",
            parameters={
                "path": {"type": "string", "description": "Root directory", "default": "."},
                "regex": {"type": "string", "description": "Regular expression pattern"},
                "recursive": {"type": "boolean", "description": "Search recursively", "default": True},
                "search_content": {"type": "boolean", "description": "Search inside file content", "default": False},
                "max_results": {"type": "integer", "description": "Maximum results", "default": 1000},
            },
            returns={"results": {"type": "array"}, "count": {"type": "integer"}, "regex": {"type": "string"}},
            permission_level=PermissionLevel.READ, category="search",
            capabilities=["search.by_regex"], tags=["search", "regex"],
        ),
        ToolContract(
            id="search.by_size", name="Search by Size",
            description="Search files by size range",
            parameters={
                "path": {"type": "string", "description": "Root directory", "default": "."},
                "min_size": {"type": "number", "description": "Minimum size", "default": 0},
                "max_size": {"type": "number", "description": "Maximum size", "required": False},
                "unit": {"type": "string", "description": "Unit: b, kb, mb, gb", "default": "b"},
                "recursive": {"type": "boolean", "description": "Search recursively", "default": True},
                "max_results": {"type": "integer", "description": "Maximum results", "default": 1000},
            },
            returns={"files": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="search",
            capabilities=["search.by_size"], tags=["search", "size"],
        ),
        ToolContract(
            id="search.by_modified", name="Search by Modified Date",
            description="Search files by modification date range",
            parameters={
                "path": {"type": "string", "description": "Root directory", "default": "."},
                "after": {"type": "string", "description": "ISO date: only files modified after this", "required": False},
                "before": {"type": "string", "description": "ISO date: only files modified before this", "required": False},
                "recursive": {"type": "boolean", "description": "Search recursively", "default": True},
                "max_results": {"type": "integer", "description": "Maximum results", "default": 1000},
            },
            returns={"results": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="search",
            capabilities=["search.by_modified"], tags=["search", "date", "modified"],
        ),
    ]

    clipboard_tools = [
        ToolContract(
            id="clipboard.read", name="Clipboard Read",
            description="Read current clipboard contents",
            parameters={},
            returns={"content": {"type": "string"}, "length": {"type": "integer"}, "has_content": {"type": "boolean"}},
            permission_level=PermissionLevel.SAFE, category="clipboard",
            capabilities=["clipboard.read"], tags=["clipboard", "read"],
        ),
        ToolContract(
            id="clipboard.write", name="Clipboard Write",
            description="Write text to the system clipboard",
            parameters={"content": {"type": "string", "description": "Text to copy to clipboard"}},
            returns={"length": {"type": "integer"}},
            permission_level=PermissionLevel.WORKSPACE, category="clipboard",
            capabilities=["clipboard.write"], tags=["clipboard", "write"],
        ),
        ToolContract(
            id="clipboard.clear", name="Clipboard Clear",
            description="Clear the system clipboard",
            parameters={},
            returns={"cleared": {"type": "boolean"}},
            permission_level=PermissionLevel.WORKSPACE, category="clipboard",
            capabilities=["clipboard.clear"], tags=["clipboard", "clear"],
        ),
        ToolContract(
            id="clipboard.monitor", name="Clipboard Monitor",
            description="Start/stop monitoring clipboard for changes (publishes clipboard:changed events)",
            parameters={
                "action": {"type": "string", "description": "start, stop, or status", "default": "start"},
                "interval": {"type": "number", "description": "Poll interval in seconds", "default": 1.0},
                "monitor_id": {"type": "string", "description": "Monitor identifier", "default": "default"},
            },
            returns={"monitoring": {"type": "boolean"}},
            permission_level=PermissionLevel.SAFE, category="clipboard",
            capabilities=["clipboard.monitor"], tags=["clipboard", "monitor"],
        ),
    ]

    archive_tools = [
        ToolContract(
            id="archive.compress", name="Compress Archive",
            description="Compress files/directories into an archive (zip, tar, tar.gz, gzip)",
            parameters={
                "source": {"type": "string", "description": "File or directory to compress"},
                "destination": {"type": "string", "description": "Output archive path", "required": False},
                "format": {"type": "string", "description": "Archive format: zip, tar, tar.gz, gzip", "default": "zip"},
                "compression_level": {"type": "integer", "description": "Compression level 0-9", "default": 6},
            },
            returns={"source": {"type": "string"}, "destination": {"type": "string"}, "format": {"type": "string"}, "size": {"type": "integer"}},
            permission_level=PermissionLevel.WORKSPACE, category="archive",
            capabilities=["archive.compress"], tags=["archive", "compress", "zip", "tar"],
        ),
        ToolContract(
            id="archive.extract", name="Extract Archive",
            description="Extract an archive file",
            parameters={
                "archive": {"type": "string", "description": "Archive file path"},
                "destination": {"type": "string", "description": "Output directory", "required": False},
                "format": {"type": "string", "description": "Format auto-detected if omitted", "required": False},
            },
            returns={"archive": {"type": "string"}, "destination": {"type": "string"}, "extracted_items": {"type": "integer"}},
            permission_level=PermissionLevel.WORKSPACE, category="archive",
            capabilities=["archive.extract"], tags=["archive", "extract", "unzip", "untar"],
        ),
        ToolContract(
            id="archive.list", name="List Archive Contents",
            description="List contents of an archive without extracting",
            parameters={
                "archive": {"type": "string", "description": "Archive file path"},
                "format": {"type": "string", "description": "Format auto-detected if omitted", "required": False},
            },
            returns={"entries": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="archive",
            capabilities=["archive.list"], tags=["archive", "list", "inspect"],
        ),
        ToolContract(
            id="archive.validate", name="Validate Archive",
            description="Check an archive for corruption or integrity issues",
            parameters={
                "archive": {"type": "string", "description": "Archive file path"},
                "format": {"type": "string", "description": "Format auto-detected if omitted", "required": False},
            },
            returns={"valid": {"type": "boolean"}, "issues": {"type": "array"}},
            permission_level=PermissionLevel.READ, category="archive",
            capabilities=["archive.validate"], tags=["archive", "validate", "check"],
        ),
    ]

    all_tools = file_tools + search_tools + clipboard_tools + archive_tools

    file_handlers = [
        _read_file, _write_file, _create_file, _delete_file,
        _copy_file, _move_file, _rename_file, _file_metadata,
        _file_hash, _list_directory, _create_directory, _delete_directory,
    ]
    search_handlers = [
        _search_files, _search_directories, _search_by_extension,
        _search_by_name, _search_by_regex, _search_by_size, _search_by_modified_date,
    ]
    clipboard_handlers = [
        lambda p: _clipboard_read(p),
        lambda p: _clipboard_write(p),
        lambda p: _clipboard_clear(p),
        lambda p: _clipboard_monitor(p, event_bus),
    ]
    archive_handlers = [_compress, _extract, _list_contents, _validate]

    all_handlers = file_handlers + search_handlers + clipboard_handlers + archive_handlers

    for contract, handler in zip(all_tools, all_handlers):
        asyncio.create_task(tm.register_tool(contract, handler))