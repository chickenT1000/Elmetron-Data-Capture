# Clear Elmetron Database Script
# Backs up and clears the test database

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$dataDir = "data"
$dbFile = "$dataDir\elmetron.sqlite"
$backupFile = "$dataDir\elmetron.sqlite.backup_$timestamp"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Elmetron Database Clear Utility" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check if database exists
if (-not (Test-Path $dbFile)) {
    Write-Host "[ERROR] Database not found: $dbFile" -ForegroundColor Red
    exit 1
}

# Get current size
$currentSize = (Get-Item $dbFile).Length / 1MB
Write-Host "[INFO] Current database size: $([math]::Round($currentSize, 2)) MB" -ForegroundColor Yellow

# Create backup
Write-Host "[INFO] Creating backup: $backupFile" -ForegroundColor Yellow
Copy-Item $dbFile $backupFile -Force

# Delete database and WAL files
Write-Host "[INFO] Removing database files..." -ForegroundColor Yellow
Remove-Item "$dbFile" -Force
if (Test-Path "$dbFile-wal") { Remove-Item "$dbFile-wal" -Force }
if (Test-Path "$dbFile-shm") { Remove-Item "$dbFile-shm" -Force }

Write-Host "`n[OK] Database cleared successfully!" -ForegroundColor Green
Write-Host "[OK] Backup saved to: $backupFile" -ForegroundColor Green
Write-Host "`nThe database will be automatically recreated when services start.`n" -ForegroundColor Cyan
