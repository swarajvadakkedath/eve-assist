# EVE — One-Click Development Launcher Guide

This guide explains how to start and stop the complete EVE development
environment from source with a single double-click. The launcher keeps the
backend (FastAPI + uvicorn) and frontend (Vite) running in **separate
terminal windows**, waits for each to be ready, opens the browser, and shuts
everything down cleanly — **no orphaned processes**.

---

## Startup sequence

```
start_eve.bat
   │
   ├─ 1. Verify Python 3.12+  (uses .venv if usable, else py launcher, else python)
   ├─ 2. Verify Node + package manager (pnpm → yarn → npm)
   ├─ 3. Ensure stable EVE_API_TOKEN (persisted to config\.eve_dev_token)
   ├─ 4. Start Backend  → python -m aios.main  (window "EVE Backend", :8456)
   ├─ 5. Wait until GET /api/v1/system/health → HTTP 200  (retry every 1s)
   ├─ 6. Start Frontend → npm run dev          (window "EVE Frontend", :5173)
   ├─ 7. Wait until http://localhost:5173 serves a page (retry every 0.5s)
   ├─ 8. Open browser at http://localhost:5173
   └─ 9. Print ready summary
```

---

## Launcher files

| File | Purpose |
|------|---------|
| `start_eve.bat` | One-click entry point (double-click). Delegates to `start_eve.ps1`. |
| `start_eve.ps1` | Start engine: env detection, backend/frontend start, health waits, browser, PID file. |
| `stop_eve.bat` | One-click shutdown (double-click). Delegates to `stop_eve.ps1`. |
| `stop_eve.ps1` | Stop engine: tree-kill backend/frontend + optional orphan sweep. |
| `.vscode/tasks.json` | VS Code tasks: `Start EVE` (Ctrl+Shift+B), `Start Backend`, `Start Frontend`, `Stop EVE`. |

## Files created at runtime

| File | Purpose |
|------|---------|
| `config/.eve_dev_token` | Persisted stable dev token (created once if missing). |
| `.eve_pids.json` | PIDs started by the launcher (used by stop to tear down cleanly). |

> Both runtime files are git-ignored.

---

## One double-click

1. Double-click **`start_eve.bat`**.
2. Two terminal windows open (`EVE Backend`, `EVE Frontend`) with live logs.
3. The launcher waits until the backend is healthy, then the frontend.
4. Your browser opens at `http://localhost:5173`.
5. The launcher window prints:

```
----------------------------------------
EVE Development Environment Ready
Backend : http://127.0.0.1:8456
Frontend: http://localhost:5173
----------------------------------------
```

To stop: double-click **`stop_eve.bat`** (or Ctrl+C in the server windows).

---

## Backend

- **Entry point:** `python -m aios.main`
- **Working directory:** `src/backend`
- **URL:** `http://127.0.0.1:8456`
- **Health route:** `GET /api/v1/system/health` → HTTP `200`

### Python executable resolution (automatic)

The launcher picks the first Python ≥ 3.12 it finds, in this order:

1. `.venv\Scripts\python.exe` **if** its version is ≥ 3.12.
2. `py -3.14`, `py -3.13`, `py -3.12` (the Windows Python launcher).
3. `python` on `PATH`.
4. `python3` on `PATH`.

> **Important:** the current `.venv` in this repo is **Python 3.10.6**, which is
> **below the 3.12 requirement** (`pyproject.toml` says `requires-python = ">=3.12"`).
> The launcher therefore falls back to the system Python 3.14. It will only use
> `.venv` once that virtual environment is rebuilt with Python 3.12+:
>
> ```bat
> :: optional: rebuild the venv with a modern interpreter
> py -3.14 -m venv --clear .venv
> .venv\Scripts\python -m pip install -e .
> ```

---

## Frontend

- **Command:** `npm run dev` (Vite). The launcher auto-detects **npm → pnpm → yarn**.
- **Working directory:** `src/frontend`
- **URL:** `http://localhost:5173` (Vite proxies `/api` → `127.0.0.1:8456`).
- **Ready check:** the launcher polls the URL until a page responds (HTTP 200).

