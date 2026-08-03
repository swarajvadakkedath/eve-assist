"""Test with lifespan enabled to get real tracebacks."""
import sys
import asyncio
import traceback
sys.path.insert(0, "E:/Eve_Ai/src/backend")

from httpx import AsyncClient, ASGITransport
from aios.api.app import create_app

async def main():
    app = create_app()
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        endpoints = [
            ("GET", "/api/v1/settings", None),
            ("GET", "/api/v1/providers", None),
            ("GET", "/api/v1/providers/health", None),
            ("GET", "/api/v1/providers/health/history?limit=5", None),
            ("POST", "/api/v1/chat/conversation", {"title": "Test"}),
            ("GET", "/api/v1/system/health", None),
        ]
        
        for method, path, body in endpoints:
            print(f"\n{'='*60}")
            print(f"{method} {path}")
            print(f"{'='*60}")
            try:
                if method == "GET":
                    r = await client.get(path)
                elif method == "POST":
                    r = await client.post(path, json=body)
                print(f"Status: {r.status_code}")
                print(f"Body: {r.text[:2000]}")
            except Exception as e:
                print(f"EXCEPTION: {e}")
                traceback.print_exc()

asyncio.run(main())
