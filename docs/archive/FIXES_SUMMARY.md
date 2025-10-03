# CX505 Connectivity Fixes - Summary

## Problem
CX505 device was detected but no measurements were being recorded in the database.

## Root Causes Identified

### 1. **Poll Interval Configuration** (CRITICAL)
- **Issue**: `poll_interval_s` was set to `0.0` in `config/protocols.toml`
- **Effect**: Disabled periodic handshake transmission, causing CX505 to stop streaming data
- **Fix**: Restored `poll_interval_s = 1.0` in `config/protocols.toml`
- **Rationale**: CX505 requires periodic handshake (`01 23 30 23 30 23 30 23 03`) every ~1 second to continue streaming measurements

### 2. **Database Constraint** (Fixed)
- **Issue**: `frame_id` column in `measurements` table had `NOT NULL` constraint, but code tried to insert `NULL` when `store_raw_frames` was disabled
- **Fix**: Modified `elmetron/storage/database.py` to always insert raw frames (removed conditional logic)
- **Location**: Line 735 in `database.py`

### 3. **Signal Handling** (Already Fixed in Previous Session)
- **Issue**: Service didn't handle SIGTERM/SIGINT properly, preventing graceful device closure
- **Fix**: Added signal handlers in `cx505_capture_service.py`
- **Effect**: Prevents device from being "busy" for other processes after service termination

## Verification

### Test Results
- **Direct cx505_d2xx.py test**: ✅ Working (1300 bytes, 13 frames in 15s)
- **Service test with poll_interval=1.0**: ✅ Working (27 measurements in 30s, 1900 bytes)
- **Health API**: ✅ Responsive (state: running, bytes_read increasing)
- **Database**: ✅ Measurements being recorded correctly

### Current Configuration
```toml
# config/protocols.toml
[profiles.cx505]
poll_hex = "01 23 30 23 30 23 30 23 03"
poll_interval_s = 1.0  # Must be > 0 for CX505!
baud = 115200
data_bits = 8
stop_bits = 2.0
parity = "E"
```

## Key Learnings
1. **CX505 Protocol**: Device requires continuous polling (handshake every ~1s) to maintain streaming
2. **Never set poll_interval_s to 0** for CX505 - it's not a "send once" handshake
3. **Database schema**: `frame_id` must always have a value (can't be NULL)
4. **Testing approach**: Compare old working code with new code to identify regression

## Files Modified
1. `config/protocols.toml` - Restored poll_interval_s = 1.0
2. `elmetron/storage/database.py` - Always insert raw frames
3. `cx505_capture_service.py` - Added signal handlers (previous session)

## Status
✅ **RESOLVED** - CX505 is now receiving and recording measurements successfully.

---

## Database Corruption Issue (2025-09-30)

### Problem
After forcefully stopping Python processes during testing, the SQLite database became corrupted:
```
sqlite3.DatabaseError: database disk image is malformed
```

### Root Cause
SQLite databases use Write-Ahead Logging (WAL) and when processes are killed with `-Force`, they can't properly close the database connection, leading to corruption.

### Recovery Steps Taken
1. **Backed up corrupted database**: `data/elmetron.sqlite.corrupted.20250930_143523`
2. **Removed corrupted files**: Deleted `.sqlite`, `.sqlite-wal`, `.sqlite-shm` files
3. **Created fresh database**: Used `Database.connect()` and `Database.initialise()`
4. **Verified integrity**: Confirmed all tables created and integrity check passed

### Prevention - Best Practices

#### ✅ CORRECT Way to Stop Services:
1. **Via UI**: Click the "Stop" button and wait for confirmation
2. **Via Terminal**: Press `Ctrl+C` and wait for "capture stopped" message
3. **Via Script**: Send SIGTERM (not SIGKILL) to allow graceful shutdown

#### ❌ WRONG - Never Do This:
```powershell
# This can corrupt the database!
Get-Process python | Stop-Process -Force
```

#### ✅ CORRECT - Safe Shutdown:
```powershell
# Stop via UI first, or:
# Send Ctrl+C, then wait for process to exit naturally
```

### Database File Management

#### Files to Include in .gitignore:
```gitignore
*.sqlite           # Main database file
*.sqlite-journal   # Rollback journal
*.sqlite-wal       # Write-Ahead Log
*.sqlite-shm       # Shared memory file
```

#### Backup Strategy:
- Corrupted databases are automatically backed up with timestamp
- Manual backups can be created before risky operations:
  ```powershell
  Copy-Item data/elmetron.sqlite "data/elmetron.sqlite.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
  ```

#### Recovery Process:
If database becomes corrupted:
```powershell
# 1. Backup corrupted database
Copy-Item data/elmetron.sqlite data/elmetron.sqlite.corrupted

# 2. Remove corrupted files
Remove-Item data/elmetron.sqlite* -Force

# 3. Recreate database
py -c "from pathlib import Path; from elmetron import load_config; from elmetron.storage import Database; config = load_config(Path('config/app.toml')); db = Database(config.storage); db.connect(); db.initialise(); db.close()"
```

### Additional Notes
- Old measurement data from corrupted database is preserved in backup files
- A fresh database starts with Session ID 1
- The service will automatically create required tables on first run if they don't exist
