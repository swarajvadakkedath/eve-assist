"""Tests for System Tool Pack (file, search, clipboard, archive)."""

import asyncio
import gzip
import os
import zipfile
from pathlib import Path

import pytest

from aios.core.tool_manager import ToolManager, ToolContract, ToolResult
from aios.core.permission_manager import PermissionManager, PermissionLevel
from aios.core.event_bus import EventBus
from aios.tools.system_tools import (
    register_system_tools,
    _read_file,
    _write_file,
    _create_file,
    _delete_file,
    _copy_file,
    _move_file,
    _rename_file,
    _file_metadata,
    _file_hash,
    _list_directory,
    _create_directory,
    _delete_directory,
    _search_files,
    _search_directories,
    _search_by_extension,
    _search_by_name,
    _search_by_regex,
    _search_by_size,
    _search_by_modified_date,
    _compress,
    _extract,
    _list_contents,
    _validate,
    _clipboard_read,
    _clipboard_write,
    _clipboard_clear,
)


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    d = tmp_path / "workspace"
    d.mkdir()
    (d / "hello.txt").write_text("hello world")
    (d / "sub").mkdir()
    (d / "sub" / "nested.txt").write_text("nested content")
    (d / "script.py").write_text("print('hi')")
    (d / "data.json").write_text('{"key": "value"}')
    return d


@pytest.fixture
def tm():
    return ToolManager(PermissionManager())


@pytest.fixture
async def eb():
    bus = EventBus()
    await bus.start()
    yield bus
    await bus.stop()


# ─── File Toolkit ───


@pytest.mark.asyncio
async def test_read_file(tmp_workspace):
    result = await _read_file({"path": str(tmp_workspace / "hello.txt")})
    assert result.success
    assert result.data["content"] == "hello world"


@pytest.mark.asyncio
async def test_read_file_not_found(tmp_workspace):
    result = await _read_file({"path": str(tmp_workspace / "nope.txt")})
    assert not result.success


@pytest.mark.asyncio
async def test_read_file_with_offset_limit(tmp_workspace):
    p = tmp_workspace / "lines.txt"
    p.write_text("line1\nline2\nline3\nline4\n")
    result = await _read_file({"path": str(p), "offset": 1, "limit": 2})
    assert result.success
    assert result.data["content"] == "line2\nline3\n"


@pytest.mark.asyncio
async def test_write_file(tmp_workspace):
    result = await _write_file({"path": str(tmp_workspace / "new.txt"), "content": "new content"})
    assert result.success
    assert (tmp_workspace / "new.txt").read_text() == "new content"


@pytest.mark.asyncio
async def test_write_file_append(tmp_workspace):
    p = tmp_workspace / "append.txt"
    p.write_text("base")
    result = await _write_file({"path": str(p), "content": "+more", "mode": "a"})
    assert result.success
    assert p.read_text() == "base+more"


@pytest.mark.asyncio
async def test_create_file(tmp_workspace):
    result = await _create_file({"path": str(tmp_workspace / "brand_new.txt"), "content": "fresh"})
    assert result.success
    assert (tmp_workspace / "brand_new.txt").read_text() == "fresh"


@pytest.mark.asyncio
async def test_create_file_already_exists(tmp_workspace):
    result = await _create_file({"path": str(tmp_workspace / "hello.txt")})
    assert not result.success


@pytest.mark.asyncio
async def test_delete_file(tmp_workspace):
    p = tmp_workspace / "delete_me.txt"
    p.write_text("bye")
    result = await _delete_file({"path": str(p), "permanent": True})
    assert result.success
    assert not p.exists()


@pytest.mark.asyncio
async def test_delete_file_not_found(tmp_workspace):
    result = await _delete_file({"path": str(tmp_workspace / "ghost.txt")})
    assert not result.success


