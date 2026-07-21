<#
.SYNOPSIS
    AIOS/Eve Launcher — starts backend and frontend with one command.
.DESCRIPTION
    Sets PYTHONPATH to include src/backend, then delegates to python -m aios.
    Run from the project root.
.EXAMPLE
    .\start_eve.ps1
#>

$ErrorActionPreference = "Stop"

# Determine project root (directory containing this script)
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

# Ensure UTF-8 for Unicode banner characters
$env:PYTHONIOENCODING = 'utf-8'

# Ensure src/backend is on PYTHONPATH so python -m aios can find the package
$BackendDir = Join-Path (Join-Path $ProjectRoot "src") "backend"
if ($env:PYTHONPATH) {
    $env:PYTHONPATH = "$BackendDir;$env:PYTHONPATH"
} else {
    $env:PYTHONPATH = $BackendDir
}

# Determine Python command — prefer py launcher, fallback to python
$pythonCmd = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
# If using py launcher, target 3.12+
$pythonArg = if ($pythonCmd -eq "py") { @("-3.12") } else { @() }

# Check Python
try {
    $pyVersion = & $pythonCmd $pythonArg -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
} catch {
    Write-Error "Python not found. Install Python >= 3.12."
    exit 1
}
if ([version]$pyVersion -lt [version]"3.12") {
    Write-Error "Python >= 3.12 required, got $pyVersion"
    exit 1
}

# Check Node
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Error "Node.js not found. Install Node.js >= 18."
    exit 1
}

& $pythonCmd $pythonArg -m aios
if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null) {
    exit $LASTEXITCODE
}
