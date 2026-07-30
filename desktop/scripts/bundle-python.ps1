param(
    [string]$PythonVersion = "3.12.9",
    [string]$Arch = "amd64",
    [string]$OutputDir = "$PSScriptRoot\..\src-tauri\python",
    [switch]$SyncToTarget
)

$ErrorActionPreference = "Stop"

$EmbedUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-$Arch.zip"
$GetPipUrl = "https://bootstrap.pypa.io/get-pip.py"
$ZipFile = "$env:TEMP\python-$PythonVersion-embed-$Arch.zip"
$GetPipFile = "$env:TEMP\get-pip.py"
$RequirementsFile = Resolve-Path "$PSScriptRoot\..\..\requirements.txt"
$LauncherDir = Resolve-Path "$PSScriptRoot\..\..\launcher"
$BackendDir = Resolve-Path "$PSScriptRoot\..\..\src\backend"

$TargetDir = Resolve-Path "$PSScriptRoot\..\src-tauri\target\release"

# Packages that MUST be importable after installation
$RequiredPackages = @(
    "fastapi",
    "uvicorn",
    "httpx",
    "pydantic",
    "pydantic_settings",
    "structlog",
    "aiosqlite",
    "openai",
    "anthropic",
    "psutil",
    "PIL",       # Pillow
    "pyperclip",
    "yaml",      # pyyaml
    "playwright"
)

Write-Host ""
Write-Host "======================================================"
Write-Host "  Eve OS - Bundle Embedded Python"
Write-Host "  Python $PythonVersion ($Arch)"
Write-Host "======================================================"
Write-Host ""

# ---- Step 1: Download ----
Write-Host "[1/6] Preparing embedded Python..."
if (-not (Test-Path -LiteralPath $ZipFile)) {
    Write-Host "      Downloading $EmbedUrl ..."
    Invoke-WebRequest -Uri $EmbedUrl -OutFile $ZipFile -UseBasicParsing
} else {
    Write-Host "      Using cached $ZipFile"
}

# ---- Step 2: Extract ----
Write-Host "[2/6] Extracting to $OutputDir ..."
if (Test-Path -LiteralPath $OutputDir) {
    Remove-Item -Recurse -Force -LiteralPath $OutputDir
}
Expand-Archive -Path $ZipFile -DestinationPath $OutputDir -Force

# ---- Step 3: Configure .pth ----
Write-Host "[3/6] Configuring Python path..."
$PthFile = Get-ChildItem -Path $OutputDir -Filter "*._pth" | Select-Object -First 1
if (-not $PthFile) {
    Write-Host "      No ._pth file found in embedded distribution" -ForegroundColor Red
    exit 1
}

$pthContent = Get-Content -Path $PthFile.FullName
$pthContent = $pthContent -replace '#import site', 'import site'
$pthContent += "`n.."
$pthContent += "`n..\backend"
$pthContent += "`n.\Lib\site-packages"
Set-Content -Path $PthFile.FullName -Value $pthContent -Encoding ASCII

$NewPthFile = [System.IO.Path]::ChangeExtension($PthFile.FullName, ".pth")
if ($PthFile.FullName -ne $NewPthFile) {
    Remove-Item -LiteralPath $NewPthFile -ErrorAction SilentlyContinue
    Rename-Item -LiteralPath $PthFile.FullName -NewName (Split-Path -Leaf $NewPthFile)
}

# Create Lib\site-packages
$SitePackages = "$OutputDir\Lib\site-packages"
New-Item -ItemType Directory -Path $SitePackages -Force | Out-Null
Write-Host "      Modified $($PthFile.Name), created $SitePackages"

# ---- Step 4: Install pip + dependencies ----
Write-Host "[4/6] Installing pip..."
$PythonExe = "$OutputDir\python.exe"
if (-not (Test-Path -LiteralPath $PythonExe)) {
    Write-Host "      python.exe not found at $PythonExe" -ForegroundColor Red
    exit 1
}
$savedEAP = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$null = & $PythonExe $GetPipFile --no-warn-script-location --target "$SitePackages" 2>&1
$pipExitCode = $LASTEXITCODE
$ErrorActionPreference = $savedEAP
if ($pipExitCode -ne 0) {
    Write-Host "      pip installation FAILED (exit code $pipExitCode)" -ForegroundColor Red
    exit 1
}
Write-Host "      pip installed"

