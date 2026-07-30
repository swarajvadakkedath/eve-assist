"""File operation tools."""

import os
import shutil
from glob import glob
from pathlib import Path
from aios.core.tool_manager import ToolResult


async def search_files(params: dict) -> ToolResult:
    pattern = params.get("pattern", "*")
    path = params.get("path", os.path.expanduser("~"))
    search_path = os.path.join(path, pattern)
    results = []
    for fp in glob(search_path, recursive=True):
        try:
            stat = os.stat(fp)
            results.append({
                "path": fp,
                "name": os.path.basename(fp),
                "size": stat.st_size,
                "is_dir": os.path.isdir(fp),
            })
        except OSError:
            continue
    return ToolResult(success=True, data={"files": results, "count": len(results)})


async def read_file(params: dict) -> ToolResult:
    path = params.get("path", "")
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return ToolResult(success=True, data={"content": content, "path": path})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def write_file(params: dict) -> ToolResult:
    path = params.get("path", "")
    content = params.get("content", "")
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return ToolResult(success=True, data={"path": path})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def delete_file(params: dict) -> ToolResult:
    path = params.get("path", "")
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        return ToolResult(success=True, data={"path": path})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def create_directory(params: dict) -> ToolResult:
    path = params.get("path", "")
    try:
        os.makedirs(path, exist_ok=True)
        return ToolResult(success=True, data={"path": path})
    except Exception as e:
        return ToolResult(success=False, error=str(e))
