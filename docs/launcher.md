# AIOS Launcher

A single-command launcher that starts the AIOS/Eve backend and frontend together.

---

## Usage

### Python (recommended)

```bash
cd E:\Eve_Ai
python -m aios
```

### PowerShell

```powershell
cd E:\Eve_Ai
.\start_eve.ps1
```

### Batch (double-click friendly)

```cmd
cd E:\Eve_Ai
start_eve.bat
```

---

## Startup Flow

```
python -m aios
  │
  ├── [print_banner]  ──────────────────────  ═══ AIOS (Eve) ═══
  │
  ├── [check_python]  ──────────────────────  ✓ Python Environment
  ├── [check_node]    ──────────────────────  ✓ Node.js
  │
  ├── [start_process: python -m aios.main]  ─  ✓ Backend Started
  │   └── subprocess: uvicorn on :8456
  │
  ├── [wait_for_backend: GET /health]  ──────  ✓ Event Bus
  │   └── polls every 0.5s, timeout 30s       ✓ Tool Manager
  │                                            ✓ Capability Registry
  │                                            ✓ AI Router
  │                                            ✓ Memory System
  │                                            ✓ API Ready
  │
  ├── [health validation]  ─────────────────  ✓ Health Validation
  │   └── verifies: event_bus, tool_manager
  │
  ├── [fetch_runtime_info]  ─────────────────  (fetches tools, caps, settings)
  │   ├── GET /api/v1/tools
  │   ├── GET /api/v1/capabilities
  │   ├── GET /api/v1/settings
  │   └── GET /api/v1/plugins/health
  │
  ├── [npm install if needed]  ─────────────  (auto-installs node_modules)
  │
  ├── [start_process: npm run dev]  ─────────  ✓ Frontend Started
  │   └── subprocess: Vite on :5173
  │
  ├── [webbrowser.open]  ───────────────────  ✓ Browser Opened
  │
  └── [runtime summary]  ───────────────────  ─── Summary ───
                                                Backend URL
                                                Frontend URL
                                                Capabilities: N
                                                Tools: N
                                                AI Provider
                                                Model
                                                Startup Time
```

### On Ctrl+C

```
  Stopping Frontend...
  Stopping Backend...
  Cleaning up...
  Goodbye.
```

---

## Console output

```
  ══════════════════════════════════════════
  AIOS (Eve)  v1.0.0
  Developer Preview
  Architecture v4.0

  Python: 3.12.3
  Backend: http://127.0.0.1:8456
  Frontend: http://localhost:5173
  ══════════════════════════════════════════

  ✓ Python Environment
  ✓ Node.js
  ✓ Backend Started
  ✓ Event Bus
  ✓ Ai Router
  ✓ Tool Manager
  ✓ Capability Registry
  ✓ Memory System
  ✓ API Ready
  ✓ Health Validation
  ✓ Frontend Started
  ✓ Browser Opened

  ──────────────────────────────────────────
  Backend:              http://127.0.0.1:8456
  Frontend:             http://localhost:5173
  Capabilities:         153
  Tools:                33
  AI Provider:          ollama
  Model:                gpt-4
  Log Level:            INFO
  Startup Time:         2.84s
  ──────────────────────────────────────────
```

---

## Requirements

| Dependency | Minimum |
|---|---|
| Python | 3.12 |
| Node.js | 18 |
| npm | (included with Node.js) |

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| ❌ Python >= 3.12 required | Wrong Python version | Install Python 3.12+ from python.org |
| ❌ aiOS package not installed | Package not in PYTHONPATH | `pip install -e .` from project root |
| ❌ Node.js not found | Node.js not installed | Install Node.js 18+ from nodejs.org |
| ❌ npm not found | npm missing from PATH | Install Node.js (includes npm) |
| ❌ Backend not ready within 30s | Port 8456 in use or backend error | `python -m aios.main` to see backend logs |
| ❌ Backend exited with code N | Backend crash | Check the error code |
| ❌ Core services not healthy | Backend services failed | `python -m aios.main` to see backend logs |
| ❌ npm install failed | npm package download error | `cd src/frontend && npm install` manually |

---

## Command Reference

| Command | Action |
|---|---|
| `python -m aios` | Start Eve (backend + frontend) |
| `python -m aios.main` | Start backend only |
| `.\start_eve.ps1` | PowerShell launcher (sets PYTHONPATH) |
| `start_eve.bat` | Batch launcher (sets PYTHONPATH) |
| `cd src/frontend && npm run dev` | Start frontend only |
| `cd src/frontend && npm run build` | Build frontend for production |

---

## Architecture

```
python -m aios
  ├── __main__.py (launcher)         ← launcher orchestration
  │   ├── check_python()               verify Python >= 3.12
  │   ├── check_node()                 verify Node.js >= 18
  │   ├── wait_for_backend()           health poll with module detail
  │   ├── fetch_runtime_info()         API: tools, caps, settings
  │   ├── health validation            verify core services
  │   └── graceful shutdown            terminate both subprocesses
  │
  ├── aios.main                       ← uvicorn + FastAPI (backend)
  │   ├── lifespan (startup)            init all services
  │   └── /api/v1/ endpoints            REST API on :8456
  │
  └── src/frontend (Vite)             ← React dev server (frontend)
      └── Vite proxy                    /api → 127.0.0.1:8456
```

No existing startup logic was changed. The launcher is an orthogonal module that spawns the existing entry points as child processes and monitors their health.

---

## Launcher v1.0.0

- Banner with version, architecture, and environment info
- Progress output per service module
- Health validation before browser launch
- Runtime summary with capability/tool counts
- Friendly error diagnostics with suggested fixes
- Structured logging (startup time, PIDs, shutdown reason)
- Graceful process termination on exit
- Auto-install of frontend dependencies
