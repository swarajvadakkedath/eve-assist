<#
.SYNOPSIS
Eve OS Development Launcher - Restart

.DESCRIPTION
Stops then starts the Eve development environment.

.EXAMPLE
.\restart.ps1
#>

$Cyan = "$([char]27)[36m"
$Bold = "$([char]27)[1m"
$Reset = "$([char]27)[0m"

Write-Host ""
Write-Host "  $Bold$Cyan Eve OS - Restarting$Reset"
Write-Host "  $('=' * 30)"

# Stop
& "$PSScriptRoot\stop.ps1"

# Brief pause to let ports release
Start-Sleep -Seconds 2

# Start
& "$PSScriptRoot\start.ps1"
