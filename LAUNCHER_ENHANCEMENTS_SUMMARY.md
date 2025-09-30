# Launcher Enhancements - Single-Instance & Hardware Status

## Issues Addressed

### Issue 1: Multiple Launcher Instances
**Problem**: Running `start.bat` multiple times opens multiple launcher windows, causing confusion and potential conflicts.

**Solution**: Single-instance enforcement using lockfile with PID tracking.

### Issue 2: Missing Hardware Status Indicator
**Problem**: Launcher shows all green even when Elmetron CX-505 is not connected, misleading users about hardware readiness.

**Solution**: Added hardware connection status indicator that checks for FTDI device presence.

---

## Implementation Details

### ✅ Single-Instance Enforcement

#### Lockfile Management
**File**: `.launcher.lock` in `captures/` directory

**Mechanism**:
1. On startup, launcher checks if lockfile exists
2. If exists, reads PID and verifies process is still running
3. If running → shows error and exits
4. If not running → removes stale lock and proceeds
5. Writes current PID to lockfile

**Code Added**:
```python
LOCKFILE = CAPTURES_DIR / ".launcher.lock"

def _acquire_lock(self) -> bool:
    """Try to acquire single-instance lock."""
    CAPTURES_DIR.mkdir(exist_ok=True)
    if LOCKFILE.exists():
        # Check if the PID in lockfile is still running
        try:
            with open(LOCKFILE, "r") as f:
                old_pid = int(f.read().strip())
            
            # Try to check if process is still running on Windows
            PROCESS_QUERY_INFORMATION = 0x0400
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, old_pid)
            if handle:
                kernel32.CloseHandle(handle)
                return False  # Process still running
            # Process not running, remove stale lock
            LOCKFILE.unlink()
        except (ValueError, FileNotFoundError, OSError):
            # Stale or invalid lockfile, remove it
            try:
                LOCKFILE.unlink()
            except FileNotFoundError:
                pass
    
    # Write current PID to lockfile
    try:
        with open(LOCKFILE, "w") as f:
            f.write(str(os.getpid()))
        return True
    except OSError:
        return False

def _release_lock(self) -> None:
    """Release single-instance lock."""
    try:
        if LOCKFILE.exists():
            LOCKFILE.unlink()
    except OSError:
        pass
```

**Error Message**:
```
Another instance of the launcher is already running.

Please close the existing launcher window before starting a new one.
```

**Lock Release**: Lockfile removed on normal exit (`_on_close()` and `run()` finally block)

---

### ✅ Hardware Connection Status

#### Hardware Detection Function
```python
def check_hardware_connected() -> bool:
    """Check if Elmetron CX-505 hardware is connected via FTDI."""
    try:
        # Try to load ftd2xx.dll
        ftd2xx = ctypes.WinDLL('ftd2xx.dll')
        
        # Define function signatures
        _ft_create_list = ftd2xx.FT_CreateDeviceInfoList
        _ft_create_list.argtypes = [ctypes.POINTER(ctypes.c_ulong)]
        _ft_create_list.restype = ctypes.c_ulong
        
        # Call FT_CreateDeviceInfoList to get device count
        count = ctypes.c_ulong()
        status = _ft_create_list(ctypes.byref(count))
        
        # Status 0 = success, count > 0 = devices found
        return status == 0 and count.value > 0
    except (OSError, AttributeError):
        # ftd2xx.dll not found or function failed
        return False
```

#### UI Integration
**New Status Row**: "CX-505 Hardware" (positioned at row 2)

**Status Messages**:
- ✅ **Connected**: "CX-505 connected" (green)
- ⚠️ **Not Connected**: "CX-505 not detected (OK for archived sessions)" (orange/waiting)

**Check Timing**: Hardware status checked at start of `_do_start()` before any service startup

**Rationale**: 
- User can still access UI for viewing archived sessions without hardware
- Clear indication of hardware presence before attempting data capture
- Non-blocking - doesn't prevent launcher from starting

---

## UI Changes

### Updated Status Layout

**Before** (6 status rows):
```
Prerequisites
Capture Service
Service Health UI
Dashboard
Overall Status
```

**After** (7 status rows):
```
CX-505 Hardware         ← NEW
Prerequisites
Capture Service
Service Health UI
Dashboard
Overall Status
```

### Grid Position Updates
- Status rows: Start at row 2
- Button row: Moved to row 8 (from row 7)
- Log label: Moved to row 9 (from row 8)
- Log box: Moved to row 10 (from row 9)
- Footer: Moved to row 11 (from row 10)

---

## Files Modified

1. **launcher.py**
   - Added `ctypes` imports for Windows API and FTDI detection
   - Added `LOCKFILE` constant
   - Added `check_hardware_connected()` function
   - Added `_acquire_lock()` and `_release_lock()` methods
   - Added `_check_hardware()` method
   - Updated `__init__()` with lock acquisition
   - Updated `_build_ui()` with hardware status row
   - Updated `_do_start()` to check hardware
   - Updated `_set_initial_statuses()` to include hardware
   - Updated `_on_close()` and `run()` to release lock
   - Adjusted all UI grid positions

2. **Road_map.md**
   - Added 2 new high-priority task entries

---

## Testing Checklist

### Single-Instance Enforcement
- [x] Run `start.bat` once → Launcher opens
- [ ] Run `start.bat` again → Error message, no second window
- [ ] Close first launcher → Lockfile removed
- [ ] Run `start.bat` again → Opens normally
- [ ] Kill launcher process → Stale lock cleaned up on next start

### Hardware Status
- [ ] **With CX-505 connected**: 
  - Start launcher
  - Hardware status shows "CX-505 connected" (green)
  - Services start normally
  
- [ ] **Without CX-505 connected**:
  - Start launcher
  - Hardware status shows "CX-505 not detected (OK for archived sessions)" (orange)
  - Services still start (UI accessible for archived data)
  
- [ ] **Device disconnected during operation**:
  - Start with device connected
  - Disconnect device
  - Press Reset
  - Hardware status updates to "not detected"

---

## Expected Behavior

### Single-Instance
✅ **Only one launcher can run at a time**
✅ **Clear error message if already running**
✅ **Stale locks automatically cleaned**
✅ **Clean lockfile removal on exit**

### Hardware Status
✅ **Real-time device detection**
✅ **Non-blocking (UI still accessible)**
✅ **Clear status indication**
✅ **User-friendly messaging**

---

## Benefits

1. **Prevents Confusion**: No more multiple launcher windows competing for resources
2. **Better UX**: Clear indication of hardware connection state
3. **Flexibility**: UI can be used for archived sessions without hardware
4. **Robustness**: Stale lock detection prevents permanent lockout
5. **Professional**: Matches behavior of professional desktop applications

---

## Implementation Date
**September 30, 2025**

**Features**:
- Single-instance enforcement with lockfile
- Hardware connection status indicator
- Updated UI layout for hardware status

**Author**: Factory AI Droid

**Status**: ✅ Implemented & Syntax Validated

---

## Next Steps

1. **Manual Testing**: Test both features with device connected/disconnected
2. **User Feedback**: Get feedback on warning message clarity
3. **Documentation**: Update operator playbook with hardware status info
4. **Optional**: Add tooltip to hardware status explaining what it means

---

## Notes

- Lockfile stored in `captures/.launcher.lock` (gitignored)
- Hardware check uses FTDI D2XX library (same as capture service)
- Status message explains that UI works without hardware (for archived sessions)
- All UI grid positions updated to accommodate new status row
