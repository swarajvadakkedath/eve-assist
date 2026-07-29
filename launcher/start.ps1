<#
.SYNOPSIS
Eve OS Development Launcher - Start

.DESCRIPTION
Starts the Eve backend and frontend development servers in separate windows,
waits for both to be healthy, and opens the browser.

.EXAMPLE
.\check.ps1
#>

param(
    [int]$BackendPort = 8456,
    [int]$FrontendPort = 5173,
    [int]$StartupTimeout = 60,
    [string]$BackendHealthUrl = "http://127.0.0.1:$BackendPort/api/v1/system/health",
    [string]$FrontendUrl = "http://localhost:$FrontendPort",
    [string]$BrowserUrl = "http://localhost:$FrontendPort"
)

$Script:ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Script:PidFile = Join-Path $PSScriptRoot ".eve_pids"

# -- Color helpers ----------------------------------
$Script:Green  = "$([char]27)[32m"
$Script:Red    = "$([char]27)[31m"
$Script:Yellow = "$([char]27)[33m"
$Script:Cyan   = "$([char]27)[36m"
$Script:Bold   = "$([char]27)[1m"
$Script:Reset  = "$([char]27)[0m"

function Write-Ok($msg)  { Write-Host "  $($Script:Green)$([char]0x2713) $msg$($Script:Reset)" }
function Write-Fail($msg){ Write-Host "  $($Script:Red)$([char]0x2717) $msg$($Script:Reset)" }
function Write-Info($msg){ Write-Host "    $msg" }
function Write-Step($msg){ Write-Host "  $($Script:Cyan)> $msg$($Script:Reset)" }

# -- Configuration ----------------------------------
$BackendDir = Join-Path (Join-Path $Script:ProjectRoot "src") "backend"
$FrontendDir = Join-Path (Join-Path $Script:ProjectRoot "src") "frontend"

$BackendCmd = "python"
$BackendArgs = @("-m", "aios.main")
$FrontendCmd = "npm"
$FrontendArgs = @("run", "dev")

# -- Startup banner --------------------------------
Write-Host ""
Write-Host "  $($Script:Bold)Eve OS - Development Launcher$($Script:Reset)"
Write-Host "  $('=' * 40)"
Write-Host "  Backend : $BackendHealthUrl"
Write-Host "  Frontend: $FrontendUrl"
Write-Host ""

# -- Helpers ----------------------------------------
function Get-AlreadyRunningPids {
    $pids = @{}
    if (Test-Path $Script:PidFile) {
        try {
            $data = Get-Content $Script:PidFile -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($data.backend -and (Get-Process -Id $data.backend -ErrorAction SilentlyContinue)) {
                $pids.backend = $data.backend
            }
            if ($data.frontend -and (Get-Process -Id $data.frontend -ErrorAction SilentlyContinue)) {
                $pids.frontend = $data.frontend
            }
        } catch {}
    }
    return $pids
}

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
        $tcp = New-Object System.Net.Sockets.TcpClient
        $async = $tcp.BeginConnect("127.0.0.1", $BackendPort, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne(2000)) { $tcp.Close(); return $false }
        $tcp.EndConnect($async) | Out-Null
        $tcp.Close()
        $resp = Invoke-WebRequest -Uri $BackendHealthUrl -TimeoutSec 2 -ErrorAction Stop -UseBasicParsing
        return ($resp.StatusCode -eq 200)
    } catch {
        return $false
    }
}

function Test-FrontendAvailable {
    try {
        $resp = Invoke-WebRequest -Uri $FrontendUrl -TimeoutSec 2 -ErrorAction Stop -UseBasicParsing
        return $true
    } catch {
        return $false
    }
}

function Save-Pids($backendPid, $frontendPid) {
    $data = @{ backend = $backendPid; frontend = $frontendPid } | ConvertTo-Json
    Set-Content -Path $Script:PidFile -Value $data -Encoding UTF8
}

# -- 1. Detect existing processes -------------------
Write-Step "Checking for existing processes..."
$existing = Get-AlreadyRunningPids
if ($existing.backend -or $existing.frontend) {
    Write-Host ""
    Write-Host "  $($Script:Yellow)Eve appears to be already running:$($Script:Reset)"
    if ($existing.backend) { Write-Info "  Backend  (PID $($existing.backend))" }
    if ($existing.frontend) { Write-Info "  Frontend (PID $($existing.frontend))" }
    Write-Host ""
    Write-Host "  What would you like to do?"
    Write-Host "    1) Open browser (continue)"
    Write-Host "    2) Restart (stop + start)"
    Write-Host "    3) Cancel"
    Write-Host ""
    $choice = Read-Host "  Enter choice [1/2/3]"
    if ($choice -eq "2") {
        Write-Step "Restarting..."
        & "$PSScriptRoot\stop.ps1"
    } elseif ($choice -eq "3") {
        Write-Fail "Cancelled."
        exit 1
    } else {
        Write-Step "Opening browser..."
        Start-Process $BrowserUrl
        Write-Ok "Browser Opened"
        exit 0
    }
}

