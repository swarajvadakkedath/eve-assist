"""Unit tests for AIOS Network Toolkit (Phase 5.5)."""

import asyncio
import json
import socket
from pathlib import Path

import pytest

from aios.core.tool_manager import ToolManager, ToolContract, ToolResult
from aios.core.permission_manager import PermissionManager, PermissionLevel
from aios.core.event_bus import EventBus
from aios.tools.network_tools import (
    register_network_tools,
    _build_query,
    _set_headers,
    _bearer_auth,
    _basic_auth,
    _dns_lookup,
    _check_port,
    _validate_url,
    _verify_checksum,
    _cancel_download,
    _download_status,
)


# ── Fixtures ──


@pytest.fixture
def tmp_file(tmp_path: Path) -> Path:
    f = tmp_path / "test.txt"
    f.write_text("hello world")
    return f


@pytest.fixture
def permission_manager() -> PermissionManager:
    return PermissionManager()


@pytest.fixture
def tool_manager(permission_manager) -> ToolManager:
    return ToolManager(permission_manager)


@pytest.fixture
async def event_bus() -> EventBus:
    bus = EventBus(max_retries=1, retry_delay=0.01)
    await bus.start()
    yield bus
    await bus.stop()


@pytest.fixture
async def registered_tools(tool_manager, event_bus, permission_manager):
    register_network_tools(tool_manager, event_bus)
    await asyncio.sleep(0.05)
    # Pre-grant WORKSPACE permissions for download/upload tools
    workspace_tools = [
        "download.file", "upload.file", "upload.multipart",
        "http.post", "http.put", "http.patch", "http.delete",
        "api.send_json", "api.send_form",
    ]
    for tid in workspace_tools:
        result = await permission_manager.request_permission(tid, PermissionLevel.WORKSPACE, action=tid)
        if not result.granted and result.request and result.request.id:
            await permission_manager.grant_permission(result.request.id)
    return tool_manager


