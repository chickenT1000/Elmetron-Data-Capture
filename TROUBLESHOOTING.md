# Troubleshooting Guide

This document covers common issues and their solutions for the Elmetron Data Capture system.

## Table of Contents
- [Service Won't Start](#service-wont-start)
- [Database Corruption](#database-corruption)
- [No Data Being Received](#no-data-being-received)
- [Device Connection Issues](#device-connection-issues)
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