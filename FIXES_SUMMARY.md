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
