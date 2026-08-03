"""Test script to capture full tracebacks from failing endpoints."""
import sys
import traceback
sys.path.insert(0, "E:/Eve_Ai/src/backend")

from fastapi.testclient import TestClient
from aios.api.app import create_app

print("Creating app...")
app = create_app()

print("Creating test client...")
client = TestClient(app)

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
            r = client.get(path)
        elif method == "POST":
            r = client.post(path, json=body)
        print(f"Status: {r.status_code}")
        if r.status_code >= 400:
            print(f"Body: {r.text[:2000]}")
        else:
            print(f"Body: {r.text[:500]}")
    except Exception as e:
        print(f"EXCEPTION: {e}")
        traceback.print_exc()
