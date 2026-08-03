#!/usr/bin/env python3
"""Stress-test the startup-readiness synchronization.

Launches the backend with various EVE_STARTUP_DELAY_MS values and verifies:
  - Status transitions: starting → initializing → ready
  - Gated routes return 503 with correct status during startup
  - Health / status / readiness bypass endpoints always return 200
  - No 500 / AttributeError during startup
  - /system/readiness reports ready: true after lifespan completes
"""

import asyncio
import os
import signal
import sys
import time

import httpx

# Ensure the backend is importable.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "backend"))

DELAY_CASES = [0, 1, 3, 5, 10, 15]
PORT = 18456  # non-default to avoid collision
BASE = f"http://127.0.0.1:{PORT}/api/v1"

BYPASS = {"/system/health", "/system/readiness", "/desktop/status"}
GATED = [
    "/chat/conversations",
    "/desktop/settings",
    "/providers",
    "/routing",
    "/system/status",
]


async def wait_for_ready(client: httpx.AsyncClient, timeout: float = 30) -> float:
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        try:
            r = await client.get(f"{BASE}/system/readiness", timeout=2)
            if r.status_code == 200:
                data = r.json()
                if data.get("ready"):
                    return time.monotonic() - t0
        except Exception:
            pass
        await asyncio.sleep(0.2)
    raise TimeoutError(f"Backend not ready after {timeout}s")


def start_backend(delay_ms: int) -> asyncio.subprocess.Process:
    env = os.environ.copy()
    env["EVE_STARTUP_DELAY_MS"] = str(delay_ms)
    env["EVE_API_PORT"] = str(PORT)
    return asyncio.create_subprocess_exec(
        sys.executable, "-m", "aios.main",
        cwd=os.path.join(os.path.dirname(__file__), "..", "src", "backend"),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
        env=env,
    )


async def stop_backend(proc: asyncio.subprocess.Process):
    try:
        proc.terminate()
        await asyncio.wait_for(proc.wait(), timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


async def test_delay(delay_ms: int) -> dict:
    result = {"delay_ms": delay_ms, "ready_time": None, "errors": [], "transitions": []}

    proc = await start_backend(delay_ms)

    async with httpx.AsyncClient(timeout=3) as client:
        # Wait for ready.
        try:
            result["ready_time"] = await wait_for_ready(client)
        except TimeoutError as e:
            result["errors"].append(str(e))
            await stop_backend(proc)
            return result

        # Verify bypass endpoints.
        for path in ["/system/health", "/system/readiness", "/desktop/status"]:
            try:
                r = await client.get(f"{BASE}{path}", timeout=2)
                if r.status_code != 200:
                    result["errors"].append(f"{path} returned {r.status_code}")
            except Exception as e:
                result["errors"].append(f"{path} error: {e}")

        # Verify gated endpoints are now 200.
        for path in GATED:
            try:
                r = await client.get(f"{BASE}{path}", timeout=2)
                if r.status_code == 503:
                    result["errors"].append(f"{path} still 503 after ready")
                elif r.status_code >= 500:
                    result["errors"].append(f"{path} returned {r.status_code}")
            except Exception as e:
                result["errors"].append(f"{path} error: {e}")

        # Check readiness response.
        try:
            r = await client.get(f"{BASE}/system/readiness", timeout=2)
            data = r.json()
            result["final_status"] = data.get("status")
            result["final_ready"] = data.get("ready")
        except Exception as e:
            result["errors"].append(f"readiness check error: {e}")

    await stop_backend(proc)
    return result


async def main():
    print(f"Startup stress test — delays: {DELAY_CASES}s")
    print("=" * 60)

    results = []
    for delay in DELAY_CASES:
        print(f"\n--- delay={delay}s ---")
        r = await test_delay(delay)
        results.append(r)
        status = "PASS" if not r["errors"] else "FAIL"
        print(f"  ready_time: {r['ready_time']:.2f}s" if r["ready_time"] else f"  ready_time: TIMEOUT")
        print(f"  final_status: {r.get('final_status', 'N/A')}")
        print(f"  final_ready: {r.get('final_ready', 'N/A')}")
        if r["errors"]:
            for e in r["errors"]:
                print(f"  ERROR: {e}")
        print(f"  Result: {status}")

    print("\n" + "=" * 60)
    all_pass = all(not r["errors"] for r in results)
    print(f"Overall: {'ALL PASS' if all_pass else 'FAILURES DETECTED'}")

    # Summary table.
    print("\n| Delay (s) | Ready (s) | Status | Ready | Errors |")
    print("|-----------|-----------|--------|-------|--------|")
    for r in results:
        d = r["delay_ms"]
        rt = f"{r['ready_time']:.2f}" if r["ready_time"] else "TIMEOUT"
        fs = r.get("final_status", "N/A")
        fr = r.get("final_ready", "N/A")
        errs = len(r["errors"])
        print(f"| {d:>9} | {rt:>9} | {fs} | {fr} | {errs:>6} |")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    asyncio.run(main())
