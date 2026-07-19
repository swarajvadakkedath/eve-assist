"""Content Processing Toolkit — Text, Search, Structured, Markdown, Code Analysis for AIOS Phase 5.4A."""

import asyncio
import csv
import io
import json
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from aios.core.tool_manager import ToolResult
from aios.core.event_bus import EventBus


# ── Helpers ──

def _detect_encoding(path: Path) -> str:
    try:
        with path.open("rb") as f:
            raw = f.read(4)
        if raw.startswith(b"\xef\xbb\xbf"):
            return "utf-8-sig"
        if raw.startswith(b"\xff\xfe"):
            return "utf-16-le"
        if raw.startswith(b"\xfe\xff"):
            return "utf-16-be"
        return "utf-8"
    except Exception:
        return "utf-8"


def _read_file_safe(path: Path, encoding: str | None = None) -> tuple[str, str]:
    enc = encoding or _detect_encoding(path)
    try:
        text = path.read_text(encoding=enc, errors="replace")
        return text, enc
    except Exception:
        text = path.read_text(encoding="utf-8", errors="replace")
        return text, "utf-8"


def _chunked_read(path: Path, chunk_size: int = 65536) -> str:
    text_parts = []
    enc = _detect_encoding(path)
    with path.open("r", encoding=enc, errors="replace") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            text_parts.append(chunk)
    return "".join(text_parts)


# ── Text File Tools ──


