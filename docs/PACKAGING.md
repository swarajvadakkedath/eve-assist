# Eve Desktop — Packaging Guide

## Bundle Structure (Installed)

```
%LOCALAPPDATA%\Programs\Eve OS\
│
├── eve-desktop.exe                    — Main executable (26 MB release)
├── resources/
│   ├── python/                        — Embedded Python 3.12.9
│   │   ├── python.exe                 — Interpreter (console)
│   │   ├── pythonw.exe                — Interpreter (windowless)
│   │   ├── python312.dll              — Python C API
│   │   ├── python3.dll                — Stable ABI
│   │   ├── python312._pth             — Path configuration
│   │   ├── python312.zip              — Standard library (.pyc)
│   │   ├── Lib/site-packages/         — 70+ pip dependencies
│   │   ├── DLLs/                      — C extension modules
│   │   └── ...
│   ├── launcher/                      — Launcher Python module (28 files)
│   │   ├── __init__.py
│   │   ├── tauri_integration.py
│   │   ├── launcher_service.py
│   │   ├── config.py
│   │   └── services/
│   └── backend/                       — Backend module (aios package)
│       └── aios/
│           ├── __init__.py
│           ├── main.py
│           └── ...
├── icons/                             — Application icons
├── LICENSE                            — MIT license
└── Uninstall Eve OS.exe               — NSIS uninstaller
```

## Resource Bundling (Tauri)

In `tauri.conf.json`, resources are specified relative to `desktop/src-tauri/`:

```json
"resources": {
  "../../launcher/**/*.py": "launcher/",
  "../../src/backend/**/*.py": "backend/",
  "python/**/*": "python/"
}
```

| Source Path (relative to src-tauri/) | Bundle Target |
|--------------------------------------|---------------|
| `../../launcher/**/*.py` (Eve_Ai/launcher/) | `resources/launcher/` |
| `../../src/backend/**/*.py` (Eve_Ai/src/backend/) | `resources/backend/` |
| `python/**/*` (src-tauri/python/) | `resources/python/` |

At runtime:
- `app.path().resource_dir()` returns the resources directory
- `resources/python/python.exe` is the bundled Python interpreter
- `PYTHONPATH` is set to include all resource directories

## Frontend Assets

Built by `beforeBuildCommand: "npm run build:frontend"`:
```powershell
cd ../src/frontend && npx vite build
```

Output: `src/frontend/dist/`
- `index.html` — Entry point (0.45 KB)
- `assets/index-BIQ1KEst.css` — Styles (107 KB)
- `assets/index-CXahS12_.js` — Application JS (300 KB)

In release builds, Tauri embeds these assets from `frontendDist: "../../src/frontend/dist"`.

## Embedded Python

See `EMBEDDED_PYTHON.md` for full details.

| Detail | Value |
|--------|-------|
| Distribution | Official embeddable CPython 3.12.9 |
| Download | `python-3.12.9-embed-amd64.zip` (10.6 MB) |
| Total with deps | ~273 MB |
| Bundle script | `desktop/scripts/bundle-python.ps1` |
| Build command | `npm run bundle:python` |
| Path config | `python312._pth` |

Python dependencies are pre-installed into `Lib/site-packages/`:
- **Web**: fastapi, uvicorn, starlette, pydantic, httpx
- **AI**: openai, anthropic
- **System**: psutil, pywin32
- **Automation**: playwright, PyAutoGUI, pytesseract
- **Voice**: SpeechRecognition, pyttsx3
- **Utilities**: Pillow, pyperclip, pyyaml, structlog, aiosqlite
- **Dev** (bundled for development): pytest, ruff, mypy

## Icons

| File | Usage |
|------|-------|
| `icons/32x32.png` | App icon (small) |
| `icons/128x128.png` | App icon (large) |
| `icons/128x128@2x.png` | App icon (HiDPI) |
| `icons/icon.ico` | Windows icon + NSIS installer icon |

## NSIS Installer Config

```json
{
  "nsis": {
    "installMode": "currentUser",
    "languages": ["English"],
    "displayLanguageSelector": false,
    "startMenuFolder": "Eve OS",
    "installerIcon": "icons/icon.ico",
    "compression": "lzma"
  }
}
```

| Setting | Effect |
|---------|--------|
| `installMode: currentUser` | Install to `%LOCALAPPDATA%\Programs\Eve OS` (no admin) |
| `startMenuFolder: "Eve OS"` | Creates Start Menu folder with shortcut |
| `installerIcon: icon.ico` | Custom installer icon |
| `compression: lzma` | Best compression ratio (~3:1 for Python) |

## Platform Metadata

| Field | Value | Source |
|-------|-------|--------|
| Product name | Eve | `tauri.conf.json` |
| Version | 1.0.0 | `tauri.conf.json` / `Cargo.toml` |
| Publisher | Eve OS | `tauri.conf.json` |
| Copyright | 2026 Eve OS | `tauri.conf.json` |
| Description | Eve OS — AI Operating System for your desktop | `tauri.conf.json` |
| Identifier | com.eve.desktop | `tauri.conf.json` |
| Category | Utility | `tauri.conf.json` |
| License | MIT | `tauri.conf.json` |

## Installer Output

| Component | Path |
|-----------|------|
| NSIS installer | `desktop/src-tauri/target/release/bundle/nsis/Eve_1.0.0_x64-setup.exe` |
| Release binary | `desktop/src-tauri/target/release/eve-desktop.exe` |
| Python bundle | `desktop/src-tauri/python/` |

## File Sizes

| Component | Raw | Compressed (LZMA) |
|-----------|-----|-------------------|
| eve-desktop.exe | 26.1 MB | 26.1 MB |
| Python runtime + deps | 272.5 MB | ~60 MB |
| Frontend assets | 0.4 MB | 0.4 MB |
| Launcher + backend | ~0.1 MB | ~0.1 MB |
| **Installer total** | — | **~89 MB** |

## Release Checklist

- [ ] Version bumped in `tauri.conf.json`, `Cargo.toml`, `package.json`, `launcher/__init__.py`
- [ ] `npm run bundle:python` succeeds and Python imports work
- [ ] `npm run build:frontend` succeeds (0 warnings)
- [ ] `npm run tauri:build` succeeds (NSIS installer generated)
- [ ] Installer size acceptable (< 150 MB)
- [ ] Desktop shortcut created on install
- [ ] Start Menu shortcut created on install
- [ ] Uninstaller registered in Windows Apps & Features
- [ ] Fresh launch: no Python error (bundled Python used)
- [ ] Fresh launch: backend health returns 200
- [ ] Fresh launch: frontend loads in window
- [ ] Fresh launch: tray icon visible with 7 menu items
- [ ] Exit: no lingering Python processes
- [ ] Clean machine test passes (TC1-TC6)
- [ ] Installer checksum generated (SHA-256)
