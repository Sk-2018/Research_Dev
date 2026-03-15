@'
# Laptop Health Guardian - Quick Runner
# Run as Administrator for full WMI/powercfg support

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Set-Location $ProjectRoot

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Laptop Health Guardian - Starting..." -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# Check Python
$py = python --version 2>&1
Write-Host "Python: $py" -ForegroundColor Green

# Install deps if needed
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt
} else {
    .\venv\Scripts\Activate.ps1
}

Write-Host "Launching Guardian... Open http://127.0.0.1:8050" -ForegroundColor Green
python -m app.main
'@ | Out-File -FilePath "scripts\run.ps1" -Encoding utf8
