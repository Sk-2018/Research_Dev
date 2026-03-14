# ============================================================
#  SmartDiskOptimizer.ps1  v2.0
#  Safe Edition — never touches system/app install paths
#  Run as: Administrator
# ============================================================

#region ── Helpers ──────────────────────────────────────────
function Write-Header($msg) {
    Write-Host "`n╔══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host   "║  $msg" -ForegroundColor Cyan
    Write-Host   "╚══════════════════════════════════════════════════════╝" -ForegroundColor Cyan
}
function Write-OK($msg)     { Write-Host "  [✔] $msg" -ForegroundColor Green }
function Write-Warn($msg)   { Write-Host "  [!] $msg" -ForegroundColor Yellow }
function Write-Info($msg)   { Write-Host "  [»] $msg" -ForegroundColor White }
function Write-Skip($msg)   { Write-Host "  [-] $msg" -ForegroundColor DarkGray }
function Write-Blocked($msg){ Write-Host "  [PROTECTED] $msg" -ForegroundColor Red }
function Write-Action($msg) { Write-Host "  [ACTION] $msg" -ForegroundColor Magenta }

function Get-FileSizeGB($path) {
    if (Test-Path $path -ErrorAction SilentlyContinue) {
        return [math]::Round((Get-Item $path -Force -ErrorAction SilentlyContinue).Length / 1GB, 2)
    }
    return $null
}

function Prompt-Confirm($question) {
    $ans = Read-Host "  [?] $question (y/n)"
    return ($ans -match '^[Yy]')
}
#endregion

#region ── PROTECTED PATHS (never touch these) ──────────────
# Any file whose path starts with or contains these segments is BLOCKED
$PROTECTED_PREFIXES = @(
    "C:\Windows",
    "C:\Program Files",
    "C:\Program Files (x86)",
    "C:\ProgramData",
    "C:\$Recycle.Bin",
    "C:\$WinREAgent",
    "C:\Recovery",
    "C:\System Volume Information",
    "C:\Boot",
    "C:\EFI",
    "C:\MSOCache",
    "C:\OneDriveTemp",
    "C:\Users\All Users",
    "C:\Users\Default",
    "C:\Users\Public"
)

# Specific protected filenames (regardless of location)
$PROTECTED_FILENAMES = @(
    "ntldr", "bootmgr", "bootnxt", "boot.ini",
    "ntdetect.com", "io.sys", "msdos.sys",
    "desktop.ini", "thumbs.db", "ntuser.dat",
    "ntuser.dat.log", "usrclass.dat"
)

# Extensions that are NEVER safe to auto-delete
$PROTECTED_EXTENSIONS = @(
    ".exe", ".dll", ".sys", ".msi", ".inf", ".cat",
    ".drv", ".ocx", ".cpl", ".scr", ".com",
    ".reg", ".bat", ".cmd", ".ps1",
    ".lnk", ".url", ".ini", ".cfg", ".conf",
    ".json", ".xml", ".yaml", ".yml",
    ".db", ".sqlite", ".mdf", ".ldf"
)

