@echo off
:: ============================================================
:: ATS Maintenance Tool - Acer Aspire Lite AL15-41 Edition
:: AMD Ryzen 7 5700U | Windows 11 Home | 477GB NVMe SSD
:: Adapted from Renz John Concepcion's original by Guardian
:: ============================================================

setlocal EnableExtensions EnableDelayedExpansion
color 0A
title ATS Maintenance Tool - Aspire Lite AL15-41

:: -------------------------
:: Admin rights check
:: -------------------------
fltmc >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [!] This tool must be run as Administrator.
    echo  [!] Right-click this file ^> "Run as administrator"
    echo.
    pause
    exit /b 1
)

:: -------------------------
:: powercfg GUIDs
:: (Universal - same on all Windows 11 systems)
:: -------------------------
set "PROC_SUBGROUP=54533251-82be-4824-96c1-47b60b740d00"
set "PROC_MAX=bc5038f7-23e0-4960-96da-33abaf5935ec"
set "PROC_MIN=893dee8e-2bef-41e0-89c6-b55d0929964c"
set "COOL_POLICY=94d3a615-a899-4ac5-ae2b-e4d8f634367f"

set "GUID_BALANCED=381b4222-f694-41f0-9685-ff5bb260df2e"
set "GUID_HIGH=8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
set "GUID_SAVER=a1841308-3541-4fab-bc81-f71556f20b4a"

:: -------------------------
:: Detect Windows Edition
:: (Needed for VHDX compact method)
:: -------------------------
for /f "tokens=3*" %%A in ('reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion" /v "EditionID" 2^>nul') do set "WIN_ED=%%A"

:menu
cls
echo.
echo  ============================================================
echo       ATS MAINTENANCE TOOL
echo       Acer Aspire Lite AL15-41 ^| AMD Ryzen 7 5700U
echo       Windows 11 Home ^| 477 GB NVMe SSD
echo  ============================================================
echo   [1] System ^& Network Cleanup  (DISM + SFC + Cache + Net)
echo   [2] Docker ^& WSL2 Cleanup     (VHDX compact + prune)
echo   [3] Generate Battery Report
echo   [4] Exit
echo  ============================================================
echo.
set "mode="
set /p mode=  Enter your choice (1-4): 

if "%mode%"=="1" goto cleanup
if "%mode%"=="2" goto docker_clean
if "%mode%"=="3" goto battery
if "%mode%"=="4" goto end

echo  [!] Invalid choice. Try again...
timeout /t 2 >nul
goto menu

:: ============================================================
:cleanup
:: ============================================================
cls
echo.
echo  ===== System ^& Network Cleanup =====
echo  Target: AMD Ryzen 7 5700U ^| NVMe SSD ^| Windows 11 Home
echo.

:: -------------------------
:: Power plan selection
:: Ryzen 5700U thermal note included
:: -------------------------
echo  Select Power Plan (defaults to [4] Smooth^&Fast in 8 seconds):
echo.
echo   [1] Balanced          - Standard plan, CPU boosts freely
echo   [2] High Performance  - Max CPU, WARNING: increases heat on 5700U
echo   [3] Power Saver       - Caps CPU, best for thermal recovery
echo   [4] Smooth ^& Fast     - 85%% CPU cap + passive cooling [DEFAULT]
echo.
choice /c 1234 /n /t 8 /d 4 /m "  Choice: "
set "psel=%errorlevel%"

if "%psel%"=="1" goto plan_balanced
if "%psel%"=="2" goto plan_high
if "%psel%"=="3" goto plan_saver
goto plan_smooth

:plan_balanced
echo.
echo  [>>] Activating Balanced plan...
powercfg /setactive %GUID_BALANCED% >nul 2>&1
echo  [OK] Balanced plan active.
goto after_plan

