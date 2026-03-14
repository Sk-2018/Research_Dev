param(
    [string]$TaskName = "LaptopHealthGuardian",
    [string]$Config = "config.yaml"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    throw "Python virtual environment not found at $PythonExe. Run scripts/run.ps1 once first."
}

$ConfigPath = Join-Path $ProjectRoot $Config
if (-not (Test-Path $ConfigPath)) {
    throw "Config file not found: $ConfigPath"
}

$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument "-m app.main --headless --config `"$ConfigPath`"" -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest -LogonType Interactive
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Principal $Principal `
    -Settings $Settings `
    -Description "Laptop Health Guardian background watchdog" `
    -Force | Out-Null

Write-Host "Scheduled task '$TaskName' created."
Write-Host "Start it with: Start-ScheduledTask -TaskName $TaskName"
