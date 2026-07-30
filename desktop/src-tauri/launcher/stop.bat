@echo off
REM Eve OS Development Launcher — Stop
REM Double-click this file to stop the Eve development environment.

set "LAUNCHER_DIR=%~dp0"
powershell -ExecutionPolicy Bypass -NoProfile -File "%LAUNCHER_DIR%stop.ps1"
if %ERRORLEVEL% neq 0 pause
