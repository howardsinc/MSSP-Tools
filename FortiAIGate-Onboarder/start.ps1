#Requires -Version 5.1
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$Host.UI.RawUI.WindowTitle = "FortiAIGate Onboarder"

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Red
Write-Host "    FortiAIGate Onboarder - Partner Edition" -ForegroundColor Red
Write-Host "  ============================================" -ForegroundColor Red
Write-Host ""

# Check for uv
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "[setup] uv not found - installing..." -ForegroundColor Yellow
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Host "[error] uv install failed." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

Write-Host "[setup] Syncing Python environment (first run ~15s, then ~1s)..." -ForegroundColor Cyan
uv sync --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "[error] uv sync failed." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[setup] OK. Launching at http://localhost:8765" -ForegroundColor Green
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Red
Write-Host "    The browser will open automatically." -ForegroundColor White
Write-Host "    Close this window to stop the onboarder." -ForegroundColor White
Write-Host "  ============================================" -ForegroundColor Red
Write-Host ""

uv run python -m app.main
