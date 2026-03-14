param(
    [string]$Config = "config.yaml",
    [switch]$Headless,
    [switch]$DryRun,
    [switch]$Once
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}

Write-Host "Installing dependencies..."
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r requirements.txt

$Args = @("-m", "app.main", "--config", $Config)
if ($Headless) { $Args += "--headless" }
if ($DryRun) { $Args += "--dry-run" }
if ($Once) { $Args += "--once" }

Write-Host "Starting Laptop Health Guardian..."
& $VenvPython @Args
