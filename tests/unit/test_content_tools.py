"""Tests for Content Processing Toolkit (Text, Search, Structured, Markdown, Code Analysis)."""

import asyncio
import json
import os
from pathlib import Path

import pytest

from aios.core.tool_manager import ToolManager, ToolResult
from aios.core.permission_manager import PermissionManager
from aios.core.event_bus import EventBus
from aios.tools.content_tools import (
    register_content_tools,
    _read_text,
    _write_text,
    _append_text,
    _replace_text,
    _search_text,
    _search_regex,
    _search_in_directory,
    _batch_replace,
    _read_json,
    _write_json,
    _validate_json,
    _validate_yaml,
    _validate_xml,
    _read_csv,
    _write_csv,
    _parse_markdown,
    _markdown_outline,
    _extract_links,
    _search_code,
    _extract_symbols,
    _list_functions,
    _list_classes,
    _count_lines,
    _detect_language,
)


@pytest.fixture
def pm():
    return PermissionManager()


@pytest.fixture
def tm(pm):
    return ToolManager(pm)


@pytest.fixture
async def eb():
    bus = EventBus(max_retries=1, retry_delay=0.01)
    await bus.start()
    yield bus
    await bus.stop()


# ── Text File Tools ──


@pytest.mark.asyncio
async def test_read_text(tmp_path):
    f = tmp_path / "hello.txt"
    f.write_text("Hello\nWorld\n")
    result = await _read_text({"path": str(f)})
    assert result.success
    assert "Hello" in result.data["content"]
    assert result.data["total_lines"] == 2


@pytest.mark.asyncio
async def test_read_text_not_found():
    result = await _read_text({"path": "/nonexistent/file.txt"})
    assert not result.success


@pytest.mark.asyncio
async def test_read_text_with_offset_limit(tmp_path):
    f = tmp_path / "lines.txt"
    f.write_text("a\nb\nc\nd\ne\n")
    result = await _read_text({"path": str(f), "offset": 1, "limit": 2})
    assert result.success
    assert result.data["content"] == "b\nc\n"


@pytest.mark.asyncio
async def test_read_text_utf8_bom(tmp_path):
    content = "\ufeffHello\nWorld\n"
    f = tmp_path / "bom.txt"
    f.write_text(content, encoding="utf-8-sig")
    result = await _read_text({"path": str(f)})
    assert result.success


@pytest.mark.asyncio
async def test_write_text(tmp_path, eb):
    f = tmp_path / "out.txt"
    result = await _write_text({"path": str(f), "content": "Hello"}, eb)
    assert result.success
    assert result.data["written"] == 5
    assert f.read_text() == "Hello"


@pytest.mark.asyncio
async def test_write_text_creates_parent(tmp_path, eb):
    f = tmp_path / "sub" / "nested" / "out.txt"
    result = await _write_text({"path": str(f), "content": "deep"}, eb)
    assert result.success
    assert f.read_text() == "deep"


@pytest.mark.asyncio
async def test_append_text(tmp_path, eb):
    f = tmp_path / "append.txt"
    f.write_text("Hello")
    result = await _append_text({"path": str(f), "content": " World"}, eb)
    assert result.success
    assert result.data["appended"] == 6
    assert f.read_text() == "Hello World"


@pytest.mark.asyncio
async def test_append_text_new_file(tmp_path, eb):
    f = tmp_path / "new.txt"
    result = await _append_text({"path": str(f), "content": "First"}, eb)
    assert result.success
    assert f.read_text() == "First"


@pytest.mark.asyncio
async def test_replace_text(tmp_path, eb):
    f = tmp_path / "replace.txt"
    f.write_text("aaa bbb aaa")
    result = await _replace_text({"path": str(f), "old": "aaa", "new": "xxx"}, eb)
    assert result.success
    assert result.data["replaced"] == 2
    assert f.read_text() == "xxx bbb xxx"


@pytest.mark.asyncio
async def test_replace_text_count_limit(tmp_path, eb):
    f = tmp_path / "replace_count.txt"
    f.write_text("aaa aaa aaa")
    result = await _replace_text({"path": str(f), "old": "aaa", "new": "xxx", "count": 2}, eb)
    assert result.success
    assert result.data["replaced"] == 2
    assert f.read_text() == "xxx xxx aaa"


