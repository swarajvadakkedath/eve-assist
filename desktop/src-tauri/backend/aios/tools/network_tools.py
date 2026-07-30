"""Network Toolkit — HTTP, Downloads, Uploads, API helpers, Diagnostics for AIOS Phase 5.5."""

import asyncio
import hashlib
import socket
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aios.core.tool_manager import ToolResult
from aios.core.event_bus import EventBus


# ── State ──

@dataclass
class DownloadState:
    url: str
    path: str
    status: str  # downloading | completed | failed | cancelled
    progress: float = 0.0
    total_bytes: int = 0
    downloaded_bytes: int = 0
    error: str | None = None
    task: asyncio.Task | None = None
    _cancel_event: asyncio.Event = field(default_factory=asyncio.Event)


_active_downloads: dict[str, DownloadState] = {}
_session_headers: dict[str, str] = {}
_session_auth: tuple[str, str] | None = None
_download_id_counter: int = 0


def _next_download_id() -> str:
    global _download_id_counter
    _download_id_counter += 1
    return f"dl_{_download_id_counter}"


def _build_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = dict(_session_headers)
    if _session_auth:
        import base64
        token = base64.b64encode(f"{_session_auth[0]}:{_session_auth[1]}".encode()).decode()
        headers.setdefault("Authorization", f"Basic {token}")
    if extra:
        headers.update(extra)
    return headers


def _prepare_httpx_args(method: str, params: dict) -> dict:
    url = params["url"]
    timeout_val = params.get("timeout", 30)
    follow_redirects = params.get("follow_redirects", True)
    headers = _build_headers(params.get("headers") or {})
    kwargs: dict[str, Any] = {
        "method": method,
        "url": url,
        "headers": headers,
        "follow_redirects": follow_redirects,
    }
    if method in ("POST", "PUT", "PATCH"):
        data = params.get("data")
        json_data = params.get("json")
        if json_data is not None:
            kwargs["json"] = json_data
        elif data is not None:
            kwargs["data"] = data
    kwargs["timeout"] = timeout_val
    return kwargs


async def _execute_http(method: str, params: dict, event_bus: EventBus | None = None) -> ToolResult:
    try:
        import httpx
        kwargs = _prepare_httpx_args(method, params)
        async with httpx.AsyncClient() as client:
            response = await client.request(**kwargs)
        result_data = {
            "url": params["url"],
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.text,
            "elapsed_ms": round(response.elapsed.total_seconds() * 1000, 2),
            "redirects": [str(r.url) for r in response.history] if response.history else [],
            "encoding": response.encoding,
        }
        if event_bus:
            await event_bus.publish(
                f"http:{method.lower()}",
                {"url": params["url"], "status_code": response.status_code},
                source="network_tools",
            )
        return ToolResult(success=True, data=result_data)
    except ImportError:
        return ToolResult(success=False, error="httpx is not installed")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── HTTP Tools ──


