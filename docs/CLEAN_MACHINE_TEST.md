# Clean Machine Test Plan

## Objective

Validate that Eve Desktop installs and runs on a Windows machine with no development tools. This simulates the end-user experience.

## Test Environment

### Specifications
- **OS**: Windows 10 22H2 or Windows 11 23H2 (or newer)
- **Architecture**: x64
- **RAM**: 8 GB minimum
- **Disk**: 500 MB free space
- **Network**: Internet connection (for first download only)

### NOT Installed
- Python (any version)
- Rust / Cargo
- Node.js / npm
- Vite
- Git
- Source code
- Visual Studio / VS Code / any IDE
- WSL

### Pre-Installed
- WebView2 Runtime (included with Windows 11, available via update on Windows 10)
- Microsoft Visual C++ Redistributable (included with most Windows installs)

## Test Cases

### TC1: Fresh Install

**Setup**: Clean machine with no previous Eve installation.

**Steps**:
1. Download `Eve_1.0.0_x64-setup.exe`
2. Double-click installer
3. Follow installation wizard
4. Accept default installation directory

**Expected Results**:
- [ ] Installer launches without errors
- [ ] No SmartScreen warning (or user can bypass)
- [ ] Installation completes within 2 minutes
- [ ] Desktop shortcut created: `%USERPROFILE%\Desktop\Eve OS.lnk`
- [ ] Start Menu shortcut created: `Start Menu\Programs\Eve OS\Eve OS.lnk`
- [ ] Uninstaller registered in Settings → Apps

**Verification**:
```powershell
# Check installation directory
Test-Path "$env:LOCALAPPDATA\Programs\Eve OS\eve-desktop.exe"

# Check desktop shortcut
Test-Path "$env:USERPROFILE\Desktop\Eve OS.lnk"

# Check start menu shortcut
Test-Path "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Eve OS\Eve OS.lnk"

# Check uninstaller in registry
Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*" | Where-Object DisplayName -eq "Eve OS"
```

### TC2: First Launch

**Setup**: After TC1 installation completes.

**Steps**:
1. Double-click `Eve OS` desktop shortcut
2. Wait for application to start (up to 30 seconds)

**Expected Results**:
- [ ] Eve Desktop window appears
- [ ] No console window (no terminal)
- [ ] No browser window opens automatically
- [ ] Application icon appears in system tray
- [ ] Backend health check passes (HTTP 200)
- [ ] Frontend loads and is interactive
- [ ] No error dialogs

**Verification**:
```powershell
# Check if process is running
Get-Process eve-desktop -ErrorAction SilentlyContinue

# Check backend health
Invoke-RestMethod -Uri "http://127.0.0.1:8456/api/v1/system/health" -ErrorAction SilentlyContinue

# Check application window
$mainWindow = Get-Process eve-desktop -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowTitle -eq "Eve"}
```

### TC3: Restart

**Setup**: Eve Desktop is running (after TC2).

**Steps**:
1. Right-click tray icon → Exit (or close window)
2. Wait 2 seconds
3. Double-click desktop shortcut again

**Expected Results**:
- [ ] Previous process terminates cleanly
- [ ] New process starts without errors
- [ ] Backend health check passes
- [ ] Frontend loads
- [ ] All tray menu items functional

### TC4: Shutdown

**Setup**: Eve Desktop is running.

**Steps**:
1. Right-click tray icon → Exit

**Expected Results**:
- [ ] Process terminates within 5 seconds
- [ ] No lingering Python processes
- [ ] No error dialogs

**Verification**:
```powershell
# Wait for process to exit
Start-Sleep -Seconds 5
Get-Process eve-desktop -ErrorAction SilentlyContinue  # Should return nothing
Get-Process python -ErrorAction SilentlyContinue  # Should return nothing
```

### TC5: Uninstall

**Setup**: After TC1-TC4 tests.

**Steps**:
1. Open Settings → Apps → Installed apps
2. Find "Eve OS"
3. Click Uninstall
4. Confirm uninstall

**Expected Results**:
- [ ] Uninstaller launches
- [ ] Files are removed
- [ ] Desktop shortcut removed
- [ ] Start Menu shortcut removed
- [ ] Uninstaller entry removed from registry
- [ ] Application directory deleted (except user data)

