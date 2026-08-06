<#
.SYNOPSIS
    EVE One-Click Development Launcher - Start engine.

.DESCRIPTION
    Starts the EVE backend (FastAPI/uvicorn), waits until it is healthy,
    starts the frontend (Vite), waits until it is available, opens the
    browser, and prints a ready summary. Written to a PID file so
    stop_eve.ps1 can tear everything down without orphans.

    Supports -OnlyBackend / -OnlyFrontend for VS Code task granularity.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File start_eve.ps1
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File start_eve.ps1 -OnlyBackend
#>
[CmdletBinding()]
param(
    [int]$BackendPort = 8456,
    [int]$FrontendPort = 5173,
    [int]$StartupTimeout = 90,
    [switch]$OnlyBackend,
    [switch]$OnlyFrontend,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

# -- Paths ----------------------------------------------------------------
$Script:Root        = Split-Path -Parent $MyInvocation.MyCommand.Path
$Script:BackendDir  = Join-Path $Script:Root "src\backend"
$Script:FrontendDir = Join-Path $Script:Root "src\frontend"
$Script:PidFile     = Join-Path $Script:Root ".eve_pids.json"
$Script:TokenFile   = Join-Path $Script:Root "config\.eve_dev_token"
$Script:HealthUrl   = "http://127.0.0.1:$BackendPort/api/v1/system/health"
$Script:FrontendUrl = "http://localhost:$FrontendPort"
$Script:BrowserUrl  = $Script:FrontendUrl
$Script:DefaultToken = "eve-development-token"

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

# -- Helpers --------------------------------------------------------------
function Test-TcpPort($port, $hostname = "127.0.0.1") {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $async = $tcp.BeginConnect($hostname, $port, $null, $null)
        $wait = $async.AsyncWaitHandle.WaitOne(1000)
        if ($wait) { $tcp.EndConnect($async) | Out-Null }
        $tcp.Close()
        return $wait
    } catch { return $false }
}

function Test-BackendHealthy {
    try {
        $resp = Invoke-WebRequest -Uri $Script:HealthUrl -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
        return ($resp.StatusCode -eq 200)
    } catch { return $false }
}

function Test-FrontendAvailable {
    try {
        Invoke-WebRequest -Uri $Script:FrontendUrl -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop | Out-Null
        return $true
    } catch { return $false }
}

function Get-ProcessVersion($cmd, $args) {
    try {
        $out = & $cmd @args -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')" 2>$null
        if ($out) { return ($out | Select-Object -Last 1) }
    } catch {}
    return $null
}

# Python resolution: prefer usable venv (>=3.12), then py launcher, then python.
function Resolve-Python {
    $candidates = @()
    $venvPy = Join-Path $Script:Root ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPy) {
        $candidates += @{ Cmd = $venvPy; Args = @() }
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($v in @("3.14", "3.13", "3.12")) {
            $candidates += @{ Cmd = "py"; Args = @("-" + $v) }
        }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $candidates += @{ Cmd = "python"; Args = @() }
    }
    if (Get-Command python3 -ErrorAction SilentlyContinue) {
        $candidates += @{ Cmd = "python3"; Args = @() }
    }
    foreach ($c in $candidates) {
        $ver = Get-ProcessVersion $c.Cmd $c.Args
        if ($ver) {
            $parts = $ver.Split(".")
            if ([int]$parts[0] -gt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -ge 12)) {
                return $c
            }
        }
    }
    return $null
}

function Resolve-FrontendCmd {
    if (Get-Command pnpm -ErrorAction SilentlyContinue) { return @{ Cmd = "pnpm"; Args = @("dev") } }
    if (Get-Command yarn -ErrorAction SilentlyContinue)  { return @{ Cmd = "yarn";  Args = @("dev") } }
    if (Get-Command npm -ErrorAction SilentlyContinue)   { return @{ Cmd = "npm";   Args = @("run", "dev") } }
    return $null
}

function Get-PersistedToken {
    if ($env:EVE_API_TOKEN) { return $env:EVE_API_TOKEN }
    if (Test-Path -LiteralPath $Script:TokenFile) {
        $stored = (Get-Content -LiteralPath $Script:TokenFile -Raw -Encoding UTF8).Trim()
        if ($stored) { return $stored }
    }
    # Persist a stable development token (never random each startup).
    try {
        New-Item -ItemType Directory -Path (Split-Path $Script:TokenFile) -Force | Out-Null
        Set-Content -LiteralPath $Script:TokenFile -Value $Script:DefaultToken -Encoding UTF8
    } catch {}
    return $Script:DefaultToken
}