async def _http_get(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    return await _execute_http("GET", params, event_bus)


async def _http_post(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    return await _execute_http("POST", params, event_bus)


async def _http_put(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    return await _execute_http("PUT", params, event_bus)


async def _http_patch(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    return await _execute_http("PATCH", params, event_bus)


async def _http_delete(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    return await _execute_http("DELETE", params, event_bus)


async def _http_head(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    try:
        import httpx
        kwargs = _prepare_httpx_args("HEAD", params)
        async with httpx.AsyncClient() as client:
            response = await client.request(**kwargs)
        result_data = {
            "url": params["url"],
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "elapsed_ms": round(response.elapsed.total_seconds() * 1000, 2),
            "encoding": response.encoding,
        }
        if event_bus:
            await event_bus.publish(
                "http:head",
                {"url": params["url"], "status_code": response.status_code},
                source="network_tools",
            )
        return ToolResult(success=True, data=result_data)
    except ImportError:
        return ToolResult(success=False, error="httpx is not installed")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Download Tools ──


async def _download_file(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    try:
        import httpx
        url = params["url"]
        output = Path(params.get("output", ""))
        timeout_val = params.get("timeout", 300)

        if not output:
            output = Path(url.split("/")[-1].split("?")[0] or "download")
        output.parent.mkdir(parents=True, exist_ok=True)

        dl_id = _next_download_id()
        state = DownloadState(url=url, path=str(output), status="downloading")
        _active_downloads[dl_id] = state

        async def _do_download():
            try:
                headers = _build_headers()
                async with httpx.AsyncClient(timeout=timeout_val) as client:
                    async with client.stream("GET", url, headers=headers, follow_redirects=True) as resp:
                        resp.raise_for_status()
                        state.total_bytes = int(resp.headers.get("content-length", 0))
                        with open(output, "wb") as f:
                            async for chunk in resp.aiter_bytes():
                                if state._cancel_event.is_set():
                                    state.status = "cancelled"
                                    output.unlink(missing_ok=True)
                                    return
                                f.write(chunk)
                                state.downloaded_bytes += len(chunk)
                                if state.total_bytes:
                                    state.progress = min(state.downloaded_bytes / state.total_bytes, 1.0)
                state.status = "completed" if state.status == "downloading" else state.status
                state.progress = 1.0
                state.downloaded_bytes = output.stat().st_size
                state.total_bytes = state.downloaded_bytes
            except Exception as e:
                state.status = "failed"
                state.error = str(e)
                output.unlink(missing_ok=True)

        state.task = asyncio.create_task(_do_download())
        await asyncio.sleep(0)

        if event_bus:
            await event_bus.publish(
                "download:started",
                {"download_id": dl_id, "url": url, "output": str(output)},
                source="network_tools",
            )

        return ToolResult(success=True, data={
            "download_id": dl_id,
            "url": url,
            "output": str(output),
            "status": "downloading",
        })
    except ImportError:
        return ToolResult(success=False, error="httpx is not installed")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _cancel_download(params: dict) -> ToolResult:
    dl_id = params.get("download_id", "")
    state = _active_downloads.get(dl_id)
    if not state:
        return ToolResult(success=False, error=f"Download not found: {dl_id}")
    if state.status != "downloading":
        return ToolResult(success=True, data={
            "download_id": dl_id, "status": state.status,
            "message": f"Download is already {state.status}",
        })
    state._cancel_event.set()
    if state.task:
        state.task.cancel()
    state.status = "cancelled"
    return ToolResult(success=True, data={
        "download_id": dl_id, "status": "cancelled",
    })


async def _download_status(params: dict) -> ToolResult:
    dl_id = params.get("download_id", "")
    state = _active_downloads.get(dl_id)
    if not state:
        return ToolResult(success=False, error=f"Download not found: {dl_id}")
    return ToolResult(success=True, data={
        "download_id": dl_id,
        "url": state.url,
        "output": state.path,
        "status": state.status,
        "progress": state.progress,
        "downloaded_bytes": state.downloaded_bytes,
        "total_bytes": state.total_bytes,
        "error": state.error,
    })


async def _verify_checksum(params: dict) -> ToolResult:
    path = Path(params["path"])
    algorithm = params.get("algorithm", "sha256")
    expected = params.get("expected", "")

    if not path.exists():
        return ToolResult(success=False, error=f"File not found: {path}")
    if not expected:
        return ToolResult(success=False, error="No expected hash provided")

    try:
        h = hashlib.new(algorithm)
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        actual = h.hexdigest()
        match = actual.lower() == expected.lower()
        return ToolResult(success=True, data={
            "path": str(path),
            "algorithm": algorithm,
            "expected": expected,
            "actual": actual,
            "match": match,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Upload Tools ──


async def _upload_file(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    try:
        import httpx
        url = params["url"]
        file_path = Path(params["file_path"])
        field_name = params.get("field_name", "file")
        timeout_val = params.get("timeout", 300)

        if not file_path.exists():
            return ToolResult(success=False, error=f"File not found: {file_path}")

        headers = _build_headers(params.get("headers") or {})
        async with httpx.AsyncClient(timeout=timeout_val) as client:
            with open(file_path, "rb") as f:
                response = await client.post(url, files={field_name: (file_path.name, f)}, headers=headers)

        if event_bus:
            await event_bus.publish(
                "upload:file",
                {"url": url, "file": str(file_path), "status_code": response.status_code},
                source="network_tools",
            )

        return ToolResult(success=True, data={
            "url": url,
            "file": str(file_path),
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.text,
            "elapsed_ms": round(response.elapsed.total_seconds() * 1000, 2),
        })
    except ImportError:
        return ToolResult(success=False, error="httpx is not installed")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _upload_multipart(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    try:
        import httpx
        url = params["url"]
        files_param = params.get("files", [])
        data = params.get("data", {})
        timeout_val = params.get("timeout", 300)

        files = {}
        for fp in files_param:
            p = Path(fp)
            if not p.exists():
                return ToolResult(success=False, error=f"File not found: {p}")
            files[p.name] = (p.name, open(p, "rb"))

        headers = _build_headers(params.get("headers") or {})
        try:
            async with httpx.AsyncClient(timeout=timeout_val) as client:
                response = await client.post(url, files=files, data=data, headers=headers)
        finally:
            for f in files.values():
                f[1].close()

        if event_bus:
            await event_bus.publish(
                "upload:multipart",
                {"url": url, "files": list(files.keys()), "status_code": response.status_code},
                source="network_tools",
            )

        return ToolResult(success=True, data={
            "url": url,
            "files": list(files.keys()),
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.text,
            "elapsed_ms": round(response.elapsed.total_seconds() * 1000, 2),
        })
    except ImportError:
        return ToolResult(success=False, error="httpx is not installed")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── API Tools ──


async def _send_json(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    try:
        import httpx
        url = params["url"]
        json_data = params.get("data", {})
        method = params.get("method", "POST").upper()
        timeout_val = params.get("timeout", 30)

        headers = _build_headers(params.get("headers") or {})
        headers.setdefault("Content-Type", "application/json")

        async with httpx.AsyncClient(timeout=timeout_val) as client:
            response = await client.request(method, url, json=json_data, headers=headers, follow_redirects=True)

        body = response.text
        try:
            body = response.json()
        except Exception:
            pass

        if event_bus:
            await event_bus.publish(
                "api:json",
                {"url": url, "method": method, "status_code": response.status_code},
                source="network_tools",
            )

        return ToolResult(success=True, data={
            "url": url,
            "method": method,
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": body,
            "elapsed_ms": round(response.elapsed.total_seconds() * 1000, 2),
        })
    except ImportError:
        return ToolResult(success=False, error="httpx is not installed")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _send_form(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    try:
        import httpx
        url = params["url"]
        form_data = params.get("data", {})
        method = params.get("method", "POST").upper()
        timeout_val = params.get("timeout", 30)

        headers = _build_headers(params.get("headers") or {})

        async with httpx.AsyncClient(timeout=timeout_val) as client:
            response = await client.request(method, url, data=form_data, headers=headers, follow_redirects=True)

        if event_bus:
            await event_bus.publish(
                "api:form",
                {"url": url, "method": method, "status_code": response.status_code},
                source="network_tools",
            )

        return ToolResult(success=True, data={
            "url": url,
            "method": method,
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.text,
            "elapsed_ms": round(response.elapsed.total_seconds() * 1000, 2),
        })
    except ImportError:
        return ToolResult(success=False, error="httpx is not installed")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _build_query(params: dict) -> ToolResult:
    base_url = params.get("base_url", "")
    query_params = params.get("params", {})
    try:
        parsed = urllib.parse.urlparse(base_url)
        existing = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        for k, v in query_params.items():
            if isinstance(v, list):
                existing[k] = [str(x) for x in v]
            else:
                existing[k] = [str(v)]
        new_query = urllib.parse.urlencode(existing, doseq=True)
        result_url = urllib.parse.ParseResult(
            parsed.scheme, parsed.netloc, parsed.path,
            parsed.params, new_query, parsed.fragment
        ).geturl()
        return ToolResult(success=True, data={
            "url": result_url,
            "params": {k: v[0] if len(v) == 1 else v for k, v in existing.items()},
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _set_headers(params: dict) -> ToolResult:
    headers = params.get("headers", {})
    mode = params.get("mode", "set")
    if mode == "clear":
        _session_headers.clear()
        return ToolResult(success=True, data={"headers": {}, "mode": "clear", "count": 0})
    if mode == "set":
        _session_headers.clear()
    _session_headers.update(headers)
    return ToolResult(success=True, data={
        "headers": dict(_session_headers),
        "mode": mode,
        "count": len(_session_headers),
    })


async def _bearer_auth(params: dict) -> ToolResult:
    token = params.get("token", "")
    if not token:
        return ToolResult(success=False, error="No token provided")
    _session_headers["Authorization"] = f"Bearer {token}"
    return ToolResult(success=True, data={
        "scheme": "Bearer",
        "token_set": bool(token),
    })


async def _basic_auth(params: dict) -> ToolResult:
    username = params.get("username", "")
    password = params.get("password", "")
    global _session_auth
    _session_auth = (username, password)
    import base64
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    _session_headers["Authorization"] = f"Basic {token}"
    return ToolResult(success=True, data={
        "scheme": "Basic",
        "username": username,
        "authenticated": bool(username),
    })


# ── Network / Diagnostics Tools ──


async def _dns_lookup(params: dict) -> ToolResult:
    hostname = params.get("hostname", "")
    if not hostname:
        return ToolResult(success=False, error="No hostname provided")
    try:
        start = datetime.now(timezone.utc)
        info = socket.getaddrinfo(hostname, None)
        elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        addresses = set()
        family_map = {socket.AF_INET: "IPv4", socket.AF_INET6: "IPv6"}
        for addr in info:
            family = family_map.get(addr[0], f"AF_{addr[0]}")
            ip = addr[4][0]
            addresses.add((family, ip))
        return ToolResult(success=True, data={
            "hostname": hostname,
            "addresses": [{"family": f, "address": ip} for f, ip in sorted(addresses)],
            "count": len(addresses),
            "elapsed_ms": round(elapsed, 2),
        })
    except socket.gaierror as e:
        return ToolResult(success=False, error=f"DNS lookup failed: {e}")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _ping_host(params: dict) -> ToolResult:
    hostname = params.get("hostname", "")
    count = params.get("count", 4)
    timeout_val = params.get("timeout", 10)
    if not hostname:
        return ToolResult(success=False, error="No hostname provided")
    try:
        import subprocess
        import platform
        system = platform.system().lower()
        if system == "windows":
            cmd = ["ping", "-n", str(count), hostname]
        else:
            cmd = ["ping", "-c", str(count), hostname]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_val)
        except asyncio.TimeoutError:
            proc.kill()
            return ToolResult(success=False, error="Ping timed out")

        output = stdout.decode("utf-8", errors="replace")
        success = proc.returncode == 0
        return ToolResult(success=True, data={
            "hostname": hostname,
            "success": success,
            "packets_sent": count,
            "return_code": proc.returncode,
            "output": output,
            "system": system,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _check_port(params: dict) -> ToolResult:
    hostname = params.get("hostname", "")
    port = params.get("port", 0)
    timeout_val = params.get("timeout", 5)
    if not hostname:
        return ToolResult(success=False, error="No hostname provided")
    if not port:
        return ToolResult(success=False, error="No port provided")
    try:
        start = datetime.now(timezone.utc)
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(hostname, port),
            timeout=timeout_val,
        )
        elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        writer.close()
        await writer.wait_closed()
        return ToolResult(success=True, data={
            "hostname": hostname,
            "port": port,
            "open": True,
            "elapsed_ms": round(elapsed, 2),
        })
    except (ConnectionRefusedError, ConnectionError, OSError):
        return ToolResult(success=True, data={
            "hostname": hostname,
            "port": port,
            "open": False,
        })
    except asyncio.TimeoutError:
        return ToolResult(success=True, data={
            "hostname": hostname,
            "port": port,
            "open": False,
            "error": "Connection timed out",
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _validate_url(params: dict) -> ToolResult:
    url = params.get("url", "")
    if not url:
        return ToolResult(success=False, error="No URL provided")
    try:
        parsed = urllib.parse.urlparse(url)
        valid_schemes = {"http", "https", "ftp", "sftp", "file", "data"}
        issues = []
        if not parsed.scheme:
            issues.append("Missing scheme")
        elif parsed.scheme not in valid_schemes:
            issues.append(f"Unrecognized scheme: {parsed.scheme}")
        if not parsed.netloc and parsed.scheme not in ("file", "data"):
            issues.append("Missing hostname")
        if parsed.scheme in ("http", "https") and not parsed.netloc:
            issues.append("HTTP/HTTPS URLs require a hostname")
        return ToolResult(success=True, data={
            "url": url,
            "valid": len(issues) == 0,
            "scheme": parsed.scheme,
            "hostname": parsed.hostname,
            "port": parsed.port,
            "path": parsed.path,
            "query": parsed.query,
            "fragment": parsed.fragment,
            "issues": issues,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Registration ──

def register_network_tools(tm, event_bus=None):
    import asyncio
    from aios.core.tool_manager import ToolContract
    from aios.core.permission_manager import PermissionLevel

    http_read_tools = [
        ToolContract(
            id="http.get", name="HTTP GET",
            description="Perform an HTTP GET request",
            parameters={
                "url": {"type": "string", "description": "Target URL"},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
                "follow_redirects": {"type": "boolean", "description": "Follow redirects", "default": True},
                "headers": {"type": "object", "description": "Additional headers", "required": False},
            },
            returns={"url": {"type": "string"}, "status_code": {"type": "integer"}, "body": {"type": "string"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=False, category="network",
            capabilities=["http.get"], tags=["http", "get"],
        ),
        ToolContract(
            id="http.head", name="HTTP HEAD",
            description="Perform an HTTP HEAD request (headers only)",
            parameters={
                "url": {"type": "string", "description": "Target URL"},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
                "follow_redirects": {"type": "boolean", "description": "Follow redirects", "default": True},
                "headers": {"type": "object", "description": "Additional headers", "required": False},
            },
            returns={"url": {"type": "string"}, "status_code": {"type": "integer"}, "headers": {"type": "object"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=False, category="network",
            capabilities=["http.head"], tags=["http", "head"],
        ),
        ToolContract(
            id="http.post", name="HTTP POST",
            description="Perform an HTTP POST request (requires confirmation)",
            parameters={
                "url": {"type": "string", "description": "Target URL"},
                "data": {"type": "object", "description": "Form data", "required": False},
                "json": {"type": "object", "description": "JSON body", "required": False},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
                "follow_redirects": {"type": "boolean", "description": "Follow redirects", "default": True},
                "headers": {"type": "object", "description": "Additional headers", "required": False},
            },
            returns={"url": {"type": "string"}, "status_code": {"type": "integer"}, "body": {"type": "string"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=True, category="network",
            capabilities=["http.post"], tags=["http", "post"],
        ),
        ToolContract(
            id="http.put", name="HTTP PUT",
            description="Perform an HTTP PUT request (requires confirmation)",
            parameters={
                "url": {"type": "string", "description": "Target URL"},
                "data": {"type": "object", "description": "Form data", "required": False},
                "json": {"type": "object", "description": "JSON body", "required": False},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
                "follow_redirects": {"type": "boolean", "description": "Follow redirects", "default": True},
                "headers": {"type": "object", "description": "Additional headers", "required": False},
            },
            returns={"url": {"type": "string"}, "status_code": {"type": "integer"}, "body": {"type": "string"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=True, category="network",
            capabilities=["http.put"], tags=["http", "put"],
        ),
        ToolContract(
            id="http.patch", name="HTTP PATCH",
            description="Perform an HTTP PATCH request (requires confirmation)",
            parameters={
                "url": {"type": "string", "description": "Target URL"},
                "data": {"type": "object", "description": "Form data", "required": False},
                "json": {"type": "object", "description": "JSON body", "required": False},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
                "follow_redirects": {"type": "boolean", "description": "Follow redirects", "default": True},
                "headers": {"type": "object", "description": "Additional headers", "required": False},
            },
            returns={"url": {"type": "string"}, "status_code": {"type": "integer"}, "body": {"type": "string"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=True, category="network",
            capabilities=["http.patch"], tags=["http", "patch"],
        ),
        ToolContract(
            id="http.delete", name="HTTP DELETE",
            description="Perform an HTTP DELETE request (requires confirmation)",
            parameters={
                "url": {"type": "string", "description": "Target URL"},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
                "follow_redirects": {"type": "boolean", "description": "Follow redirects", "default": True},
                "headers": {"type": "object", "description": "Additional headers", "required": False},
            },
            returns={"url": {"type": "string"}, "status_code": {"type": "integer"}, "body": {"type": "string"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=True, category="network",
            capabilities=["http.delete"], tags=["http", "delete"],
        ),
    ]

    download_tools = [
        ToolContract(
            id="download.file", name="Download File",
            description="Download a file from a URL to local storage (requires confirmation)",
            parameters={
                "url": {"type": "string", "description": "Download URL"},
                "output": {"type": "string", "description": "Output file path", "required": False},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 300},
            },
            returns={"download_id": {"type": "string"}, "url": {"type": "string"}, "output": {"type": "string"}, "status": {"type": "string"}},
            permission_level=PermissionLevel.WORKSPACE, requires_confirmation=True, category="network",
            capabilities=["download.file"], tags=["download", "file"],
        ),
        ToolContract(
            id="download.cancel", name="Cancel Download",
            description="Cancel an active download",
            parameters={
                "download_id": {"type": "string", "description": "Download ID to cancel"},
            },
            returns={"download_id": {"type": "string"}, "status": {"type": "string"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=False, category="network",
            capabilities=["download.cancel"], tags=["download", "cancel"],
        ),
        ToolContract(
            id="download.status", name="Download Status",
            description="Check the status and progress of a download",
            parameters={
                "download_id": {"type": "string", "description": "Download ID"},
            },
            returns={"download_id": {"type": "string"}, "status": {"type": "string"}, "progress": {"type": "number"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=False, category="network",
            capabilities=["download.status"], tags=["download", "status"],
        ),
        ToolContract(
            id="network.verify_checksum", name="Verify Checksum",
            description="Verify a file's cryptographic checksum against an expected value",
            parameters={
                "path": {"type": "string", "description": "File path"},
                "algorithm": {"type": "string", "description": "Hash algorithm (sha256, md5, sha1)", "default": "sha256"},
                "expected": {"type": "string", "description": "Expected hash value"},
            },
            returns={"path": {"type": "string"}, "algorithm": {"type": "string"}, "match": {"type": "boolean"}},
            permission_level=PermissionLevel.READ, requires_confirmation=False, category="network",
            capabilities=["network.verify_checksum"], tags=["verify", "checksum", "hash"],
        ),
    ]

    upload_tools = [
        ToolContract(
            id="upload.file", name="Upload File",
            description="Upload a single file via HTTP POST (requires confirmation)",
            parameters={
                "url": {"type": "string", "description": "Upload URL"},
                "file_path": {"type": "string", "description": "Path to file to upload"},
                "field_name": {"type": "string", "description": "Form field name", "default": "file"},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 300},
                "headers": {"type": "object", "description": "Additional headers", "required": False},
            },
            returns={"url": {"type": "string"}, "status_code": {"type": "integer"}, "body": {"type": "string"}},
            permission_level=PermissionLevel.WORKSPACE, requires_confirmation=True, category="network",
            capabilities=["upload.file"], tags=["upload", "file"],
        ),
        ToolContract(
            id="upload.multipart", name="Upload Multipart",
            description="Upload multiple files as multipart form data (requires confirmation)",
            parameters={
                "url": {"type": "string", "description": "Upload URL"},
                "files": {"type": "array", "description": "List of file paths to upload"},
                "data": {"type": "object", "description": "Additional form fields", "default": {}},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 300},
                "headers": {"type": "object", "description": "Additional headers", "required": False},
            },
            returns={"url": {"type": "string"}, "status_code": {"type": "integer"}, "body": {"type": "string"}},
            permission_level=PermissionLevel.WORKSPACE, requires_confirmation=True, category="network",
            capabilities=["upload.multipart"], tags=["upload", "multipart"],
        ),
    ]

    api_tools = [
        ToolContract(
            id="api.send_json", name="Send JSON",
            description="Send a JSON payload via HTTP (requires confirmation)",
            parameters={
                "url": {"type": "string", "description": "Target URL"},
                "data": {"type": "object", "description": "JSON-serializable data"},
                "method": {"type": "string", "description": "HTTP method (POST, PUT, PATCH, GET)", "default": "POST"},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
                "headers": {"type": "object", "description": "Additional headers", "required": False},
            },
            returns={"url": {"type": "string"}, "status_code": {"type": "integer"}, "body": {"type": "object"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=True, category="network",
            capabilities=["api.send_json"], tags=["api", "json"],
        ),
        ToolContract(
            id="api.send_form", name="Send Form",
            description="Send form-urlencoded data via HTTP (requires confirmation)",
            parameters={
                "url": {"type": "string", "description": "Target URL"},
                "data": {"type": "object", "description": "Form data"},
                "method": {"type": "string", "description": "HTTP method (POST, PUT)", "default": "POST"},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
                "headers": {"type": "object", "description": "Additional headers", "required": False},
            },
            returns={"url": {"type": "string"}, "status_code": {"type": "integer"}, "body": {"type": "string"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=True, category="network",
            capabilities=["api.send_form"], tags=["api", "form"],
        ),
        ToolContract(
            id="api.build_query", name="Build Query",
            description="Build a URL with query parameters",
            parameters={
                "base_url": {"type": "string", "description": "Base URL"},
                "params": {"type": "object", "description": "Query parameters"},
            },
            returns={"url": {"type": "string"}, "params": {"type": "object"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=False, category="network",
            capabilities=["api.build_query"], tags=["api", "query", "url"],
        ),
        ToolContract(
            id="api.set_headers", name="Set Headers",
            description="Set default headers for subsequent network requests",
            parameters={
                "headers": {"type": "object", "description": "Headers to set"},
                "mode": {"type": "string", "description": "set (replace all), merge (add), clear", "default": "set"},
            },
            returns={"headers": {"type": "object"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=False, category="network",
            capabilities=["api.set_headers"], tags=["api", "headers"],
        ),
        ToolContract(
            id="api.bearer_auth", name="Bearer Auth",
            description="Set Bearer token authentication for subsequent requests",
            parameters={
                "token": {"type": "string", "description": "Bearer token"},
            },
            returns={"scheme": {"type": "string"}, "token_set": {"type": "boolean"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=False, category="network",
            capabilities=["api.bearer_auth"], tags=["api", "auth", "bearer"],
        ),
        ToolContract(
            id="api.basic_auth", name="Basic Auth",
            description="Set Basic authentication credentials for subsequent requests",
            parameters={
                "username": {"type": "string", "description": "Username"},
                "password": {"type": "string", "description": "Password"},
            },
            returns={"scheme": {"type": "string"}, "username": {"type": "string"}, "authenticated": {"type": "boolean"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=False, category="network",
            capabilities=["api.basic_auth"], tags=["api", "auth", "basic"],
        ),
    ]

    network_diag_tools = [
        ToolContract(
            id="network.dns_lookup", name="DNS Lookup",
            description="Resolve a hostname to IP addresses",
            parameters={
                "hostname": {"type": "string", "description": "Hostname to resolve"},
            },
            returns={"hostname": {"type": "string"}, "addresses": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=False, category="network",
            capabilities=["network.dns_lookup"], tags=["network", "dns"],
        ),
        ToolContract(
            id="network.ping_host", name="Ping Host",
            description="Ping a host to check reachability",
            parameters={
                "hostname": {"type": "string", "description": "Hostname or IP to ping"},
                "count": {"type": "integer", "description": "Number of ping packets", "default": 4},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 10},
            },
            returns={"hostname": {"type": "string"}, "output": {"type": "string"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=False, category="network",
            capabilities=["network.ping_host"], tags=["network", "ping"],
        ),
        ToolContract(
            id="network.check_port", name="Check Port",
            description="Check if a TCP port is open on a host",
            parameters={
                "hostname": {"type": "string", "description": "Hostname or IP"},
                "port": {"type": "integer", "description": "TCP port number"},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 5},
            },
            returns={"hostname": {"type": "string"}, "port": {"type": "integer"}, "open": {"type": "boolean"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=False, category="network",
            capabilities=["network.check_port"], tags=["network", "port"],
        ),
        ToolContract(
            id="network.validate_url", name="Validate URL",
            description="Parse and validate a URL structure",
            parameters={
                "url": {"type": "string", "description": "URL to validate"},
            },
            returns={"url": {"type": "string"}, "valid": {"type": "boolean"}, "issues": {"type": "array"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=False, category="network",
            capabilities=["network.validate_url"], tags=["network", "url", "validate"],
        ),
    ]

    all_tools = http_read_tools + download_tools + upload_tools + api_tools + network_diag_tools

    http_read_handlers = [
        lambda p, eb=event_bus: _http_get(p, eb),
        lambda p, eb=event_bus: _http_head(p, eb),
        lambda p, eb=event_bus: _http_post(p, eb),
        lambda p, eb=event_bus: _http_put(p, eb),
        lambda p, eb=event_bus: _http_patch(p, eb),
        lambda p, eb=event_bus: _http_delete(p, eb),
    ]

    download_handlers = [
        lambda p, eb=event_bus: _download_file(p, eb),
        _cancel_download,
        _download_status,
        _verify_checksum,
    ]

    upload_handlers = [
        lambda p, eb=event_bus: _upload_file(p, eb),
        lambda p, eb=event_bus: _upload_multipart(p, eb),
    ]

    api_handlers = [
        lambda p, eb=event_bus: _send_json(p, eb),
        lambda p, eb=event_bus: _send_form(p, eb),
        _build_query,
        _set_headers,
        _bearer_auth,
        _basic_auth,
    ]

    network_diag_handlers = [
        _dns_lookup,
        _ping_host,
        _check_port,
        _validate_url,
    ]

    all_handlers = http_read_handlers + download_handlers + upload_handlers + api_handlers + network_diag_handlers

    for contract, handler in zip(all_tools, all_handlers):
        asyncio.create_task(tm.register_tool(contract, handler))