**Verification**:
```powershell
# Verify app directory removed
Test-Path "$env:LOCALAPPDATA\Programs\Eve OS"  # Should be False

# Verify user data NOT removed (for future reinstall)
Test-Path "$env:USERPROFILE\.eve"  # Should be True or handled gracefully

# Verify uninstaller removed from registry
Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*" -ErrorAction SilentlyContinue | Where-Object DisplayName -eq "Eve OS"  # Should return nothing
```

### TC6: Reinstall

**Setup**: After TC5 (uninstall completed).

**Steps**:
1. Download fresh `Eve_1.0.0_x64-setup.exe`
2. Run installer
3. Launch Eve

**Expected Results**:
- [ ] Installer succeeds
- [ ] Launch succeeds
- [ ] Previous user data (if any) is preserved

### TC7: Missing Permissions

**Setup**: Install to a read-only or protected directory.

**Steps**:
1. Attempt to install to `C:\Program Files` without admin rights (installMode is currentUser, so this should not happen)
2. Attempt to launch without write access to `%USERPROFILE%`

**Expected Results**:
- [ ] Installer handles permission errors gracefully
- [ ] Error message is user-friendly
- [ ] Application does not crash without handling

### TC8: Corrupted Install

**Setup**: Delete or corrupt one or more resource files.

**Steps**:
1. Install Eve normally (TC1)
2. Delete `resources/launcher/` directory
3. Launch Eve

**Expected Results**:
- [ ] Error dialog appears with meaningful message
- [ ] Application exits gracefully (not a crash)

**Variations**:
- [ ] Delete `resources/python/python.exe`
- [ ] Delete `resources/backend/`
- [ ] Delete `resources/python/python312._pth`
- [ ] Delete `resources/python/Lib/site-packages/`

### TC9: No Network

**Setup**: Machine with no internet connection. Eve already installed (TC1).

**Steps**:
1. Disconnect network
2. Launch Eve

**Expected Results**:
- [ ] Application starts normally
- [ ] Backend starts (no network needed for local FastAPI)
- [ ] Frontend loads (local assets)
- [ ] AI providers show "disconnected" status (expected)
- [ ] No error dialogs for missing network

### TC10: Upgrade (Same Version)

**Setup**: Eve already installed (from TC1).

**Steps**:
1. Run installer again without uninstalling first
2. Choose same install directory

**Expected Results**:
- [ ] Installer detects existing installation
- [ ] Replaces files without errors
- [ ] Shortcuts remain intact
- [ ] Launch works after install

### TC11: Multiple Monitors

**Setup**: System with 2+ monitors.

**Steps**:
1. Launch Eve
2. Move window to second monitor
3. Close and reopen

**Expected Results**:
- [ ] Window opens on remembered monitor
- [ ] Position is restored (window state plugin)

### TC12: System Tray

**Setup**: Eve is running.

**Steps**:
1. Close window (click X)
2. Verify tray icon remains

**Expected Results**:
- [ ] Window hides, application continues running
- [ ] Tray icon visible
- [ ] Click tray icon restores window
- [ ] Right-click shows menu with 7 items

## Test Summary

| TC | Test | Priority | Status |
|----|------|----------|--------|
| TC1 | Fresh Install | P0 | |
| TC2 | First Launch | P0 | |
| TC3 | Restart | P0 | |
| TC4 | Shutdown | P0 | |
| TC5 | Uninstall | P0 | |
| TC6 | Reinstall | P0 | |
| TC7 | Missing Permissions | P1 | |
| TC8 | Corrupted Install | P1 | |
| TC9 | No Network | P2 | |
| TC10 | Upgrade | P2 | |
| TC11 | Multi-Monitor | P2 | |
| TC12 | System Tray | P1 | |

## Success Criteria

- [ ] All P0 tests pass
- [ ] At least 80% of all tests pass
- [ ] No unhandled crashes in any test
- [ ] Backend always returns HTTP 200 on `/api/v1/system/health`
- [ ] Frontend loads without errors in WebView