@pytest.mark.asyncio
async def test_replace_text_regex(tmp_path, eb):
    f = tmp_path / "replace_regex.txt"
    f.write_text("abc123 def456")
    result = await _replace_text({"path": str(f), "old": r"\d+", "new": "X", "regex": True}, eb)
    assert result.success
    assert result.data["replaced"] == 2
    assert f.read_text() == "abcX defX"


@pytest.mark.asyncio
async def test_replace_text_file_not_found(eb):
    result = await _replace_text({"path": "/nope.txt", "old": "x", "new": "y"}, eb)
    assert not result.success


# ── Search Tools ──


@pytest.mark.asyncio
async def test_search_text(tmp_path):
    f = tmp_path / "search.txt"
    f.write_text("apple\nbanana\napple pie\ncherry")
    result = await _search_text({"path": str(f), "query": "apple"})
    assert result.success
    assert result.data["matches"] == 2


@pytest.mark.asyncio
async def test_search_text_case_sensitive(tmp_path):
    f = tmp_path / "case.txt"
    f.write_text("Apple\napple\nAPPLE")
    result = await _search_text({"path": str(f), "query": "Apple", "case_sensitive": True})
    assert result.success
    assert result.data["matches"] == 1


@pytest.mark.asyncio
async def test_search_regex(tmp_path):
    f = tmp_path / "regex.txt"
    f.write_text("cat\ndog\ncar\nbar")
    result = await _search_regex({"path": str(f), "pattern": r"c[ar][tr]"})
    assert result.success
    assert result.data["matches"] >= 2


@pytest.mark.asyncio
async def test_search_regex_invalid():
    result = await _search_regex({"path": str(__file__), "pattern": r"["})
    assert not result.success


@pytest.mark.asyncio
async def test_search_in_directory(tmp_path):
    (tmp_path / "a.txt").write_text("hello world")
    (tmp_path / "b.txt").write_text("goodbye world")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.txt").write_text("hello again")
    result = await _search_in_directory({"path": str(tmp_path), "query": "hello", "recursive": True})
    assert result.success
    assert result.data["matches"] == 2


@pytest.mark.asyncio
async def test_batch_replace(tmp_path, eb):
    (tmp_path / "f1.txt").write_text("foo")
    (tmp_path / "f2.txt").write_text("foo bar")
    (tmp_path / "f3.txt").write_text("baz")
    result = await _batch_replace({"path": str(tmp_path), "pattern": "*.txt", "old": "foo", "new": "qux"}, eb)
    assert result.success
    assert result.data["files_processed"] == 2
    assert result.data["total_replaced"] == 2
    assert (tmp_path / "f1.txt").read_text() == "qux"
    assert (tmp_path / "f3.txt").read_text() == "baz"


# ── Structured File Tools ──


@pytest.mark.asyncio
async def test_read_json(tmp_path):
    data = {"name": "test", "values": [1, 2, 3]}
    f = tmp_path / "data.json"
    f.write_text(json.dumps(data))
    result = await _read_json({"path": str(f)})
    assert result.success
    assert result.data["data"]["name"] == "test"


