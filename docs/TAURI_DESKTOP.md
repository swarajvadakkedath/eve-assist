# Eve Desktop — Tauri Native Shell

## Architecture

```
Eve.exe (Tauri v2)
├── Rust Runtime
│   ├── Native Window (WebView2)
│   │   └── React Frontend (src/frontend/)
│   ├── System Tray (Tauri native)
│   ├── Python Launcher (child process)
│   │   └── LauncherService
│   │       ├── BackendService → python -m aios.main (port 8456)
│   │       ├── HealthService  → polls backend health
│   │       └── ConfigService  → ~/.eve/launcher_config.json
│   └── Plugins
│       ├── notification — native Windows notifications
│       ├── clipboard-manager — system clipboard
│       ├── dialog — open/save/message dialogs
│       ├── shell — open URLs, spawn processes
│       └── window-state — persist window position/size
├── WebView
│   └── Frontend communicates with Backend via HTTP
│       └── http://127.0.0.1:8456/api/v1/...
└── System Tray
    ├── Open Eve
    ├── Developer Tools
    ├── Health Dashboard
    ├── Restart Backend
    ├── Settings
    ├── Logs
    └── Exit
```

## Directory Layout

```
desktop/
├── package.json                    — npm project (tauri CLI)
├── src-tauri/
│   ├── Cargo.toml                  — Rust dependencies
│   ├── tauri.conf.json             — Tauri configuration
│   ├── build.rs                    — Tauri build script
│   ├── .cargo/config.toml          — LLD linker config (MinGW workaround)
│   ├── capabilities/
│   │   └── default.json            — Permission capabilities
│   ├── icons/
│   │   ├── 32x32.png               — App icon
│   │   ├── 128x128.png             — App icon
│   │   ├── 128x128@2x.png          — App icon (HiDPI)
│   │   └── icon.ico                — Windows icon
│   └── src/
│       ├── main.rs                 — Entry point
│       ├── lib.rs                  — App setup, window, tray, plugins
│       ├── commands.rs             — Tauri commands (IPC)
│       └── launcher.rs             — Python child process management

launcher/
├── tauri_integration.py            — Python launcher adapter
└── services/
    └── tauri_frontend_service.py   — FrontendProtocol for Tauri

src/frontend/src/services/
├── api.ts                          — Updated with Tauri URL detection
└── tauri.ts                        — Tauri IPC helpers
```

## Integration Points

### 1. LauncherService (Python) + Tauri (Rust)

Communication: **Stdin/stdout JSON lines**

**Python → Rust (stdout):**
```json
{"type":"status","state":"initialized"}
{"type":"status","state":"ready","backend_url":"http://127.0.0.1:8456"}
{"type":"response","command":"status","state":"running",...}
```

**Rust → Python (stdin):**
```json
{"type":"command","command":"status"}
{"type":"command","command":"restart"}
{"type":"command","command":"shutdown"}
```

### 2. LauncherService + LauncherService

The `tauri_integration.py` script creates a `LauncherService` without UI wrappers:
- No splash screen
- No pystray tray
- No browser launch
- Just: init → start backend → report status → listen for commands

### 3. TauriFrontendService

`launcher/services/tauri_frontend_service.py` implements `FrontendProtocol` but is a no-op — Tauri manages the webview window itself. When Tauri is the shell, `LauncherService` is initialized with `TauriFrontendService` instead of `BrowserFrontendService`.

### 4. Frontend API

`src/frontend/src/services/api.ts` detects Tauri context via `window.__TAURI_INTERNALS__`:
- In browser/dev mode: uses relative paths → Vite proxy → `http://127.0.0.1:8456`
- In Tauri production: uses absolute URL `http://127.0.0.1:8456/api/v1/...`
- No other frontend changes needed

### 5. System Tray

Native Tauri tray replaces pystray:
- Tray is created in Rust (`lib.rs`)
- Menu items: Open, DevTools, Health, Restart, Settings, Logs, Exit
- Close window → minimize to tray (handled via `WindowEvent::CloseRequested`)
- Left-click tray → show window
- Exit tray menu → shutdown Python launcher + exit app

## Development

### Prerequisites
- Rust 1.70+ (`rustup`)
- Node.js 18+
- Python 3.12+
- WebView2 (included in Windows 10+)
- MinGW-w64 + LLVM (scoop) — see Build Configuration below

### Setup

```powershell
# Install Tauri CLI
cd desktop
npm install

# Run in development mode
npm run tauri:dev
# This starts the Vite dev server and opens Tauri window
```

### Building

```powershell
cd desktop
npm run tauri:build
# Output: desktop/src-tauri/target/release/Eve.exe
# MSI installer: desktop/src-tauri/target/release/bundle/msi/
```

### One-command release build

```powershell
cd desktop
npm run eve:build
# 1. Builds React frontend → src/frontend/dist/
# 2. Builds Rust binary → target/release/eve-desktop.exe
# 3. Packages NSIS installer → target/release/bundle/nsis/
```

### Direct binary (debug, no Vite dev server)