function Test-IsProtected($fullPath) {
    if ([string]::IsNullOrWhiteSpace($fullPath)) { return $true }

    $normalised = $fullPath.TrimEnd('\').ToLower()

    # Check prefix match
    foreach ($prefix in $PROTECTED_PREFIXES) {
        if ($normalised.StartsWith($prefix.ToLower())) {
            return $true
        }
    }

    # Check filename
    $fname = [System.IO.Path]::GetFileName($normalised)
    foreach ($pf in $PROTECTED_FILENAMES) {
        if ($fname -eq $pf.ToLower()) { return $true }
    }

    # Check extension
    $ext = [System.IO.Path]::GetExtension($normalised)
    foreach ($pe in $PROTECTED_EXTENSIONS) {
        if ($ext -eq $pe.ToLower()) { return $true }
    }

    return $false
}
#endregion

#region ── SAFE SCAN PATHS (only scan these) ────────────────
# Scanning is RESTRICTED to these folders for safety
$SAFE_SCAN_ROOTS = @(
    "$env:USERPROFILE\Downloads",
    "$env:USERPROFILE\Documents",
    "$env:USERPROFILE\Desktop",
    "$env:USERPROFILE\Videos",
    "$env:USERPROFILE\Music",
    "$env:USERPROFILE\Pictures",
    "$env:USERPROFILE\AppData\Local\Temp",
    "$env:USERPROFILE\AppData\Local\Docker",
    "$env:USERPROFILE\AppData\Local\pip",
    "$env:USERPROFILE\AppData\Local\npm-cache",
    "$env:USERPROFILE\AppData\Roaming\npm-cache",
    "$env:USERPROFILE\AppData\Local\JetBrains",
    "$env:USERPROFILE\AppData\Local\Google\Chrome\User Data\Default\Cache",
    "$env:USERPROFILE\AppData\Local\Microsoft\Edge\User Data\Default\Cache",
    "C:\Temp",
    "C:\Logs"
)

# SYSTEM-LEVEL special files allowed for targeted handling (not general scan)
$SYSTEM_SPECIAL_FILES = @(
    "C:\pagefile.sys",
    "C:\hiberfil.sys",
    "C:\swapfile.sys"
)
#endregion

#region ── Categorizer ──────────────────────────────────────
function Get-FileCategory($fullName) {
    switch -Wildcard ($fullName.ToLower()) {
        "*docker_data.vhdx"  { return "DOCKER_VHDX" }
        "*ext4.vhdx"         { return "WSL_VHDX" }
        "*pagefile.sys"      { return "PAGEFILE" }
        "*hiberfil.sys"      { return "HIBERFIL" }
        "*swapfile.sys"      { return "SWAPFILE" }
        "*.zip"              { return "ARCHIVE" }
        "*.tar"              { return "ARCHIVE" }
        "*.gz"               { return "ARCHIVE" }
        "*.7z"               { return "ARCHIVE" }
        "*.rar"              { return "ARCHIVE" }
        "*.iso"              { return "ISO" }
        "*.vhd"              { return "VHD" }
        "*.vhdx"             { return "VHD" }
        "*.vmdk"             { return "VMDK" }
        "*.bak"              { return "BACKUP" }
        "*.log"              { return "LOG" }
        "*.mp4"              { return "MEDIA" }
        "*.mkv"              { return "MEDIA" }
        "*.avi"              { return "MEDIA" }
        "*.mov"              { return "MEDIA" }
        "*.mp3"              { return "MEDIA" }
        "*\temp\*"           { return "TEMP" }
        "*appdata\local\temp*" { return "TEMP" }
        "*node_modules*"     { return "NODE_MODULES" }
        "*\.nuget\*"         { return "NUGET_CACHE" }
        "*pip\cache*"        { return "PIP_CACHE" }
        "*npm-cache*"        { return "NPM_CACHE" }
        "*jetbrains*"        { return "IDE_CACHE" }
        "*\cache\*"          { return "GENERIC_CACHE" }
        default              { return "UNKNOWN" }
    }
}

function Get-Recommendation($category) {
    switch ($category) {
        "DOCKER_VHDX"    { return @{ Action="AUTO";   Desc="Prune Docker images/containers + compact VHDX" } }
        "WSL_VHDX"       { return @{ Action="AUTO";   Desc="Compact WSL VHDX virtual disk" } }
        "PAGEFILE"       { return @{ Action="AUTO";   Desc="Resize pagefile: auto → fixed 2GB/4GB" } }
        "HIBERFIL"       { return @{ Action="PROMPT"; Desc="Disable hibernation to remove (~6 GB freed)" } }
        "SWAPFILE"       { return @{ Action="INFO";   Desc="Managed by Windows — leave unless hiberfil is off" } }
        "ARCHIVE"        { return @{ Action="PROMPT"; Desc="Delete if already extracted or no longer needed" } }
        "ISO"            { return @{ Action="PROMPT"; Desc="Delete if software is already installed" } }
        "VHD"            { return @{ Action="PROMPT"; Desc="Compact or delete if VM/disk is unused" } }
        "VMDK"           { return @{ Action="PROMPT"; Desc="Compact or delete if VM is unused" } }
        "BACKUP"         { return @{ Action="PROMPT"; Desc="Move to external drive or delete old copies" } }
        "LOG"            { return @{ Action="PROMPT"; Desc="Safe to delete if not actively debugging" } }
        "MEDIA"          { return @{ Action="PROMPT"; Desc="Move to external/NAS or delete" } }
        "TEMP"           { return @{ Action="PROMPT"; Desc="Temporary file — safe to delete" } }
        "NODE_MODULES"   { return @{ Action="PROMPT"; Desc="Delete & restore with 'npm install' when needed" } }
        "PIP_CACHE"      { return @{ Action="PROMPT"; Desc="Run: pip cache purge" } }
        "NPM_CACHE"      { return @{ Action="PROMPT"; Desc="Run: npm cache clean --force" } }
        "NUGET_CACHE"    { return @{ Action="PROMPT"; Desc="Run: dotnet nuget locals all --clear" } }
        "IDE_CACHE"      { return @{ Action="PROMPT"; Desc="JetBrains/IDE cache — safe to clear from IDE settings" } }
        "GENERIC_CACHE"  { return @{ Action="PROMPT"; Desc="App cache — inspect before deleting" } }
        default          { return @{ Action="INFO";   Desc="Unknown type — inspect manually" } }
    }
}
#endregion

# ── Admin check ─────────────────────────────────────────────
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Warn "Re-run this script as Administrator!"
    exit 1
}

