# Embedded Python Runtime

## Approach

We use the **official embeddable CPython distribution** from python.org (Option D). This is the most maintainable approach because:

- **Official**: Same Python you know, just packaged differently
- **Small**: ~10 MB base, grows to ~273 MB with all dependencies
- **Isolated**: No interaction with system Python installations
- **Updatable**: Simple zip replacement to upgrade Python version
- **No build step**: Direct .py execution, no compilation

## Bundle Script

`desktop/scripts/bundle-python.ps1` automates the entire process:

1. Downloads `python-3.12.9-embed-amd64.zip` from python.org
2. Extracts to `desktop/src-tauri/python/`
3. Configures `python312._pth` for correct import paths
4. Downloads `get-pip.py` and installs pip
5. Installs all dependencies from `requirements.txt`
6. Copies `launcher/` and `backend/` modules alongside the Python dir

## Path Configuration (`python312._pth`)

The `._pth` file controls how the embedded Python finds modules:

```
python312.zip      # stdlib
.                  # current directory (python/)
import site        # enable site.main() for pip packages
..                 # parent dir (resources/) — adds launcher to path
..\backend         # parent/backend — adds aios module to path
.\Lib\site-packages  # pip-installed packages
```

This ensures:
- `python -m launcher.tauri_integration` finds the launcher module
- `python -m aios.main` finds the backend module
- All pip-installed dependencies (fastapi, uvicorn, openai, etc.) are importable

## Python Version

**Python 3.12.9** — the last binary release of the 3.12 series before it moved to security-only source releases.

To upgrade Python version:
1. Update `$PythonVersion` in `desktop/scripts/bundle-python.ps1`
2. Run `npm run bundle:python`
3. Rebuild: `npm run eve:build`

## Resource Directory Layout (Installed)

```
resources/
├── python/                 # Embedded Python 3.12.9
│   ├── python.exe          # Interpreter (console)
│   ├── pythonw.exe         # Interpreter (windowless)
│   ├── python312.dll
│   ├── python3.dll
│   ├── python312._pth      # Path configuration
│   ├── python312.zip       # Standard library
│   ├── Lib/site-packages/  # All pip dependencies
│   └── DLLs/
├── launcher/               # Launcher Python module
│   ├── __init__.py
│   └── tauri_integration.py
└── backend/                # Backend Python module
    └── aios/
        └── main.py
```

## Python Resolution (Rust Side)

In `desktop/src-tauri/src/launcher.rs`, the `spawn()` method resolves Python in this order:

### Production (`#[cfg(not(debug_assertions))]`)
1. Check `resource_dir/python/python.exe` (bundled)
2. If not found, fall back to system Python (with warning)
3. If no Python found, show error dialog

### Debug (`#[cfg(debug_assertions)]`)
1. Check system Python (python, python3, py)
2. If not found, show error dialog

## PYTHONPATH

The `build_pythonpath()` function constructs PYTHONPATH to include:

- `resources/` (parent of launcher/)
- `resources/backend/` (parent of aios/)
- `resources/python/Lib/site-packages/`
- `resources/python/DLLs/`
- The executable directory

## Dependency Size

| Category | Size |
|----------|------|
| Embeddable Python base | 10.6 MB |
| pip + wheel | 1.8 MB |
| Web framework (fastapi, uvicorn, starlette) | 3.2 MB |
| AI SDKs (openai, anthropic) | 2.6 MB |
| System (psutil, pywin32) | 7.0 MB |
| Automation (playwright, PyAutoGUI) | 38.5 MB |
| Speech (SpeechRecognition, pyttsx3, comtypes) | 33.9 MB |
| Image (Pillow, pytesseract) | 7.2 MB |
| Testing (pytest, ruff, mypy) | 23.4 MB |
| Other dependencies | 144.4 MB |
| **Total** | **272.5 MB** |

## Python Environment Variables

The embedded Python respects these environment variables:

- `PYTHONPATH` — additional module search paths
- `PYTHONHOME` — not set; Python uses its own location
- `PYTHONUNBUFFERED` — set for proper stdout line buffering
- `PYTHONDONTWRITEBYTECODE` — not set; .pyc files are written to avoid recompilation

## Limitations

- **No pip at runtime**: pip is removed from the bundled runtime to save space. Dependencies are pre-installed.
- **No Tcl/Tk**: Not included in embeddable distribution. Not needed by Eve.
- **No IDLE**: Not included. Not needed.
- **No documentation**: Not included. Not needed.
- **Single architecture**: Only x64 is supported. ARM64 requires a separate build.
