@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

title FortiAIGate Onboarder

echo.
echo  ============================================
echo    FortiAIGate Onboarder - Partner Edition
echo  ============================================
echo.

REM Check for uv (fast Python package + venv manager)
where uv >nul 2>&1
if errorlevel 1 (
    echo [setup] uv not found - installing via PowerShell...
    powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    REM uv installer puts itself in %USERPROFILE%\.local\bin
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
    where uv >nul 2>&1
    if errorlevel 1 (
        echo [error] uv install failed. Visit https://docs.astral.sh/uv/ for manual install.
        pause
        exit /b 1
    )
)

echo [setup] Syncing Python environment (first run ~15s, then ~1s)...
uv sync --quiet
if errorlevel 1 (
    echo [error] uv sync failed.
    pause
    exit /b 1
)

echo [setup] OK. Launching at http://localhost:8765
echo.
echo  ============================================
echo    The browser will open automatically.
echo    Close this window to stop the onboarder.
echo  ============================================
echo.

uv run python -m app.main
