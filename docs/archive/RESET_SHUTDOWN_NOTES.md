# Reset Button - Graceful Shutdown Implementation

## Overview
The Reset button now uses a **database-safe graceful shutdown** strategy with three phases.

## Shutdown Phases

### Phase 1: Graceful Shutdown Request (SIGTERM)
- Sends `SIGTERM` signal to all services
- This triggers signal handlers in:
  - **Data API Service**: Calls `cleanup()` → closes database connection
  - **Capture Service**: Calls `request_stop()` → flushes data and closes DB
  - **UI Server**: Receives termination signal

### Phase 2: Wait for Clean Exit (5 seconds max)
- Checks every 0.2 seconds if processes have exited
- Services have time to:
  - Close database connections properly
  - Flush any pending writes
  - Release file handles
  - Clean up resources
- Maximum wait: **5 seconds**

### Phase 3: Force-Kill Stubborn Processes (last resort)
- Only used if a process doesn't exit within 5 seconds
- Uses `taskkill /F /T` on Windows
- Typically only needed for UI server (Node/Vite)
- **Data API and Capture Service should exit gracefully in Phase 2**

## Database Safety

### ✅ Safe Shutdown Path (Normal Case)
1. SIGTERM sent to Data API
2. Data API signal handler calls `cleanup()`
3. `cleanup()` calls `db.close()`
4. SQLite connection closed cleanly
5. No corruption risk

### ⚠️ Force-Kill Path (Rare Case)
- Only triggered if service hangs for >5 seconds
- This should NOT happen under normal conditions
- If it does happen, indicates a bug in the service

## Signal Handlers

### Data API Service (`data_api_service.py`)
```python
def signal_handler(signum, frame):
    signal_name = signal.Signals(signum).name
    logger.info(f"[SIGNAL] Received signal {signal_name}")
    cleanup()  # Closes database connection
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
```

### Capture Service (`cx505_capture_service.py`)
```python
def signal_handler(signum, frame):
    if not shutdown_requested:
        shutdown_requested = True
        print(f'Received shutdown signal {signum}, stopping capture...')
        runner.service.request_stop()  # Flushes and closes DB

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
```

## Expected Reset Timeline

| Time | Action |
|------|--------|
| 0s | User clicks Reset button |
| 0s | Launcher sends SIGTERM to all services |
| 0-1s | Data API closes DB and exits |
| 0-1s | Capture Service flushes, closes DB, and exits |
| 1-3s | UI server (Node/Vite) exits |
| 3-5s | If any service hung, force-kill it |
| 5-8s | Wait for ports to be freed |
| 8-10s | Services restart |
| **Total: ~8-10 seconds** |

## Testing Recommendations

1. **Normal Reset**: Should complete in ~8-10 seconds with all graceful exits
2. **Database Integrity**: Run after Reset to verify no corruption
   ```bash
   sqlite3 captures/device_data.db "PRAGMA integrity_check;"
   ```
3. **Log Verification**: Check logs for graceful shutdown messages:
   ```
   [SIGNAL] Received signal SIGTERM
   [OK] Database connection closed
   [BYE] Data API service stopped
   ```

## Troubleshooting

### If Reset takes >15 seconds:
- Check logs for which service is hanging
- Likely the UI server (Node/Vite) on Windows
- This is normal - force-kill will handle it

### If database corruption occurs:
- Should NOT happen with this implementation
- Indicates a service didn't respond to SIGTERM
- Check service logs for exceptions in shutdown path
- May need to increase `max_wait` timeout

### If "port already in use" errors:
- Launcher waits up to 15s for ports to be freed
- If still occurring, increase port wait timeout in launcher

## Code Location
- **Launcher**: `launcher.py` → `_terminate_processes()` method (line ~760)
- **Data API**: `data_api_service.py` → `signal_handler()` (line ~635)
- **Capture Service**: `cx505_capture_service.py` → `signal_handler()` (line ~150)