```powershell
cd desktop/src-tauri
cargo build
./target/debug/eve-desktop.exe
# Window loads http://localhost:5173 (requires Vite running separately)
# Or use production mode (see below)
```

### Production mode preview (built frontend, no installer)

```powershell
npm run build:frontend
cd desktop/src-tauri && cargo build --release
./target/release/eve-desktop.exe
# Release mode loads from frontendDist (bundled assets)
# No Vite required. No terminal required.
```

## Build Configuration

### Toolchain: `x86_64-pc-windows-gnu`

The project uses the GNU toolchain with MinGW-w64 binutils (for `as.exe`, `dlltool.exe`) and LLVM's LLD linker (for `--exclude-all-symbols` workaround).

**Required tools (scoop):**
```powershell
scoop install mingw
scoop install llvm
```

**PATH requirement:**
Both `scoop/apps/mingw/current/bin` and `scoop/apps/llvm/current/bin` must be on PATH before cargo.

**`.cargo/config.toml`:**
```toml
[target.x86_64-pc-windows-gnu]
rustflags = ["-C", "link-args=-fuse-ld=lld -Wl,--exclude-all-symbols -Wl,--strip-all"]
```

- `-fuse-ld=lld`: Use LLVM LLD linker instead of GNU ld
- `--exclude-all-symbols --strip-all`: Workaround for PE export limit (127K symbols > 65535 max). The Windows PE format has a 65535 symbol export limit. MinGW generates exports for all symbols; LLD with these flags strips them on the PE side.

### Alternative: MSVC toolchain (requires Visual Studio BuildTools)

```powershell
scoop install visualstudio2022-workload-vctools
rustup default stable-x86_64-pc-windows-msvc
```

## Startup Sequence (Verified)

| Stage | Component | Time | Status |
|-------|-----------|------|--------|
| 1 | Binary launch, config load | ~0.1s | ✅ |
| 2 | Python launcher spawned | ~0.3s | ✅ |
| 3 | Launcher ready (backend healthy) | ~2.2s | ✅ |
| 4 | Tray + window created | ~0.1s | ✅ |
| **Total** | | **~2.6s** | ✅ |

### Detailed flow:

1. `main.rs` calls `eve_desktop::run()` → `try_run()` in `lib.rs`
2. `[eve] starting Eve Desktop` — project root resolved via `CARGO_MANIFEST_DIR`
3. Tauri Builder registers 5 plugins (notification, clipboard, dialog, shell, window-state)
4. `setup()` hook:
   - Spawns Python: `python -m launcher.tauri_integration` (60s timeout)
   - Python discovers Python via `resolve_python()` — tries `python`, `python3`, `py`
   - Python creates `LauncherService`, calls `initialize()` then `start()`
   - Backend spawned: `python -m aios.main` on port 8456
   - Health poll: waits up to 30s for `GET /api/v1/system/health` → 200
   - On healthy: Python emits `{"type":"status","state":"ready"}`
5. Rust receives "ready" → builds tray menu (7 items) → shows window
6. `[eve] startup complete in 2.6s`
7. WebView loads `http://localhost:5173` (dev) or `frontendDist/index.html` (prod)
8. Frontend detects Tauri context → uses `http://127.0.0.1:8456/api/v1/...`

### On failure:

**Launcher spawn fails (Python not found):** Error dialog (Win32 MessageBoxW) shown with message: "Python not found. Ensure Python is installed and on PATH."

**Launcher ready timeout (>60s):** Warning logged, app continues (tray + window shown without backend readiness).

**Backend health timeout (>30s):** Python reports `{"type":"status","state":"error"}`. Rust propagates as launcher failure error.

## Native APIs Used

| API | Plugin | Use |
|-----|--------|-----|
| Notifications | `tauri-plugin-notification` | Native Windows toast notifications |
| Clipboard | `tauri-plugin-clipboard-manager` | Read/write system clipboard |
| Dialogs | `tauri-plugin-dialog` | Open file, save file, message boxes |
| Shell | `tauri-plugin-shell` | Open URLs in default browser, spawn processes |
| Window State | `tauri-plugin-window-state` | Persist window position and size |
| Tray Icon | Tauri core (`tray-icon` feature) | Native system tray |
| WebView2 | Tauri core | Render React frontend |

## Tauri Commands (IPC)

| Command | Rust handler | Frontend caller | Description |
|---------|-------------|----------------|-------------|
| `get_status` | `commands::get_status` | `tauri.getStatus()` | Launcher + backend status |
| `get_health` | `commands::get_health` | `tauri.getHealth()` | Backend health check |
| `restart_backend` | `commands::restart_backend` | `tauri.restartBackend()` | Restart Python backend |
| `shutdown` | `commands::shutdown` | `tauri.shutdown()` | Graceful app shutdown |
| `show_notification` | `commands::show_notification` | `tauri.showNotification()` | Native toast |
| `open_url` | `commands::open_url` | `tauri.openUrl()` | Open URL in default browser |
| `get_app_config` | `commands::get_app_config` | `tauri.getAppConfig()` | Get launcher config |
| `set_app_config` | `commands::set_app_config` | `tauri.setAppConfig()` | Set launcher config |