Write-Host "[5/6] Installing dependencies from requirements.txt..."
$ErrorActionPreference = "Continue"
$null = & $PythonExe -m pip install --no-warn-script-location --target "$SitePackages" -r "$RequirementsFile" 2>&1
$pipInstallExitCode = $LASTEXITCODE
$ErrorActionPreference = $savedEAP
if ($pipInstallExitCode -ne 0) {
    Write-Host "      pip install FAILED (exit code $pipInstallExitCode)" -ForegroundColor Red
    Write-Host "      Check requirements.txt for invalid or missing packages"
    exit 1
}
Write-Host "      All dependencies installed"
Write-Host "      All dependencies installed"

# ---- Step 5: Copy launcher and backend modules ----
Write-Host "      Copying launcher module..."
if (Test-Path -LiteralPath "$OutputDir\..\launcher") {
    Remove-Item -Recurse -Force -LiteralPath "$OutputDir\..\launcher"
}
Copy-Item -Recurse -Force -LiteralPath $LauncherDir -Destination "$OutputDir\..\launcher"

Write-Host "      Copying backend modules..."
if (Test-Path -LiteralPath "$OutputDir\..\backend") {
    Remove-Item -Recurse -Force -LiteralPath "$OutputDir\..\backend"
}
Copy-Item -Recurse -Force -LiteralPath $BackendDir -Destination "$OutputDir\..\backend"

# ---- Step 6: Verify imports ----
Write-Host "[6/6] Verifying imports..."
$FailedImports = @()
$ImportNames = @{
    "fastapi"         = "fastapi"
    "uvicorn"         = "uvicorn"
    "httpx"           = "httpx"
    "pydantic"        = "pydantic"
    "pydantic_settings" = "pydantic_settings"
    "structlog"       = "structlog"
    "aiosqlite"       = "aiosqlite"
    "openai"          = "openai"
    "anthropic"       = "anthropic"
    "psutil"          = "psutil"
    "PIL"             = "Pillow"
    "pyperclip"       = "pyperclip"
    "yaml"            = "pyyaml"
    "playwright"      = "playwright"
}

foreach ($pkg in $ImportNames.Keys) {
    $display = $ImportNames[$pkg]
    Write-Host "      Checking $display ... " -NoNewline
    $result = & $PythonExe -c "import $pkg; print('OK')" 2>&1
    if ($LASTEXITCODE -eq 0 -and $result -eq "OK") {
        Write-Host "OK" -ForegroundColor Green
    } else {
        Write-Host "FAILED" -ForegroundColor Red
        Write-Host "        $result"
        $FailedImports += $display
    }
}

# Also verify launcher module
Write-Host "      Checking launcher ... " -NoNewline
$result = & $PythonExe -c "import launcher.tauri_integration; print('OK')" 2>&1
if ($LASTEXITCODE -eq 0 -and $result -eq "OK") {
    Write-Host "OK" -ForegroundColor Green
} else {
    Write-Host "FAILED" -ForegroundColor Red
    Write-Host "        $result"
    $FailedImports += "launcher.tauri_integration"
}

# Generate dependency report (uses import names that work, not requirements.txt names)
$DepReport = @()
$DepReport += "# Eve OS - Python Dependency Report"
$DepReport += "# Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
$DepReport += "# Python: $PythonVersion ($Arch)"
$DepReport += ""
$ReportPackages = @(
    "fastapi","uvicorn","httpx","pydantic","pydantic_settings",
    "structlog","aiosqlite","openai","anthropic","psutil",
    "PIL","pyperclip","yaml","playwright"
)
foreach ($pkg in $ReportPackages) {
    $pyCmd = "import $pkg; v = getattr($pkg, '__version__', 'unknown'); print(v)"
    $depLine = & $PythonExe -c $pyCmd 2>&1
    if ($LASTEXITCODE -eq 0) {
        $DepReport += "- $pkg==$depLine"
    }
}
$DepReport += ""
$DepReport += "# Additional runtime packages:"
$DepReport += "- launcher.tauri_integration"
$DepReportPath = "$PSScriptRoot\..\dependency-report.txt"
$DepReport | Out-File -FilePath $DepReportPath -Encoding utf8
Write-Host "      Dependency report: $DepReportPath"

