@echo off
REM AIOS/Eve Launcher — starts backend and frontend with one command.
REM Run from the project root.

setlocal enabledelayedexpansion

REM Determine project root (directory containing this script)
set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

REM Ensure UTF-8 for Unicode banner characters
set "PYTHONIOENCODING=utf-8"

REM Ensure src/backend is on PYTHONPATH so python -m aios can find the package
set "BACKEND_DIR=%PROJECT_ROOT%src\backend"
if defined PYTHONPATH (
    set "PYTHONPATH=%BACKEND_DIR%;%PYTHONPATH%"
) else (
    set "PYTHONPATH=%BACKEND_DIR%"
)

REM Determine Python command — prefer py launcher, fallback to python
where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PY_CMD=py -3.12"
) else (
    set "PY_CMD=python"
)

REM Check Python
%PY_CMD% -c "import sys; assert sys.version_info >= (3, 12), 'Python 3.12+ required'" 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: Python ^>= 3.12 required.
    exit /b 1
)

REM Check Node
where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: Node.js not found. Install Node.js ^>= 18.
    exit /b 1
)

%PY_CMD% -m aios
exit /b %ERRORLEVEL%