## Known Issues & Fixes Applied

### Fixed

| Issue | File | Fix |
|-------|------|-----|
| Project root resolution | `launcher.rs` | Use `CARGO_MANIFEST_DIR` compile-time path instead of fragile `resource_dir().parent()` chain |
| Python discovery | `launcher.rs` | Try `python`, `python3`, `py` with `--version` probe before spawn |
| Backend `memory_store` param | `app.py` | `HealthDashboard.__init__` expects `memory`, not `memory_store` (x2: `Diagnostics` too) |
| Startup error dialog | `lib.rs` | Added Win32 `MessageBoxW` on fatal startup errors |
| Cleanup on drop | `launcher.rs` | Added `Drop` impl calling `kill()` to prevent zombie Python processes |
| Startup diagnostics | `lib.rs` | 4-stage logging with timestamps, `[eve]` prefix |
| `selectPrevious` duplicate | `CommandStore.ts` | Removed duplicate method body |
| `kill()` unused warning | `launcher.rs` | Method exists and is called via `Drop` |
| Missing `use` imports | `lib.rs`, `launcher.rs` | Added `Emitter`, `Manager`, `Read`, `Instant` |
| Deprecated `shell().open()` | `lib.rs` | Marked with `#[allow(deprecated)]` + `ShellExt` import |
| PE export limit | `.cargo/config.toml` | `--exclude-all-symbols --strip-all` via LLD |
| Icon truncation | `icons/icon.ico` | Regenerated from 32x32.png via PowerShell |

### Remaining (non-blocking)

- Frontend window shows blank page when running binary directly without Vite dev server (expected — dev URL only works with `cargo tauri dev`)
- backend shutdown waits 10s for process termination (normal — backend graceful shutdown)
- asyncio cleanup warnings on Python process exit (harmless)

## Production Flow

1. User double-clicks `Eve.exe`
2. Tauri `setup()` spawns Python `launcher/tauri_integration.py` from compiled project root
3. Python creates `LauncherService` → initializes → starts backend
4. Python writes `{"type":"status","state":"ready"}` to stdout
5. Rust receives "ready" → creates system tray → shows main window
6. WebView loads React frontend (from `frontendDist`)
7. Frontend fetches `http://127.0.0.1:8456/api/v1/...` for all API calls
8. User closes window → minimizes to tray
9. User clicks "Exit" → Rust sends "shutdown" → Python stops backend → Rust exits

## Troubleshooting

**"Python not found" error on startup:**
Verify `python --version` works in terminal. Install Python 3.12+ and ensure it's on PATH.

**Backend fails to start (app window shows but no health endpoint):**
Run the launcher directly to see backend errors:
```powershell
cd E:\Eve_Ai
$env:PYTHONPATH = "E:\Eve_Ai\src\backend"
python -m launcher.tauri_integration
```

**Build fails with link errors:**
Ensure MinGW and LLVM are on PATH:
```powershell
$env:PATH = "C:\Users\swara\scoop\apps\mingw\current\bin;C:\Users\swara\scoop\apps\llvm\current\bin;$env:PATH"
```

**Frontend blank in production:**
Ensure frontend is built:
```powershell
cd desktop && npm run build:frontend
```

## Release Pipeline

```powershell
cd E:\Eve_Ai\desktop
npm run eve:build
```

This single command:
1. Builds the React frontend via `beforeBuildCommand: npm run build:frontend`
2. Builds the Rust binary in release mode (`cargo build --release`)
3. Packages the NSIS installer via `tauri build`

### Resource Bundling

The `launcher/` Python module is bundled as a Tauri resource:

```json
"resources": {
  "../../launcher/**/*.py": "launcher/"
}
```

At runtime, the release binary sets `PYTHONPATH` to the resource directory so Python can find the launcher module. The working directory is discovered by probing upward from the executable for the `launcher/` directory.

### Installer Output

| Artifact | Path |
|----------|------|
| Release EXE | `desktop/src-tauri/target/release/eve-desktop.exe` |
| NSIS Installer | `desktop/src-tauri/target/release/bundle/nsis/Eve_1.0.0_x64-setup.exe` |
| Frontend Dist | `src/frontend/dist/` |

Details: See `docs/RELEASE_GUIDE.md`, `docs/INSTALLATION.md`, `docs/PACKAGING.md`.

## Future Improvements

- **Deep links**: Register `eve://` protocol handler for URL activation
- **Auto-start**: Registry-based launch on Windows login (`HKCU\...\Run`)
- **Auto-updater**: `tauri-plugin-updater` for in-app updates
- **Custom title bar**: Replace decorations with custom title bar for theming
- **Window tabs**: Multiple Eve windows for multi-workspace
- **Global shortcuts**: System-wide hotkeys (Ctrl+Alt+E to open Eve)
- **Taskbar progress**: Show backend status in taskbar
- **Drag-drop**: File drag-drop from OS into Eve
- **MSI signing**: Code-sign the installer
- **Frontend dist resource bundling**: Bundle `launcher/` directory as Tauri resource for release builds