:plan_high
echo.
echo  ============================================================
echo  [!] WARNING: High Performance on Ryzen 7 5700U
echo      This WILL raise CPU temps significantly.
echo      Your Aspire Lite AL15-41 has limited cooling headroom.
echo      Recommended only when plugged in + on a hard flat surface.
echo  ============================================================
echo.
choice /c yn /n /m "  Are you sure? (Y/N): "
if errorlevel 2 goto menu
echo.
echo  [>>] Activating High Performance plan...
powercfg /setactive %GUID_HIGH% >nul 2>&1
powercfg /setacvalueindex SCHEME_CURRENT %PROC_SUBGROUP% %PROC_MAX% 100 >nul 2>&1
powercfg /setacvalueindex SCHEME_CURRENT %PROC_SUBGROUP% %PROC_MIN% 100 >nul 2>&1
powercfg /setacvalueindex SCHEME_CURRENT %PROC_SUBGROUP% %COOL_POLICY% 0 >nul 2>&1
powercfg /setdcvalueindex SCHEME_CURRENT %PROC_SUBGROUP% %PROC_MAX% 100 >nul 2>&1
powercfg /setdcvalueindex SCHEME_CURRENT %PROC_SUBGROUP% %PROC_MIN% 100 >nul 2>&1
powercfg /setdcvalueindex SCHEME_CURRENT %PROC_SUBGROUP% %COOL_POLICY% 0 >nul 2>&1
powercfg /setactive SCHEME_CURRENT >nul 2>&1
echo  [OK] High Performance active. Monitor your temperatures closely.
goto after_plan

:plan_saver
echo.
echo  [>>] Activating Power Saver plan (best for thermal recovery)...
powercfg /setactive %GUID_SAVER% >nul 2>&1
echo  [OK] Power Saver active.
goto after_plan

:plan_smooth
echo.
echo  [>>] Applying Smooth ^& Fast (85%% CPU cap + passive cooling)...
powercfg /setactive %GUID_BALANCED% >nul 2>&1
:: AC (plugged in)
powercfg /setacvalueindex SCHEME_CURRENT %PROC_SUBGROUP% %PROC_MAX% 85 >nul 2>&1
powercfg /setacvalueindex SCHEME_CURRENT %PROC_SUBGROUP% %PROC_MIN% 5  >nul 2>&1
powercfg /setacvalueindex SCHEME_CURRENT %PROC_SUBGROUP% %COOL_POLICY% 1 >nul 2>&1
:: DC (on battery)
powercfg /setdcvalueindex SCHEME_CURRENT %PROC_SUBGROUP% %PROC_MAX% 75 >nul 2>&1
powercfg /setdcvalueindex SCHEME_CURRENT %PROC_SUBGROUP% %PROC_MIN% 5  >nul 2>&1
powercfg /setdcvalueindex SCHEME_CURRENT %PROC_SUBGROUP% %COOL_POLICY% 1 >nul 2>&1
powercfg /setactive SCHEME_CURRENT >nul 2>&1
echo  [OK] Smooth ^& Fast active (AC: 85%% cap, Battery: 75%% cap, passive cooling ON).
goto after_plan

:after_plan
echo.

:: -------------------------
:: [1/11] DISM
:: -------------------------
echo  [1/11] Running DISM RestoreHealth (may take 10-20 min)...
DISM /Online /Cleanup-Image /RestoreHealth
echo  [OK] DISM complete.
echo.

:: -------------------------
:: [2/11] SFC
:: -------------------------
echo  [2/11] Running SFC System File Check...
sfc /scannow
echo  [OK] SFC complete.
echo.

:: -------------------------
:: [3/11] DNS Flush
:: -------------------------
echo  [3/11] Flushing DNS Cache...
ipconfig /flushdns >nul 2>&1
echo  [OK] DNS cache flushed.

:: -------------------------
:: [4/11] Temp Files
:: -------------------------
echo  [4/11] Cleaning Temp Files...
:: User temp
del /f /q "%TEMP%\*" >nul 2>&1
for /d %%G in ("%TEMP%\*") do rmdir /s /q "%%G" >nul 2>&1
:: Windows temp
del /f /q "C:\Windows\Temp\*" >nul 2>&1
for /d %%G in ("C:\Windows\Temp\*") do rmdir /s /q "%%G" >nul 2>&1
:: Prefetch (safe to clear; Windows rebuilds it automatically)
del /f /q "C:\Windows\Prefetch\*" >nul 2>&1
echo  [OK] Temp files cleaned.

:: -------------------------
:: [5/11] Browser Cache
:: -------------------------
echo  [5/11] Clearing Browser Caches...
echo  NOTE: Close all browsers first. Locked files will be skipped.