@pytest.fixture
async def mock_http_server(event_bus):
    """Run a minimal HTTP server for testing."""
    import httpx

    server = None
    server_task = None
    results = []

    async def handler(reader, writer):
        request = b""
        while b"\r\n\r\n" not in request:
            chunk = await reader.read(4096)
            if not chunk:
                break
            request += chunk
        lines = request.decode("utf-8", errors="replace").split("\r\n")
        method, path, _ = lines[0].split(" ", 2)
        body_start = request.find(b"\r\n\r\n") + 4
        body = request[body_start:].decode("utf-8", errors="replace")

        results.append({"method": method, "path": path, "body": body})

        if path == "/redirect":
            response = (
                "HTTP/1.1 302 Found\r\n"
                "Location: /target\r\n"
                "Content-Length: 0\r\n\r\n"
            )
        elif path == "/target":
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: application/json\r\n"
                "Content-Length: 15\r\n\r\n"
                '{"target": true}'
            )
        elif path == "/json":
            resp_body = '{"status": "ok", "value": 42}'
            response = (
                f"HTTP/1.1 200 OK\r\n"
                f"Content-Type: application/json\r\n"
                f"Content-Length: {len(resp_body)}\r\n\r\n"
                f"{resp_body}"
            )
        elif path == "/post":
            resp_body = json.dumps({"received": body or "{}"})
            response = (
                f"HTTP/1.1 201 Created\r\n"
                f"Content-Type: application/json\r\n"
                f"Content-Length: {len(resp_body)}\r\n\r\n"
                f"{resp_body}"
            )
        elif path == "/download":
            content = b"x" * 1000
            response = (
                f"HTTP/1.1 200 OK\r\n"
                f"Content-Type: application/octet-stream\r\n"
                f"Content-Length: {len(content)}\r\n\r\n"
            ).encode() + content
        else:
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/plain\r\n"
                "Content-Length: 4\r\n\r\n"
                "OK\r\n"
            )
        writer.write(response.encode() if isinstance(response, str) else response)
        await writer.drain()
        writer.close()

    async def run_server():
        nonlocal server
        server = await asyncio.start_server(handler, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        await server.serve_forever()

    server_task = asyncio.create_task(run_server())
    await asyncio.sleep(0.1)
    port = server.sockets[0].getsockname()[1]
    base = f"http://127.0.0.1:{port}"

    yield base, results, port

    server_task.cancel()
    try:
        await server_task
    except (asyncio.CancelledError, OSError):
        pass


# ═══════════════════════════════════════════════════════════════════
# HTTP Tools
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_http_get(registered_tools, mock_http_server):
    base, results, port = mock_http_server
    result = await registered_tools.execute("http.get", {"url": f"{base}/test"})
    assert result.success, result.error
    assert result.data["status_code"] == 200
    assert "body" in result.data


@pytest.mark.asyncio
async def test_http_get_with_timeout(registered_tools, mock_http_server):
    base, results, port = mock_http_server
    result = await registered_tools.execute("http.get", {
        "url": f"{base}/test", "timeout": 5,
    })
    assert result.success


@pytest.mark.asyncio
async def test_http_post(registered_tools, mock_http_server):
    base, results, port = mock_http_server
    result = await registered_tools.execute("http.post", {
        "url": f"{base}/post",
        "json": {"key": "value"},
    })
    assert result.success, result.error
    assert result.data["status_code"] == 201


@pytest.mark.asyncio
async def test_http_put(registered_tools, mock_http_server):
    base, results, port = mock_http_server
    result = await registered_tools.execute("http.put", {
        "url": f"{base}/post",
        "data": {"key": "value"},
    })
    assert result.success, result.error


@pytest.mark.asyncio
async def test_http_patch(registered_tools, mock_http_server):
    base, results, port = mock_http_server
    result = await registered_tools.execute("http.patch", {
        "url": f"{base}/post",
        "json": {"key": "value"},
    })
    assert result.success, result.error


@pytest.mark.asyncio
async def test_http_delete(registered_tools, mock_http_server):
    base, results, port = mock_http_server
    result = await registered_tools.execute("http.delete", {"url": f"{base}/test"})
    assert result.success, result.error


@pytest.mark.asyncio
async def test_http_head(registered_tools, mock_http_server):
    base, results, port = mock_http_server
    result = await registered_tools.execute("http.head", {"url": f"{base}/test"})
    assert result.success, result.error
    assert result.data["status_code"] == 200
    assert "body" not in result.data or not result.data.get("body")


@pytest.mark.asyncio
async def test_http_redirect(registered_tools, mock_http_server):
    base, results, port = mock_http_server
    result = await registered_tools.execute("http.get", {
        "url": f"{base}/redirect",
        "follow_redirects": True,
    })
    assert result.success, result.error
    assert result.data["status_code"] == 200
    assert result.data["redirects"]


@pytest.mark.asyncio
async def test_http_no_redirect(registered_tools, mock_http_server):
    base, results, port = mock_http_server
    result = await registered_tools.execute("http.get", {
        "url": f"{base}/redirect",
        "follow_redirects": False,
    })
    assert result.success
    assert result.data["status_code"] == 302


@pytest.mark.asyncio
async def test_http_error_handling(registered_tools):
    result = await registered_tools.execute("http.get", {"url": "http://192.0.2.1:1"})
    assert not result.success


@pytest.mark.asyncio
async def test_http_missing_url(registered_tools):
    result = await registered_tools.execute("http.get", {})
    assert not result.success


# ═══════════════════════════════════════════════════════════════════
# HTTP with JSON body response
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_http_get_json_response(registered_tools, mock_http_server):
    base, results, port = mock_http_server
    result = await registered_tools.execute("http.get", {"url": f"{base}/json"})
    assert result.success
    body = result.data["body"]
    assert "status" in body
    assert "ok" in body


# ═══════════════════════════════════════════════════════════════════
# Download Tools
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_download_file(registered_tools, mock_http_server, tmp_path):
    base, results, port = mock_http_server
    out = tmp_path / "downloaded.bin"
    result = await registered_tools.execute("download.file", {
        "url": f"{base}/download",
        "output": str(out),
    })
    assert result.success, result.error
    dl_id = result.data["download_id"]
    assert result.data["status"] == "downloading"

    await asyncio.sleep(0.5)

    status_result = await registered_tools.execute("download.status", {"download_id": dl_id})
    assert status_result.success
    assert status_result.data["status"] in ("completed", "downloading")


@pytest.mark.asyncio
async def test_cancel_download(registered_tools, mock_http_server, tmp_path):
    base, results, port = mock_http_server
    out = tmp_path / "cancel_test.bin"
    result = await registered_tools.execute("download.file", {
        "url": f"{base}/download",
        "output": str(out),
    })
    assert result.success
    dl_id = result.data["download_id"]

    cancel_result = await registered_tools.execute("download.cancel", {"download_id": dl_id})
    assert cancel_result.success
    assert cancel_result.data["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_download_not_found(registered_tools):
    result = await registered_tools.execute("download.cancel", {"download_id": "nonexistent"})
    assert not result.success


@pytest.mark.asyncio
async def test_download_status_not_found(registered_tools):
    result = await registered_tools.execute("download.status", {"download_id": "nonexistent"})
    assert not result.success


# ═══════════════════════════════════════════════════════════════════
# Verify Checksum
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_verify_checksum_match(tmp_file):
    import hashlib
    h = hashlib.sha256(tmp_file.read_bytes()).hexdigest()
    result = await _verify_checksum({
        "path": str(tmp_file),
        "algorithm": "sha256",
        "expected": h,
    })
    assert result.success
    assert result.data["match"] is True


@pytest.mark.asyncio
async def test_verify_checksum_mismatch(tmp_file):
    result = await _verify_checksum({
        "path": str(tmp_file),
        "algorithm": "sha256",
        "expected": "0000000000000000000000000000000000000000000000000000000000000000",
    })
    assert result.success
    assert result.data["match"] is False


@pytest.mark.asyncio
async def test_verify_checksum_not_found():
    result = await _verify_checksum({
        "path": "/nonexistent/file",
        "algorithm": "sha256",
        "expected": "0" * 64,
    })
    assert not result.success


@pytest.mark.asyncio
async def test_verify_checksum_no_expected(tmp_file):
    result = await _verify_checksum({
        "path": str(tmp_file),
        "algorithm": "sha256",
        "expected": "",
    })
    assert not result.success


@pytest.mark.asyncio
async def test_verify_checksum_md5(tmp_file):
    import hashlib
    h = hashlib.md5(tmp_file.read_bytes()).hexdigest()
    result = await _verify_checksum({
        "path": str(tmp_file),
        "algorithm": "md5",
        "expected": h,
    })
    assert result.success
    assert result.data["match"] is True


# ═══════════════════════════════════════════════════════════════════
# Upload Tools
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_upload_file_not_found(registered_tools):
    result = await registered_tools.execute("upload.file", {
        "url": "http://example.com/upload",
        "file_path": "/nonexistent/file.txt",
    })
    assert not result.success


@pytest.mark.asyncio
async def test_upload_multipart_not_found(registered_tools):
    result = await registered_tools.execute("upload.multipart", {
        "url": "http://example.com/upload",
        "files": ["/nonexistent/file.txt"],
    })
    assert not result.success


# ═══════════════════════════════════════════════════════════════════
# API Tools
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_build_query():
    result = await _build_query({
        "base_url": "https://api.example.com/search",
        "params": {"q": "hello", "page": "1", "limit": 10},
    })
    assert result.success
    assert "q=hello" in result.data["url"]
    assert "page=1" in result.data["url"]
    assert "limit=10" in result.data["url"]


@pytest.mark.asyncio
async def test_build_query_no_params():
    result = await _build_query({
        "base_url": "https://api.example.com/search",
        "params": {},
    })
    assert result.success
    assert result.data["url"] == "https://api.example.com/search"


@pytest.mark.asyncio
async def test_build_query_multiple_values():
    result = await _build_query({
        "base_url": "https://api.example.com/filter",
        "params": {"tag": ["a", "b", "c"]},
    })
    assert result.success
    assert "tag=a" in result.data["url"]
    assert "tag=b" in result.data["url"]
    assert "tag=c" in result.data["url"]


@pytest.mark.asyncio
async def test_build_query_empty_base():
    result = await _build_query({
        "base_url": "",
        "params": {"key": "val"},
    })
    assert result.success


@pytest.mark.asyncio
async def test_set_headers():
    result = await _set_headers({
        "headers": {"X-Custom": "value", "Accept": "application/json"},
    })
    assert result.success
    assert result.data["count"] == 2


@pytest.mark.asyncio
async def test_set_headers_clear():
    await _set_headers({"headers": {"X-Temp": "val"}})
    result = await _set_headers({"headers": {}, "mode": "clear"})
    assert result.success
    assert result.data["count"] == 0


@pytest.mark.asyncio
async def test_set_headers_merge():
    await _set_headers({"headers": {"X-Existing": "yes"}})
    result = await _set_headers({"headers": {"X-New": "added"}, "mode": "merge"})
    assert result.success
    assert result.data["count"] >= 2


@pytest.mark.asyncio
async def test_bearer_auth():
    result = await _bearer_auth({"token": "my-token-123"})
    assert result.success
    assert result.data["token_set"] is True


@pytest.mark.asyncio
async def test_bearer_auth_no_token():
    result = await _bearer_auth({"token": ""})
    assert not result.success


@pytest.mark.asyncio
async def test_basic_auth():
    result = await _basic_auth({"username": "user", "password": "pass"})
    assert result.success
    assert result.data["authenticated"] is True


@pytest.mark.asyncio
async def test_basic_auth_no_username():
    result = await _basic_auth({"username": "", "password": ""})
    assert result.success
    assert result.data["authenticated"] is False


# ═══════════════════════════════════════════════════════════════════
# API send_json / send_form
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_send_json(registered_tools, mock_http_server):
    base, results, port = mock_http_server
    result = await registered_tools.execute("api.send_json", {
        "url": f"{base}/post",
        "data": {"hello": "world"},
        "method": "POST",
    })
    assert result.success, result.error


@pytest.mark.asyncio
async def test_send_form(registered_tools, mock_http_server):
    base, results, port = mock_http_server
    result = await registered_tools.execute("api.send_form", {
        "url": f"{base}/post",
        "data": {"field1": "value1", "field2": "value2"},
        "method": "POST",
    })
    assert result.success, result.error


# ═══════════════════════════════════════════════════════════════════
# Network / Diagnostics Tools
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_dns_lookup():
    result = await _dns_lookup({"hostname": "localhost"})
    assert result.success, result.error
    assert result.data["count"] >= 1
    assert any("127.0.0.1" in addr["address"] for addr in result.data["addresses"])


@pytest.mark.asyncio
async def test_dns_lookup_no_hostname():
    result = await _dns_lookup({"hostname": ""})
    assert not result.success


@pytest.mark.asyncio
async def test_dns_lookup_invalid():
    result = await _dns_lookup({"hostname": "invalid-hostname-xyz-12345.local"})
    assert not result.success


@pytest.mark.asyncio
async def test_ping_host_localhost(registered_tools):
    """Use registered_tools to test ping (falls through to execute)."""
    result = await registered_tools.execute("network.ping_host", {
        "hostname": "127.0.0.1",
        "count": 1,
        "timeout": 10,
    })
    assert result.success, result.error


@pytest.mark.asyncio
async def test_ping_host_no_hostname(registered_tools):
    result = await registered_tools.execute("network.ping_host", {"hostname": ""})
    assert not result.success


@pytest.mark.asyncio
async def test_check_port_open(mock_http_server):
    base, results, port = mock_http_server
    result = await _check_port({"hostname": "127.0.0.1", "port": port})
    assert result.success, result.error
    assert result.data["open"] is True


@pytest.mark.asyncio
async def test_check_port_closed():
    result = await _check_port({"hostname": "127.0.0.1", "port": 19999})
    assert result.success
    assert result.data["open"] is False


@pytest.mark.asyncio
async def test_check_port_no_hostname():
    result = await _check_port({"hostname": "", "port": 80})
    assert not result.success


@pytest.mark.asyncio
async def test_check_port_no_port():
    result = await _check_port({"hostname": "127.0.0.1", "port": 0})
    assert not result.success


@pytest.mark.asyncio
async def test_validate_url_valid():
    result = await _validate_url({"url": "https://api.example.com/v1/users?page=1#top"})
    assert result.success
    assert result.data["valid"] is True
    assert result.data["scheme"] == "https"
    assert result.data["hostname"] == "api.example.com"


@pytest.mark.asyncio
async def test_validate_url_no_scheme():
    result = await _validate_url({"url": "example.com/path"})
    assert result.success
    assert result.data["valid"] is False
    assert "Missing scheme" in result.data["issues"]


@pytest.mark.asyncio
async def test_validate_url_no_hostname():
    result = await _validate_url({"url": "http:///path"})
    assert result.success
    assert result.data["valid"] is False


@pytest.mark.asyncio
async def test_validate_url_empty():
    result = await _validate_url({"url": ""})
    assert not result.success


@pytest.mark.asyncio
async def test_validate_url_file_scheme():
    result = await _validate_url({"url": "file:///etc/hosts"})
    assert result.success
    assert result.data["valid"] is True


# ═══════════════════════════════════════════════════════════════════
# Registration & Permissions
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_register_network_tools(registered_tools):
    tools = await registered_tools.list_tools()
    network_tools = [t for t in tools if t.category == "network"]
    assert len(network_tools) >= 22


@pytest.mark.asyncio
async def test_network_tool_ids_unique(registered_tools):
    tools = await registered_tools.list_tools()
    network_ids = [t.id for t in tools if t.category == "network"]
    assert len(network_ids) == len(set(network_ids))


@pytest.mark.asyncio
async def test_network_tools_have_permission_levels(registered_tools):
    tools = await registered_tools.list_tools()
    network_tools = [t for t in tools if t.category == "network"]
    for t in network_tools:
        assert t.permission_level is not None


@pytest.mark.asyncio
async def test_write_network_tools_require_confirmation(registered_tools):
    tools = await registered_tools.list_tools()
    tools_with_confirm = [t for t in tools if t.category == "network" and t.requires_confirmation]
    write_ops = {"http.post", "http.put", "http.patch", "http.delete",
                 "download.file", "upload.file", "upload.multipart",
                 "api.send_json", "api.send_form"}
    confirmed_ids = {t.id for t in tools_with_confirm}
    for tid in write_ops:
        assert tid in confirmed_ids, f"{tid} should require confirmation"


@pytest.mark.asyncio
async def test_read_network_tools_no_confirmation(registered_tools):
    tools = await registered_tools.list_tools()
    tools_no_confirm = [t for t in tools if t.category == "network" and not t.requires_confirmation]
    read_ops = {"http.get", "http.head", "download.cancel", "download.status",
                "network.verify_checksum", "api.build_query", "api.set_headers",
                "api.bearer_auth", "api.basic_auth", "network.dns_lookup",
                "network.ping_host", "network.check_port", "network.validate_url"}
    no_confirm_ids = {t.id for t in tools_no_confirm}
    for tid in read_ops:
        assert tid in no_confirm_ids, f"{tid} should NOT require confirmation"


# ═══════════════════════════════════════════════════════════════════
# Cancellation edge cases
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_cancel_already_cancelled_download(registered_tools, mock_http_server, tmp_path):
    base, results, port = mock_http_server
    out = tmp_path / "already_cancelled.bin"
    result = await registered_tools.execute("download.file", {
        "url": f"{base}/download",
        "output": str(out),
    })
    assert result.success
    dl_id = result.data["download_id"]

    await registered_tools.execute("download.cancel", {"download_id": dl_id})
    cancel_again = await registered_tools.execute("download.cancel", {"download_id": dl_id})
    assert cancel_again.success
    assert "already" in cancel_again.data.get("message", "").lower() or cancel_again.data["status"] == "cancelled"


# ═══════════════════════════════════════════════════════════════════
# Event Bus publishing (indirect check via registered tools)
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_http_event_published(registered_tools, mock_http_server, event_bus):
    base, results, port = mock_http_server
    events = []
    await event_bus.subscribe("http:get", lambda e: events.append(e))

    await registered_tools.execute("http.get", {"url": f"{base}/event-check"})
    await asyncio.sleep(0.1)
    assert len(events) >= 1, "Expected http:get event to be published"


@pytest.mark.asyncio
async def test_download_event_published(registered_tools, mock_http_server, event_bus, tmp_path):
    base, results, port = mock_http_server
    events = []
    await event_bus.subscribe("download:started", lambda e: events.append(e))

    out = tmp_path / "event_download.bin"
    await registered_tools.execute("download.file", {
        "url": f"{base}/download",
        "output": str(out),
    })
    await asyncio.sleep(0.2)
    assert len(events) >= 1, "Expected download:started event to be published"
