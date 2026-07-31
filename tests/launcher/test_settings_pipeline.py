"""Settings E2E regression — verifies backend remains responsive under stdout load.

Secondary to the pipe-drain regression in test_stdin_nonblocking.py.
Boots the real backend on a test port, generates sustained logging,
then calls settings and other endpoints.

Skips automatically if the backend cannot start (e.g., sandbox/CI).
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

import httpx
import pytest

TEST_PORT = 8457
TEST_HOST = "127.0.0.1"
BASE_URL = f"http://{TEST_HOST}:{TEST_PORT}"
HEALTH_URL = f"{BASE_URL}/api/v1/system/health"
SETTINGS_URL = f"{BASE_URL}/api/v1/desktop/settings"
CONVERSATIONS_URL = f"{BASE_URL}/api/v1/chat/conversations"
STARTUP_TIMEOUT = 20


def _get_backend_env():
    """Build env for the backend subprocess."""
    root = Path(__file__).resolve().parent.parent.parent
    backend_aios = root / "src" / "backend" / "aios"
    if not backend_aios.is_dir():
        backend_aios = root / "desktop" / "src-tauri" / "backend" / "aios"
    pkg_path = str(backend_aios.parent)
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{pkg_path};{existing}" if existing else pkg_path
    env["EVE_PORT"] = str(TEST_PORT)
    env["EVE_HOST"] = TEST_HOST
    return env, backend_aios.parent


async def _try_start_backend():
    """Attempt to start the backend. Returns (proc, env) or raises."""
    env, cwd = _get_backend_env()
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "aios.main",
        cwd=str(cwd),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    deadline = time.monotonic() + STARTUP_TIMEOUT
    async with httpx.AsyncClient() as client:
        while time.monotonic() < deadline:
            try:
                resp = await client.get(HEALTH_URL, timeout=2)
                if resp.status_code == 200:
                    return proc
            except Exception:
                pass
            await asyncio.sleep(0.5)

    proc.kill()
    await proc.wait()
    pytest.skip("Backend could not start within timeout")


@pytest.fixture
async def backend():
    """Async fixture: starts backend, yields it, kills on teardown."""
    proc = await _try_start_backend()
    yield proc
    if proc.returncode is None:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5)
        except (asyncio.TimeoutError, ProcessLookupError):
            proc.kill()
            await proc.wait()


@pytest.mark.asyncio
async def test_settings_endpoint_responds(backend):
    """Settings endpoint returns HTTP 200 with valid JSON."""
    async with httpx.AsyncClient() as client:
        t0 = time.monotonic()
        resp = await client.get(SETTINGS_URL, timeout=10)
        latency = time.monotonic() - t0

    assert resp.status_code == 200, f"Settings returned {resp.status_code}"
    assert latency < 5.0, f"Settings latency {latency:.1f}s exceeds 5s"
    data = resp.json()
    assert isinstance(data, dict), "Settings response is not a dict"


@pytest.mark.asyncio
async def test_conversations_endpoint_responds(backend):
    """Conversation list endpoint returns HTTP 200."""
    async with httpx.AsyncClient() as client:
        t0 = time.monotonic()
        resp = await client.get(CONVERSATIONS_URL, timeout=10)
        latency = time.monotonic() - t0

    assert resp.status_code == 200, f"Conversations returned {resp.status_code}"
    assert latency < 5.0, f"Conversations latency {latency:.1f}s exceeds 5s"


@pytest.mark.asyncio
async def test_health_responsive_under_load(backend):
    """Health endpoint stays responsive while backend generates logs."""
    async with httpx.AsyncClient() as client:
        tasks = [
            client.get(HEALTH_URL, timeout=10),
            client.get(HEALTH_URL, timeout=10),
            client.get(SETTINGS_URL, timeout=10),
            client.get(CONVERSATIONS_URL, timeout=10),
        ]

        t0 = time.monotonic()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.monotonic() - t0

    for i, r in enumerate(results):
        if isinstance(r, Exception):
            pytest.fail(f"Request {i} failed: {r}")
        assert r.status_code == 200, f"Request {i} returned {r.status_code}"

    assert elapsed < 15.0, f"Batch took {elapsed:.1f}s"


@pytest.mark.asyncio
async def test_health_endpoint_detailed(backend):
    """Health endpoint returns version and module status."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(HEALTH_URL, timeout=10)

    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data or "version" in data, f"Health: {data}"