function Save-Pids($backendPid, $frontendPid) {
    # Preserve previously recorded PIDs so a later stop can always find the
    # launcher windows, even when this run detected them as already running.
    $existing = $null
    if (Test-Path -LiteralPath $Script:PidFile) {
        try { $existing = Get-Content -LiteralPath $Script:PidFile -Raw -Encoding UTF8 | ConvertFrom-Json } catch {}
    }
    if (-not $backendPid  -and $existing.backend)  { $backendPid  = $existing.backend }
    if (-not $frontendPid -and $existing.frontend) { $frontendPid = $existing.frontend }

    $data = @{
        backend   = $backendPid
        frontend  = $frontendPid
        startedAt = (Get-Date).ToString("o")
    } | ConvertTo-Json
    Set-Content -LiteralPath $Script:PidFile -Value $data -Encoding UTF8
}

function Wait-Deadline($deadline) { return ([datetime]::Now -lt $deadline) }

# -- Banner ---------------------------------------------------------------
Write-Host ""
Write-Host "  $($Script:Bold)EVE - One-Click Development Launcher$($Script:Reset)"
Write-Host "  $('=' * 44)"
Write-Host "  Backend : $($Script:HealthUrl)"
Write-Host "  Frontend: $($Script:FrontendUrl)"
Write-Host ""

# -- Verify environment ---------------------------------------------------
Write-Step "Verifying environment..."

$py = Resolve-Python
if (-not $py) {
    Write-Fail "Python 3.12+ not found"
    Write-Info "Install from https://www.python.org/downloads/ (or fix .venv - current .venv is Python 3.10, too old)."
    exit 1
}
Write-Ok "Python  $((Get-ProcessVersion $py.Cmd $py.Args))  ($($py.Cmd))"

$fe = Resolve-FrontendCmd
if (-not $fe) {
    Write-Fail "No package manager found (npm / pnpm / yarn)"
    Write-Info "Install Node.js from https://nodejs.org/"
    exit 1
}
Write-Ok "Node   $($fe.Cmd) detected"

$token = Get-PersistedToken
Write-Ok "Token  stable ($($token.Substring(0, [Math]::Min(16, $token.Length)))...)"

if (-not (Test-Path -LiteralPath $Script:BackendDir)) {
    Write-Fail "Backend directory not found: $($Script:BackendDir)"
    exit 1
}
if (-not (Test-Path -LiteralPath $Script:FrontendDir)) {
    Write-Fail "Frontend directory not found: $($Script:FrontendDir)"
    exit 1
}
if (-not (Test-Path -LiteralPath (Join-Path $Script:FrontendDir "node_modules"))) {
    Write-Fail "Frontend dependencies missing - run 'npm install' in src/frontend first."
    exit 1
}

# -- Token / env ----------------------------------------------------------
$env:EVE_API_TOKEN = $token
$env:EVE_ENV = "dev"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = if ($env:PYTHONPATH) { "$($Script:BackendDir);$env:PYTHONPATH" } else { $Script:BackendDir }

$backendPid = $null
$frontendPid = $null