$totalSaved   = 0
$blockedCount = 0
$allFiles     = @()

# ════════════════════════════════════════════════════════════
#  STEP 1 — Disk Usage Overview for C:\
# ════════════════════════════════════════════════════════════
Write-Header "STEP 1 — C:\ Drive Overview"

$drive        = Get-PSDrive C
$totalGB      = [math]::Round(($drive.Used + $drive.Free) / 1GB, 2)
$usedGB       = [math]::Round($drive.Used / 1GB, 2)
$freeGB       = [math]::Round($drive.Free / 1GB, 2)
$usedPct      = [math]::Round(($drive.Used / ($drive.Used + $drive.Free)) * 100, 1)
$barFilled    = [math]::Round($usedPct / 5)
$bar          = ("█" * $barFilled) + ("░" * (20 - $barFilled))

Write-Host ""
Write-Host "  Drive  : C:\" -ForegroundColor White
Write-Host "  Total  : $totalGB GB" -ForegroundColor White
Write-Host "  Used   : $usedGB GB  ($usedPct%)" -ForegroundColor $(if ($usedPct -gt 85) {"Red"} elseif ($usedPct -gt 65) {"Yellow"} else {"Green"})
Write-Host "  Free   : $freeGB GB" -ForegroundColor White
Write-Host "  [$bar] $usedPct%" -ForegroundColor $(if ($usedPct -gt 85) {"Red"} elseif ($usedPct -gt 65) {"Yellow"} else {"Cyan"})

if ($usedPct -gt 90) { Write-Warn "CRITICAL: Disk is over 90% full!" }
elseif ($usedPct -gt 75) { Write-Warn "WARNING: Disk usage above 75% — cleanup recommended." }
else { Write-OK "Disk usage is healthy." }

# ════════════════════════════════════════════════════════════
#  STEP 2 — Add system special files first (pagefile, hiberfil)
# ════════════════════════════════════════════════════════════
Write-Header "STEP 2 — Checking System-Managed Special Files"

