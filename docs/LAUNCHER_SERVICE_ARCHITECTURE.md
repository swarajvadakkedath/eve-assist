# Launcher Service Architecture

## Overview

The Launcher Service transforms Eve's launcher from a monolithic entry point into a reusable orchestration engine. It separates concerns into independent services, removes UI ownership, introduces lifecycle events, and exposes a status API.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        eve.py / eve.bat                         │
│                   (thin entry point — delegates to              │
│                    DesktopLauncher wrapper)                     │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                   DesktopLauncher (launcher.py)                  │
│   Optional UI layer: SplashScreen, FirstRunWizard, TrayService  │
│   Wraps LauncherService for standalone desktop use               │
│   Future Tauri: SKIP this layer, call LauncherService directly   │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    LauncherService                               │
│           (launcher_service.py + launcher_api.py)                │
│                                                                  │
│   initialize() | start() | stop() | restart() | shutdown()      │
│   status() → LauncherStatus | health() → dict                   │
│   on_event() / off_event() — subscribe to lifecycle events      │
│   launch_frontend() | open_devtools() | open_health()           │
└──────┬──────┬──────┬──────┬──────┬──────┬──────┬─────────────────┘
       │      │      │      │      │      │      │
       ▼      ▼      ▼      ▼      ▼      ▼      ▼
┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐
│Config  ││Logger  ││Process ││Backend ││Frontend││Health  ││Provider│
│Service ││Service ││Service ││Service ││Service ││Service ││Service │
└────────┘└────────┘└────────┘└────────┘└────────┘└────────┘└────────┘
                                              ┌────────┐┌────────┐
                                              │  Tray  ││Startup │
                                              │ Service││Service │
                                              └────────┘└────────┘
                                              ┌────────┐
                                              │Shutdown│
                                              │Service │
                                              └────────┘
```

## Key Design Decisions

### 1. LauncherService is UI-agnostic
- Does NOT open browser windows
- Does NOT own application windows
- Does NOT hardcode frontend type
- `launch_frontend()` is a convenience method, not required for operation
- Future Tauri can call `LauncherService.start()` without browser involvement

### 2. Services are independent and composable
Each service has a single responsibility:
- **ConfigService** — settings management (JSON-backed)
- **LoggerService** — log setup, rotation, folder access
- **ProcessService** — subprocess lifecycle (low-level, no domain knowledge)
- **BackendService** — backend process (domain: Python subprocess)
- **FrontendService** — frontend process (abstracted via `FrontendProtocol`)
- **HealthService** — health polling, provider detection, event emission
- **ProviderService** — AI provider connectivity checks
- **TrayService** — system tray (abstracted; pystray now, Tauri later)
- **StartupService** — orchestration of startup sequence
- **ShutdownService** — orchestration of shutdown sequence

### 3. FrontendService is abstracted
```python
class FrontendProtocol(Protocol):
    async def start(self, url: str) -> int: ...
    async def stop(self, timeout: float): ...
    async def restart(self, timeout: float) -> int: ...
    async def is_alive(self) -> bool: ...
    def get_type(self) -> str: ...
```
- Current: `BrowserFrontendService` launches `npm run dev`
- Future: `TauriFrontendService` launches native window
- LauncherService only depends on the protocol

### 4. Lifecycle Events
Events are typed dataclasses with a string type identifier:

| Event | Meaning |
|-------|---------|
| `launcher:starting` | Initialization started |
| `launcher:ready` | All services running |
| `launcher:stopping` | Shutdown initiated |
| `launcher:stopped` | All services stopped |
| `launcher:error` | Startup failure |
| `backend:started` | Backend process started |
| `backend:stopped` | Backend process stopped |
| `backend:failed` | Backend health failure |
| `backend:degraded` | Backend health degraded |
| `frontend:started` | Frontend process started |
| `frontend:stopped` | Frontend process stopped |
| `provider:connected` | AI provider connected |
| `provider:disconnected` | AI provider disconnected |
| `service:health_changed` | Service health transition |
| `shutdown:requested` | Shutdown requested |
| `shutdown:completed` | Shutdown finished |
| `restart:requested` | Restart initiated |
| `restart:completed` | Restart finished |

### 5. Status API
```python
@dataclass
class LauncherStatus:
    state: str          # initializing | running | stopping | stopped | error
    version: str        # launcher version
    started_at: float   # timestamp
    backend_url: str
    frontend_url: str
    frontend_type: str  # "browser" or "tauri"
    services: dict      # name → status string
    providers: dict     # name → {connected, error}
    uptime: float       # seconds since start
