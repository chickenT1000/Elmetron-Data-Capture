# Troubleshooting Guide

This document covers common issues and their solutions for the Elmetron Data Capture system.

## Table of Contents
- [Service Won't Start](#service-wont-start)
- [Database Corruption](#database-corruption)
- [No Data Being Received](#no-data-being-received)
- [Device Connection Issues](#device-connection-issues)
- [UI Shows Archive Mode](#ui-shows-archive-mode)
- [UI API Errors (404/500)](#ui-api-errors-404500)
- [Git Branch Switching Problems](#git-branch-switching-problems)

---

## Service Won't Start

### Symptom
```
ERROR: Capture service did not respond at /health.
Process capture exited with code 1
```

### Common Causes & Solutions

#### 1. Database Corruption
**Check**: Run database integrity check
```powershell
py -c "import sqlite3; conn = sqlite3.connect('data/elmetron.sqlite'); cursor = conn.cursor(); cursor.execute('PRAGMA integrity_check'); print(cursor.fetchone()[0])"
```

**Solution**: See [Database Corruption](#database-corruption) section below.

#### 2. Port Already in Use
**Check**: Another instance is running on the same port
```powershell
netstat -ano | findstr :8050
```

**Solution**: Stop conflicting process or use a different port
```powershell
# Stop existing Python processes
Get-Process python -ErrorAction SilentlyContinue | Stop-Process

# Or specify different port
py cx505_capture_service.py --health-api-port 8051
```

#### 3. Missing Configuration Files
**Check**: Verify config files exist
```powershell
Test-Path config/app.toml
Test-Path config/protocols.toml
```

**Solution**: Ensure configuration files are in place and valid TOML format.

---

## Database Corruption

### Symptom
```
sqlite3.DatabaseError: database disk image is malformed
```

### Root Cause
Database was not properly closed (e.g., process killed with `Stop-Process -Force`)

### Recovery Steps

#### Step 1: Backup Corrupted Database
```powershell
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item data/elmetron.sqlite "data/elmetron.sqlite.corrupted.$timestamp"
```

#### Step 2: Remove Corrupted Files
```powershell
Remove-Item data/elmetron.sqlite -Force
Remove-Item data/elmetron.sqlite-wal -Force -ErrorAction SilentlyContinue
Remove-Item data/elmetron.sqlite-shm -Force -ErrorAction SilentlyContinue
```

#### Step 3: Recreate Database
```powershell
py -c "from pathlib import Path; from elmetron import load_config; from elmetron.storage import Database; config = load_config(Path('config/app.toml')); db = Database(config.storage); db.connect(); db.initialise(); db.close()"
```

#### Step 4: Verify
```powershell
py -c "import sqlite3; conn = sqlite3.connect('data/elmetron.sqlite'); cursor = conn.cursor(); cursor.execute('PRAGMA integrity_check'); print(f'Status: {cursor.fetchone()[0]}'); cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\"'); print(f'Tables: {len(cursor.fetchall())}'); conn.close()"
```

### Prevention

**✅ ALWAYS Stop Services Gracefully:**
- Via UI: Click "Stop" button and wait for confirmation
- Via Terminal: Press `Ctrl+C` and wait for "capture stopped" message
- Never use: `Get-Process python | Stop-Process -Force`

**✅ Regular Backups:**
```powershell
# Create backup before risky operations
Copy-Item data/elmetron.sqlite "data/elmetron.sqlite.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
```

---

## No Data Being Received

### Symptom
- Health API shows `bytes_read: 0` or low values
- Database has no new measurements
- Logs show "Waiting for data... (RX queue: 0 bytes)"

### Diagnostic Steps

#### 1. Check Device Connection
```powershell
py -c "from elmetron.hardware import list_devices; devices = list_devices(); print('Connected devices:'); [print(f'  [{d.index}] {d.description} (S/N {d.serial})') for d in devices]"
```

**Expected**: Should show CX505 device
**If empty**: Check USB connection, try different port, check device power

#### 2. Test Direct Communication
```powershell
py cx505_d2xx.py --duration 15 --poll-hex "01 23 30 23 30 23 30 23 03" --poll-interval 1.0 --baud 115200 --databits 8 --stopbits 2 --parity E
```

**Expected**: Should receive frames with measurement data
**If fails**: Hardware or driver issue

#### 3. Check Poll Interval Configuration
```powershell
Select-String -Path "config/protocols.toml" -Pattern "poll_interval_s"
```

**Expected**: `poll_interval_s = 1.0` (must be > 0 for CX505)
**If 0.0**: Change to 1.0 - CX505 requires continuous polling!

#### 4. Verify Device Mode
- Check CX505 display shows actual measurements (not "Error1" or fault state)
- For testing, use REDOX mode (least sensitive to electrode issues)
- Ensure probe is connected and immersed in solution

### Common Solutions

#### Solution 1: Fix Poll Interval
Edit `config/protocols.toml`:
```toml
[profiles.cx505]
poll_interval_s = 1.0  # Must be > 0!
```

#### Solution 2: Reset Device
1. Unplug CX505 USB cable
2. Wait 5 seconds
3. Reconnect USB cable
4. Restart capture service

#### Solution 3: Check Handshake Payload
Verify in `config/protocols.toml`:
```toml
poll_hex = "01 23 30 23 30 23 30 23 03"  # Correct for CX505
```

---

## Device Connection Issues

### Symptom: Device Shows as "Busy"
Other software can't connect to CX505 after using capture service.

### Cause
Service didn't release device properly (missing signal handlers or forceful termination).

### Solution
1. **Close all applications** using the device
2. **Unplug and replug** USB cable
3. **Ensure signal handlers** are in place (already fixed in current version)

### Verification
Check `cx505_capture_service.py` has signal handlers:
```python
import signal
import sys

def signal_handler(sig, frame):
    print('\nShutdown signal received, stopping gracefully...')
    # ... cleanup code ...
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
```

---

## UI Shows Archive Mode

### Symptom
Web UI displays "Archive Mode" message and shows greyed-out sections even when device is connected.

### What is Archive Mode?
Archive Mode is a graceful degradation state when:
- CX-505 device is not connected
- Capture service is not running
- No live data is flowing (`frames = 0`)

In this mode, users can still **browse historical sessions** but cannot monitor live data.

### Diagnostic Steps

#### 1. Check Device Connection
```powershell
# Check if capture service sees device
curl http://localhost:8051/health | ConvertFrom-Json | Select-Object frames, state
```

**Expected when live**:
```json
{
  "frames": 1234,
  "state": "running"
}
```

**If frames = 0**: Device not sending data (see [No Data Being Received](#no-data-being-received))

#### 2. Check Live Status Endpoint
```powershell
curl http://localhost:8050/api/live/status | ConvertFrom-Json
```

**Expected when live**:
```json
{
  "mode": "live",
  "live_capture_active": true,
  "device_connected": true
}
```

**If mode = "archive"**: System correctly detected no live data

### Solutions

#### Solution 1: Device Not Connected
1. Check CX-505 USB connection
2. Restart capture service
3. Verify device shows in Device Manager

#### Solution 2: Capture Service Not Running
```powershell
# Check if service is running
netstat -ano | findstr :8051

# Restart if needed
py cx505_capture_service.py --config config/app.toml --protocols config/protocols.toml --health-api-port 8051
```

#### Solution 3: Device Connected But No Data
See [No Data Being Received](#no-data-being-received) section for poll interval and configuration fixes.

### Expected Behavior

**When Device is Unplugged (Archive Mode is NORMAL)**:
- ✅ Shows "Archive Mode" info message
- ✅ Can browse Sessions tab for historical data
- ✅ Live monitoring sections hidden (clean UI)
- ℹ️ This is the correct, user-friendly behavior!

**When Device is Connected (Live Mode)**:
- ✅ Shows live measurements updating
- ✅ Health monitoring active
- ✅ All green indicators
- ✅ Command history and logs visible

---

## UI API Errors (404/500)

### Symptom: 404 Not Found Errors

**Common 404 errors in browser console:**
```
GET http://localhost:8050/health/logs 404 (Not Found)
GET http://localhost:8050/sessions/recent 404 (Not Found)
```

### Root Cause
API endpoints were recently reorganized. Older UI code may be calling wrong paths.

### Fixed Endpoints (Current Version)

| Old Path (❌ Wrong) | New Path (✅ Correct) |
|---------------------|----------------------|
| `/health/logs` | `/health/logs` *(health service on :8051)* |
| `/sessions/recent` | `/api/sessions` *(data API on :8050)* |
| `/sessions/{id}/evaluation` | `/api/sessions/{id}/evaluation` |

### Port Configuration

**Two services run on different ports:**

1. **Data API Service (Port 8050)**
   - `/health` - API health check
   - `/api/sessions` - Session list
   - `/api/sessions/{id}` - Session details
   - `/api/sessions/{id}/measurements` - Session measurements
   - `/api/sessions/{id}/evaluation` - Export evaluation data
   - `/api/sessions/{id}/export` - Export session
   - `/api/live/status` - Live/archive mode status

2. **Capture Service (Port 8051)**
   - `/health` - Capture service health
   - `/health/logs` - Health log events
   - `/health/logs.ndjson` - NDJSON log stream (for advanced use)
   - `/health/bundle` - Diagnostic bundle download

### Solutions

#### Solution 1: Verify Services Are Running
```powershell
# Check both services
netstat -ano | findstr "8050 8051"
```

**Expected**: Both ports should show LISTENING

#### Solution 2: Check UI Configuration
Verify `ui/src/config.ts`:
```typescript
const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8050';  // Data API
const DEFAULT_HEALTH_BASE_URL = 'http://127.0.0.1:8051';  // Capture health
```

#### Solution 3: Hard Refresh Browser
```
Ctrl + F5  (or Ctrl + Shift + R)
```

Clears cached API calls and reloads with latest endpoints.

### Symptom: 500 Internal Server Error

**Common causes:**
1. Database schema mismatch
2. Missing table or column
3. Backend exception

### Diagnostic Steps

#### 1. Check Backend Logs
Look for Python exceptions in capture service terminal

#### 2. Test Endpoint Directly
```powershell
curl http://localhost:8050/api/sessions/1/evaluation
```

#### 3. Verify Database Schema
```powershell
py -c "import sqlite3; conn = sqlite3.connect('data/elmetron.sqlite'); print([row for row in conn.execute('PRAGMA table_info(raw_frames)').fetchall()])"
```

### Known Fixes Applied

**✅ Fixed in current version:**
- Database table name: `frames` → `raw_frames`
- Column name: `captured_at` → `created_at`
- Added missing `/api/sessions/{id}/evaluation` endpoint

If you still see 500 errors, database may need recreation (see [Database Corruption](#database-corruption))

---

## Git Branch Switching Problems

### Symptom
```
error: unable to unlink old 'data/elmetron.sqlite-wal': Invalid argument
fatal: Could not reset index file to revision 'HEAD'.
```

### Cause
SQLite WAL files are locked by running capture service.

### Solution

#### Step 1: Stop All Services
```powershell
# Stop Python (capture service)
Get-Process python -ErrorAction SilentlyContinue | Stop-Process

# Stop Node (React dev server)
Get-Process node -ErrorAction SilentlyContinue | Stop-Process
```

#### Step 2: Wait for Database Release
```powershell
Start-Sleep -Seconds 2
```

#### Step 3: Try Git Operation Again
Now branch switching should work in GitHub Desktop.

### Prevention
**Always stop services before Git operations** that involve branch switching or stashing.

---

## Health Check Commands

Quick commands to verify system status:

```powershell
# Check if service is running
Invoke-RestMethod -Uri "http://127.0.0.1:8050/health"

# Check database integrity
py -c "import sqlite3; conn = sqlite3.connect('data/elmetron.sqlite'); print(conn.execute('PRAGMA integrity_check').fetchone()[0])"

# Count recent measurements
py -c "import sqlite3; conn = sqlite3.connect('data/elmetron.sqlite'); print(f'Measurements: {conn.execute(\"SELECT COUNT(*) FROM measurements\").fetchone()[0]}'); conn.close()"

# Check device connection
py -c "from elmetron.hardware import list_devices; print(f'Devices: {len(list_devices())}')"
```

---

## Getting Help

If issues persist:

1. **Check logs**: Review service output for error messages
2. **Test components**: Use direct `cx505_d2xx.py` test to isolate issues
3. **Verify configuration**: Compare with working `config/protocols.toml`
4. **Create issue**: Include error messages, logs, and steps to reproduce

### Useful Debug Information to Collect

```powershell
# System info
py --version
npm --version

# Device info
py -c "from elmetron.hardware import list_devices; [print(vars(d)) for d in list_devices()]"

# Configuration
Get-Content config/app.toml
Get-Content config/protocols.toml

# Database status
py -c "import sqlite3; conn = sqlite3.connect('data/elmetron.sqlite'); print('Tables:', [row[0] for row in conn.execute('SELECT name FROM sqlite_master WHERE type=\"table\"').fetchall()]); print('Sessions:', conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]); print('Measurements:', conn.execute('SELECT COUNT(*) FROM measurements').fetchone()[0])"
```

---

## Future Improvements

### Planned: Crash-Resistant Session Buffering System
**Status**: Roadmap - High Priority (see Road_map.md section 4)

A robust solution is being designed to eliminate database corruption risk entirely:

**Proposed Architecture:**
1. **Session Buffering**: Active session data written to append-only JSONL files in captures/session_{id}_buffer.jsonl
2. **Deferred Database Merge**: Data only committed to SQLite on graceful launcher shutdown
3. **Automatic Recovery**: On startup, system auto-recovers any orphaned buffer files from previous crashes
4. **Periodic Flush**: Every 100 measurements flushed to buffer file to minimize data loss
5. **Audit Trail**: Raw capture files preserved for forensic analysis

**Benefits:**
- ? Eliminates 99% of database corruption scenarios
- ? Automatic crash recovery without manual intervention
- ? Maintains complete audit trail of all raw captures
- ? Minimal performance impact (~5% overhead for file I/O)
- ? Resilient to power loss, task manager kills, and system crashes

**Implementation Timeline:**
Priority raised to **High** after database corruption incident on 2025-09-30. This feature addresses the root cause rather than just documenting recovery procedures.

**Workaround Until Implementation:**
Follow the prevention best practices documented above and always stop services gracefully.