# -- 2. Verify environment -------------------------
Write-Step "Verifying environment..."

$Script:PythonCmd = "python"
$pythonOk = $false
$ver = $null
try {
    $ver = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
    if ($ver -and [version]$ver -ge [version]"3.12") {
        $pythonOk = $true
    }
} catch {}
if (-not $pythonOk) {
    try {
        $ver = & py -3.12 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($ver -and [version]$ver -ge [version]"3.12") {
            $Script:PythonCmd = "py"
            $Script:PythonVerArg = "-3.12"
            $pythonOk = $true
        }
    } catch {}
}
if (-not $pythonOk) {
    Write-Fail "Python 3.12+ required"
    Write-Info "Install from: https://www.python.org/downloads/"
    exit 1
}
Write-Ok "Python $ver"

$nodeOk = $false
try {
    $nodeVer = & node --version 2>$null
    if ($nodeVer) { $nodeOk = $true }
} catch {}
if (-not $nodeOk) {
    Write-Fail "Node.js not found"
    Write-Info "Install from: https://nodejs.org/"
    exit 1
}
Write-Ok "Node.js $nodeVer"

$npmOk = $false
try {
    $npmVer = & npm --version 2>$null
    if ($npmVer) { $npmOk = $true }
} catch {}
if (-not $npmOk) {
    Write-Fail "npm not found"
    Write-Info "npm comes with Node.js - reinstall from https://nodejs.org/"
    exit 1
}
Write-Ok "npm $npmVer"

# -- 3. Check dependencies --------------------------
Write-Step "Checking dependencies..."

$pyDepsOk = $true
try {
    $pyArgs = @("-c", "import aios")
    if ($Script:PythonVerArg) { $pyArgs = @($Script:PythonVerArg) + $pyArgs }
    & $Script:PythonCmd $pyArgs 2>$null
    if ($LASTEXITCODE -ne 0) { $pyDepsOk = $false }
} catch { $pyDepsOk = $false }

if (-not $pyDepsOk) {
    Write-Host "  $($Script:Yellow)Backend dependencies not installed.$($Script:Reset)"
    Write-Info "Run: pip install -e ."
    try { $install = Read-Host "  Install now? [Y/n]" } catch { $install = "y" }
    if ($install -ne "n" -and $install -ne "N") {
        Write-Step "Installing backend dependencies..."
        Set-Location -LiteralPath $Script:ProjectRoot
        $pipArgs = @("-m", "pip", "install", "-e", ".")
        if ($Script:PythonVerArg) { $pipArgs = @($Script:PythonVerArg) + $pipArgs }
        & $Script:PythonCmd $pipArgs
        if ($LASTEXITCODE -ne 0) {
            Write-Fail "pip install failed"
            exit 1
        }
        Write-Ok "Backend dependencies installed"
    } else {
        Write-Fail "Backend dependencies missing - aborting."
        exit 1
    }
} else {
    Write-Ok "Backend dependencies"
}

$npmDepsOk = Test-Path (Join-Path $FrontendDir "node_modules")
if (-not $npmDepsOk) {
    Write-Host "  $($Script:Yellow)Frontend dependencies not installed.$($Script:Reset)"
    Write-Info "Run: cd src/frontend && npm install"
    $install = Read-Host "  Install now? [Y/n]"
    if ($install -ne "n" -and $install -ne "N") {
        Write-Step "Installing frontend dependencies..."
        Set-Location -LiteralPath $FrontendDir
        & npm install
        if ($LASTEXITCODE -ne 0) {
            Write-Fail "npm install failed"
            exit 1
        }
        Write-Ok "Frontend dependencies installed"
    } else {
        Write-Fail "Frontend dependencies missing - aborting."
        exit 1
    }
} else {
    Write-Ok "Frontend dependencies"
}

# -- 4. Check port availability ---------------------
Write-Step "Checking port availability..."
if (Test-PortOpen $BackendPort) {
    Write-Fail "Port $BackendPort already in use"
    Write-Info "Something is already running on port $BackendPort."
    Write-Info "Stop that process or change the port in launcher config."
    exit 1
}
Write-Ok "Port $BackendPort available"

if (Test-PortOpen $FrontendPort "localhost") {
    Write-Fail "Port $FrontendPort already in use"
    Write-Info "Something is already running on port $FrontendPort."
    exit 1
}
Write-Ok "Port $FrontendPort available"

