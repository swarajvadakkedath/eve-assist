<#
.SYNOPSIS
Eve OS Development Launcher - Stop

.DESCRIPTION
Stops the Eve backend and frontend development servers.
Only kills processes tracked by the launcher's PID file.

.EXAMPLE
.\stop.ps1
#>

$ErrorActionPreference = "Stop"

$Script:PidFile = Join-Path $PSScriptRoot ".eve_pids"

$Green  = "$([char]27)[32m"
$Red    = "$([char]27)[31m"
$Yellow = "$([char]27)[33m"
$Cyan   = "$([char]27)[36m"
$Bold   = "$([char]27)[1m"
$Reset  = "$([char]27)[0m"

function Write-Ok($msg)  { Write-Host "  $Green$([char]0x2713) $msg$Reset" }
function Write-Fail($msg){ Write-Host "  $Red$([char]0x2717) $msg$Reset" }
function Write-Info($msg){ Write-Host "    $msg" }
function Write-Step($msg){ Write-Host "  $Cyan> $msg$Reset" }

function Kill-ProcessTree($pid) {
    try {
        $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if (-not $process) { return $false }

        # Kill child processes first
        Get-CimInstance -ClassName Win32_Process -Filter "ParentProcessId=$pid" -ErrorAction SilentlyContinue | ForEach-Object {
            Kill-ProcessTree($_.ProcessId)
        }

        # Kill the process itself
        $process.Kill()
        Wait-Process -Id $pid -Timeout 5 -ErrorAction SilentlyContinue
        return $true
    } catch {
        return $false
    }
}

function Get-TrackedPids {
    if (-not (Test-Path $Script:PidFile)) {
        return $null
    }
    try {
        $data = Get-Content $Script:PidFile -Raw -Encoding UTF8 | ConvertFrom-Json
        return $data
    } catch {
        return $null
    }
}

# -- Main ------------------------------------------
Write-Host ""
Write-Host "  $Bold$Cyan Eve OS - Stopping$Reset"
Write-Host ""

$tracked = Get-TrackedPids
if (-not $tracked) {
    Write-Info "No tracked processes found."
    Write-Info "The launcher PID file ($Script:PidFile) is missing or empty."
    Write-Info "You may need to close terminal windows manually."
    exit 0
}

$stoppedAny = $false

# Stop frontend first (reverse order)
if ($tracked.frontend) {
    Write-Step "Stopping Frontend (PID $($tracked.frontend))..."
    if (Kill-ProcessTree $tracked.frontend) {
        Write-Ok "Frontend stopped"
        $stoppedAny = $true
    } else {
        Write-Info "Frontend process not found (may already be stopped)."
    }
}

# Stop backend
if ($tracked.backend) {
    Write-Step "Stopping Backend (PID $($tracked.backend))..."
    if (Kill-ProcessTree $tracked.backend) {
        Write-Ok "Backend stopped"
        $stoppedAny = $true
    } else {
        Write-Info "Backend process not found (may already be stopped)."
    }
}

# Cleanup PID file
if (Test-Path $Script:PidFile) {
    Remove-Item $Script:PidFile -Force
}

# Also try to find and kill any orphaned npm/node processes from frontend
# (Start-Process with powershell creates a parent-child chain that may survive)
Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -match "vite|dev" -or $_.CommandLine -match "frontend"
} | ForEach-Object {
    Write-Step "Cleaning up orphaned Node process (PID $($_.Id))..."
    Kill-ProcessTree $_.Id
    $stoppedAny = $true
}

if ($stoppedAny) {
    Write-Ok "All servers stopped"
} else {
    Write-Info "No running servers found."
}

Write-Host ""
Write-Ok "Done."
Write-Host ""