# -- Backend --------------------------------------------------------------
if ($OnlyFrontend) {
    Write-Step "Skipping backend (-OnlyFrontend)"
} elseif (Test-BackendHealthy) {
    Write-Ok "Backend already healthy on port $BackendPort"
} else {
    if (Test-TcpPort $BackendPort) {
        Write-Fail "Port $BackendPort already in use but not healthy."
        Write-Info "Stop the existing process or run stop_eve.bat first."
        exit 1
    }
    Write-Step "Starting Backend..."
    $pyStr = $py.Cmd
    if ($py.Cmd.Contains(" ")) { $pyStr = "'$($py.Cmd)'" }
    $pyArgsStr = ($py.Args + @("-m", "aios.main")) -join " "
    $backendChild = "Set-Location -LiteralPath '$($Script:BackendDir)'; " +
        "`$env:PYTHONPATH='$($Script:BackendDir)'; " +
        "`$env:PYTHONIOENCODING='utf-8'; `$env:PYTHONUTF8='1'; `$env:EVE_ENV='dev'; " +
        "`$env:EVE_API_TOKEN='$token'; " +
        "Write-Host '=== EVE Backend ===' -ForegroundColor Cyan; " +
        "& $pyStr $pyArgsStr"
    $backendProc = Start-Process -FilePath "powershell" -ArgumentList @("-NoExit", "-Command", $backendChild) -WindowStyle Normal -PassThru
    $backendPid = $backendProc.Id
    Write-Ok "Backend starting (PID $backendPid)"

    Write-Step "Waiting for backend health (timeout: ${StartupTimeout}s)..."
    Start-Sleep -Seconds 6
    $deadline = [datetime]::Now.AddSeconds($StartupTimeout)
    $healthy = $false
    while (Wait-Deadline $deadline) {
        if (Test-BackendHealthy) { $healthy = $true; break }
        if (-not (Get-Process -Id $backendPid -ErrorAction SilentlyContinue)) {
            Write-Fail "Backend process exited unexpectedly"
            exit 1
        }
        Start-Sleep -Milliseconds 1000
        Write-Host "." -NoNewline
    }
    Write-Host ""
    if (-not $healthy) {
        Write-Fail "Backend not healthy within ${StartupTimeout}s"
        Write-Info "Check the 'EVE Backend' terminal window."
        exit 1
    }
    Write-Ok "Backend healthy ($($Script:HealthUrl))"
}

# -- Frontend -------------------------------------------------------------
if ($OnlyBackend) {
    Write-Step "Skipping frontend (-OnlyBackend)"
} elseif (Test-FrontendAvailable) {
    Write-Ok "Frontend already running on port $FrontendPort"
} else {
    if (Test-TcpPort $FrontendPort "localhost") {
        Write-Fail "Port $FrontendPort already in use but not serving."
        exit 1
    }
    Write-Step "Starting Frontend..."
    $feArgsStr = $fe.Args -join " "
    $feChild = "Set-Location -LiteralPath '$($Script:FrontendDir)'; " +
        "`$env:PYTHONUTF8='1'; " +
        "Write-Host '=== EVE Frontend ===' -ForegroundColor Cyan; " +
        "& $($fe.Cmd) $feArgsStr"
    $feProc = Start-Process -FilePath "powershell" -ArgumentList @("-NoExit", "-Command", $feChild) -WindowStyle Normal -PassThru
    $frontendPid = $feProc.Id
    Write-Ok "Frontend starting (PID $frontendPid)"

    Write-Step "Waiting for frontend (timeout: ${StartupTimeout}s)..."
    $deadline = [datetime]::Now.AddSeconds($StartupTimeout)
    $frontendReady = $false
    while (Wait-Deadline $deadline) {
        if (Test-FrontendAvailable) { $frontendReady = $true; break }
        if (-not (Get-Process -Id $frontendPid -ErrorAction SilentlyContinue)) {
            Write-Fail "Frontend process exited unexpectedly"
            exit 1
        }
        Start-Sleep -Milliseconds 500
        Write-Host "." -NoNewline
    }
    Write-Host ""
    if (-not $frontendReady) {
        Write-Fail "Frontend not ready within ${StartupTimeout}s"
        Write-Info "Check the 'EVE Frontend' terminal window."
        exit 1
    }
    Write-Ok "Frontend running ($($Script:FrontendUrl))"
}

# -- Persist PIDs ---------------------------------------------------------
Save-Pids $backendPid $frontendPid

# -- Open browser ---------------------------------------------------------
if (-not $NoBrowser) {
    Write-Step "Opening browser..."
    Start-Process $Script:BrowserUrl
    Write-Ok "Browser opened"
}

# -- Summary --------------------------------------------------------------
Write-Host ""
Write-Host "  $($Script:Bold)$($Script:Green)----------------------------------------$($Script:Reset)"
Write-Host "  $($Script:Bold)$($Script:Green)EVE Development Environment Ready$($Script:Reset)"
Write-Host "  $($Script:Bold)Backend : $($Script:Cyan)http://127.0.0.1:$BackendPort$($Script:Reset)"
Write-Host "  $($Script:Bold)Frontend: $($Script:Cyan)http://localhost:$FrontendPort$($Script:Reset)"
Write-Host "  $($Script:Bold)$($Script:Green)----------------------------------------$($Script:Reset)"
Write-Host ""
Write-Host "  Stop: run stop_eve.bat  (or Ctrl+C in the server windows)"
Write-Host ""
