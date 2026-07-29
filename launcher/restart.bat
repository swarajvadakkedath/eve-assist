@echo off
REM Eve OS Development Launcher — Restart
REM Double-click this file to restart the Eve development environment.

set "LAUNCHER_DIR=%~dp0"
powershell -ExecutionPolicy Bypass -NoProfile -File "%LAUNCHER_DIR%restart.ps1"
if %ERRORLEVEL% neq 0 (
    echo.
    echo An error occurred. Check the messages above.
    pause
)