foreach ($sf in $SYSTEM_SPECIAL_FILES) {
    if (Test-Path $sf -ErrorAction SilentlyContinue) {
        $item = Get-Item $sf -Force -ErrorAction SilentlyContinue
        if ($item) {
            $sizeGB   = [math]::Round($item.Length / 1GB, 2)
            $category = Get-FileCategory $sf
            $rec      = Get-Recommendation $category
            Write-Info "$sf  →  $sizeGB GB  [$category]"
            $allFiles += [PSCustomObject]@{
                Rank     = 0
                SizeGB   = $sizeGB
                Category = $category
                FullName = $sf
                Action   = $rec.Action
                Desc     = $rec.Desc
                Source   = "SYSTEM"
            }
        }
    }
}

# ════════════════════════════════════════════════════════════
#  STEP 3 — Scan safe user paths for large files
# ════════════════════════════════════════════════════════════
Write-Header "STEP 3 — Scanning Safe User Paths for Large Files"
Write-Info "Only scanning user-owned, non-system directories..."
Write-Info "Protected system paths are excluded automatically."
Write-Host ""

$scannedFiles = @()
foreach ($root in $SAFE_SCAN_ROOTS) {
    if (Test-Path $root -ErrorAction SilentlyContinue) {
        Write-Info "Scanning: $root"
        $found = Get-ChildItem $root -Recurse -Force -ErrorAction SilentlyContinue |
                 Where-Object { -not $_.PSIsContainer } |
                 Where-Object { -not (Test-IsProtected $_.FullName) }
        $scannedFiles += $found
    }
}

$topScanned = $scannedFiles |
              Sort-Object Length -Descending |
              Select-Object -First 10

Write-Host ""
Write-Host ("  {0,-5} {1,-10} {2,-18} {3}" -f "#", "Size(GB)", "Category", "Path") -ForegroundColor Cyan
Write-Host ("  {0,-5} {1,-10} {2,-18} {3}" -f "---", "--------", "--------", "----") -ForegroundColor DarkGray

$rank = 1
foreach ($f in $topScanned) {
    # Skip if already captured as system special file
    if ($SYSTEM_SPECIAL_FILES -contains $f.FullName) { continue }

    $sizeGB   = [math]::Round($f.Length / 1GB, 2)
    $category = Get-FileCategory $f.FullName
    $rec      = Get-Recommendation $category

    # Final safety gate — double-check before adding
    if (Test-IsProtected $f.FullName) {
        $blockedCount++
        Write-Blocked "Skipped (protected): $($f.FullName)"
        continue
    }

    $color = switch ($rec.Action) {
        "AUTO"   { "Green" }
        "PROMPT" { "Yellow" }
        default  { "DarkGray" }
    }

    Write-Host ("  {0,-5} {1,-10} {2,-18} {3}" -f $rank, "$sizeGB GB", $category, $f.FullName) -ForegroundColor $color
    $allFiles += [PSCustomObject]@{
        Rank     = $rank
        SizeGB   = $sizeGB
        Category = $category
        FullName = $f.FullName
        Action   = $rec.Action
        Desc     = $rec.Desc
        Source   = "SCAN"
    }
    $rank++
}

Write-Host ""
Write-Info "Files blocked by protection rules: $blockedCount"
Write-Info "Legend: [Green]=Auto-handled  [Yellow]=Needs decision  [Gray]=Info only"

# ════════════════════════════════════════════════════════════
#  STEP 4 — Interactive Processing
# ════════════════════════════════════════════════════════════
Write-Header "STEP 4 — Processing Recommendations"

