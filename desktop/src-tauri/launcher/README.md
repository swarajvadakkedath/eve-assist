# Eve OS — Development Launcher

One-click start, stop, restart, and health check for the Eve development environment.

## Requirements

| Dependency | Version | Check |
|---|---|---|
| Python | >= 3.12 | `python --version` |
| Node.js | >= 18 | `node --version` |
| npm | (comes with Node) | `npm --version` |
| Backend deps | — | `pip install -e .` (from project root) |
| Frontend deps | — | `npm install` (from `src/frontend`) |

The launcher checks all requirements on startup and offers to install missing
dependencies interactively.

## Quick Start

Double-click **`start.bat`** or run:

```
.\start.ps1
```

The launcher will:

1. Verify Python, Node.js, and npm are installed
2. Check that backend and frontend dependencies exist
3. Start the backend (`python -m aios.main` on port 8456)
4. Wait for the backend health check (`/api/v1/system/health`)
5. Start the frontend (`npm run dev` on port 5173)
6. Wait for the frontend to be ready
7. Open the browser to `http://localhost:5173`
8. Print a summary of running services

## Commands

| Command | Description |
|---|---|
| `start.bat` / `start.ps1` | Start backend + frontend |
| `stop.bat` / `stop.ps1` | Stop backend + frontend |
| `restart.bat` / `restart.ps1` | Restart everything |
| `check.ps1` | Check server status |

## Configuration

Edit the parameters at the top of `start.ps1` and `check.ps1`:

```powershell
$BackendPort = 8456        # Backend API port
$FrontendPort = 5173       # Frontend dev server port
$StartupTimeout = 30       # Seconds to wait for each service
$BrowserUrl = "http://localhost:5173"  # URL to open in browser
```

## How It Works

- The launcher tracks process PIDs in `.eve_pids` (a JSON file in the
  `launcher/` directory).
- `stop.ps1` reads this file and kills the tracked process trees.
- `restart.ps1` calls stop then start with a brief pause.
- `check.ps1` tests both ports and the backend health endpoint, then prints a
  summary.

## Troubleshooting

### Port already in use

```
✗ Port 8456 already in use
```

Something else is running on that port. Find and stop it, or change
`$BackendPort` in the launcher config.

### Backend not ready within timeout

```
✗ Backend not ready within 30s
```

Open the backend terminal window to see error logs. Common causes:

- Missing Python dependencies (`pip install -e .`)
- Port conflict
- Python version < 3.12
- Missing `.env` or config file

### Frontend not ready within timeout

```
✗ Frontend not ready within 30s
```

Open the frontend terminal window to see error logs. Common causes:

- Missing `node_modules` (`cd src/frontend && npm install`)
- Port conflict
- Node.js version incompatibility

### No tracked PIDs

```
No tracked PIDs found.
```

The launcher PID file is missing or empty. The `stop.ps1` script can only kill
processes it started. Close terminal windows manually.

### Process detection on restart

If you run `start.ps1` while Eve is already running, the launcher will detect
the existing processes and offer to open the browser, restart, or cancel.

## File Structure

```
launcher/
  start.bat          # Double-click to start
  stop.bat           # Double-click to stop
  restart.bat        # Double-click to restart
  start.ps1          # PowerShell start script
  stop.ps1           # PowerShell stop script
  restart.ps1        # PowerShell restart script
  check.ps1          # Health check
  README.md          # This file
  .eve_pids          # (auto-generated) Process PID storage
```
