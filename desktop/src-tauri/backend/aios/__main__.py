"""AIOS launcher — single-command startup for backend and frontend.

Usage:
    python -m aios

Starts:
    1. Backend (aios.main) on http://127.0.0.1:8456
    2. Frontend (Vite dev server) on http://localhost:5173
"""

import asyncio
import logging
import os
import shutil
import sys
import time
import webbrowser
from pathlib import Path

import httpx

LAUNCHER_VERSION = "1.2.0-rc.2"
BACKEND_DIR = Path(__file__).resolve().parent
BACKEND_PKG_DIR = BACKEND_DIR.parent
PROJECT_ROOT = BACKEND_PKG_DIR.parent.parent
FRONTEND_DIR = PROJECT_ROOT / "src" / "frontend"
BASE_URL = "http://127.0.0.1:8456"
HEALTH_URL = f"{BASE_URL}/api/v1/system/health"
TOOLS_URL = f"{BASE_URL}/api/v1/tools"
CAPABILITIES_URL = f"{BASE_URL}/api/v1/capabilities"
SETTINGS_URL = f"{BASE_URL}/api/v1/settings"
PLUGINS_HEALTH_URL = f"{BASE_URL}/api/v1/plugins/health"
FRONTEND_URL = "http://localhost:5173"
BACKEND_TIMEOUT = 30
ENSURE_PATH = str(BACKEND_PKG_DIR)

logger = logging.getLogger("aios.launcher")

DIVIDER = "\u2500" * 46
HEADER = "\u2550" * 46


class LauncherError(Exception):
    pass