```

### 6. DI-Friendly Design
Every service accepts its dependencies via constructor injection. No global state. No module-level singletons. All services can be registered in the existing `DIContainer` from `src/backend/aios/core/di_container.py`.

```python
# Example: wiring all services
config = ConfigService()
logs = LoggerService()
ps = ProcessService()
backend = BackendService(ps)
frontend = BrowserFrontendService(ps)
svc = LauncherService(
    config_service=config,
    logger_service=logs,
    process_service=ps,
    backend_service=backend,
    frontend_service=frontend,
)
await svc.initialize()
await svc.start()
```

### 7. Backward Compatibility
All old import paths still work via re-export wrappers:
- `launcher.config.LauncherConfig` → `LauncherConfig(ConfigService)`
- `launcher.logger.setup_launcher_logging` → creates fresh `LoggerService`
- `launcher.process_manager.ProcessManager` → `ProcessService`
- `launcher.health_checker.HealthChecker` → `HealthService`
- `launcher.startup.StartupOrchestrator` → `StartupOrchestrator(StartupService)`
- `launcher.shutdown.ShutdownManager` → `ShutdownManager(ShutdownService)`
- `launcher.tray.TrayManager` → `TrayService`

All 31 old tests pass unchanged.

## Migration Path: Sprint 2 (Tauri)

```
Sprint 1.5 (Current)           Sprint 2 (Tauri)
─────────────────              ──────────────
eve.py                         Eve.exe (Tauri)
  └─ DesktopLauncher              └─ LauncherService (unchanged)
       └─ LauncherService              ├─ initialize()
            ├─ initialize()            ├─ start()
            ├─ start()                 ├─ shutdown()
            ├─ shutdown()              └─ status()
            ├─ BrowserFrontendService  └─ TauriFrontendService
            └─ TrayService (pystray)   └─ TrayService (Tauri native)
```

## Startup Sequence

```
LauncherService.initialize()
  ├─ LoggerService.setup()
  ├─ ConfigService() — load/save
  ├─ Create HealthService
  ├─ Create ProviderService
  ├─ Create StartupService
  └─ Create ShutdownService

LauncherService.start()
  ├─ StartupService.run()
  │   ├─ BackendService.start() → wait for health
  │   ├─ ProviderService.check_all()
  │   └─ Return success/failure
  ├─ HealthService.start_monitoring()
  └─ Emit LAUNCHER_READY

LauncherService.shutdown()
  ├─ Emit SHUTDOWN_REQUESTED
  ├─ ShutdownService.shutdown()
  │   ├─ HealthService.stop_monitoring()
  │   ├─ FrontendService.stop()
  │   └─ BackendService.stop()
  └─ Emit SHUTDOWN_COMPLETED
```

## File Layout

```
launcher/
    __init__.py                     ← version (1.1.0)
    launcher.py                     ← DesktopLauncher (thin UI wrapper)
    launcher_service.py             ← LauncherService (orchestration API)
    launcher_api.py                 ← LauncherStatus, LauncherAPI
    launcher_events.py              ← event types and constants
    config.py                       ← backward-compat re-export
    logger.py                       ← backward-compat re-export
    process_manager.py              ← backward-compat re-export
    health_checker.py               ← backward-compat re-export
    startup.py                      ← backward-compat re-export
    shutdown.py                     ← backward-compat re-export
    tray.py                         ← backward-compat re-export
    splash.py                       ← unchanged (optional UI)
    first_run.py                    ← unchanged (optional UI)
    updater.py                      ← unchanged
    services/
        __init__.py
        config_service.py           ← ConfigService
        logger_service.py           ← LoggerService
        process_service.py          ← ProcessService
        backend_service.py          ← BackendService
        frontend_service.py         ← BrowserFrontendService + FrontendProtocol
        health_service.py           ← HealthService
        provider_service.py         ← ProviderService
        tray_service.py             ← TrayService (abstracted)
        startup_service.py          ← StartupService
        shutdown_service.py         ← ShutdownService
```