if ($FailedImports.Count -gt 0) {
    Write-Host ""
    Write-Host "!!! DEPENDENCY VERIFICATION FAILED !!!" -ForegroundColor Red
    Write-Host "    The following packages failed to import:" -ForegroundColor Red
    foreach ($f in $FailedImports) {
        Write-Host "    - $f" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "Failing build due to missing dependencies" -ForegroundColor Red
    exit 1
}

# ---- Optional: sync to target/release for local testing ----
if ($SyncToTarget) {
    Write-Host "      Syncing to $TargetDir ..."
    if (Test-Path -LiteralPath "$TargetDir\python") {
        Remove-Item -Recurse -Force -LiteralPath "$TargetDir\python"
    }
    if (Test-Path -LiteralPath "$TargetDir\launcher") {
        Remove-Item -Recurse -Force -LiteralPath "$TargetDir\launcher"
    }
    if (Test-Path -LiteralPath "$TargetDir\backend") {
        Remove-Item -Recurse -Force -LiteralPath "$TargetDir\backend"
    }
    Copy-Item -Recurse -Force -LiteralPath $OutputDir -Destination "$TargetDir\python"
    Copy-Item -Recurse -Force -LiteralPath "$OutputDir\..\launcher" -Destination "$TargetDir\launcher"
    Copy-Item -Recurse -Force -LiteralPath "$OutputDir\..\backend" -Destination "$TargetDir\backend"
    Write-Host "      Synced Python runtime to target/release/"
}

# ---- Cleanup ----
Write-Host "      Cleaning up..."
Get-ChildItem -Path $OutputDir -Recurse -Include "__pycache__", "*.pyc", "*.pyo" -Directory -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path "$SitePackages" -Recurse -Include "*.dist-info" -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    $docsDir = Join-Path $_.FullName "docs"
    if (Test-Path -LiteralPath $docsDir) {
        Remove-Item -Recurse -Force -LiteralPath $docsDir -ErrorAction SilentlyContinue
    }
}
Remove-Item -Recurse -Force -LiteralPath "$OutputDir\..\launcher\__pycache__" -ErrorAction SilentlyContinue

# Remove stray .py files from python root that shadow real packages
$StrayPyFiles = @("anyio.py", "trio.py", "uvloop.py", "sniffio.py", "typing_extensions.py")
foreach ($file in $StrayPyFiles) {
    $path = "$OutputDir\$file"
    if (Test-Path -LiteralPath $path) {
        $size = (Get-Item -LiteralPath $path).Length
        Write-Host "      Removing stray $file ($($size) bytes)"
        Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
    }
}

# ---- Summary ----
$pythonSize = (Get-ChildItem -Recurse -LiteralPath $OutputDir | Measure-Object -Property Length -Sum).Sum
$totalSize = (Get-ChildItem -Recurse -LiteralPath "$OutputDir\.." | Measure-Object -Property Length -Sum).Sum

Write-Host ""
Write-Host "======================================================"
Write-Host "  Bundle Complete"
Write-Host "  Python runtime: $([math]::Round($pythonSize / 1MB, 1)) MB"
Write-Host "  Total bundled:  $([math]::Round($totalSize / 1MB, 1)) MB"
Write-Host "  Dependencies:    $($ImportNames.Count) verified, 0 failed"
Write-Host "======================================================"
Write-Host ""
Write-Host "  Python:    $PythonExe"
Write-Host "  Launcher:  $OutputDir\..\launcher"
Write-Host "  Backend:   $OutputDir\..\backend"
Write-Host "  Report:    $DepReportPath"
Write-Host ""