@pytest.mark.asyncio
async def test_copy_file(tmp_workspace):
    result = await _copy_file({"source": str(tmp_workspace / "hello.txt"), "destination": str(tmp_workspace / "hello_copy.txt")})
    assert result.success
    assert (tmp_workspace / "hello_copy.txt").read_text() == "hello world"


@pytest.mark.asyncio
async def test_copy_file_no_overwrite(tmp_workspace):
    result = await _copy_file({"source": str(tmp_workspace / "hello.txt"), "destination": str(tmp_workspace / "hello.txt")})
    assert not result.success


@pytest.mark.asyncio
async def test_copy_file_overwrite(tmp_workspace):
    p = tmp_workspace / "overwrite_target.txt"
    p.write_text("old")
    result = await _copy_file({"source": str(tmp_workspace / "hello.txt"), "destination": str(p), "overwrite": True})
    assert result.success
    assert p.read_text() == "hello world"


@pytest.mark.asyncio
async def test_move_file(tmp_workspace):
    p = tmp_workspace / "movable.txt"
    p.write_text("move me")
    result = await _move_file({"source": str(p), "destination": str(tmp_workspace / "moved.txt")})
    assert result.success
    assert not p.exists()
    assert (tmp_workspace / "moved.txt").read_text() == "move me"


@pytest.mark.asyncio
async def test_rename_file(tmp_workspace):
    p = tmp_workspace / "old_name.txt"
    p.write_text("rename me")
    result = await _rename_file({"path": str(p), "new_name": "new_name.txt"})
    assert result.success
    assert not p.exists()
    assert (tmp_workspace / "new_name.txt").read_text() == "rename me"


@pytest.mark.asyncio
async def test_file_metadata(tmp_workspace):
    result = await _file_metadata({"path": str(tmp_workspace / "hello.txt")})
    assert result.success
    assert result.data["name"] == "hello.txt"
    assert result.data["is_file"] is True
    assert result.data["size"] == 11


@pytest.mark.asyncio
async def test_file_hash(tmp_workspace):
    result = await _file_hash({"path": str(tmp_workspace / "hello.txt")})
    assert result.success
    assert result.data["algorithm"] == "sha256"
    assert len(result.data["hash"]) == 64


@pytest.mark.asyncio
async def test_file_hash_algorithm(tmp_workspace):
    result = await _file_hash({"path": str(tmp_workspace / "hello.txt"), "algorithm": "md5"})
    assert result.success
    assert result.data["algorithm"] == "md5"
    assert len(result.data["hash"]) == 32


@pytest.mark.asyncio
async def test_list_directory(tmp_workspace):
    result = await _list_directory({"path": str(tmp_workspace)})
    assert result.success
    assert result.data["count"] >= 4
    names = [e["name"] for e in result.data["entries"]]
    assert "hello.txt" in names


@pytest.mark.asyncio
async def test_list_directory_recursive(tmp_workspace):
    result = await _list_directory({"path": str(tmp_workspace), "recursive": True})
    assert result.success
    assert result.data["count"] >= 5


@pytest.mark.asyncio
async def test_create_directory(tmp_workspace):
    result = await _create_directory({"path": str(tmp_workspace / "newdir")})
    assert result.success
    assert (tmp_workspace / "newdir").is_dir()


@pytest.mark.asyncio
async def test_delete_directory(tmp_workspace):
    d = tmp_workspace / "toremove"
    d.mkdir()
    (d / "file.txt").write_text("x")
    result = await _delete_directory({"path": str(d), "recursive": True})
    assert result.success
    assert not d.exists()


# ─── Search Toolkit ───


@pytest.mark.asyncio
async def test_search_files_by_pattern(tmp_workspace):
    result = await _search_files({"path": str(tmp_workspace), "pattern": "*.txt"})
    assert result.success
    assert result.data["count"] >= 2


@pytest.mark.asyncio
async def test_search_directories(tmp_workspace):
    result = await _search_directories({"path": str(tmp_workspace), "pattern": "*"})
    assert result.success
    names = [d["name"] for d in result.data["directories"]]
    assert "sub" in names