@pytest.mark.asyncio
async def test_read_json_invalid(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("{invalid}")
    result = await _read_json({"path": str(f)})
    assert not result.success


@pytest.mark.asyncio
async def test_write_json(tmp_path, eb):
    f = tmp_path / "out.json"
    data = {"key": "value", "num": 42}
    result = await _write_json({"path": str(f), "data": data}, eb)
    assert result.success
    loaded = json.loads(f.read_text())
    assert loaded["key"] == "value"
    assert loaded["num"] == 42


@pytest.mark.asyncio
async def test_validate_json_string():
    result = await _validate_json({"source": '{"a": 1}'})
    assert result.success
    assert result.data["valid"]


@pytest.mark.asyncio
async def test_validate_json_invalid():
    result = await _validate_json({"source": "{bad}"})
    assert result.success
    assert not result.data["valid"]


@pytest.mark.asyncio
async def test_validate_json_file(tmp_path):
    f = tmp_path / "test.json"
    f.write_text('{"ok": true}')
    result = await _validate_json({"source": str(f)})
    assert result.success
    assert result.data["valid"]


@pytest.mark.asyncio
async def test_validate_yaml_string():
    result = await _validate_yaml({"source": "key: value\nnum: 42"})
    assert result.success
    assert result.data["valid"]


@pytest.mark.asyncio
async def test_validate_yaml_file(tmp_path):
    f = tmp_path / "test.yaml"
    f.write_text("key: value\n")
    result = await _validate_yaml({"source": str(f)})
    assert result.success
    assert result.data["valid"]


@pytest.mark.asyncio
async def test_validate_xml_string():
    result = await _validate_xml({"source": "<root><item>val</item></root>"})
    assert result.success
    assert result.data["valid"]


@pytest.mark.asyncio
async def test_validate_xml_invalid():
    result = await _validate_xml({"source": "<root><unclosed>"})
    assert result.success
    assert not result.data["valid"]


@pytest.mark.asyncio
async def test_validate_xml_file(tmp_path):
    f = tmp_path / "test.xml"
    f.write_text("<doc><e/></doc>")
    result = await _validate_xml({"source": str(f)})
    assert result.success
    assert result.data["valid"]


@pytest.mark.asyncio
async def test_read_csv(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("name,age\nAlice,30\nBob,25\n")
    result = await _read_csv({"path": str(f)})
    assert result.success
    assert result.data["count"] == 2
    assert result.data["fieldnames"] == ["name", "age"]


@pytest.mark.asyncio
async def test_read_csv_no_header(tmp_path):
    f = tmp_path / "noheader.csv"
    f.write_text("a,b\nc,d\n")
    result = await _read_csv({"path": str(f), "has_header": False})
    assert result.success
    assert result.data["count"] == 2


@pytest.mark.asyncio
async def test_write_csv(tmp_path, eb):
    f = tmp_path / "out.csv"
    data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
    result = await _write_csv({"path": str(f), "data": data}, eb)
    assert result.success
    assert result.data["rows"] == 2
    text = f.read_text()
    assert "Alice" in text
    assert "Bob" in text


# ── Markdown Tools ──


@pytest.mark.asyncio
async def test_parse_markdown():
    md = "# Title\n\nSome text.\n\n## Sub\n\n- item1\n- item2"
    result = await _parse_markdown({"source": md})
    assert result.success
    assert result.data["section_count"] >= 2


@pytest.mark.asyncio
async def test_parse_markdown_file(tmp_path):
    f = tmp_path / "test.md"
    f.write_text("# Hello\n\nWorld.\n")
    result = await _parse_markdown({"source": str(f)})
    assert result.success
    assert result.data["section_count"] >= 1


@pytest.mark.asyncio
async def test_markdown_outline():
    md = "# H1\n\n## H2\n\n### H3\n\nText."
    result = await _markdown_outline({"source": md})
    assert result.success
    assert result.data["count"] == 3


@pytest.mark.asyncio
async def test_extract_links():
    md = "[Google](https://google.com) and [Git](https://github.com)"
    result = await _extract_links({"source": md})
    assert result.success
    assert result.data["count"] == 2


@pytest.mark.asyncio
async def test_extract_links_bare_urls():
    md = "Visit https://example.com/page for info."
    result = await _extract_links({"source": md})
    assert result.success
    assert result.data["count"] >= 1


# ── Code Analysis Tools ──


@pytest.mark.asyncio
async def test_search_code_file(tmp_path):
    f = tmp_path / "code.py"
    f.write_text("def foo():\n    pass\n\ndef bar():\n    pass\n")
    result = await _search_code({"path": str(f), "query": "def "})
    assert result.success
    assert result.data["matches"] == 2


@pytest.mark.asyncio
async def test_search_code_directory(tmp_path):
    (tmp_path / "a.py").write_text("import os\n")
    (tmp_path / "b.py").write_text("import sys\n")
    result = await _search_code({"path": str(tmp_path), "query": "import"})
    assert result.success
    assert result.data["matches"] == 2


@pytest.mark.asyncio
async def test_extract_symbols_python(tmp_path):
    f = tmp_path / "sample.py"
    f.write_text("""
class MyClass:
    def method_one(self):
        pass

def standalone():
    pass
""")
    result = await _extract_symbols({"path": str(f)})
    assert result.success
    names = {s["name"] for s in result.data["symbols"]}
    assert "MyClass" in names
    assert "method_one" in names
    assert "standalone" in names


@pytest.mark.asyncio
async def test_extract_symbols_unknown_language(tmp_path):
    f = tmp_path / "data.xyz"
    f.write_text("some unknown content")
    result = await _extract_symbols({"path": str(f), "language": "python"})
    assert result.success


@pytest.mark.asyncio
async def test_list_functions(tmp_path):
    f = tmp_path / "funcs.py"
    f.write_text("""
def func_a():
    pass

def func_b():
    pass

class X:
    def method_c(self):
        pass
""")
    result = await _list_functions({"path": str(f)})
    assert result.success
    func_names = {f["name"] for f in result.data["functions"]}
    assert "func_a" in func_names
    assert "func_b" in func_names
    assert "method_c" in func_names


@pytest.mark.asyncio
async def test_list_classes(tmp_path):
    f = tmp_path / "classes.py"
    f.write_text("""
class ClassA:
    pass

class ClassB:
    pass
""")
    result = await _list_classes({"path": str(f)})
    assert result.success
    names = {c["name"] for c in result.data["classes"]}
    assert "ClassA" in names
    assert "ClassB" in names


@pytest.mark.asyncio
async def test_count_lines_single_file(tmp_path):
    f = tmp_path / "lines.py"
    f.write_text("a\nb\nc\n")
    result = await _count_lines({"path": str(f)})
    assert result.success
    assert result.data["summary"]["total"] == 3


@pytest.mark.asyncio
async def test_count_lines_directory(tmp_path):
    (tmp_path / "a.py").write_text("x\ny\n")
    (tmp_path / "b.py").write_text("1\n2\n3\n")
    result = await _count_lines({"path": str(tmp_path)})
    assert result.success
    assert result.data["summary"]["total"] == 5


@pytest.mark.asyncio
async def test_detect_language_from_path(tmp_path):
    f = tmp_path / "script.py"
    f.write_text("import os\nprint('hello')\n")
    result = await _detect_language({"path": str(f)})
    assert result.success
    assert result.data["language"] == "python"


@pytest.mark.asyncio
async def test_detect_language_from_source():
    result = await _detect_language({"source": "def foo():\n    return 1\nimport sys"})
    assert result.success
    assert result.data["language"] == "python"


# ── Error Handling ──


@pytest.mark.asyncio
async def test_read_text_directory(tmp_path):
    result = await _read_text({"path": str(tmp_path)})
    assert not result.success


@pytest.mark.asyncio
async def test_search_text_no_file():
    result = await _search_text({"path": "/nope", "query": "x"})
    assert not result.success


@pytest.mark.asyncio
async def test_search_in_directory_no_query(tmp_path):
    result = await _search_in_directory({"path": str(tmp_path), "query": ""})
    assert not result.success


@pytest.mark.asyncio
async def test_batch_replace_no_old(tmp_path, eb):
    result = await _batch_replace({"path": str(tmp_path), "old": "", "new": "y"}, eb)
    assert not result.success


@pytest.mark.asyncio
async def test_detect_language_no_input():
    result = await _detect_language({})
    assert not result.success


# ── Registration ──


@pytest.mark.asyncio
async def test_register_content_tools(tm, eb):
    register_content_tools(tm, eb)
    await asyncio.sleep(0.05)
    all_tools = await tm.list_tools()
    content_tools = [t for t in all_tools if t.category == "content"]
    ids = {t.id for t in content_tools}

    expected = {
        "content.read_text", "content.write_text", "content.append_text", "content.replace_text",
        "content.search_text", "content.search_regex", "content.search_in_directory", "content.batch_replace",
        "content.read_json", "content.write_json",
        "content.validate_json", "content.validate_yaml", "content.validate_xml",
        "content.read_csv", "content.write_csv",
        "content.parse_markdown", "content.markdown_outline", "content.extract_links",
        "content.search_code", "content.extract_symbols",
        "content.list_functions", "content.list_classes",
        "content.count_lines", "content.detect_language",
    }
    assert ids == expected, f"Missing: {expected - ids}, Extra: {ids - expected}"
    assert len(content_tools) == 24, f"Expected 24, got {len(content_tools)}"


# ── Large File Support ──


@pytest.mark.asyncio
async def test_read_large_file(tmp_path):
    f = tmp_path / "large.txt"
    f.write_text("x" * 100_000)
    result = await _read_text({"path": str(f)})
    assert result.success
    assert result.data["size"] == 100_000


@pytest.mark.asyncio
async def test_search_in_large_file(tmp_path):
    f = tmp_path / "huge.txt"
    f.write_text("needle\n" + "x" * 50_000 + "\nneedle\n")
    result = await _search_text({"path": str(f), "query": "needle"})
    assert result.success
    assert result.data["matches"] == 2


# ── Batch Operation Tests ──


@pytest.mark.asyncio
async def test_batch_replace_per_file_results(tmp_path, eb):
    (tmp_path / "a.txt").write_text("hello foo")
    (tmp_path / "b.txt").write_text("foo bar foo")
    (tmp_path / "c.txt").write_text("no match")
    result = await _batch_replace({"path": str(tmp_path), "pattern": "*.txt", "old": "foo", "new": "baz"}, eb)
    assert result.success
    assert result.data["files_processed"] == 2
    assert len(result.data["files"]) == 2
    file_names = {Path(f["file"]).name for f in result.data["files"]}
    assert file_names == {"a.txt", "b.txt"}


# ── Encoding Tests ──


@pytest.mark.asyncio
async def test_write_and_read_back(tmp_path, eb):
    f = tmp_path / "unicode.txt"
    content = "Hello, 世界! café ☕"
    result = await _write_text({"path": str(f), "content": content}, eb)
    assert result.success

    result = await _read_text({"path": str(f)})
    assert result.success
    assert result.data["content"] == content


@pytest.mark.asyncio
async def test_json_write_with_unicode(tmp_path, eb):
    f = tmp_path / "unicode.json"
    data = {"msg": "こんにちは", "price": "5€"}
    result = await _write_json({"path": str(f), "data": data}, eb)
    assert result.success
    loaded = json.loads(f.read_text(encoding="utf-8"))
    assert loaded["msg"] == "こんにちは"


# ── Validation Tests ──


@pytest.mark.asyncio
async def test_validate_json_with_schema():
    result = await _validate_json({
        "source": '{"name": "Alice", "age": 30}',
        "schema": {"name": "str", "age": "int"},
    })
    assert result.success


@pytest.mark.asyncio
async def test_validate_json_schema_missing_key():
    result = await _validate_json({
        "source": '{"name": "Alice"}',
        "schema": {"name": "str", "age": "int"},
    })
    assert result.success
    assert not result.data["valid"]
    assert any("age" in e for e in result.data["errors"])


# ── Tool Contract Tests ──


@pytest.mark.asyncio
async def test_content_tool_ids_unique(tm, eb):
    register_content_tools(tm, eb)
    await asyncio.sleep(0.05)
    all_tools = await tm.list_tools()
    content_tools = [t for t in all_tools if t.category == "content"]
    ids = [t.id for t in content_tools]
    assert len(ids) == len(set(ids)), "Duplicate tool IDs found"


@pytest.mark.asyncio
async def test_content_tools_have_permission_levels(tm, eb):
    register_content_tools(tm, eb)
    await asyncio.sleep(0.05)
    all_tools = await tm.list_tools()
    content_tools = [t for t in all_tools if t.category == "content"]
    for t in content_tools:
        assert t.permission_level is not None
        assert 0 <= int(t.permission_level) <= 3


@pytest.mark.asyncio
async def test_write_tools_require_confirmation(tm, eb):
    register_content_tools(tm, eb)
    await asyncio.sleep(0.05)
    write_ids = {
        "content.write_text", "content.append_text", "content.replace_text",
        "content.batch_replace", "content.write_json", "content.write_csv",
    }
    for tid in write_ids:
        contract = await tm.get_tool(tid)
        assert contract is not None, f"{tid} not registered"
        assert contract.requires_confirmation, f"{tid} should require confirmation"