async def _read_text(params: dict) -> ToolResult:
    try:
        path = Path(params["path"])
        encoding = params.get("encoding")
        offset = params.get("offset")
        limit = params.get("limit")

        if not path.exists():
            return ToolResult(success=False, error=f"File not found: {path}")
        if path.is_dir():
            return ToolResult(success=False, error=f"Path is a directory: {path}")

        text, detected_enc = _read_file_safe(path, encoding)
        lines = text.splitlines(keepends=True)

        if offset is not None or limit is not None:
            start = offset or 0
            end = start + limit if limit else len(lines)
            content = "".join(lines[start:end])
        else:
            content = text

        return ToolResult(success=True, data={
            "path": str(path),
            "content": content,
            "encoding": detected_enc,
            "size": len(text),
            "total_lines": len(lines),
            "offset": offset or 0,
            "lines_returned": len(content.splitlines()),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _write_text(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    try:
        path = Path(params["path"])
        content = params.get("content", "")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

        if event_bus:
            await event_bus.publish(
                "content:write",
                {"path": str(path), "size": len(content)},
                source="content_tools",
            )

        return ToolResult(success=True, data={
            "path": str(path),
            "written": len(content),
            "encoding": "utf-8",
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _append_text(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    try:
        path = Path(params["path"])
        content = params.get("content", "")

        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(content)

        if event_bus:
            await event_bus.publish(
                "content:append",
                {"path": str(path), "appended": len(content)},
                source="content_tools",
            )

        return ToolResult(success=True, data={
            "path": str(path),
            "appended": len(content),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _replace_text(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    try:
        path = Path(params["path"])
        old = params.get("old", "")
        new = params.get("new", "")
        count = params.get("count", 0)
        regex = params.get("regex", False)

        if not path.exists():
            return ToolResult(success=False, error=f"File not found: {path}")
        if not old:
            return ToolResult(success=False, error="No search text provided")

        text, enc = _read_file_safe(path)

        if regex:
            pattern = re.compile(old)
            new_text, actual_count = pattern.subn(new, text, count=count if count > 0 else 0)
        else:
            if count > 0:
                actual_count = text.count(old)
                if actual_count > count:
                    actual_count = count
                new_text = text.replace(old, new, count)
            else:
                actual_count = text.count(old)
                new_text = text.replace(old, new)

        path.write_text(new_text, encoding=enc)

        if event_bus:
            await event_bus.publish(
                "content:replace",
                {"path": str(path), "replaced": actual_count, "regex": regex},
                source="content_tools",
            )

        return ToolResult(success=True, data={
            "path": str(path),
            "replaced": actual_count,
            "regex": regex,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Search Tools ──


async def _search_text(params: dict) -> ToolResult:
    try:
        path = Path(params.get("path", ""))
        query = params.get("query", "")
        case_sensitive = params.get("case_sensitive", False)
        max_results = params.get("max_results", 100)

        if not path or not path.exists():
            return ToolResult(success=False, error=f"File not found: {path}")
        if not query:
            return ToolResult(success=False, error="No search query provided")

        text, enc = _read_file_safe(path)
        lines = text.splitlines()
        results = []
        q = query if case_sensitive else query.lower()

        for i, line in enumerate(lines):
            if len(results) >= max_results:
                break
            check = line if case_sensitive else line.lower()
            if q in check:
                results.append({
                    "line": i + 1,
                    "content": line[:500],
                    "column": check.index(q) + 1 if not case_sensitive else line.index(query) + 1,
                })

        return ToolResult(success=True, data={
            "path": str(path),
            "query": query,
            "results": results,
            "matches": len(results),
            "case_sensitive": case_sensitive,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _search_regex(params: dict) -> ToolResult:
    try:
        path = Path(params.get("path", ""))
        pattern = params.get("pattern", "")
        max_results = params.get("max_results", 100)

        if not path or not path.exists():
            return ToolResult(success=False, error=f"File not found: {path}")
        if not pattern:
            return ToolResult(success=False, error="No regex pattern provided")

        try:
            regex = re.compile(pattern)
        except re.error as e:
            return ToolResult(success=False, error=f"Invalid regex: {e}")

        text, enc = _read_file_safe(path)
        lines = text.splitlines()
        results = []

        for i, line in enumerate(lines):
            if len(results) >= max_results:
                break
            for match in regex.finditer(line):
                if len(results) >= max_results:
                    break
                results.append({
                    "line": i + 1,
                    "content": line[:500],
                    "match": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                })
            if not regex.findall(line) and regex.search(line):
                pass

        return ToolResult(success=True, data={
            "path": str(path),
            "pattern": pattern,
            "results": results,
            "matches": len(results),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _search_in_directory(params: dict) -> ToolResult:
    try:
        root = Path(params.get("path", "."))
        query = params.get("query", "")
        pattern = params.get("pattern", "*")
        recursive = params.get("recursive", True)
        max_results = params.get("max_results", 100)
        case_sensitive = params.get("case_sensitive", False)

        if not root.exists():
            return ToolResult(success=False, error=f"Path not found: {root}")
        if not query:
            return ToolResult(success=False, error="No search query provided")

        q = query if case_sensitive else query.lower()
        results = []
        iterator = root.rglob(pattern) if recursive else root.glob(pattern)

        for entry in iterator:
            if not entry.is_file():
                continue
            if len(results) >= max_results:
                break
            try:
                text, _ = _read_file_safe(entry)
                lines = text.splitlines()
                for i, line in enumerate(lines):
                    if len(results) >= max_results:
                        break
                    check = line if case_sensitive else line.lower()
                    if q in check:
                        results.append({
                            "file": str(entry),
                            "line": i + 1,
                            "content": line[:500],
                        })
            except Exception:
                continue

        return ToolResult(success=True, data={
            "path": str(root),
            "query": query,
            "results": results,
            "matches": len(results),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _batch_replace(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    try:
        root = Path(params.get("path", "."))
        pattern = params.get("pattern", "*")
        old = params.get("old", "")
        new = params.get("new", "")
        recursive = params.get("recursive", True)
        regex = params.get("regex", False)
        max_files = params.get("max_files", 50)

        if not root.exists():
            return ToolResult(success=False, error=f"Path not found: {root}")
        if not old:
            return ToolResult(success=False, error="No search text provided")

        file_results = []
        total_replaced = 0
        files_processed = 0

        iterator = root.rglob(pattern) if recursive else root.glob(pattern)

        for entry in iterator:
            if not entry.is_file():
                continue
            if files_processed >= max_files:
                break

            try:
                text, enc = _read_file_safe(entry)
                if regex:
                    compiled = re.compile(old)
                    new_text, count = compiled.subn(new, text)
                else:
                    count = text.count(old)
                    if count == 0:
                        continue
                    new_text = text.replace(old, new)

                entry.write_text(new_text, encoding=enc)
                total_replaced += count
                files_processed += 1
                file_results.append({
                    "file": str(entry),
                    "replaced": count,
                })
            except Exception as e:
                file_results.append({
                    "file": str(entry),
                    "error": str(e),
                })

        if event_bus:
            await event_bus.publish(
                "content:batch_replace",
                {
                    "path": str(root), "files_processed": files_processed,
                    "total_replaced": total_replaced,
                },
                source="content_tools",
            )

        return ToolResult(success=True, data={
            "path": str(root),
            "files": file_results,
            "files_processed": files_processed,
            "total_replaced": total_replaced,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Structured File Tools ──


async def _read_json(params: dict) -> ToolResult:
    try:
        path = Path(params["path"])
        if not path.exists():
            return ToolResult(success=False, error=f"File not found: {path}")

        text, enc = _read_file_safe(path)
        data = json.loads(text)

        return ToolResult(success=True, data={
            "path": str(path),
            "data": data,
            "encoding": enc,
            "size": len(text),
        })
    except json.JSONDecodeError as e:
        return ToolResult(success=False, error=f"Invalid JSON: {e}")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _write_json(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    try:
        path = Path(params["path"])
        data = params.get("data")
        indent = params.get("indent", 2)
        sort_keys = params.get("sort_keys", False)

        if data is None:
            return ToolResult(success=False, error="No data provided")

        path.parent.mkdir(parents=True, exist_ok=True)
        json_str = json.dumps(data, indent=indent, sort_keys=sort_keys, ensure_ascii=False)
        path.write_text(json_str, encoding="utf-8")

        if event_bus:
            await event_bus.publish(
                "content:write_json",
                {"path": str(path), "size": len(json_str)},
                source="content_tools",
            )

        return ToolResult(success=True, data={
            "path": str(path),
            "written": len(json_str),
            "pretty": indent > 0,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _validate_json(params: dict) -> ToolResult:
    try:
        source = params.get("source", "")
        schema = params.get("schema")

        if not source:
            return ToolResult(success=False, error="No source provided")

        if Path(source).exists():
            text, _ = _read_file_safe(Path(source))
            source_path = source
        else:
            text = source
            source_path = None

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            return ToolResult(success=True, data={
                "valid": False,
                "errors": [f"Line {e.lineno}, col {e.colno}: {e.msg}"],
                "source": source_path,
            })

        validation_errors = []

        if schema:
            try:
                schema_data = json.loads(schema) if isinstance(schema, str) else schema
                if isinstance(data, dict) and isinstance(schema_data, dict):
                    for key, expected_type in schema_data.items():
                        if key not in data:
                            validation_errors.append(f"Missing required key: {key}")
                        elif expected_type and not isinstance(data[key], eval(expected_type)):
                            validation_errors.append(
                                f"Key '{key}' expected {expected_type}, got {type(data[key]).__name__}"
                            )
            except Exception as e:
                validation_errors.append(f"Schema validation error: {e}")

        return ToolResult(success=True, data={
            "valid": len(validation_errors) == 0,
            "errors": validation_errors,
            "source": source_path,
            "parsed_type": type(data).__name__,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _validate_yaml(params: dict) -> ToolResult:
    try:
        source = params.get("source", "")

        if not source:
            return ToolResult(success=False, error="No source provided")

        if Path(source).exists():
            text, _ = _read_file_safe(Path(source))
            source_path = source
        else:
            text = source
            source_path = None

        try:
            import yaml
            data = yaml.safe_load(text)
            valid = True
            errors = []
        except ImportError:
            return ToolResult(success=False, error="PyYAML is not installed")
        except yaml.YAMLError as e:
            valid = False
            errors = [str(e)]
            data = None

        return ToolResult(success=True, data={
            "valid": valid,
            "errors": errors,
            "source": source_path,
            "parsed_type": type(data).__name__ if data is not None else "null",
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _validate_xml(params: dict) -> ToolResult:
    try:
        source = params.get("source", "")

        if not source:
            return ToolResult(success=False, error="No source provided")

        if Path(source).exists():
            text, _ = _read_file_safe(Path(source))
            source_path = source
        else:
            text = source
            source_path = None

        try:
            ET.fromstring(text)
            valid = True
            errors = []
        except ET.ParseError as e:
            valid = False
            errors = [str(e)]

        return ToolResult(success=True, data={
            "valid": valid,
            "errors": errors,
            "source": source_path,
            "root_element": None,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _read_csv(params: dict) -> ToolResult:
    try:
        path = Path(params["path"])
        dialect = params.get("dialect", "excel")
        has_header = params.get("has_header", True)
        max_rows = params.get("max_rows", 10000)

        if not path.exists():
            return ToolResult(success=False, error=f"File not found: {path}")

        text, enc = _read_file_safe(path)
        reader = csv.DictReader(io.StringIO(text)) if has_header else csv.reader(io.StringIO(text))

        rows = []
        for i, row in enumerate(reader):
            if i >= max_rows:
                break
            rows.append(row if isinstance(row, dict) else dict(enumerate(row)))

        if has_header:
            fieldnames = reader.fieldnames
        else:
            fieldnames = list(range(len(rows[0]))) if rows else []

        return ToolResult(success=True, data={
            "path": str(path),
            "rows": rows,
            "count": len(rows),
            "fieldnames": fieldnames,
            "has_header": has_header,
            "encoding": enc,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _write_csv(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    try:
        path = Path(params["path"])
        data = params.get("data", [])
        fieldnames = params.get("fieldnames")

        if not data:
            return ToolResult(success=False, error="No data provided")

        path.parent.mkdir(parents=True, exist_ok=True)
        output = io.StringIO()

        if fieldnames and isinstance(data[0], dict):
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        elif isinstance(data[0], dict):
            writer = csv.DictWriter(output, fieldnames=list(data[0].keys()))
            writer.writeheader()
            writer.writerows(data)
        else:
            writer = csv.writer(output)
            for row in data:
                writer.writerow(row if isinstance(row, (list, tuple)) else [row])

        csv_str = output.getvalue()
        path.write_text(csv_str, encoding="utf-8")

        if event_bus:
            await event_bus.publish(
                "content:write_csv",
                {"path": str(path), "rows": len(data), "size": len(csv_str)},
                source="content_tools",
            )

        return ToolResult(success=True, data={
            "path": str(path),
            "rows": len(data),
            "written": len(csv_str),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Markdown Tools ──


def _parse_markdown_structure(text: str) -> list[dict]:
    structure = []
    lines = text.splitlines()
    current_heading = None
    current_content = []
    in_code_block = False
    in_list = False
    list_items = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading_match:
            if current_heading or current_content:
                structure.append({
                    "type": "section",
                    "heading": current_heading,
                    "content": "\n".join(current_content).strip() if current_content else "",
                })
            current_heading = {"level": len(heading_match.group(1)), "text": heading_match.group(2).strip()}
            current_content = []
            continue

        if re.match(r"^[-*+]\s+", stripped):
            if not in_list:
                list_items = []
                in_list = True
            list_items.append(re.sub(r"^[-*+]\s+", "", stripped))
            continue
        else:
            if in_list and list_items:
                current_content.append("\n".join(f"- {item}" for item in list_items))
                list_items = []
                in_list = False

        if stripped:
            current_content.append(stripped)

    if in_list and list_items:
        current_content.append("\n".join(f"- {item}" for item in list_items))

    if current_heading or current_content:
        structure.append({
            "type": "section",
            "heading": current_heading,
            "content": "\n".join(current_content).strip() if current_content else "",
        })

    return structure


async def _parse_markdown(params: dict) -> ToolResult:
    try:
        source = params.get("source", "")
        if Path(source).exists():
            text, enc = _read_file_safe(Path(source))
            source_path = source
        else:
            text = source
            source_path = None

        structure = _parse_markdown_structure(text)

        return ToolResult(success=True, data={
            "source": source_path,
            "sections": structure,
            "section_count": len(structure),
            "total_chars": len(text),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _markdown_outline(params: dict) -> ToolResult:
    try:
        source = params.get("source", "")
        if Path(source).exists():
            text, _ = _read_file_safe(Path(source))
            source_path = source
        else:
            text = source
            source_path = None

        headings = []
        for line in text.splitlines():
            m = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
            if m:
                headings.append({
                    "level": len(m.group(1)),
                    "text": m.group(2).strip(),
                })

        return ToolResult(success=True, data={
            "source": source_path,
            "headings": headings,
            "count": len(headings),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _extract_links(params: dict) -> ToolResult:
    try:
        source = params.get("source", "")
        if Path(source).exists():
            text, _ = _read_file_safe(Path(source))
            source_path = source
        else:
            text = source
            source_path = None

        markdown_links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", text)
        bare_urls = re.findall(r"https?://[^\s)\]}>\"']+", text)

        links = []
        seen = set()

        for link_text, url in markdown_links:
            if url not in seen:
                links.append({"type": "markdown", "text": link_text, "url": url})
                seen.add(url)

        for url in bare_urls:
            if url not in seen and ") <" not in url:
                links.append({"type": "bare", "text": url, "url": url})
                seen.add(url)

        return ToolResult(success=True, data={
            "source": source_path,
            "links": links,
            "count": len(links),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Code Analysis Tools ──

LANGUAGE_PATTERNS: dict[str, dict[str, Any]] = {
    "python": {
        "extensions": {".py", ".pyw", ".pyx"},
        "comments": {"#"},
        "symbols": re.compile(r"^(?:class|def|async\s+def)\s+(\w+)"),
    },
    "javascript": {
        "extensions": {".js", ".jsx", ".mjs"},
        "comments": {"//", "/*"},
        "symbols": re.compile(r"^(?:function\s+(\w+)|(?:export\s+)?(?:const|let|var)\s+(\w+)\s*[:=]\s*(?:async\s+)?function|class\s+(\w+))"),
    },
    "typescript": {
        "extensions": {".ts", ".tsx"},
        "comments": {"//", "/*"},
        "symbols": re.compile(r"^(?:function\s+(\w+)|(?:export\s+)?(?:const|let|var)\s+(\w+)\s*[:=]\s*(?:async\s+)?function|class\s+(\w+)|interface\s+(\w+)|type\s+(\w+))"),
    },
    "java": {
        "extensions": {".java"},
        "comments": {"//", "/*"},
        "symbols": re.compile(r"^\s*(?:public|private|protected|static|\s)*(?:class|interface|enum)\s+(\w+)"),
    },
    "go": {
        "extensions": {".go"},
        "comments": {"//"},
        "symbols": re.compile(r"^(?:func\s+(\w+)|type\s+(\w+)\s+)"),
    },
    "rust": {
        "extensions": {".rs"},
        "comments": {"//", "/*"},
        "symbols": re.compile(r"^(?:fn\s+(\w+)|struct\s+(\w+)|enum\s+(\w+)|trait\s+(\w+)|impl\s+(\w+))"),
    },
    "cpp": {
        "extensions": {".cpp", ".cc", ".cxx", ".hpp", ".h", ".hxx"},
        "comments": {"//", "/*"},
        "symbols": re.compile(r"^\s*(?:class|struct|enum|union)\s+(\w+)"),
    },
    "ruby": {
        "extensions": {".rb"},
        "comments": {"#"},
        "symbols": re.compile(r"^(?:def\s+(?:self\.)?(\w+)|class\s+(\w+)|module\s+(\w+))"),
    },
}


def _detect_language_from_path(path: Path) -> str | None:
    ext = path.suffix.lower()
    for lang, info in LANGUAGE_PATTERNS.items():
        if ext in info["extensions"]:
            return lang
    return None


def _detect_language_from_content(text: str) -> str | None:
    scores: dict[str, int] = {}
    for lang, info in LANGUAGE_PATTERNS.items():
        score = 0
        for comment in info["comments"]:
            if comment in text:
                score += 10
        matches = info["symbols"].findall(text)
        if matches:
            score += len(matches) * 5
        if "python" in lang and ("import " in text or "from " in text or "def " in text):
            score += 3
        if "javascript" in lang and ("=>" in text or "const " in text or "let " in text):
            score += 3
        if "go" in lang and ("func " in text or "package " in text):
            score += 3
        if "rust" in lang and ("fn " in text or "let mut " in text):
            score += 3
        if "java" in lang and ("public class" in text or "public static" in text):
            score += 3
        if score > 0:
            scores[lang] = score
    if scores:
        return max(scores, key=scores.get)
    return None


def _extract_symbols_from_text(text: str, lang: str) -> list[dict]:
    info = LANGUAGE_PATTERNS.get(lang)
    if not info:
        return []

    symbols = []
    seen = set()
    lines = text.splitlines()
    regex = info["symbols"]

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("//"):
            continue
        matches = regex.findall(stripped)
        for match_val in matches:
            names = [n for n in match_val if n] if isinstance(match_val, tuple) else [match_val] if match_val else []
            for name in names:
                if name not in seen:
                    symbols.append({
                        "name": name,
                        "line": i + 1,
                        "type": _infer_symbol_type(stripped),
                    })
                    seen.add(name)
    return symbols


def _infer_symbol_type(line: str) -> str:
    if line.startswith("class") or " class " in line:
        return "class"
    if line.startswith("def ") or line.startswith("async def "):
        return "function"
    if line.startswith("fn ") or " fn " in line:
        return "function"
    if line.startswith("interface") or " interface " in line:
        return "interface"
    if line.startswith("struct") or " struct " in line:
        return "struct"
    if line.startswith("enum") or " enum " in line:
        return "enum"
    if line.startswith("type ") or " type " in line:
        return "type"
    return "symbol"


async def _search_code(params: dict) -> ToolResult:
    try:
        path = Path(params.get("path", ""))
        query = params.get("query", "")
        language = params.get("language", "")
        max_results = params.get("max_results", 100)

        if not path or not path.exists():
            return ToolResult(success=False, error=f"Path not found: {path}")
        if not query:
            return ToolResult(success=False, error="No search query provided")

        results = []

        if path.is_file():
            files = [path]
        else:
            ext_filter = params.get("extension", "")
            if ext_filter:
                pattern = f"*{ext_filter}" if ext_filter.startswith(".") else f"*.{ext_filter}"
            elif language:
                lang_info = LANGUAGE_PATTERNS.get(language)
                if not lang_info:
                    return ToolResult(success=False, error=f"Unknown language: {language}")
                pattern = f"*{{{','.join(ext[1:] for ext in lang_info['extensions'])}}}"
            else:
                pattern = "*"
            files = list(path.rglob(pattern)) if path.is_dir() else [path]

        for entry in files:
            if not entry.is_file():
                continue
            if len(results) >= max_results:
                break
            try:
                text, _ = _read_file_safe(entry)
                detected = _detect_language_from_path(entry)
                lines = text.splitlines()
                for i, line in enumerate(lines):
                    if len(results) >= max_results:
                        break
                    if query in line:
                        results.append({
                            "file": str(entry),
                            "line": i + 1,
                            "content": line.strip()[:500],
                            "language": detected,
                        })
            except Exception:
                continue

        return ToolResult(success=True, data={
            "query": query,
            "results": results,
            "matches": len(results),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _extract_symbols(params: dict) -> ToolResult:
    try:
        path = Path(params.get("path", ""))
        language = params.get("language", "")

        if not path or not path.exists():
            return ToolResult(success=False, error=f"File not found: {path}")

        text, enc = _read_file_safe(path)
        lang = language or _detect_language_from_path(path) or _detect_language_from_content(text)

        if not lang:
            return ToolResult(success=False, error="Could not detect language")

        symbols = _extract_symbols_from_text(text, lang)

        return ToolResult(success=True, data={
            "path": str(path),
            "language": lang,
            "symbols": symbols,
            "count": len(symbols),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _list_functions(params: dict) -> ToolResult:
    try:
        path = Path(params.get("path", ""))
        language = params.get("language", "")

        if not path or not path.exists():
            return ToolResult(success=False, error=f"File not found: {path}")

        text, enc = _read_file_safe(path)
        lang = language or _detect_language_from_path(path) or _detect_language_from_content(text)

        symbols = _extract_symbols_from_text(text, lang or "python")
        functions = [s for s in symbols if s["type"] == "function"]

        return ToolResult(success=True, data={
            "path": str(path),
            "language": lang,
            "functions": functions,
            "count": len(functions),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _list_classes(params: dict) -> ToolResult:
    try:
        path = Path(params.get("path", ""))
        language = params.get("language", "")

        if not path or not path.exists():
            return ToolResult(success=False, error=f"File not found: {path}")

        text, enc = _read_file_safe(path)
        lang = language or _detect_language_from_path(path) or _detect_language_from_content(text)

        symbols = _extract_symbols_from_text(text, lang or "python")
        classes = [s for s in symbols if s["type"] in ("class", "struct", "interface", "enum")]

        return ToolResult(success=True, data={
            "path": str(path),
            "language": lang,
            "classes": classes,
            "count": len(classes),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _count_lines(params: dict) -> ToolResult:
    try:
        path = Path(params.get("path", ""))
        include_empty = params.get("include_empty", True)
        include_comments = params.get("include_comments", True)

        if not path or not path.exists():
            return ToolResult(success=False, error=f"Path not found: {path}")

        if path.is_file():
            files = [path]
        else:
            files = list(path.rglob("*")) if path.is_dir() else [path]
            files = [f for f in files if f.is_file()]

        total_lines = 0
        total_code = 0
        total_comments = 0
        total_blank = 0
        file_counts = []

        for entry in files:
            try:
                text, _ = _read_file_safe(entry)
                lines = text.splitlines()
                n = len(lines)

                if include_empty:
                    blank = sum(1 for l in lines if not l.strip())
                else:
                    blank = 0

                if include_comments:
                    comment_lines = sum(1 for l in lines if l.strip().startswith(("#", "//", "/*", "*")))
                else:
                    comment_lines = 0

                code_lines = n - blank if include_empty else n

                if include_comments:
                    code_lines -= comment_lines

                total_lines += n
                total_code += code_lines
                total_comments += comment_lines
                total_blank += blank

                file_counts.append({
                    "file": str(entry),
                    "total": n,
                    "code": code_lines,
                    "comments": comment_lines,
                    "blank": blank,
                })
            except Exception:
                continue

        return ToolResult(success=True, data={
            "path": str(path),
            "files": file_counts if len(files) > 1 else file_counts[0] if file_counts else {},
            "summary": {
                "total": total_lines,
                "code": total_code,
                "comments": total_comments,
                "blank": total_blank,
            },
            "file_count": len(files) if len(files) > 1 else 1,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _detect_language(params: dict) -> ToolResult:
    try:
        path = params.get("path", "")
        source = params.get("source", "")

        if path:
            p = Path(path)
            if not p.exists():
                return ToolResult(success=False, error=f"File not found: {path}")
            text, _ = _read_file_safe(p)
            lang = _detect_language_from_path(p) or _detect_language_from_content(text)
            source_path = str(p)
        elif source:
            lang = _detect_language_from_content(source)
            source_path = None
        else:
            return ToolResult(success=False, error="Provide path or source")

        return ToolResult(success=True, data={
            "language": lang or "unknown",
            "confidence": "high" if (path and lang and _detect_language_from_path(Path(path))) else "medium",
            "source": source_path,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Registration ──

def register_content_tools(tm, event_bus=None):
    import asyncio
    from aios.core.tool_manager import ToolContract
    from aios.core.permission_manager import PermissionLevel

    text_tools = [
        ToolContract(
            id="content.read_text", name="Read Text",
            description="Read a text file with automatic encoding detection",
            parameters={
                "path": {"type": "string", "description": "Path to the file"},
                "encoding": {"type": "string", "description": "File encoding (auto-detected if omitted)", "required": False},
                "offset": {"type": "integer", "description": "Start line", "required": False},
                "limit": {"type": "integer", "description": "Max lines to read", "required": False},
            },
            returns={"path": {"type": "string"}, "content": {"type": "string"}, "encoding": {"type": "string"}},
            permission_level=PermissionLevel.READ, category="content",
            capabilities=["content.read_text"], tags=["content", "text", "read"],
        ),
        ToolContract(
            id="content.write_text", name="Write Text",
            description="Write text to a file (creates parent directories, requires confirmation)",
            parameters={
                "path": {"type": "string", "description": "Path to the file"},
                "content": {"type": "string", "description": "Content to write"},
            },
            returns={"path": {"type": "string"}, "written": {"type": "integer"}},
            permission_level=PermissionLevel.WORKSPACE, category="content",
            requires_confirmation=True,
            capabilities=["content.write_text"], tags=["content", "text", "write"],
        ),
        ToolContract(
            id="content.append_text", name="Append Text",
            description="Append text to a file (creates file if not exists, requires confirmation)",
            parameters={
                "path": {"type": "string", "description": "Path to the file"},
                "content": {"type": "string", "description": "Content to append"},
            },
            returns={"path": {"type": "string"}, "appended": {"type": "integer"}},
            permission_level=PermissionLevel.WORKSPACE, category="content",
            requires_confirmation=True,
            capabilities=["content.append_text"], tags=["content", "text", "append"],
        ),
        ToolContract(
            id="content.replace_text", name="Replace Text",
            description="Replace text in a file with confirmation",
            parameters={
                "path": {"type": "string", "description": "Path to the file"},
                "old": {"type": "string", "description": "Text to search for"},
                "new": {"type": "string", "description": "Replacement text"},
                "count": {"type": "integer", "description": "Max replacements (0 = all)", "default": 0},
                "regex": {"type": "boolean", "description": "Use regex for search", "default": False},
            },
            returns={"path": {"type": "string"}, "replaced": {"type": "integer"}},
            permission_level=PermissionLevel.WORKSPACE, category="content",
            requires_confirmation=True,
            capabilities=["content.replace_text"], tags=["content", "text", "replace"],
        ),
    ]

    search_tools = [
        ToolContract(
            id="content.search_text", name="Search Text",
            description="Search for a substring in a file",
            parameters={
                "path": {"type": "string", "description": "Path to the file"},
                "query": {"type": "string", "description": "Text to search for"},
                "case_sensitive": {"type": "boolean", "description": "Case sensitive search", "default": False},
                "max_results": {"type": "integer", "description": "Max results", "default": 100},
            },
            returns={"path": {"type": "string"}, "query": {"type": "string"}, "results": {"type": "array"}, "matches": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="content",
            capabilities=["content.search_text"], tags=["content", "search", "text"],
        ),
        ToolContract(
            id="content.search_regex", name="Search Regex",
            description="Search for a regex pattern in a file",
            parameters={
                "path": {"type": "string", "description": "Path to the file"},
                "pattern": {"type": "string", "description": "Regex pattern"},
                "max_results": {"type": "integer", "description": "Max results", "default": 100},
            },
            returns={"path": {"type": "string"}, "pattern": {"type": "string"}, "results": {"type": "array"}, "matches": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="content",
            capabilities=["content.search_regex"], tags=["content", "search", "regex"],
        ),
        ToolContract(
            id="content.search_in_directory", name="Search in Directory",
            description="Search across all files in a directory for a substring",
            parameters={
                "path": {"type": "string", "description": "Root directory"},
                "query": {"type": "string", "description": "Text to search for"},
                "pattern": {"type": "string", "description": "File glob pattern", "default": "*"},
                "recursive": {"type": "boolean", "description": "Search recursively", "default": True},
                "max_results": {"type": "integer", "description": "Max results", "default": 100},
                "case_sensitive": {"type": "boolean", "description": "Case sensitive", "default": False},
            },
            returns={"path": {"type": "string"}, "query": {"type": "string"}, "results": {"type": "array"}, "matches": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="content",
            capabilities=["content.search_in_directory"], tags=["content", "search", "directory"],
        ),
        ToolContract(
            id="content.batch_replace", name="Batch Replace",
            description="Replace text across multiple files (requires confirmation)",
            parameters={
                "path": {"type": "string", "description": "Root directory", "default": "."},
                "pattern": {"type": "string", "description": "File glob pattern", "default": "*"},
                "old": {"type": "string", "description": "Text to search for"},
                "new": {"type": "string", "description": "Replacement text"},
                "recursive": {"type": "boolean", "description": "Search recursively", "default": True},
                "regex": {"type": "boolean", "description": "Use regex", "default": False},
                "max_files": {"type": "integer", "description": "Max files to process", "default": 50},
            },
            returns={"path": {"type": "string"}, "files": {"type": "array"}, "total_replaced": {"type": "integer"}},
            permission_level=PermissionLevel.WORKSPACE, category="content",
            requires_confirmation=True,
            capabilities=["content.batch_replace"], tags=["content", "batch", "replace"],
        ),
    ]

    structured_tools = [
        ToolContract(
            id="content.read_json", name="Read JSON",
            description="Read and parse a JSON file",
            parameters={
                "path": {"type": "string", "description": "Path to JSON file"},
            },
            returns={"path": {"type": "string"}, "data": {"type": "object"}, "encoding": {"type": "string"}},
            permission_level=PermissionLevel.READ, category="content",
            capabilities=["content.read_json"], tags=["content", "json", "read"],
        ),
        ToolContract(
            id="content.write_json", name="Write JSON",
            description="Serialize data as JSON and write to file (requires confirmation)",
            parameters={
                "path": {"type": "string", "description": "Path to JSON file"},
                "data": {"type": "object", "description": "Data to serialize"},
                "indent": {"type": "integer", "description": "Indentation spaces", "default": 2},
                "sort_keys": {"type": "boolean", "description": "Sort dictionary keys", "default": False},
            },
            returns={"path": {"type": "string"}, "written": {"type": "integer"}},
            permission_level=PermissionLevel.WORKSPACE, category="content",
            requires_confirmation=True,
            capabilities=["content.write_json"], tags=["content", "json", "write"],
        ),
        ToolContract(
            id="content.validate_json", name="Validate JSON",
            description="Validate a JSON string or file (optionally against a schema)",
            parameters={
                "source": {"type": "string", "description": "JSON string or path to JSON file"},
                "schema": {"type": "object", "description": "Optional schema for validation", "required": False},
            },
            returns={"valid": {"type": "boolean"}, "errors": {"type": "array"}},
            permission_level=PermissionLevel.READ, category="content",
            capabilities=["content.validate_json"], tags=["content", "json", "validate"],
        ),
        ToolContract(
            id="content.validate_yaml", name="Validate YAML",
            description="Validate a YAML string or file",
            parameters={
                "source": {"type": "string", "description": "YAML string or path to YAML file"},
            },
            returns={"valid": {"type": "boolean"}, "errors": {"type": "array"}},
            permission_level=PermissionLevel.READ, category="content",
            capabilities=["content.validate_yaml"], tags=["content", "yaml", "validate"],
        ),
        ToolContract(
            id="content.validate_xml", name="Validate XML",
            description="Validate an XML string or file",
            parameters={
                "source": {"type": "string", "description": "XML string or path to XML file"},
            },
            returns={"valid": {"type": "boolean"}, "errors": {"type": "array"}},
            permission_level=PermissionLevel.READ, category="content",
            capabilities=["content.validate_xml"], tags=["content", "xml", "validate"],
        ),
        ToolContract(
            id="content.read_csv", name="Read CSV",
            description="Read a CSV file as structured data",
            parameters={
                "path": {"type": "string", "description": "Path to CSV file"},
                "has_header": {"type": "boolean", "description": "File has header row", "default": True},
                "max_rows": {"type": "integer", "description": "Max rows to read", "default": 10000},
            },
            returns={"path": {"type": "string"}, "rows": {"type": "array"}, "count": {"type": "integer"}, "fieldnames": {"type": "array"}},
            permission_level=PermissionLevel.READ, category="content",
            capabilities=["content.read_csv"], tags=["content", "csv", "read"],
        ),
        ToolContract(
            id="content.write_csv", name="Write CSV",
            description="Write structured data as CSV file (requires confirmation)",
            parameters={
                "path": {"type": "string", "description": "Path to CSV file"},
                "data": {"type": "array", "description": "Array of objects or arrays"},
                "fieldnames": {"type": "array", "description": "Column order (optional)", "required": False},
            },
            returns={"path": {"type": "string"}, "rows": {"type": "integer"}, "written": {"type": "integer"}},
            permission_level=PermissionLevel.WORKSPACE, category="content",
            requires_confirmation=True,
            capabilities=["content.write_csv"], tags=["content", "csv", "write"],
        ),
    ]

    markdown_tools = [
        ToolContract(
            id="content.parse_markdown", name="Parse Markdown",
            description="Parse markdown text or file into structured sections",
            parameters={
                "source": {"type": "string", "description": "Markdown string or path to .md file"},
            },
            returns={"sections": {"type": "array"}, "section_count": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="content",
            capabilities=["content.parse_markdown"], tags=["content", "markdown", "parse"],
        ),
        ToolContract(
            id="content.markdown_outline", name="Markdown Outline",
            description="Extract heading outline from markdown text or file",
            parameters={
                "source": {"type": "string", "description": "Markdown string or path to .md file"},
            },
            returns={"headings": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="content",
            capabilities=["content.markdown_outline"], tags=["content", "markdown", "outline"],
        ),
        ToolContract(
            id="content.extract_links", name="Extract Links",
            description="Extract all links from markdown text or file",
            parameters={
                "source": {"type": "string", "description": "Markdown string or path to .md file"},
            },
            returns={"links": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="content",
            capabilities=["content.extract_links"], tags=["content", "markdown", "links"],
        ),
    ]

    code_tools = [
        ToolContract(
            id="content.search_code", name="Search Code",
            description="Search code files for a substring",
            parameters={
                "path": {"type": "string", "description": "File or directory path"},
                "query": {"type": "string", "description": "Text to search for"},
                "language": {"type": "string", "description": "Filter by language", "required": False},
                "extension": {"type": "string", "description": "Filter by file extension", "required": False},
                "max_results": {"type": "integer", "description": "Max results", "default": 100},
            },
            returns={"query": {"type": "string"}, "results": {"type": "array"}, "matches": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="content",
            capabilities=["content.search_code"], tags=["content", "code", "search"],
        ),
        ToolContract(
            id="content.extract_symbols", name="Extract Symbols",
            description="Extract symbols (classes, functions, etc.) from a code file",
            parameters={
                "path": {"type": "string", "description": "Path to code file"},
                "language": {"type": "string", "description": "Language override (auto-detected)", "required": False},
            },
            returns={"language": {"type": "string"}, "symbols": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="content",
            capabilities=["content.extract_symbols"], tags=["content", "code", "symbols"],
        ),
        ToolContract(
            id="content.list_functions", name="List Functions",
            description="List all function definitions in a code file",
            parameters={
                "path": {"type": "string", "description": "Path to code file"},
                "language": {"type": "string", "description": "Language override", "required": False},
            },
            returns={"language": {"type": "string"}, "functions": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="content",
            capabilities=["content.list_functions"], tags=["content", "code", "functions"],
        ),
        ToolContract(
            id="content.list_classes", name="List Classes",
            description="List all class definitions in a code file",
            parameters={
                "path": {"type": "string", "description": "Path to code file"},
                "language": {"type": "string", "description": "Language override", "required": False},
            },
            returns={"language": {"type": "string"}, "classes": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="content",
            capabilities=["content.list_classes"], tags=["content", "code", "classes"],
        ),
        ToolContract(
            id="content.count_lines", name="Count Lines",
            description="Count lines of code, comments, and blanks in a file or directory",
            parameters={
                "path": {"type": "string", "description": "File or directory path"},
                "include_empty": {"type": "boolean", "description": "Include blank lines", "default": True},
                "include_comments": {"type": "boolean", "description": "Include comment lines", "default": True},
            },
            returns={"summary": {"type": "object"}, "file_count": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="content",
            capabilities=["content.count_lines"], tags=["content", "code", "lines"],
        ),
        ToolContract(
            id="content.detect_language", name="Detect Language",
            description="Detect the programming language of a file or source text",
            parameters={
                "path": {"type": "string", "description": "Path to file", "required": False},
                "source": {"type": "string", "description": "Source code text", "required": False},
            },
            returns={"language": {"type": "string"}, "confidence": {"type": "string"}},
            permission_level=PermissionLevel.READ, category="content",
            capabilities=["content.detect_language"], tags=["content", "code", "detect"],
        ),
    ]

    all_tools = text_tools + search_tools + structured_tools + markdown_tools + code_tools

    text_handlers = [
        _read_text,
        lambda p, eb=event_bus: _write_text(p, eb),
        lambda p, eb=event_bus: _append_text(p, eb),
        lambda p, eb=event_bus: _replace_text(p, eb),
    ]
    search_handlers = [
        _search_text, _search_regex, _search_in_directory,
        lambda p, eb=event_bus: _batch_replace(p, eb),
    ]
    structured_handlers = [
        _read_json,
        lambda p, eb=event_bus: _write_json(p, eb),
        _validate_json, _validate_yaml, _validate_xml,
        _read_csv,
        lambda p, eb=event_bus: _write_csv(p, eb),
    ]
    markdown_handlers = [
        _parse_markdown, _markdown_outline, _extract_links,
    ]
    code_handlers = [
        _search_code, _extract_symbols,
        _list_functions, _list_classes,
        _count_lines, _detect_language,
    ]

    all_handlers = text_handlers + search_handlers + structured_handlers + markdown_handlers + code_handlers

    for contract, handler in zip(all_tools, all_handlers):
        asyncio.create_task(tm.register_tool(contract, handler))
