#!/usr/bin/env pwsh
# Elmetron Data Capture - Full Cleanup and Restart Script
# This script stops services, cleans caches, reinstalls dependencies, and restarts

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Elmetron Data Capture - Cleanup & Restart" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Stop all Python and Node processes
Write-Host "[1/6] Stopping services..." -ForegroundColor Yellow
Write-Host "  Killing Python processes on ports 8050, 8051..." -ForegroundColor Gray

# Find and kill processes on the service ports
$ports = @(8050, 8051, 5173)
foreach ($port in $ports) {
    $connection = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($connection) {
        $process = Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "    Stopping $($process.ProcessName) (PID: $($process.Id)) on port $port" -ForegroundColor Gray
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
    }
}

# Wait for processes to terminate
Write-Host "  Waiting 3 seconds for processes to terminate..." -ForegroundColor Gray
Start-Sleep -Seconds 3

Write-Host "  ✓ Services stopped" -ForegroundColor Green
Write-Host ""

# Step 2: Clean Vite cache
Write-Host "[2/6] Cleaning Vite cache..." -ForegroundColor Yellow
$viteCachePath = "ui\node_modules\.vite"
if (Test-Path $viteCachePath) {
    Write-Host "  Removing $viteCachePath" -ForegroundColor Gray
    Remove-Item -Recurse -Force $viteCachePath -ErrorAction SilentlyContinue
    Write-Host "  ✓ Vite cache cleared" -ForegroundColor Green
} else {
    Write-Host "  No Vite cache found (this is OK)" -ForegroundColor Gray
}
Write-Host ""

# Step 3: Clean Vite dist
Write-Host "[3/6] Cleaning UI dist folder..." -ForegroundColor Yellow
$distPath = "ui\dist"
if (Test-Path $distPath) {
    Write-Host "  Removing $distPath" -ForegroundColor Gray
    Remove-Item -Recurse -Force $distPath -ErrorAction SilentlyContinue
    Write-Host "  ✓ UI dist folder cleared" -ForegroundColor Green
} else {
    Write-Host "  No dist folder found (this is OK)" -ForegroundColor Gray
}
Write-Host ""

# Step 4: Clean log files
Write-Host "[4/6] Archiving old logs..." -ForegroundColor Yellow
$capturesPath = "captures"
if (Test-Path $capturesPath) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $archivePath = "captures\archive_$timestamp"
    New-Item -ItemType Directory -Path $archivePath -Force | Out-Null
    
    $logFiles = Get-ChildItem -Path $capturesPath -Filter "*.log" -File
    if ($logFiles.Count -gt 0) {
        Write-Host "  Moving $($logFiles.Count) log files to archive..." -ForegroundColor Gray
        foreach ($logFile in $logFiles) {
            Move-Item -Path $logFile.FullName -Destination $archivePath -Force -ErrorAction SilentlyContinue
        }
        Write-Host "  ✓ Logs archived to $archivePath" -ForegroundColor Green
    } else {
        Write-Host "  No log files to archive" -ForegroundColor Gray
        Remove-Item -Path $archivePath -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "  No captures folder found" -ForegroundColor Gray
}
Write-Host ""

# Step 5: Reinstall UI dependencies
Write-Host "[5/6] Reinstalling UI dependencies..." -ForegroundColor Yellow
Write-Host "  This may take a minute..." -ForegroundColor Gray

Push-Location ui
try {
    # Check if npm is available
    $npmPath = (Get-Command npm -ErrorAction SilentlyContinue).Source
    if (-not $npmPath) {
        Write-Host "  ✗ npm not found! Please install Node.js" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "  Running: npm install" -ForegroundColor Gray
    npm install 2>&1 | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ UI dependencies installed" -ForegroundColor Green
    } else {
        Write-Host "  ✗ npm install failed (exit code: $LASTEXITCODE)" -ForegroundColor Red
        Write-Host "  You may need to run 'npm install' manually in the ui folder" -ForegroundColor Yellow
    }
} finally {
    Pop-Location
}
Write-Host ""

# Step 6: Instructions for restart
Write-Host "[6/6] Cleanup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "1. Open the launcher (py launcher.py)" -ForegroundColor White
Write-Host "2. Click 'Start' to start all services" -ForegroundColor White
Write-Host "3. Wait for all services to show green" -ForegroundColor White
Write-Host "4. The browser should open automatically" -ForegroundColor White
Write-Host ""
Write-Host "If the launcher is already open, you can just click 'Start' now." -ForegroundColor Yellow
Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
