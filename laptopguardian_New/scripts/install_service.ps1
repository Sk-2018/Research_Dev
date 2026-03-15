@'
# Install Guardian as a Windows Scheduled Task (runs at logon, background)
# Run as Administrator

$ErrorActionPreference = "Stop"
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$PythonExe  = Join-Path $ProjectRoot "venv\Scripts\python.exe"
$MainScript = Join-Path $ProjectRoot "app\main.py"
$TaskName   = "LaptopHealthGuardian"

if (-not (Test-Path $PythonExe)) {
    Write-Error "venv not found. Run scripts\run.ps1 first to create the venv."
    exit 1
}

$Action  = New-ScheduledTaskAction -Execute $PythonExe -Argument "-m app.main" -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
             -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
             -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger `
    -Settings $Settings -RunLevel Highest -Force

Write-Host "Scheduled Task '$TaskName' registered. Guardian will start at next logon." -ForegroundColor Green
Write-Host "To start now: Start-ScheduledTask -TaskName '$TaskName'"
'@ | Out-File -FilePath "scripts\install_service.ps1" -Encoding utf8
