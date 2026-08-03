"""Process service — low-level subprocess management."""

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Callable

BACKEND_DIR: Path | None = None
PROJECT_ROOT: Path | None = None


def _resolve_backend_dir() -> Path:
    script_dir = Path(__file__).resolve().parent.parent.parent
    development = script_dir.parent / "src" / "backend" / "aios"
    if development.is_dir():
        return development
    bundled = script_dir / "backend" / "aios"
    if bundled.is_dir():
        return bundled
    return script_dir


def _resolve_project_root() -> Path:
    backend = _resolve_backend_dir()
    return backend.parent.parent


BACKEND_DIR = _resolve_backend_dir()
PROJECT_ROOT = _resolve_project_root()


class ManagedProcess:
    def __init__(self, name: str, proc, buffer: list, reader):
        self.name = name
        self.proc = proc
        self.buffer = buffer
        self.reader = reader

    @property
    def pid(self) -> int:
        return self.proc.pid

    @property
    def is_running(self) -> bool:
        return self.proc.returncode is None

    @property
    def returncode(self) -> int | None:
        return self.proc.returncode


class ProcessService:
    def __init__(self, on_output: Callable | None = None):
        self._processes: dict[str, ManagedProcess] = {}
        self._on_output = on_output

    def _build_env(self):
        env = os.environ.copy()
        pkg_path = str(BACKEND_DIR.parent)
        existing = env.get("PYTHONPATH", "")
        if pkg_path not in existing:
            env["PYTHONPATH"] = f"{pkg_path};{existing}" if existing else pkg_path
        if "EVE_ENV" not in env:
            env["EVE_ENV"] = "dev"
        return env

    def _get_log_path(self, name: str) -> Path:
        logs_dir = Path.home() / ".eve" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        return logs_dir / f"{name}.log"

    async def _read_stream(self, stream, buffer, log_path: Path | None = None):
        while True:
            line = await stream.readline()
            if not line:
                break
            decoded = line.decode(errors="replace").rstrip()
            buffer.append(decoded)
            if log_path:
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(decoded + "\n")
                except Exception:
                    pass
            if self._on_output:
                self._on_output(decoded)

    async def start(self, name: str, *args, cwd=None, env=None) -> ManagedProcess:
        if env is None:
            env = self._build_env()
        proc = await asyncio.create_subprocess_exec(
            *args, cwd=cwd, env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        buffer = []
        log_path = self._get_log_path(name)
        reader = asyncio.ensure_future(self._read_stream(proc.stdout, buffer, log_path))
        mp = ManagedProcess(name, proc, buffer, reader)
        self._processes[name] = mp
        return mp

    def get(self, name: str) -> ManagedProcess | None:
        return self._processes.get(name)

    async def stop(self, name: str, timeout: float = 5.0):
        mp = self._processes.pop(name, None)
        if mp is None or not mp.is_running:
            return
        if sys.platform == "win32":
            mp.proc.terminate()
        else:
            mp.proc.send_signal(signal.SIGTERM)
        try:
            await asyncio.wait_for(mp.proc.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            mp.proc.kill()
            await mp.proc.wait()
        mp.reader.cancel()

    async def stop_all(self, timeout: float = 5.0):
        for name in list(self._processes.keys()):
            await self.stop(name, timeout)

    async def is_alive(self, name: str) -> bool:
        mp = self._processes.get(name)
        return mp is not None and mp.is_running

    def list_processes(self) -> dict[str, ManagedProcess]:
        return dict(self._processes)
