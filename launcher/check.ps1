<#
.SYNOPSIS
Eve OS Development Launcher - Health Check

.DESCRIPTION
Checks if the Eve backend and frontend are running and responsive.

.EXAMPLE
.\check.ps1
#>

param(
    [int]$BackendPort = 8456,
    [int]$FrontendPort = 5173,
    [string]$BackendHealthUrl = "http://127.0.0.1:$BackendPort/api/v1/system/health",
    [string]$FrontendUrl = "http://localhost:$FrontendPort"
)

$Script:PidFile = Join-Path $PSScriptRoot ".eve_pids"

$Green  = "$([char]27)[32m"
$Red    = "$([char]27)[31m"
$Yellow = "$([char]27)[33m"
$Cyan   = "$([char]27)[36m"
$Bold   = "$([char]27)[1m"
$Reset  = "$([char]27)[0m"

function Write-Ok($msg)  { Write-Host "  $Green$([char]0x2713) $msg$Reset" }
function Write-Fail($msg){ Write-Host "  $Red$([char]0x2717) $msg$Reset" }
function Write-Warn($msg){ Write-Host "  $Yellow! $msg$Reset" }
function Write-Info($msg){ Write-Host "    $msg" }

function Test-PortOpen($port, $hostname = "127.0.0.1") {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $async = $tcp.BeginConnect($hostname, $port, $null, $null)
        $wait = $async.AsyncWaitHandle.WaitOne(1000)
        if ($wait) {
            $tcp.EndConnect($async) | Out-Null
            $tcp.Close()
            return $true
        }
        $tcp.Close()
        return $false
    } catch {
        return $false
    }
}

function Test-BackendHealthy {
    try {
        $resp = Invoke-WebRequest -Uri $BackendHealthUrl -TimeoutSec 5 -ErrorAction Stop
        return $resp.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Test-FrontendAvailable {
    return Test-PortOpen $FrontendPort "localhost"
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

Write-Host ""
Write-Host "  $Bold$Cyan Eve OS - Health Check$Reset"
Write-Host "  $('=' * 35)"
Write-Host ""

# -- Tracked PIDs -----------------------------------
$tracked = Get-TrackedPids
if ($tracked) {
    Write-Info "Tracked PIDs:"
    if ($tracked.backend) {
        $proc = Get-Process -Id $tracked.backend -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Ok "Backend PID $($tracked.backend) (running)"
        } else {
            Write-Warn "Backend PID $($tracked.backend) (not found)"
        }
    }
    if ($tracked.frontend) {
        $proc = Get-Process -Id $tracked.frontend -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Ok "Frontend PID $($tracked.frontend) (running)"
        } else {
            Write-Warn "Frontend PID $($tracked.frontend) (not found)"
        }
    }
} else {
    Write-Host "  $Yellow  No tracked PIDs (launcher may not have started Eve)$Reset"
}
Write-Host ""

# -- Port checks ------------------------------------
Write-Info "Port Checks:"
$backendPortOpen = Test-PortOpen $BackendPort
if ($backendPortOpen) {
    Write-Ok "Port $BackendPort (Backend) - OPEN"
} else {
    Write-Fail "Port $BackendPort (Backend) - CLOSED"
}

$frontendPortOpen = Test-PortOpen $FrontendPort "localhost"
if ($frontendPortOpen) {
    Write-Ok "Port $FrontendPort (Frontend) - OPEN"
} else {
    Write-Fail "Port $FrontendPort (Frontend) - CLOSED"
}
Write-Host ""

# -- HTTP health ------------------------------------
Write-Info "HTTP Health:"

$backendHealthy = Test-BackendHealthy
if ($backendHealthy) {
    Write-Ok "Backend: Running"
} else {
    Write-Fail "Backend: Not responding"
}

$frontendOk = Test-FrontendAvailable
if ($frontendOk) {
    Write-Ok "Frontend: Running"
} else {
    Write-Fail "Frontend: Not responding"
}
Write-Host ""

# -- Browser check (try to reach frontend via HTTP) --
try {
    $resp = Invoke-WebRequest -Uri $FrontendUrl -TimeoutSec 3 -ErrorAction Stop
    if ($resp.StatusCode -eq 200) {
        Write-Ok "Browser: OK (HTTP $($resp.StatusCode))"
    } else {
        Write-Warn "Browser: HTTP $($resp.StatusCode)"
    }
} catch {
    if ($frontendPortOpen) {
        $statusCode = $_.Exception.Response.StatusCode.value__
        if ($statusCode) {
            Write-Warn "Browser: HTTP $statusCode (port is open)"
        } else {
            Write-Warn "Browser: Port open but HTTP error"
        }
    } else {
        Write-Fail "Browser: Cannot reach $FrontendUrl"
    }
}

Write-Host ""
Write-Info "Summary:"
if ($backendHealthy -and $frontendOk) {
    Write-Host "  $Green$Bold  Eve OS is fully operational.$Reset"
} elseif ($backendHealthy -or $frontendOk) {
    Write-Host "  $Yellow  Eve OS is partially running.$Reset"
    Write-Info "Run '.\start.ps1' to start missing services."
} else {
    Write-Host "  $Red  Eve OS is not running.$Reset"
    Write-Info "Run '.\start.ps1' to launch."
}
Write-Host ""

# -- Exit code -------------------------------------
if ($backendHealthy -and $frontendOk) { exit 0 }
else { exit 1 }