def _setup_logging():
    if logger.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] launcher: %(message)s",
        datefmt="%H:%M:%S",
    ))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def print_banner():
    print()
    print(f"  {HEADER}")
    print(f"  AIOS (Eve)  v{LAUNCHER_VERSION}")
    print(f"  Developer Preview")
    print(f"  Architecture v4.0")
    print()
    print(f"  Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print(f"  Backend: {BASE_URL}")
    print(f"  Frontend: {FRONTEND_URL}")
    print(f"  {HEADER}")
    print()


def ok(msg: str):
    print(f"  \u2713 {msg}")


def info(msg: str):
    print(f"    {msg}")


def fail(msg: str):
    print(f"  \u2717 {msg}")


def summary_line(key: str, val: str):
    print(f"  {key:20} {val}")


def _build_proc_env():
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    if ENSURE_PATH and ENSURE_PATH not in existing:
        env["PYTHONPATH"] = f"{ENSURE_PATH};{existing}" if existing else ENSURE_PATH
    return env


async def _read_stream(stream, buffer):
    while True:
        line = await stream.readline()
        if not line:
            break
        buffer.append(line)


async def start_process(*args, cwd=None, env=None):
    if env is None:
        env = _build_proc_env()
    proc = await asyncio.create_subprocess_exec(
        *args,
        cwd=cwd,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    buffer = []
    reader = asyncio.ensure_future(_read_stream(proc.stdout, buffer))
    return proc, buffer, reader


async def api_get(client: httpx.AsyncClient, url: str, timeout: float = 5.0):
    try:
        resp = await client.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


async def wait_for_backend(timeout=BACKEND_TIMEOUT):
    deadline = time.time() + timeout
    async with httpx.AsyncClient() as client:
        while time.time() < deadline:
            try:
                resp = await client.get(HEALTH_URL, timeout=2)
                if resp.status_code == 200:
                    return True, resp.json()
            except Exception:
                pass
            await asyncio.sleep(0.5)
    return False, None


async def fetch_runtime_info():
    async with httpx.AsyncClient() as client:
        info = {
            "capabilities": 0,
            "tools": 0,
            "plugins": 0,
            "plugins_active": 0,
            "ai_provider": "unknown",
            "ai_model": "unknown",
            "log_level": "unknown",
        }

        tools_data = await api_get(client, TOOLS_URL)
        if isinstance(tools_data, dict):
            info["tools"] = len(tools_data.get("tools", []))

        caps_data = await api_get(client, CAPABILITIES_URL)
        if isinstance(caps_data, dict):
            info["capabilities"] = len(caps_data.get("capabilities", []))

        settings = await api_get(client, SETTINGS_URL)
        if isinstance(settings, dict):
            s = settings.get("settings", {})
            info["ai_provider"] = s.get("ai.provider", "unknown")
            info["ai_model"] = s.get("ai.model", "unknown")
            info["log_level"] = s.get("log.level", "unknown")

        plugins = await api_get(client, PLUGINS_HEALTH_URL)
        if isinstance(plugins, dict):
            info["plugins"] = plugins.get("total", 0)

        return info


def check_python():
    vi = sys.version_info
    if vi.major < 3 or (vi.major == 3 and vi.minor < 12):
        raise LauncherError(
            f"Python >= 3.12 required, got {vi.major}.{vi.minor}\n"
            f"    Download: https://www.python.org/downloads/"
        )
    try:
        import aios
        _ = aios.__version__
    except ImportError:
        raise LauncherError(
            "aios package not installed\n"
            "    Run: pip install -e ."
        )
    return True


def check_node():
    if not shutil.which("node"):
        raise LauncherError(
            "Node.js not found\n"
            "    Install: https://nodejs.org/"
        )
    if not shutil.which("npm"):
        raise LauncherError(
            "npm not found\n"
            "    Install Node.js (includes npm): https://nodejs.org/"
        )
    return True


async def run():
    start_time = time.monotonic()

    _setup_logging()
    print_banner()

    backend = frontend = None
    backend_buf = []

    try:
        # ── 1. Environment ──
        try:
            check_python()
            ok("Python Environment")
        except LauncherError as e:
            fail(str(e).split("\n")[0])
            info(str(e).split("\n")[1].strip() if "\n" in str(e) else "")
            raise

        try:
            check_node()
            ok("Node.js")
        except LauncherError as e:
            fail(str(e).split("\n")[0])
            info(str(e).split("\n")[1].strip() if "\n" in str(e) else "")
            raise

        # ── 2. Start backend ──
        proc_env = _build_proc_env()
        backend, backend_buf, backend_reader = await start_process(
            sys.executable, "-m", "aios.main",
            env=proc_env,
        )
        logger.info("backend started", extra={"pid": backend.pid})
        ok("Backend Started")

        # ── 3. Wait for health ──
        health_ok, health_data = await wait_for_backend()
        if not health_ok:
            debug = b"".join(backend_buf).decode(errors="replace").strip()
            if backend.returncode is not None and backend.returncode != 0:
                fail(f"Backend exited with code {backend.returncode}")
            else:
                fail(f"Backend not ready within {BACKEND_TIMEOUT}s")
                info("Check if port 8456 is free, or run:")
                info("  python -m aios.main  (to see backend logs)")
            if debug:
                info(f"  Last output: {debug[:200]}")
            raise LauncherError("backend startup failed")

        # ── 4. Show module progress from health data ──
        modules = health_data.get("modules", {}) if health_data else {}
        module_order = ["event_bus", "ai_router", "tool_manager",
                        "capability_registry", "memory_system"]
        for mod_name in module_order:
            mod_status = modules.get(mod_name, "unknown")
            label = mod_name.replace("_", " ").title()
            if mod_status == "healthy":
                ok(label)
            else:
                info(f"{label}: {mod_status}")
        ok("API Ready")
        logger.info("backend healthy", extra={"health": health_data})

        # ── 5. Health validation ──
        required_modules = {"event_bus", "tool_manager"}
        healthy_mods = {k for k, v in (modules or {}).items() if v == "healthy"}
        missing = required_modules - healthy_mods
        if missing:
            fail("Core services not healthy")
            info("Run: python -m aios.main  (to see backend logs)")
            raise LauncherError("health validation failed")
        ok("Health Validation")

        # ── 6. Fetch runtime info ──
        runtime = await fetch_runtime_info()
        logger.info("runtime info fetched",
                    extra={"tools": runtime["tools"], "capabilities": runtime["capabilities"]})

        # ── 7. Install frontend deps if needed ──
        if not (FRONTEND_DIR / "node_modules").exists():
            info("Installing frontend dependencies...")
            installer = await asyncio.create_subprocess_exec(
                "npm", "install",
                cwd=str(FRONTEND_DIR),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await installer.wait()
            if installer.returncode != 0:
                fail("npm install failed")
                info("Run: cd src/frontend && npm install")
                raise LauncherError("npm install failed")

        # ── 8. Start frontend ──
        frontend, frontend_buf, frontend_reader = await start_process(
            "npm", "run", "dev",
            cwd=str(FRONTEND_DIR),
            env=proc_env,
        )
        logger.info("frontend started", extra={"pid": frontend.pid})
        ok("Frontend Started")

        # ── 9. Open browser ──
        webbrowser.open(FRONTEND_URL)
        ok("Browser Opened")

        # ── 10. Runtime summary ──
        elapsed = time.monotonic() - start_time
        print()
        print(f"  {DIVIDER}")
        summary_line("Backend:", BASE_URL)
        summary_line("Frontend:", FRONTEND_URL)
        summary_line("Capabilities:", str(runtime.get("capabilities", 0)))
        summary_line("Tools:", str(runtime.get("tools", 0)))
        if runtime.get("plugins", 0) > 0:
            summary_line("Plugins:", str(runtime["plugins"]))
        summary_line("AI Provider:", runtime.get("ai_provider", "unknown"))
        summary_line("Model:", runtime.get("ai_model", "unknown"))
        summary_line("Log Level:", runtime.get("log_level", "unknown"))
        summary_line("Startup Time:", f"{elapsed:.2f}s")
        print(f"  {DIVIDER}")
        print()

        logger.info("launcher ready",
                    extra={"elapsed_s": round(elapsed, 2), "pid_backend": backend.pid,
                           "pid_frontend": frontend.pid if frontend else None})

        # ── 11. Wait for shutdown ──
        await asyncio.wait(
            [asyncio.create_task(backend.wait()),
             asyncio.create_task(frontend.wait())],
            return_when=asyncio.FIRST_COMPLETED,
        )

    except asyncio.CancelledError:
        pass
    finally:
        for name, proc in [("Frontend", frontend), ("Backend", backend)]:
            if proc and proc.returncode is None:
                print(f"  Stopping {name}...")
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5)
                except asyncio.TimeoutError:
                    proc.kill()
        print("  Cleaning up...")
        print("  Goodbye.\n")
        logger.info("launcher shutdown")


def main():
    try:
        asyncio.run(run())
    except LauncherError:
        sys.exit(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
