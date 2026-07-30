@echo off
REM Eve OS Development Launcher — Start
REM Double-click this file to start the Eve development environment.

set "LAUNCHER_DIR=%~dp0"
powershell -ExecutionPolicy Bypass -NoProfile -File "%LAUNCHER_DIR%start.ps1"
if %ERRORLEVEL% neq 0 (
    echo.
    echo An error occurred. Check the messages above.
    pause
)
