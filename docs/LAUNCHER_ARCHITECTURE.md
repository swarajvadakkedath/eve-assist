# Eve Launcher Architecture

## Overview

The Eve Launcher transforms Eve from a development project into a desktop application. Users double-click `eve.bat` (or run `python eve.py`) and Eve starts — backend, frontend, services, all with a splash screen and system tray integration.

The launcher is built as a service-oriented architecture with `LauncherService` as the core orchestration engine. The service layer is UI-agnostic and reusable by future Tauri integration.

## Architecture Diagram

```
eve.py / eve.bat
     │
     ▼
DesktopLauncher (launcher.py)      ← Optional UI layer
  ┌─────────────────────────┐        (SplashScreen, TrayService,
  │  SplashScreen           │         FirstRunWizard)
  │  TrayService            │
  │  FirstRunWizard         │
  └─────────┬───────────────┘
            │
            ▼
     LauncherService (launcher_service.py)
  ┌─────────────────────────────────────┐
  │  initialize()  │  start()          │
  │  stop()        │  restart()        │
  │  shutdown()    │  status()         │
  │  health()      │  on_event()       │
  └─┬───┬───┬───┬───┬───┬───┬───┬─────┘
    │   │   │   │   │   │   │   │
    ▼   ▼   ▼   ▼   ▼   ▼   ▼   ▼
  Cfg  Log  Proc Back Fnt  Hlth Prov
  Svc  Svc  Svc  Svc  Svc  Svc  Svc
                  [FntProtocol]
                    ▲
                    │ implements
              ┌─────┴──────┐
              │            │
        BrowserFE    TauriFE (future)
```

## Service Layer

| Service | Responsibility |
|---------|---------------|
| `ConfigService` | JSON-backed settings at `~/.eve/launcher_config.json` |
| `LoggerService` | File + console logging with rotation |
| `ProcessService` | Low-level subprocess lifecycle |
| `BackendService` | Backend Python process (`python -m aios.main`) |
| `FrontendService` | Frontend process — abstracted via `FrontendProtocol` |
| `HealthService` | Health polling for backend, frontend, AI providers |
| `ProviderService` | AI provider connectivity (Gemini, Groq, Ollama, etc.) |
| `TrayService` | System tray — abstracted (pystray now, Tauri later) |
| `StartupService` | Sequential launch orchestration |
| `ShutdownService` | Graceful teardown orchestration |

## LauncherService API

```python
class LauncherService:
    async def initialize(self) -> bool     # Load config, setup logging, create services
    async def start(self) -> bool           # Run startup sequence, start health monitor
    async def stop(self)                    # Stop all services gracefully
    async def restart(self) -> bool         # Stop then start
    async def shutdown(self)                # Full shutdown (stops tray, stops services)
    def status(self) -> LauncherStatus      # Current state, services, providers, URLs
    async def health(self) -> dict          # Health check results
    def launch_frontend(self)               # Open browser frontend
    def open_devtools(self)                 # Open API docs
    def open_health_dashboard(self)         # Open health endpoint
    def open_settings(self)                 # Open settings page
    def on_event(self, handler) -> UUID     # Subscribe to lifecycle events
    def off_event(self, sub_id)             # Unsubscribe from events
```

## Lifecycle

```
stopped → initialize() → initialized → start() → running → stop() → stopped
                                                      ↓
                                                  restart()
                                                      ↓
                                                  running
```

## Events

18 lifecycle events: `launcher:starting`, `launcher:ready`, `launcher:stopping`, `launcher:stopped`, `launcher:error`, `backend:started`, `backend:stopped`, `backend:failed`, `backend:degraded`, `frontend:started`, `frontend:stopped`, `provider:connected`, `provider:disconnected`, `service:health_changed`, `shutdown:requested`, `shutdown:completed`, `restart:requested`, `restart:completed`.

## Key Design Decisions

1. **LauncherService owns no UI** — no browser opening, no window management
2. **FrontendService is pluggable** — `FrontendProtocol` allows Tauri replacement
3. **TrayService is abstracted** — can be replaced with native Tauri tray
4. **No global state** — all state lives in `LauncherService` instance
5. **Constructor injection** — all services accept dependencies via constructor
6. **Backward compatible** — old import paths still work (re-export wrappers)
7. **Events decouple** — UI components subscribe to events instead of coupling

## Backward Compatibility

All old module paths remain functional:
- `launcher.config.LauncherConfig`
- `launcher.logger.setup_launcher_logging()`
- `launcher.process_manager.ProcessManager`
- `launcher.health_checker.HealthChecker`
- `launcher.startup.StartupOrchestrator`
- `launcher.shutdown.ShutdownManager`
- `launcher.tray.TrayManager`

## File Layout

```
eve.py                          ← root entry point
eve.bat                         ← Windows double-click launcher
launcher/
    __init__.py                 ← package marker, version
    launcher.py                 ← DesktopLauncher (standalone UI wrapper)
    launcher_service.py         ← LauncherService (orchestration API)
    launcher_api.py             ← LauncherStatus, LauncherAPI
    launcher_events.py          ← lifecycle event types
    config.py                   ← backward-compat LauncherConfig
    logger.py                   ← backward-compat logger
    process_manager.py          ← backward-compat ProcessManager
    health_checker.py           ← backward-compat HealthChecker
    startup.py                  ← backward-compat StartupOrchestrator
    shutdown.py                 ← backward-compat ShutdownManager
    tray.py                     ← backward-compat TrayManager
    splash.py                   ← Tkinter splash (optional UI)
    first_run.py                ← Tkinter wizard (optional UI)
    updater.py                  ← auto-update placeholder
    services/
        __init__.py
        config_service.py
        logger_service.py
        process_service.py
        backend_service.py
        frontend_service.py
        health_service.py
        provider_service.py
        tray_service.py
        startup_service.py
        shutdown_service.py
```
