$ErrorActionPreference = "Stop"
$PythonExe = "E:\Eve_Ai\desktop\src-tauri\python\python.exe"
$GetPipFile = "$env:TEMP\get-pip.py"
$SitePackages = "E:\Eve_Ai\desktop\src-tauri\python\Lib\site-packages"

Write-Host "Step 1: Running pip install..."
$pipOutput = & $PythonExe $GetPipFile --no-warn-script-location --target "$SitePackages" 2>&1
$pipExitCode = $LASTEXITCODE
Write-Host "LASTEXITCODE = $LASTEXITCODE"
Write-Host "pipExitCode = $pipExitCode"
Write-Host "pipOutput type = $($pipOutput.GetType().Name)"

if ($pipExitCode -ne 0) {
    Write-Host "FAILED (exit code $pipExitCode)" -ForegroundColor Red
    Write-Host "Output: $pipOutput"
    exit 1
}
Write-Host "pip install OK" -ForegroundColor Green
exit 0
