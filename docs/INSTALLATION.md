# Eve Desktop — Installation Guide

## System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| OS | Windows 10 1809+ (64-bit) | Windows 11 23H2+ |
| RAM | 4 GB | 8 GB |
| Disk | 500 MB free | 1 GB free |
| Python | **Not required** (bundled) | N/A |
| WebView2 | Windows 10/11 (included) | Latest version via Windows Update |

## Installation

### Method 1: NSIS Installer (Recommended)

1. Download `Eve_[version]_x64-setup.exe` from the release page
2. Double-click the installer
3. Follow the setup wizard (defaults are recommended)
4. A desktop shortcut and Start Menu entry are created automatically
5. Double-click "Eve OS" to launch

**No additional setup required.** Python, launcher, and backend are bundled in the installer.

### Method 2: Standalone Binary

For advanced users who want to use system Python.

1. Download `eve-desktop.exe` from the release page
2. Create a folder (e.g., `C:\Program Files\Eve\`)
3. Copy `eve-desktop.exe` into the folder
4. Copy `resources/` directory alongside it (from the installer or build output)
5. Ensure Python 3.12+ is installed and on PATH
6. Double-click `eve-desktop.exe` to launch

## First Launch

On first launch, Eve will:

1. Start the Eve desktop window (no console/terminal)
2. Initialize the embedded Python launcher
3. Start the backend service (port 8456)
4. Perform health checks
5. Show the system tray icon
6. Display the main application window

**Total startup time:** ~5-15 seconds (depending on system)

## What's Included

The installer bundles everything needed to run Eve:

| Component | Included | Source |
|-----------|----------|--------|
| Python 3.12.9 | ✅ Bundled | Embeddable CPython from python.org |
| Launcher module | ✅ Bundled | `launcher/` directory |
| Backend (aios) | ✅ Bundled | `src/backend/` directory |
| Frontend (React) | ✅ Bundled | Built from `src/frontend/` |
| Python dependencies | ✅ Bundled | 70+ packages from requirements.txt |
| Application binary | ✅ Bundled | Rust/Tauri shell (26 MB) |

## Uninstallation

### Via NSIS Installer

1. Open Settings → Apps → Installed Apps
2. Find "Eve OS" in the list
3. Click Uninstall
4. Follow the uninstaller wizard

### Manual Uninstall (standalone binary)

1. Delete the installation folder
2. Delete `%USERPROFILE%\.eve\` (launcher data, settings)
3. Delete `%LOCALAPPDATA%\eve-desktop` (window state)

## User Data

Eve stores user data separately from the application:

| Data | Location |
|------|----------|
| Launcher config | `%USERPROFILE%\.eve\launcher_config.json` |
| Logs | `%USERPROFILE%\.eve\logs\` |
| Desktop state | `%LOCALAPPDATA%\eve-desktop\` |
| Backend data | `%USERPROFILE%\.eve\` |

User data is preserved during uninstall/reinstall.

## Troubleshooting

### "Python not found" on launch

1. This error should not occur with the installer — Python is bundled
2. If it does, the bundled Python may be missing or corrupted
3. Reinstall Eve
4. If the problem persists, install Python 3.12+ from https://python.org as a fallback

### Application window is blank

1. Close Eve (right-click tray → Exit)
2. Wait 5 seconds
3. Restart Eve
4. If blank, check `%USERPROFILE%\.eve\logs\` for error details

### Backend fails to start

Run the launcher directly to see detailed errors:
```powershell
cd "%LOCALAPPDATA%\Programs\Eve OS"
.\resources\python\python.exe -m launcher.tauri_integration
```

### Port 8456 already in use

Another application is using port 8456. Close the conflicting application or change the backend port configuration.

### Installer fails with "Unknown Publisher"

1. Click "More info" → "Run anyway"
2. This is expected for unsigned releases
3. Future releases will be code-signed

### Cannot uninstall

If the NSIS uninstaller fails, manually delete:
1. `%LOCALAPPDATA%\Programs\Eve OS\` (application files)
2. `%USERPROFILE%\.eve\` (user data)
3. `%LOCALAPPDATA%\eve-desktop\` (window state)
4. Desktop shortcut: `%USERPROFILE%\Desktop\Eve OS.lnk`
5. Start Menu shortcut: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Eve OS\`