:: Chrome
if exist "%LocalAppData%\Google\Chrome\User Data" (
    for /d %%P in ("%LocalAppData%\Google\Chrome\User Data\*") do (
        if exist "%%P\Cache"      rmdir /s /q "%%P\Cache"      >nul 2>&1
        if exist "%%P\Code Cache" rmdir /s /q "%%P\Code Cache" >nul 2>&1
        if exist "%%P\GPUCache"   rmdir /s /q "%%P\GPUCache"   >nul 2>&1
    )
    echo  [OK] Chrome cache cleared.
)

:: Edge
if exist "%LocalAppData%\Microsoft\Edge\User Data" (
    for /d %%P in ("%LocalAppData%\Microsoft\Edge\User Data\*") do (
        if exist "%%P\Cache"      rmdir /s /q "%%P\Cache"      >nul 2>&1
        if exist "%%P\Code Cache" rmdir /s /q "%%P\Code Cache" >nul 2>&1
        if exist "%%P\GPUCache"   rmdir /s /q "%%P\GPUCache"   >nul 2>&1
    )
    echo  [OK] Edge cache cleared.
)

:: Firefox
if exist "%APPDATA%\Mozilla\Firefox\Profiles" (
    for /d %%P in ("%APPDATA%\Mozilla\Firefox\Profiles\*") do (
        if exist "%%P\cache2"        rmdir /s /q "%%P\cache2"        >nul 2>&1
        if exist "%%P\offlineCache"  rmdir /s /q "%%P\offlineCache"  >nul 2>&1
        if exist "%%P\startupCache"  rmdir /s /q "%%P\startupCache"  >nul 2>&1
    )
    echo  [OK] Firefox cache cleared.
)

:: VS Code / Electron cache (relevant for your dev workflow)
if exist "%AppData%\Code\Cache"           rmdir /s /q "%AppData%\Code\Cache"           >nul 2>&1
if exist "%AppData%\Code\CachedData"      rmdir /s /q "%AppData%\Code\CachedData"      >nul 2>&1
if exist "%AppData%\Code\CachedExtensions" rmdir /s /q "%AppData%\Code\CachedExtensions" >nul 2>&1
echo  [OK] VS Code cached data cleared.

:: -------------------------
:: [6/11] NVMe Drive Optimization
:: (SSD TRIM - safe; /O selects best method per drive type)
:: -------------------------
echo  [6/11] Optimizing NVMe SSD (TRIM)...
defrag C: /O /U
echo  [OK] SSD TRIM issued.

:: -------------------------
:: [7/11] Windows Update Cache
:: -------------------------
echo  [7/11] Clearing Windows Update download cache...
net stop wuauserv /y >nul 2>&1
net stop bits /y    >nul 2>&1
if exist "C:\Windows\SoftwareDistribution\Download" (
    del /f /q /s "C:\Windows\SoftwareDistribution\Download\*" >nul 2>&1
    echo  [OK] Windows Update cache cleared.
)
net start wuauserv >nul 2>&1
net start bits     >nul 2>&1

:: -------------------------
:: [8/11] Delivery Optimization Cache
:: -------------------------
echo  [8/11] Clearing Delivery Optimization cache...
net stop dosvc /y >nul 2>&1
if exist "%ProgramData%\Microsoft\Windows\DeliveryOptimization\Cache" (
    del /f /q "%ProgramData%\Microsoft\Windows\DeliveryOptimization\Cache\*" >nul 2>&1
    for /d %%G in ("%ProgramData%\Microsoft\Windows\DeliveryOptimization\Cache\*") do rmdir /s /q "%%G" >nul 2>&1
    echo  [OK] Delivery Optimization cache cleared.
)
net start dosvc >nul 2>&1

:: -------------------------
:: [9/11] Network: WinHTTP + Winsock + TCP Reset
:: -------------------------
echo  [9/11] Resetting network stack...
set "RESETLOG=%TEMP%\netsh-reset.log"
netsh winhttp reset proxy                           >nul 2>&1
netsh winsock reset                                 >nul 2>&1
netsh int ip reset "%RESETLOG%"                     >nul 2>&1
netsh int tcp set global autotuninglevel=normal     >nul 2>&1
netsh int tcp set global rss=enabled                >nul 2>&1
echo  [OK] Winsock + TCP-IP reset. Log: %RESETLOG%

:: -------------------------
:: [10/11] Clear destination cache
:: (Replaces "delete arpcache" which is removed in Win 11)
:: -------------------------
echo  [10/11] Clearing IP destination cache...
netsh interface ipv4 delete destinationcache >nul 2>&1
echo  [OK] IP destination cache cleared.