@pytest.mark.asyncio
async def test_search_by_extension(tmp_workspace):
    result = await _search_by_extension({"path": str(tmp_workspace), "extension": ".py"})
    assert result.success
    assert any(f["extension"] == ".py" for f in result.data["files"])


@pytest.mark.asyncio
async def test_search_by_name(tmp_workspace):
    result = await _search_by_name({"path": str(tmp_workspace), "query": "hello"})
    assert result.success
    assert result.data["count"] >= 1


@pytest.mark.asyncio
async def test_search_by_regex(tmp_workspace):
    result = await _search_by_regex({"path": str(tmp_workspace), "regex": r".*\.py$"})
    assert result.success
    assert result.data["count"] >= 1


@pytest.mark.asyncio
async def test_search_by_regex_invalid(tmp_workspace):
    result = await _search_by_regex({"path": str(tmp_workspace), "regex": r"["})
    assert not result.success


@pytest.mark.asyncio
async def test_search_by_regex_content(tmp_workspace):
    result = await _search_by_regex({"path": str(tmp_workspace), "regex": "hello", "search_content": True})
    assert result.success
    assert result.data["count"] >= 1


@pytest.mark.asyncio
async def test_search_by_size(tmp_workspace):
    result = await _search_by_size({"path": str(tmp_workspace), "min_size": 0, "unit": "b"})
    assert result.success
    assert result.data["count"] >= 2


@pytest.mark.asyncio
async def test_search_by_size_range(tmp_workspace):
    result = await _search_by_size({"path": str(tmp_workspace), "min_size": 100, "unit": "kb"})
    assert result.success
    assert result.data["count"] == 0


@pytest.mark.asyncio
async def test_search_by_modified(tmp_workspace):
    result = await _search_by_modified_date({"path": str(tmp_workspace), "after": "2020-01-01T00:00:00"})
    assert result.success
    assert result.data["count"] >= 1


# ─── Clipboard Toolkit (requires pyperclip) ───


@pytest.mark.skipif(
    not bool(__import__("importlib", fromlist=[""]).util.find_spec("pyperclip")),
    reason="pyperclip not installed",
)
@pytest.mark.asyncio
async def test_clipboard_write_read():
    result = await _clipboard_write({"content": "test clipboard"})
    assert result.success
    result = await _clipboard_read({})
    assert result.success
    # pyperclip may not work in headless envs


# ─── Archive Toolkit ───


@pytest.mark.asyncio
async def test_compress_zip(tmp_workspace):
    dst = tmp_workspace / "archive.zip"
    result = await _compress({"source": str(tmp_workspace / "hello.txt"), "destination": str(dst), "format": "zip"})
    assert result.success
    assert dst.exists()
    with zipfile.ZipFile(dst, "r") as zf:
        names = zf.namelist()
        assert "hello.txt" in names


@pytest.mark.asyncio
async def test_compress_tar_gz(tmp_workspace):
    dst = tmp_workspace / "archive.tar.gz"
    result = await _compress({"source": str(tmp_workspace / "hello.txt"), "destination": str(dst), "format": "tar.gz"})
    assert result.success
    assert dst.exists()


@pytest.mark.asyncio
async def test_compress_gzip(tmp_workspace):
    dst = tmp_workspace / "file.gz"
    result = await _compress({"source": str(tmp_workspace / "hello.txt"), "destination": str(dst), "format": "gzip"})
    assert result.success
    assert dst.exists()


@pytest.mark.asyncio
async def test_compress_directory_zip(tmp_workspace):
    dst = tmp_workspace / "dir.zip"
    result = await _compress({"source": str(tmp_workspace / "sub"), "destination": str(dst), "format": "zip"})
    assert result.success
    assert dst.exists()


