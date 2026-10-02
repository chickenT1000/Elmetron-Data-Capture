# Service Health - Log Levels Explained

## What You Were Seeing (DEBUG Logs)

```
DEBUG - capture - Window captured data
{"bytes":900,"frames_total":405}
```

**What it means:**
- These are **DEBUG** level logs - very verbose, for developers only
- "Window captured data" = routine confirmation that data capture is working
- Happens every ~10 seconds during normal operation
- **Not important for typical users** - just noise confirming the system is working

---

## Log Levels (Priority Order)

### **CRITICAL** (Highest Priority) 🔴
- System is broken or about to crash
- Immediate action required
- Examples:
  - "Database connection lost"
  - "Device communication failed completely"
  - "Out of memory"

### **ERROR** 🔴
- Something failed but system continues
- Should be investigated
- Examples:
  - "Failed to save measurement to database"
  - "Command timeout - device not responding"
  - "Export failed"

### **WARNING** ⚠️
- Potential problem or degraded performance
- System still working but needs attention
- Examples:
  - "Disk space low"
  - "Calibration overdue"
  - "Device responding slowly"

### **INFO** ℹ️
- Important events users should know about
- Normal operation milestones
- Examples:
  - "Calibration started"
  - "Session created"
  - "Export completed successfully"
  - "Device connected"

### **DEBUG** 🐛 (Lowest Priority)
- Verbose technical details
- For developers/troubleshooting only
- Examples:
  - "Window captured data" (routine confirmation)
  - "Command sent: GET_TEMP"
  - "Buffer flushed: 1024 bytes"
  - Internal state changes

---

## What We Changed

### Before:
- Showed **ALL** log levels including DEBUG
- Result: 90% of logs were routine "Window captured data" messages
- Too noisy, hid important events

### After:
- Filter: Show only **INFO and above** (INFO, WARNING, ERROR, CRITICAL)
- Result: Only important events visible
- Users see:
  - ✅ Calibrations
  - ✅ Sessions starting/stopping
  - ✅ Errors and warnings
  - ✅ Important state changes
  - ❌ Routine debug messages (hidden)

---

## Time Display Issue

**Problem:** Times are off from PC time (after recent time change)

**Likely Causes:**
1. **Daylight Saving Time (DST)** change not handled properly
2. Backend storing times in UTC but displaying without timezone conversion
3. Browser timezone not matching system timezone

**Where to Fix:**
- Backend should store times in UTC
- Frontend should convert UTC to local time for display
- Check timezone handling in:
  - `formatDateTime()` function
  - Backend timestamp generation
  - Database timestamp columns

**Example Fix:**
```typescript
const formatDateTime = (value?: string | null): string => {
  if (!value) return 'Never';
  const date = new Date(value);
  if (isNaN(date.getTime())) return value;
  
  // Use local timezone
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};
```

---

## Summary

### What Those Logs Meant:
- ❌ **DEBUG** logs = routine noise, not important
- ✅ Now filtered out - you'll only see important events

### What You'll See Now:
- **INFO**: Calibrations, sessions, normal milestones
- **WARNING**: Things needing attention
- **ERROR**: Failures and problems
- **CRITICAL**: Urgent issues

### Next Steps:
1. ✅ **Done:** Filter out DEBUG logs
2. ⏳ **TODO:** Fix time display (timezone/DST issue)
3. ⏳ **Optional:** Add toggle to show DEBUG logs for advanced users