:: -------------------------
:: [11/11] Renew IP
:: -------------------------
echo  [11/11] Renewing IP (DHCP adapters)...
ipconfig /renew >nul 2>&1
echo  [OK] IP renewed.

:: -------------------------
:: Pagefile advisory (based on your 16GB RAM system)
:: -------------------------
echo.
echo  ============================================================
echo  [ADVISORY] Pagefile ^& Hibernate Tip for Your System:
echo    - Your RAM is 16 GB. A pagefile of 4-8 GB is sufficient.
echo    - If pagefile.sys ^> 8 GB, run the Guardian PowerShell
echo      disk cleanup script to reclaim space.
echo    - Hibernate (hiberfil.sys ~6 GB) can be disabled if not
echo      used: run  powercfg /hibernate off  as Admin.
echo  ============================================================
echo.

echo  === Cleanup Complete ===
echo  IMPORTANT: Restart recommended for Winsock/TCP-IP changes to apply.
echo.
pause
goto menu

:: ============================================================
:docker_clean
:: ============================================================
cls
echo.
echo  ===== Docker ^& WSL2 Cleanup =====
echo  Targets: docker_data.vhdx + unused images/containers/volumes
echo.

:: Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo  [!] Docker Desktop is NOT running.
    echo  [!] Please start Docker Desktop first, then re-run this option.
    echo.
    pause
    goto menu
)

echo  [1/3] Pruning unused Docker images, containers, volumes...
echo  WARNING: This removes all stopped containers + unused images.
choice /c yn /n /m "  Proceed with docker system prune -af? (Y/N): "
if errorlevel 2 goto menu
docker system prune -af --volumes
echo  [OK] Docker prune complete.
echo.

echo  [2/3] Shutting down WSL2 for VHDX compaction...
wsl --shutdown >nul 2>&1
timeout /t 3 >nul
echo  [OK] WSL2 shut down.
echo.

echo  [3/3] Compacting docker_data.vhdx...
set "VHDX=%LOCALAPPDATA%\Docker\wsl\disk\docker_data.vhdx"
if not exist "%VHDX%" (
    echo  [!] VHDX not found at: %VHDX%
    echo  [!] Docker Desktop may use a different path. Check manually.
    pause
    goto menu
)

:: Windows 11 Home uses diskpart (Optimize-VHD requires Pro/Enterprise)
echo  [>>] Using diskpart method (Windows 11 Home compatible)...
echo  select vdisk file="%VHDX%"  > "%TEMP%\compact_vhdx.txt"
echo  attach vdisk readonly       >> "%TEMP%\compact_vhdx.txt"
echo  compact vdisk               >> "%TEMP%\compact_vhdx.txt"
echo  detach vdisk                >> "%TEMP%\compact_vhdx.txt"
echo  exit                        >> "%TEMP%\compact_vhdx.txt"
diskpart /s "%TEMP%\compact_vhdx.txt"
del /f /q "%TEMP%\compact_vhdx.txt" >nul 2>&1
echo  [OK] VHDX compact complete. Docker Desktop may take a moment to restart WSL2.
echo.
pause
goto menu

:: ============================================================
:battery
:: ============================================================
cls
echo.
echo  ===== Generating Battery Report =====
echo  Device: Acer Aspire Lite AL15-41 (confirmed laptop with battery)
echo.
set "report=%USERPROFILE%\Desktop\battery-report.html"
powercfg /batteryreport /output "%report%" >nul 2>&1
if exist "%report%" (
    echo  [OK] Battery report saved to: %report%
    echo  [>>] Opening report in browser...
    start "" "%report%"
    echo.
    echo  TIP: Check "BATTERY CAPACITY HISTORY" section for wear/health.
    echo       For Ryzen 7 5700U: a healthy battery should show Design
    echo       Capacity close to Full Charge Capacity. If Full is ^<80%%
    echo       of Design, consider a battery replacement.
) else (
    echo  [!] Battery report failed to generate.
    echo      Possible causes: WMI service issue or driver problem.
    echo      Try: net start winmgmt  and run again.
)
echo.
pause
goto menu

:end
cls
echo.
echo  ============================================================
echo   Maintenance Completed - Aspire Lite AL15-41
echo   Restart your system to apply all changes.
echo  ============================================================
echo.
pause
endlocal
exit /b 0
