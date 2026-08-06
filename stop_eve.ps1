<#
.SYNOPSIS
    EVE One-Click Development Launcher - Stop engine.

.DESCRIPTION
    Gracefully terminates the backend, frontend, and their child process
    trees recorded by start_eve.ps1, then cleans up any orphaned
    aios.main / vite processes so nothing is left behind.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File stop_eve.ps1
#>
[CmdletBinding()]
param(
    [int]$BackendPort = 8456,
    [int]$FrontendPort = 5173
)

$ErrorActionPreference = "Continue"

$Script:Root        = Split-Path -Parent $MyInvocation.MyCommand.Path
$Script:PidFile     = Join-Path $Script:Root ".eve_pids.json"
$Script:BackendDir  = Join-Path $Script:Root "src\backend"
$Script:FrontendDir = Join-Path $Script:Root "src\frontend"

$Script:Green  = "$([char]27)[32m"
$Script:Red    = "$([char]27)[31m"
$Script:Yellow = "$([char]27)[33m"
$Script:Cyan   = "$([char]27)[36m"
$Script:Bold   = "$([char]27)[1m"
$Script:Reset  = "$([char]27)[0m"

function Write-Ok($msg)   { Write-Host "  $($Script:Green)$([char]0x2713) $msg$($Script:Reset)" }
function Write-Fail($msg) { Write-Host "  $($Script:Red)$([char]0x2717) $msg$($Script:Reset)" }
function Write-Info($msg) { Write-Host "    $msg" }
function Write-Step($msg) { Write-Host "  $($Script:Cyan)> $msg$($Script:Reset)" }

function Kill-Tree($procId) {
    if (-not $procId) { return $false }
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if (-not $proc) { return $false }

    # Children first, then self (graceful).
    Get-CimInstance -ClassName Win32_Process -Filter "ParentProcessId=$procId" -ErrorAction SilentlyContinue | ForEach-Object {
        Kill-Tree $_.ProcessId
    }

    try {
        $proc.CloseMainWindow() | Out-Null
        if (-not $proc.WaitForExit(2000)) {
            $proc.Kill()
            $proc.WaitForExit(3000) | Out-Null
        }
    } catch {
        try { $proc.Kill() } catch {}
    }
    return $true
}

function Kill-ByPort($port) {
    try {
        $owner = (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -First 1).OwningProcess
        if ($owner) {
            Write-Step "Port $port held by PID $owner - stopping..."
            Kill-Tree $owner
        }
    } catch {}
}

Write-Host ""
Write-Host "  $($Script:Bold)$($Script:Cyan)EVE - Stopping development environment$($Script:Reset)"
Write-Host "  $('=' * 44)"
Write-Host ""

# -- 1. Read tracked PIDs ------------------------------------------------
$tracked = $null
if (Test-Path -LiteralPath $Script:PidFile) {
    try {
        $tracked = Get-Content -LiteralPath $Script:PidFile -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch { $tracked = $null }
}

$stoppedAny = $false

# -- 2. Stop tracked processes (children of recorded launcher windows) ----
if ($tracked.frontend) {
    Write-Step "Stopping frontend (PID $($tracked.frontend))..."
    if (Kill-Tree $tracked.frontend) { Write-Ok "Frontend stopped"; $stoppedAny = $true }
    else { Write-Info "Frontend already stopped." }
}

if ($tracked.backend) {
    Write-Step "Stopping backend (PID $($tracked.backend))..."
    if (Kill-Tree $tracked.backend) { Write-Ok "Backend stopped"; $stoppedAny = $true }
    else { Write-Info "Backend already stopped." }
}

# -- 3. Orphan cleanup: anything still listening on our ports ------------
Kill-ByPort $BackendPort
Kill-ByPort $FrontendPort

# -- 4. Sweep aios.main and vite processes --------------------------------
$stale = @()
$stale += Get-CimInstance -ClassName Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "aios\.main" }
$stale += Get-CimInstance -ClassName Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "vite" -or $_.CommandLine -match [regex]::Escape($Script:FrontendDir) }

foreach ($s in $stale) {
    Write-Step "Cleaning orphaned $($s.Name) (PID $($s.ProcessId))..."
    if (Kill-Tree $s.ProcessId) { $stoppedAny = $true }
}

# -- 5. Cleanup PID file -------------------------------------------------
if (Test-Path -LiteralPath $Script:PidFile) {
    Remove-Item -LiteralPath $Script:PidFile -Force
}

Write-Host ""
if ($stoppedAny) { Write-Ok "All EVE processes stopped - no orphans left." }
else { Write-Info "Nothing was running." }
Write-Host ""
