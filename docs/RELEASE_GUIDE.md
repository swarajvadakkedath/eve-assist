# Eve Desktop — Release Guide

## Overview

Complete pipeline from source code to installable Windows application with embedded Python runtime.

## Release Pipeline

```
Source Code
    │
    ▼
npm run eve:build
    │
    ├── 1. bundle:python           — Download + configure embedded Python 3.12
    ├── 2. build:frontend          — Build React to src/frontend/dist/
    ├── 3. cargo build --release   — Build Rust binary (target/release/)
    └── 4. tauri build             — Generate NSIS installer
```

## Prerequisites

### Build Machine

| Tool | Version | Install |
|------|---------|---------|
| Rust | stable | `rustup install stable` |
| Node.js | 18+ LTS | `scoop install nodejs` |
| Python | 3.12+ | `scoop install python` (for bundling deps only) |
| MinGW-w64 | — | `scoop install mingw` (GNU target) |
| LLVM | — | `scoop install llvm` (for LLD linker) |
| NSIS | 3.08+ | `winget install NSIS.NSIS` or nsis.sourceforge.io |

### PATH Setup

```powershell
$env:PATH += ";C:\Program Files (x86)\NSIS\Bin"
```

### Rust Toolchain

```powershell
rustup default stable-x86_64-pc-windows-gnu
```

## Build Commands

### Full Release (One Command)

```powershell
cd E:\Eve_Ai\desktop
npm run eve:build
```

### Step-by-Step

```powershell
cd E:\Eve_Ai\desktop

# 1. Bundle embedded Python (download, extract, install deps)
npm run bundle:python

# 2. Build React frontend
npm run build:frontend

# 3. Build Rust binary + generate NSIS installer
npm run tauri:build
```

### Binary Only (No Installer)

```powershell
cd E:\Eve_Ai\desktop
npm run build:frontend
cd src-tauri
cargo build --release
```

## Output Artifacts

| Artifact | Location | Size |
|----------|----------|------|
| NSIS installer | `target/release/bundle/nsis/Eve_1.0.0_x64-setup.exe` | ~89 MB |
| Release binary | `target/release/eve-desktop.exe` | ~26 MB |
| Debug binary | `target/debug/eve-desktop.exe` | ~49 MB |
| Frontend dist | `../../src/frontend/dist/` | ~0.4 MB |
| Python bundle | `python/` | ~273 MB |

## Resource Bundling

Resources are relative to `desktop/src-tauri/`:

| Resource | Source | Bundle Target |
|----------|--------|--------------|
| Python runtime | `python/**/*` | `resources/python/` |
| Launcher module | `../../launcher/**/*.py` | `resources/launcher/` |
| Backend module | `../../src/backend/**/*.py` | `resources/backend/` |
| Frontend assets | `../../src/frontend/dist/` | (embedded via `frontendDist`) |

## Release Config

| Setting | Value | File |
|---------|-------|------|
| Product name | Eve | `tauri.conf.json` |
| Version | 1.0.0 | `tauri.conf.json`, `Cargo.toml` |
| Identifier | com.eve.desktop | `tauri.conf.json` |
| Publisher | Eve OS | `tauri.conf.json` |
| Copyright | 2026 Eve OS | `tauri.conf.json` |
| Install mode | CurrentUser | `tauri.conf.json` → NSIS |
| Compression | LZMA | `tauri.conf.json` → NSIS |
| Start Menu folder | Eve OS | `tauri.conf.json` → NSIS |
| Python version | 3.12.9 | `scripts/bundle-python.ps1` |

## Python Resolution at Runtime

**Production mode** (NSIS install):
1. Check `resources/python/python.exe` (bundled)
2. If missing, fall back to system Python
3. If not found, show error dialog

**Debug mode** (cargo build/dev):
1. System Python (`python`, `python3`, `py`)
2. If not found, show error dialog

## Verifying the Installer

```powershell
# Check installer exists and size
Get-ChildItem "target/release/bundle/nsis/Eve_1.0.0_x64-setup.exe"

# Check release binary
Get-ChildItem "target/release/eve-desktop.exe"

# Verify bundled Python works
& "python/python.exe" --version
& "python/python.exe" -c "import launcher.tauri_integration; print('ok')"
& "python/python.exe" -c "import fastapi; print(fastapi.__version__)"
```

## Troubleshooting

### Build fails: NSIS missing
Install NSIS: `winget install NSIS.NSIS` then add to PATH:
```powershell
$env:PATH += ";C:\Program Files (x86)\NSIS\Bin"
```
Make PATH permanent: `[Environment]::SetEnvironmentVariable("Path", "$env:PATH;C:\Program Files (x86)\NSIS\Bin", "User")`

### Build fails: `frontendDist` not found
The `frontendDist` path is relative to `src-tauri/`. Ensure it points to the correct dist directory:
- From `Eve_Ai/desktop/src-tauri/` to `Eve_Ai/src/frontend/dist/` → `../../src/frontend/dist`

### Resource bundling fails: file not found
Resource paths are relative to `src-tauri/`. Verify:
- `../../launcher/**/*.py` → exists at `Eve_Ai/launcher/`
- `../../src/backend/**/*.py` → exists at `Eve_Ai/src/backend/`
- `python/**/*` → exists at `Eve_Ai/desktop/src-tauri/python/`

### Installer too large
The Python runtime is ~273 MB. To reduce:
1. Remove development dependencies from requirements.txt (pytest, ruff, mypy)
2. Remove unused packages (playwright browser driver)
3. Use `--no-deps` for certain packages

### Blank window in release binary
Ensure frontend was built: `npm run build:frontend`
Check `frontendDist` points to correct directory.
Run from command line to see error output: `eve-desktop.exe`

### Linker errors (GNU target)
See `.cargo/config.toml` for LLD workaround with `--exclude-all-symbols`.
