@echo off
REM ============================================================
REM  EVE One-Click Development Launcher - Stop
REM  Gracefully stops backend, frontend and child processes.
REM  Logic lives in stop_eve.ps1 (same directory).
REM ============================================================
setlocal
chcp 65001 >nul
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_eve.ps1"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if "%EXIT_CODE%"=="0" (
    echo [OK] EVE stopped. No orphan processes left.
) else (
    echo [WARNING] Some processes may not have stopped cleanly.
    echo           Close the server terminal windows if they remain.
)
echo.
pause
endlocal
exit /b %EXIT_CODE%