> Requires `src/frontend/node_modules` to be installed. If missing, run
> `npm install` inside `src/frontend` once.

---

## Environment variables

The launcher sets these for the backend process:

| Variable | Value | Notes |
|----------|-------|-------|
| `EVE_API_TOKEN` | Stable persisted token (default `eve-development-token`) | **Not** randomly regenerated each startup. Persisted to `config/.eve_dev_token`, reused across reboots. Override by setting `EVE_API_TOKEN` in your environment first. |
| `EVE_ENV` | `dev` | Enables uvicorn `reload` for hot-reload during development. |
| `PYTHONPATH` | `src/backend;…` | So `python -m aios.main` resolves the `aios` package. |
| `PYTHONIOENCODING` | `utf-8` | Prevents Unicode banner corruption on cp1252 consoles. |
| `PYTHONUTF8` | `1` | UTF-8 mode for Python. |

---

## Health check logic

- The launcher does **not** start the frontend until the backend is healthy.
- It polls `GET http://127.0.0.1:8456/api/v1/system/health` every 1 second
  until the response is **HTTP 200**, up to a timeout (default **90 s**).
- If the backend process exits before becoming healthy, the launcher aborts.
- The frontend is polled every 0.5 s until `http://localhost:5173` responds.

> **Note:** the task description references `GET /health`, but the EVE backend
> exposes readiness at **`/api/v1/system/health`** (no `/health` route exists).
> The launcher deliberately uses the real route — the project architecture was
> not modified.

---

## Stopping (no orphans)

`stop_eve.bat` / `stop_eve.ps1`:

1. Reads the PIDs written by `start_eve.ps1` (`.eve_pids.json`).
2. Tree-kills the **frontend**, then the **backend** (children first, then parent).
3. Any process still holding ports `8456` / `5173` is stopped.
4. Sweeps stray `aios.main` (python) and `vite` (node) processes.
5. Deletes the PID file.

Result: backend, frontend, and all child/npm/node sub-processes are removed —
no orphans.

---

## VS Code (optional)

`.vscode/tasks.json` provides four tasks:

- **`Start EVE`** — full stack; bound to **Ctrl+Shift+B** (`defaultBuildTask`).
- **`Start Backend`** — backend only (`-OnlyBackend`).
- **`Start Frontend`** — frontend only (`-OnlyFrontend`).
- **`Stop EVE`** — graceful shutdown.

Run via **Terminal → Run Task…**, or press **Ctrl+Shift+B** to start the whole
environment.

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| `Python 3.12+ not found` | No suitable interpreter. Install Python 3.12+, or rebuild `.venv` (see above). |
| `Frontend dependencies missing` | Run `npm install` in `src/frontend`. |
| Port 8456 / 5173 already in use but not healthy | A stale process holds the port. Run `stop_eve.bat` (or kill the process) and retry. |
| Backend not healthy within timeout | Check the `EVE Backend` window for a stack trace (missing deps, port conflict, Python version). |
| Backend exits immediately | Missing deps → `pip install -e .` in `src/backend` / project root. |
| Browser opened but shows errors | Ensure backend is healthy first; Vite proxies `/api` to `127.0.0.1:8456`. |
| 401 on API calls | `EVE_API_TOKEN` mismatch. Delete `config/.eve_dev_token` and restart (a fresh stable token is written), or set `EVE_API_TOKEN` explicitly. |
| Unicode `□` boxes / garbled logs | UTF-8 mode is already forced; if a server window still garbles, set the console to `chcp 65001`. |
| `.venv` ignored / Python version differs | The launcher falls back to system Python ≥3.12 automatically; see the MVP section. |

---

## Expected startup time

- Backend ready: **~6–15 s** (uvicorn boots, `--reload` initial scan).
- Frontend ready: **~4–8 s** (Vite `ready in ~4 s`).
- Total one-click startup to a ready browser tab: **~15–25 s**.

Timers: backend health poll every 1 s, frontend poll every 0.5 s, overall
timeout 90 s.