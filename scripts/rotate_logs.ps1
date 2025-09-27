[CmdletBinding()]
param(
    [string]$LogPath = 'C:\Elmetron\logs\capture.log',
    [int]$RetentionDays = 30,
    [switch]$KeepCurrent,
    [switch]$WhatIf
)

Set-StrictMode -Version Latest

function Write-Note([string]$message) {
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Write-Output "[$timestamp] $message"
}

$logDir = Split-Path -Parent $LogPath
if (-not $logDir) {
    throw "Unable to derive log directory from path '$LogPath'."
}

if (-not (Test-Path $logDir)) {
    throw "Log directory '$logDir' does not exist."
}

$logFile = Split-Path -Leaf $LogPath
$prefix = [System.IO.Path]::GetFileNameWithoutExtension($logFile)
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$archiveName = "{0}_{1}.log.zip" -f $prefix, $timestamp
$archivePath = Join-Path $logDir $archiveName

if (Test-Path $LogPath -PathType Leaf) {
    $tempCopy = Join-Path $logDir ("{0}_{1}.log" -f $prefix, $timestamp)
    Write-Note "Archiving '$LogPath' to '$archivePath'."
    if (-not $WhatIf) {
        Copy-Item -LiteralPath $LogPath -Destination $tempCopy -Force
        Compress-Archive -LiteralPath $tempCopy -DestinationPath $archivePath -Force
        Remove-Item -LiteralPath $tempCopy -Force
        if (-not $KeepCurrent) {
            Clear-Content -LiteralPath $LogPath
        }
    }
} else {
    Write-Note "Log file '$LogPath' missing; skipping archive step."
}

$threshold = (Get-Date).AddDays(-[math]::Abs($RetentionDays))
$oldArchives = Get-ChildItem -LiteralPath $logDir -Filter "${prefix}_*.log.zip" -File |
    Where-Object { $_.LastWriteTime -lt $threshold }

foreach ($item in $oldArchives) {
    Write-Note "Removing expired archive '$($item.FullName)' (older than $RetentionDays days)."
    if (-not $WhatIf) {
        Remove-Item -LiteralPath $item.FullName -Force
    }
}

Write-Note "Rotation complete for '$LogPath'."
