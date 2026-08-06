@echo off
REM ============================================================
REM  EVE One-Click Development Launcher - Start
REM  Double-click to start backend + frontend + browser.
REM  Logic lives in start_eve.ps1 (same directory).
REM ============================================================
setlocal
chcp 65001 >nul
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_eve.ps1"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if "%EXIT_CODE%"=="0" (
    echo [OK] EVE started successfully.
) else (
    echo [ERROR] EVE failed to start (exit code %EXIT_CODE%).
    echo        Check the messages above.
)
echo.
pause
endlocal
exit /b %EXIT_CODE%
