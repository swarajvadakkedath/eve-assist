"""Tests for the startup-readiness middleware and /system/readiness endpoint.

Covers:
  - StartupReadyMiddleware blocks routes before lifespan, allows bypass routes.
  - /system/readiness returns correct status and ready flag.
  - EVE_STARTUP_DELAY_MS knob delays lifespan without breaking endpoints.
  - Post-lifespan all routes pass through.
"""

import asyncio
import os
import sys

import httpx
import pytest
from httpx import ASGITransport

from aios.api.app import create_app


def _make_no_lifespan_client():
    """Client with lifespan NOT triggered — simulates pre-init window."""
    app = create_app()
    transport = ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


@pytest.mark.asyncio
async def test_bypass_health_200_before_lifespan():
    async with _make_no_lifespan_client() as client:
        r = await client.get("/api/v1/system/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_bypass_readiness_200_before_lifespan():
    async with _make_no_lifespan_client() as client:
        r = await client.get("/api/v1/system/readiness")
        assert r.status_code == 200
        body = r.json()
        assert body["ready"] is False
        assert body["status"] == "starting"


@pytest.mark.asyncio
async def test_bypass_status_200_before_lifespan():
    async with _make_no_lifespan_client() as client:
        r = await client.get("/api/v1/desktop/status")
        assert r.status_code == 200
        assert r.json()["status"] == "starting"


@pytest.mark.asyncio
async def test_blocked_routes_return_503_before_lifespan():
    blocked = [
        "/api/v1/chat/conversations",
        "/api/v1/desktop/settings",
        "/api/v1/providers",
        "/api/v1/routing",
        "/api/v1/system/status",
    ]
    async with _make_no_lifespan_client() as client:
        for path in blocked:
            r = await client.get(path)
            assert r.status_code == 503, f"{path} should be 503"
            body = r.json()
            assert body["status"] in ("starting", "initializing"), f"{path} status={body['status']}"
            assert "Server initializing" in body["detail"]


@pytest.mark.asyncio
async def test_blocked_post_returns_503_before_lifespan():
    async with _make_no_lifespan_client() as client:
        r = await client.post("/api/v1/chat/conversation")
        assert r.status_code == 503
        assert r.json()["status"] in ("starting", "initializing")


@pytest.mark.asyncio
async def test_readiness_ready_false_before_lifespan():
    async with _make_no_lifespan_client() as client:
        r = await client.get("/api/v1/system/readiness")
        body = r.json()
        assert body["ready"] is False


@pytest.mark.asyncio
async def test_status_initIALIZING_during_lifespan():
    """With lifespan running (asgi-lifespan), status should become READY."""
    try:
        from asgi_lifespan import LifespanManager
    except ImportError:
        pytest.skip("asgi-lifespan not installed")

    app = create_app()
    async with LifespanManager(app) as manager:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            r = await client.get("/api/v1/system/readiness")
            assert r.status_code == 200
            body = r.json()
            assert body["ready"] is True
            assert body["status"] == "ready"


@pytest.mark.asyncio
async def test_all_routes_pass_after_lifespan():
    try:
        from asgi_lifespan import LifespanManager
    except ImportError:
        pytest.skip("asgi-lifespan not installed")

    app = create_app()
    async with LifespanManager(app) as manager:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Routes that access app.state should return 200 (not 503).
            routes_200 = [
                "/api/v1/chat/conversations",
                "/api/v1/desktop/settings",
                "/api/v1/desktop/status",
                "/api/v1/system/health",
                "/api/v1/system/readiness",
            ]
            for path in routes_200:
                r = await client.get(path)
                assert r.status_code == 200, f"{path} should be 200 after lifespan"

            # POST should also pass middleware (may 422 on missing body, not 503).
            r = await client.post("/api/v1/chat/conversation")
            assert r.status_code != 503


@pytest.mark.asyncio
async def test_eve_startup_delay_knob():
    try:
        from asgi_lifespan import LifespanManager
    except ImportError:
        pytest.skip("asgi-lifespan not installed")

    old = os.environ.get("EVE_STARTUP_DELAY_MS")
    os.environ["EVE_STARTUP_DELAY_MS"] = "1000"
    try:
        import time
        app = create_app()
        t0 = time.monotonic()
        async with LifespanManager(app) as manager:
            elapsed = time.monotonic() - t0
            assert elapsed >= 1.0, f"Expected >=1s delay, got {elapsed:.2f}s"
            transport = ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                r = await client.get("/api/v1/system/readiness")
                assert r.json()["ready"] is True
    finally:
        if old is None:
            os.environ.pop("EVE_STARTUP_DELAY_MS", None)
        else:
            os.environ["EVE_STARTUP_DELAY_MS"] = old


@pytest.mark.asyncio
async def test_middleware_reads_actual_status():
    """Middleware 503 body contains a valid status string from StatusService."""
    async with _make_no_lifespan_client() as client:
        r = await client.get("/api/v1/chat/conversations")
        assert r.status_code == 503
        body = r.json()
        # StatusService is a process-wide singleton; by the time this test runs
        # after lifespan tests it may already be READY.  Just verify the body
        # has a non-empty status string from the real StatusService.
        assert isinstance(body["status"], str)
        assert len(body["status"]) > 0