@pytest.mark.asyncio
async def test_compress_invalid_format(tmp_workspace):
    result = await _compress({"source": str(tmp_workspace / "hello.txt"), "format": "rar"})
    assert not result.success


@pytest.mark.asyncio
async def test_extract_zip(tmp_workspace):
    src = tmp_workspace / "hello.txt"
    archive = tmp_workspace / "extract_test.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.write(src, "hello.txt")
    dst = tmp_workspace / "extracted"
    result = await _extract({"archive": str(archive), "destination": str(dst)})
    assert result.success
    assert (dst / "hello.txt").read_text() == "hello world"


@pytest.mark.asyncio
async def test_extract_gzip(tmp_workspace):
    src = tmp_workspace / "hello.txt"
    archive = tmp_workspace / "test.gz"
    with gzip.open(archive, "wb") as gf:
        gf.write(src.read_bytes())
    dst = tmp_workspace / "gzip_out"
    result = await _extract({"archive": str(archive), "destination": str(dst)})
    assert result.success
    assert (dst / "test").exists()
    assert (dst / "test").read_text() == "hello world"


@pytest.mark.asyncio
async def test_list_zip_contents(tmp_workspace):
    archive = tmp_workspace / "list_test.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.write(tmp_workspace / "hello.txt", "hello.txt")
    result = await _list_contents({"archive": str(archive)})
    assert result.success
    assert result.data["count"] >= 1
    assert any(e["name"] == "hello.txt" for e in result.data["entries"])


@pytest.mark.asyncio
async def test_validate_valid_zip(tmp_workspace):
    archive = tmp_workspace / "valid.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.write(tmp_workspace / "hello.txt", "hello.txt")
    result = await _validate({"archive": str(archive)})
    assert result.success
    assert result.data["valid"] is True


@pytest.mark.asyncio
async def test_validate_valid_gzip(tmp_workspace):
    archive = tmp_workspace / "valid.gz"
    with gzip.open(archive, "wb") as gf:
        gf.write(b"test")
    result = await _validate({"archive": str(archive)})
    assert result.success
    assert result.data["valid"] is True


@pytest.mark.asyncio
async def test_archive_format_auto_detect(tmp_workspace):
    archive = tmp_workspace / "auto.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("file.txt", "data")
    result = await _list_contents({"archive": str(archive)})
    assert result.success
    assert result.data["format"] == "zip"


# ─── Registration ───


@pytest.mark.asyncio
async def test_register_system_tools(tm, eb):
    register_system_tools(tm, eb)
    await asyncio.sleep(0.05)

    file_tool = await tm.get_tool("file.read")
    assert file_tool is not None
    assert file_tool.category == "filesystem"

    search_tool = await tm.get_tool("search.files")
    assert search_tool is not None
    assert search_tool.category == "search"

    clip_tool = await tm.get_tool("clipboard.read")
    assert clip_tool is not None
    assert clip_tool.category == "clipboard"

    archive_tool = await tm.get_tool("archive.compress")
    assert archive_tool is not None
    assert archive_tool.category == "archive"


@pytest.mark.asyncio
async def test_register_all_system_tools(tm, eb):
    register_system_tools(tm, eb)
    await asyncio.sleep(0.05)
    all_tools = await tm.list_tools()
    tool_ids = [t.id for t in all_tools]

    expected = [
        "file.read", "file.write", "file.create", "file.delete",
        "file.copy", "file.move", "file.rename", "file.metadata",
        "file.hash", "file.list", "file.create_directory", "file.delete_directory",
        "search.files", "search.directories", "search.by_extension",
        "search.by_name", "search.by_regex", "search.by_size", "search.by_modified",
        "clipboard.read", "clipboard.write", "clipboard.clear", "clipboard.monitor",
        "archive.compress", "archive.extract", "archive.list", "archive.validate",
    ]
    for tid in expected:
        assert tid in tool_ids, f"Missing tool: {tid}"
