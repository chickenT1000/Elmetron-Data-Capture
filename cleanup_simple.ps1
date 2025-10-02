Write-Host "=========================================="
Write-Host "Elmetron Data Capture - Cleanup & Restart"
Write-Host "=========================================="
Write-Host ""

Write-Host "[1/5] Stopping services..."
$ports = @(8050, 8051, 5173)
foreach ($port in $ports) {
    $connection = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($connection) {
        $process = Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "  Stopping $($process.ProcessName) on port $port"
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
    }
}
Write-Host "  Waiting 3 seconds..."
Start-Sleep -Seconds 3
Write-Host "  Done"
Write-Host ""

Write-Host "[2/5] Cleaning Vite cache..."
if (Test-Path "ui\node_modules\.vite") {
    Remove-Item -Recurse -Force "ui\node_modules\.vite" -ErrorAction SilentlyContinue
    Write-Host "  Vite cache cleared"
} else {
    Write-Host "  No cache found"
}
Write-Host ""

Write-Host "[3/5] Cleaning dist folder..."
if (Test-Path "ui\dist") {
    Remove-Item -Recurse -Force "ui\dist" -ErrorAction SilentlyContinue
    Write-Host "  Dist cleared"
}
Write-Host ""

Write-Host "[4/5] Archiving logs..."
if (Test-Path "captures") {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $archivePath = "captures\archive_$timestamp"
    New-Item -ItemType Directory -Path $archivePath -Force | Out-Null
    Get-ChildItem -Path "captures" -Filter "*.log" -File | Move-Item -Destination $archivePath -ErrorAction SilentlyContinue
    Write-Host "  Logs archived"
}
Write-Host ""

Write-Host "[5/5] Reinstalling UI dependencies..."
Push-Location ui
npm install
Pop-Location
Write-Host ""

Write-Host "=========================================="
Write-Host "Cleanup complete!"
Write-Host "=========================================="
Write-Host "Next: Click 'Start' in the launcher"
Write-Host ""