foreach ($item in ($allFiles | Sort-Object SizeGB -Descending)) {
    Write-Host ""
    Write-Host "  ── $($item.FullName)" -ForegroundColor White
    Write-Host "     Size     : $($item.SizeGB) GB" -ForegroundColor Gray
    Write-Host "     Category : $($item.Category)" -ForegroundColor Gray
    Write-Action $item.Desc

    # FINAL protection gate before any action
    if (($item.Source -ne "SYSTEM") -and (Test-IsProtected $item.FullName)) {
        Write-Blocked "Action blocked — path matched system protection rules."
        continue
    }

    switch ($item.Action) {

        "AUTO" {
            switch ($item.Category) {

                "PAGEFILE" {
                    if (Prompt-Confirm "Resize pagefile to Initial=2GB / Max=4GB? (saves ~$([math]::Round($item.SizeGB - 4,2)) GB after reboot)") {
                        try {
                            $cs = Get-CimInstance Win32_ComputerSystem
                            $cs.AutomaticManagedPagefile = $false
                            Set-CimInstance -InputObject $cs
                            $pf = Get-CimInstance Win32_PageFileSetting | Where-Object { $_.Name -like "C:\*" }
                            if ($null -eq $pf) {
                                Set-WmiInstance -Class Win32_PageFileSetting -Arguments @{
                                    Name="C:\pagefile.sys"; InitialSize=2048; MaximumSize=4096
                                } | Out-Null
                            } else {
                                $pf.InitialSize = 2048; $pf.MaximumSize = 4096
                                Set-CimInstance -InputObject $pf
                            }
                            $est = [math]::Max(0, [math]::Round($item.SizeGB - 4, 2))
                            $totalSaved += $est
                            Write-OK "Pagefile resized to 2-4 GB. Reboot required. (Est. saved: $est GB)"
                        } catch { Write-Warn "Failed: $_" }
                    } else { Write-Skip "Skipped." }
                }

                { $_ -in "DOCKER_VHDX","WSL_VHDX","VHD" } {
                    if (Prompt-Confirm "Compact VHDX '$($item.FullName)'?") {
                        $before = Get-FileSizeGB $item.FullName

                        if ($item.Category -eq "DOCKER_VHDX") {
                            Write-Info "Running docker system prune -af ..."
                            docker system prune -af 2>&1 | ForEach-Object { Write-Info $_ }
                        }

                        Write-Info "Shutting down WSL..."
                        wsl --shutdown
                        Start-Sleep -Seconds 5

                        if (Get-Command Optimize-VHD -ErrorAction SilentlyContinue) {
                            Write-Info "Using Optimize-VHD (Pro/Enterprise)..."
                            Optimize-VHD -Path $item.FullName -Mode Full
                        } else {
                            Write-Info "Using diskpart (Home edition fallback)..."
                            $ds = "select vdisk file=`"$($item.FullName)`"`r`nattach vdisk readonly`r`ncompact vdisk`r`ndetach vdisk`r`nexit"
                            $tmp = "$env:TEMP\compact_vhdx.txt"
                            $ds | Out-File $tmp -Encoding ASCII
                            diskpart /s $tmp
                            Remove-Item $tmp -Force
                        }

                        $after = Get-FileSizeGB $item.FullName
                        $saved = [math]::Max(0, [math]::Round($before - $after, 2))
                        $totalSaved += $saved
                        Write-OK "VHDX compacted: $before GB → $after GB  (saved $saved GB)"
                    } else { Write-Skip "Skipped VHDX compaction." }
                }
            }
        }

        "PROMPT" {
            switch ($item.Category) {

                "HIBERFIL" {
                    if (Prompt-Confirm "Disable hibernation? This removes hiberfil.sys (~$($item.SizeGB) GB)") {
                        powercfg /hibernate off
                        $totalSaved += $item.SizeGB
                        Write-OK "Hibernation disabled. File removed on reboot."
                    } else { Write-Skip "Skipped." }
                }

                "ARCHIVE" {
                    if (Prompt-Confirm "Delete archive? '$($item.FullName)' ($($item.SizeGB) GB)") {
                        Remove-Item $item.FullName -Force -ErrorAction SilentlyContinue
                        $totalSaved += $item.SizeGB
                        Write-OK "Deleted. Saved $($item.SizeGB) GB."
                    } else { Write-Skip "Skipped." }
                }

                { $_ -in "LOG","TEMP","MEDIA","ISO","BACKUP" } {
                    if (Prompt-Confirm "Delete '$($item.FullName)'? ($($item.SizeGB) GB)") {
                        Remove-Item $item.FullName -Force -ErrorAction SilentlyContinue
                        $totalSaved += $item.SizeGB
                        Write-OK "Deleted. Saved $($item.SizeGB) GB."
                    } else { Write-Skip "Skipped." }
                }

                "NODE_MODULES" {
                    Write-Info "Restore later with: cd <project-folder> && npm install"
                    if (Prompt-Confirm "Delete node_modules at '$($item.FullName)'? ($($item.SizeGB) GB)") {
                        Remove-Item $item.FullName -Recurse -Force -ErrorAction SilentlyContinue
                        $totalSaved += $item.SizeGB
                        Write-OK "Deleted. Saved $($item.SizeGB) GB."
                    } else { Write-Skip "Skipped." }
                }

                "PIP_CACHE" {
                    if (Prompt-Confirm "Clear pip cache? (~$($item.SizeGB) GB)") {
                        pip cache purge 2>&1 | ForEach-Object { Write-Info $_ }
                        $totalSaved += $item.SizeGB
                        Write-OK "pip cache purged."
                    } else { Write-Skip "Skipped." }
                }

                "NPM_CACHE" {
                    if (Prompt-Confirm "Clear npm cache? (~$($item.SizeGB) GB)") {
                        npm cache clean --force 2>&1 | ForEach-Object { Write-Info $_ }
                        $totalSaved += $item.SizeGB
                        Write-OK "npm cache cleared."
                    } else { Write-Skip "Skipped." }
                }

                "NUGET_CACHE" {
                    if (Prompt-Confirm "Clear NuGet cache? (~$($item.SizeGB) GB)") {
                        dotnet nuget locals all --clear 2>&1 | ForEach-Object { Write-Info $_ }
                        $totalSaved += $item.SizeGB
                        Write-OK "NuGet cache cleared."
                    } else { Write-Skip "Skipped." }
                }

                default {
                    Write-Skip "Unknown category — open manually: explorer.exe '/select,$($item.FullName)'"
                }
            }
        }

        "INFO" { Write-Skip "Informational only — no automated action." }
    }
}

# ════════════════════════════════════════════════════════════
#  STEP 5 — Post-Cleanup Disk Status
# ════════════════════════════════════════════════════════════
Write-Header "STEP 5 — Post-Cleanup Disk Status"

$driveAfter   = Get-PSDrive C
$freeGBAfter  = [math]::Round($driveAfter.Free / 1GB, 2)
$usedGBAfter  = [math]::Round($driveAfter.Used / 1GB, 2)
$usedPctAfter = [math]::Round(($driveAfter.Used / ($driveAfter.Used + $driveAfter.Free)) * 100, 1)
$barFilled2   = [math]::Round($usedPctAfter / 5)
$bar2         = ("█" * $barFilled2) + ("░" * (20 - $barFilled2))

Write-Host ""
Write-Host "  Used (before) : $usedGB GB  ($usedPct%)" -ForegroundColor Gray
Write-Host "  Used (after)  : $usedGBAfter GB  ($usedPctAfter%)" -ForegroundColor Green
Write-Host "  Free (after)  : $freeGBAfter GB" -ForegroundColor White
Write-Host "  [$bar2] $usedPctAfter%" -ForegroundColor Cyan
Write-Host ""
Write-OK "Session total freed : ~$([math]::Round($totalSaved, 2)) GB"
Write-Warn "Reboot required for pagefile + hibernation changes to fully apply."
Write-Info "Tip: Re-run monthly to keep C:\ healthy."
Write-Host ""
