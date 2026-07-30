# Auto-Update Architecture

## Overview

Eve Desktop supports automatic updates. The architecture is designed to allow version checking, download, installation, restart, and rollback. Current implementation is a placeholder — auto-updates are disabled by default.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Eve Desktop                          │
├──────────────────────┬──────────────────────────────────────┤
│   Rust Shell         │   Python Launcher                    │
│   (tauri)            │   (updater.py)                       │
│                      │                                      │
│  tauri-plugin-       │  Updater class:                      │
│  updater (optional)  │  • check_for_update()                │
│                      │  • download_update()                 │
│                      │  • apply_update()                    │
│                      │                                      │
│  app.handle().       │  Communicates via stdin/stdout JSON  │
│  process().restart() │  Same protocol as launcher:          │
│                      │  {"type":"command","command":"update"}│
└──────────────────────┴──────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────┐
│              Update Server                │
│  https://updates.eveos.ai/latest         │
│                                           │
│  Response:                                │
│  {                                        │
│    "version": "1.1.0",                    │
│    "download_url": "https://...",         │
│    "changelog": "...",                    │
│    "mandatory": false,                    │
│    "checksum_sha256": "..."               │
│  }                                        │
└──────────────────────────────────────────┘
```

## Update Flow

### Version Check

1. At startup or periodic interval, `Updater.check_for_update()` is called
2. Sends HTTP GET to `https://updates.eveos.ai/latest`
3. Server responds with `UpdateInfo` JSON
4. Compares `version` with `LAUNCHER_VERSION` from `launcher/__init__.py`
5. If newer version available, emits event to UI

### Download

1. `Updater.download_update(info)` downloads the new installer to `%TEMP%\eve_update_{version}.exe`
2. Downloads to temporary file with `.partial` extension
3. Verifies SHA-256 checksum against server-provided hash
4. Renames `.partial` to final name on successful verification
5. Reports progress via JSON events: `{"type":"update_status","state":"downloading","progress":0.5}`

### Install

1. `Updater.apply_update(info)` launches the downloaded installer silently:
   ```python
   subprocess.run([
       installer_path,
       "/S",                             # Silent install (NSIS)
       "/D=" + install_dir,              # Same install directory
   ], check=True)
   ```
2. NSIS silently replaces all application files
3. User data in `%USERPROFILE%\.eve\` is preserved

### Restart

1. After update installation, send `{"type":"command","command":"restart"}` to launcher
2. Tauri `process().restart()` restarts the application
3. New version runs with preserved user data

### Rollback

1. Previous version is preserved in `resources/previous/` during update
2. If new version fails to start within 30 seconds:
   - Copy `resources/previous/` back to application directory
   - Restart with previous version
3. Rollback is automatic — no user action required

## Implementation Status

| Component | Status | File |
|-----------|--------|------|
| UpdateInfo dataclass | ✅ Complete | `launcher/updater.py` |
| Updater class (stub) | ✅ Complete | `launcher/updater.py` |
| check_for_update() | ⏸ Placeholder | Returns `available=False` |
| download_update() | ⏸ Placeholder | Returns `False` |
| apply_update() | ⏸ Placeholder | Returns `False` |
| SHA-256 verification | ❌ Not implemented | |
| Progress reporting | ❌ Not implemented | |
| Rollback mechanism | ❌ Not implemented | |
| Server endpoint | ❌ Not deployed | |
| UI notification | ❌ Not implemented | |

## Server API Design

### Endpoint

```
GET https://updates.eveos.ai/api/v1/update/latest
```

### Request Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `current_version` | string | Current installed version (e.g., "1.0.0") |
| `platform` | string | `windows-x64`, `windows-arm64` |
| `channel` | string | `stable`, `beta`, `alpha` |

### Response

```json
{
  "version": "1.1.0",
  "download_url": "https://updates.eveos.ai/download/v1.1.0/Eve_1.1.0_x64-setup.exe",
  "checksum_sha256": "a1b2c3d4e5f6...",
  "changelog_url": "https://updates.eveos.ai/changelog/v1.1.0",
  "changelog": "## What's New\n- ...",
  "mandatory": false,
  "size_bytes": 93657542,
  "release_date": "2026-08-15T00:00:00Z",
  "min_version": "1.0.0"
}
```

### Error Response

```json
{
  "error": "update_check_failed",
  "message": "No internet connection"
}
```

## Tauri Integration

### Option A: tauri-plugin-updater (Recommended)

Tauri v2 provides `tauri-plugin-updater` which handles:
- Version checking
- Download with progress
- Installer execution
- Signature verification

```json
// tauri.conf.json
{
  "plugins": {
    "updater": {
      "endpoints": ["https://updates.eveos.ai/api/v1/update/latest"],
      "pubkey": "...",
      "windows": {
        "installMode": "passive"
      }
    }
  }
}
```

### Option B: Python-side updater (Current approach)

The `launcher/updater.py` does everything via Python. This is simpler to implement but requires:
- Embedded Python to have `httpx` (already bundled)
- Admin privileges for NSIS silent install

## Tray Menu Integration

When an update is available, a new tray menu item is added:

```
Open Eve
───────
Update Available: v1.1.0   ← (new, highlighted)
───────
Developer Tools
Health Dashboard
Restart Backend
Settings
Logs
───────
Exit
```

## User Preferences

Update behavior is configurable in `%USERPROFILE%\.eve\launcher_config.json`:

```json
{
  "auto_update": true,
  "update_channel": "stable",
  "last_update_check": "2026-07-23T12:00:00Z",
  "skip_version": ""
}
```