# -- 5. Set up PYTHONPATH --------------------------
$env:PYTHONPATH = if ($env:PYTHONPATH) {
    "$BackendDir;$env:PYTHONPATH"
} else {
    $BackendDir
}

# -- 6. Start Backend ------------------------------
Write-Step "Starting Backend..."
$backendPwshCmd = "Set-Location '$BackendDir'; " +
    "`$env:PYTHONPATH='$BackendDir'; " +
    "Write-Host 'Eve Backend - AIOS v4.0' -ForegroundColor Cyan; " +
    "Write-Host 'Press Ctrl+C to stop' -ForegroundColor DarkGray; " +
    "$Script:PythonCmd $Script:PythonVerArg -m aios.main"
$env:PYTHONPATH = $BackendDir
$backendProcess = Start-Process -FilePath "powershell" -ArgumentList @(
    "-NoExit"
    "-Command"
    $backendPwshCmd
) -WindowStyle Normal -PassThru

Write-Ok "Backend Starting (PID $($backendProcess.Id))"
$backendPid = $backendProcess.Id

# -- 7. Wait for Backend Health ---------------------
Write-Step "Waiting for Backend to be ready (timeout: ${StartupTimeout}s)..."
Start-Sleep -Seconds 8
$deadline = [datetime]::Now.AddSeconds($StartupTimeout)
$healthy = $false
while ([datetime]::Now -lt $deadline) {
    if (Test-BackendHealthy) {
        $healthy = $true
        break
    }
    if (-not (Get-Process -Id $backendPid -ErrorAction SilentlyContinue)) {
        Write-Fail "Backend process exited unexpectedly"
        exit 1
    }
    Start-Sleep -Milliseconds 1000
    Write-Host "." -NoNewline
}
Write-Host ""

if (-not $healthy) {
    Write-Fail "Backend not ready within ${StartupTimeout}s"
    Write-Info "Check the backend terminal window for errors."
    Write-Info "Common issues: port conflict, missing dependencies, Python version."
    exit 1
}
Write-Ok "Backend Running ($BackendHealthUrl)"

# -- 8. Start Frontend ------------------------------
Write-Step "Starting Frontend..."
if ($env:PYTHONPATH) {
    $frontendEnv = @{ "PYTHONPATH" = $env:PYTHONPATH }
} else {
    $frontendEnv = @{}
}
$frontendStartCmd = "Set-Location '$FrontendDir'; " +
    "Write-Host 'Eve Frontend - Vite Dev Server' -ForegroundColor Cyan; " +
    "Write-Host 'Press Ctrl+C to stop' -ForegroundColor DarkGray; " +
    "npm run dev"
$frontendProcess = Start-Process -FilePath "powershell" -ArgumentList @(
    "-NoExit"
    "-Command"
    $frontendStartCmd
) -WindowStyle Normal -PassThru

Write-Ok "Frontend Starting (PID $($frontendProcess.Id))"
$frontendPid = $frontendProcess.Id

# -- 9. Wait for Frontend ---------------------------
Write-Step "Waiting for Frontend to be ready (timeout: ${StartupTimeout}s)..."
$deadline = [datetime]::Now.AddSeconds($StartupTimeout)
$frontendReady = $false
while ([datetime]::Now -lt $deadline) {
    if (Test-FrontendAvailable) {
        $frontendReady = $true
        break
    }
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
    Write-Info "Check the frontend terminal window for errors."
    exit 1
}
Write-Ok "Frontend Running ($FrontendUrl)"

# -- 10. Save PIDs ---------------------------------
Save-Pids $backendPid $frontendPid

# -- 11. Open Browser ------------------------------
Write-Step "Opening browser..."
Start-Process $BrowserUrl
Write-Ok "Browser Opened"

# -- 12. Summary -----------------------------------
Write-Host ""
Write-Host "  $($Script:Bold)$($Script:Green)Eve OS is running!$($Script:Reset)"
Write-Host "  $('-' * 40)"
Write-Host "  Backend : $($Script:Cyan)$BackendHealthUrl$($Script:Reset)"
Write-Host "  Frontend: $($Script:Cyan)$FrontendUrl$($Script:Reset)"
Write-Host "  Browser : $($Script:Cyan)$BrowserUrl$($Script:Reset)"
Write-Host ""
Write-Host "  Commands:"
Write-Host "    $($Script:Yellow)stop.ps1$($Script:Reset)     Stop all servers"
Write-Host "    $($Script:Yellow)restart.ps1$($Script:Reset)  Restart all servers"
Write-Host "    $($Script:Yellow)check.ps1$($Script:Reset)    Check server status"
Write-Host ""
