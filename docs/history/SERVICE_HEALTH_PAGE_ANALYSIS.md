# Service Health Page - Analysis & Cleanup Plan

## Current Issues

### 1. **Polling Shows as Warning (Yellow/Error State)**
**Problem:** `polling` connection state is shown with warning color and label "Polling fallback"
**Reality:** Polling is a **correct and normal mode** - not an error!

**Current Code:**
```tsx
const connectionStateColor = (state: HealthLogConnectionState) => {
  switch (state) {
    case 'streaming':
      return 'success';  // Green
    case 'polling':
      return 'warning';  // Yellow - WRONG!
    case 'error':
      return 'error';    // Red
```

**Label:**
```tsx
case 'polling':
  return 'Polling fallback';  // Sounds negative!
```

**Fix:**
- Change `polling` color to `'success'` (green)
- Change label from "Polling fallback" to just "Polling" or "Active (Polling)"

---

## What All the Monitors Mean

### Core Service Status

#### 1. **Service State** (data.state)
- **What:** Is the capture service running?
- **Values:** 
  - `running` (green) - Service is active
  - `stopped` (red) - Service not running
- **Necessary:** ✅ **YES** - Critical to know if service is alive

#### 2. **Watchdog Alert** (data.watchdog_alert)
- **What:** Has the watchdog detected the service is hung/frozen?
- **Purpose:** Safety mechanism that monitors if service stops responding
- **Necessary:** ✅ **YES** - Catches frozen/crashed service

#### 3. **Mode** (liveStatus?.mode)
- **What:** Is a device connected?
- **Values:**
  - `live` - Device connected and streaming
  - `archive` - No device, viewing historical data
- **Necessary:** ✅ **YES** - Critical context

---

### Log Connection State

#### 4. **Log Stream Status** (logConnectionState)
- **What:** How are logs being received?
- **Values:**
  - `streaming` - Server-Sent Events (SSE) active
  - `polling` - Fallback to regular HTTP polling
  - `error` - Can't connect
  - `connecting` - Establishing connection
  - `loading` - Initial load
- **Necessary:** ✅ **YES** - Important diagnostic info
- **Fix Needed:** ✅ Remove "warning" for polling - it's normal!

---

### Command Queue Metrics

#### 5. **Queue Depth** (commandMetrics.queue_depth)
- **What:** Number of commands waiting to be sent to device
- **Purpose:** Detect if commands are backing up
- **Normal:** 0-2 commands
- **Warning:** >5 commands (device might be slow/unresponsive)
- **Necessary:** ⚠️ **OPTIONAL** - Only useful for debugging slow device response

#### 6. **Result Backlog** (commandMetrics.result_backlog)
- **What:** Number of command results waiting to be processed
- **Purpose:** Detect if processing is lagging behind
- **Normal:** 0-1
- **Warning:** >5 (system might be overloaded)
- **Necessary:** ⚠️ **OPTIONAL** - Debugging only

#### 7. **Inflight Commands** (commandMetrics.inflight)
- **What:** Commands sent to device but no response yet
- **Purpose:** Detect hung commands
- **Normal:** 0-3
- **Warning:** >5 (device not responding)
- **Necessary:** ⚠️ **OPTIONAL** - Debugging only

#### 8. **Scheduled Commands** (commandMetrics.scheduled)
- **What:** List of recurring commands (like periodic measurements)
- **Shows:** Command name, interval, last run, next run
- **Necessary:** ⚠️ **OPTIONAL** - Interesting but not critical

---

### Watchdog History

#### 9. **Watchdog Events** (data.watchdog_history)
- **What:** History of service hangs/recoveries
- **Events:**
  - `timeout` - Service stopped responding
  - `recovery` - Service recovered
- **Necessary:** ⚠️ **OPTIONAL** - Only matters if there ARE events

---

### Log Rotation

#### 10. **Log Rotation Task** (data.log_rotation)
- **What:** Automatic cleanup of old log files
- **Current Status:** **DISABLED**
- **Purpose:** Prevent logs from filling up disk
- **Details:**
  - Deletes logs older than X days/size
  - Runs periodically (e.g., daily)
  - Prevents `/captures/*.log` from growing forever

**Is it necessary?**
- ✅ **YES for production** - Logs will grow indefinitely without it
- ⚠️ **OPTIONAL for development** - Can manually delete logs
- 🔧 **SHOULD ENABLE** - Set to run weekly, delete logs >30 days old

**Why it's currently disabled:**
- Might not be implemented yet
- Might be intentionally disabled during testing
- Might require configuration

---

## Recommendations

### Must Fix (Critical):
1. ✅ **Change polling from warning to success**
   - Color: yellow → green
   - Label: "Polling fallback" → "Polling"

### Should Show (Always Visible):
1. ✅ Service State (running/stopped)
2. ✅ Mode (live/archive)
3. ✅ Log Connection (streaming/polling)
4. ✅ Watchdog Alert (if active)

### Optional/Debug (Show in Collapsible Section):
1. ⚠️ Queue Depth
2. ⚠️ Result Backlog
3. ⚠️ Inflight Commands
4. ⚠️ Scheduled Commands
5. ⚠️ Watchdog History (only if events exist)

### Should Enable:
1. ✅ **Log Rotation** - Enable with reasonable defaults:
   - Max log age: 30 days
   - Max log size: 100 MB per file
   - Run frequency: Daily at midnight

---

## Simplified Service Health Display

### Proposed Layout:

```
┌─────────────────────────────────────────┐
│ Service Health                          │
│                                         │
│ Service:  ● Running                     │
│ Mode:     ● Live (Device Connected)     │
│ Logs:     ● Polling                     │
│ Watchdog: ● No Alerts                   │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Recent Log Events (25)             [↻]  │
│                                         │
│ [INFO] 12:34:56 - Measurement received │
│ [INFO] 12:34:55 - Command sent         │
│ ...                                     │
└─────────────────────────────────────────┘

▼ Advanced Diagnostics (collapsed by default)
  
  Command Queue Metrics:
  - Queue Depth: 0
  - Result Backlog: 0
  - Inflight: 1
  
  Scheduled Commands:
  - periodic_measurement (every 1s)
  - status_check (every 5s)
  
  Watchdog History: No events
```

---

## Implementation Plan

### Phase 1: Fix Polling Display (5 minutes)

**File:** `ui/src/pages/ServiceHealthPage.tsx`

**Change 1: Color**
```tsx
// Line 116-130
const connectionStateColor = (state: HealthLogConnectionState) => {
  switch (state) {
    case 'streaming':
    case 'polling':  // Add polling here
      return 'success';  // Both are green!
    case 'error':
      return 'error';
    case 'connecting':
    case 'loading':
      return 'info';
    default:
      return 'default';
  }
};
```

**Change 2: Label**
```tsx
// Line 132-145
const connectionStateLabel = (state: HealthLogConnectionState): string => {
  switch (state) {
    case 'streaming':
      return 'Streaming';
    case 'polling':
      return 'Polling';  // Remove "fallback"
    case 'connecting':
      return 'Connecting';
    case 'loading':
      return 'Loading';
    case 'error':
      return 'Connection error';
    default:
      return 'Idle';
  }
};
```

---

### Phase 2: Simplify Display (30 minutes)

**Group metrics into collapsible sections:**

```tsx
<Accordion>
  <AccordionSummary>
    <Typography>Advanced Diagnostics</Typography>
  </AccordionSummary>
  <AccordionDetails>
    {/* Move command queue, scheduled commands, watchdog history here */}
  </AccordionDetails>
</Accordion>
```

---

### Phase 3: Enable Log Rotation (Backend)

**File:** Backend configuration (likely in `config/` or `cx505_capture_service.py`)

**Add to config:**
```python
LOG_ROTATION_CONFIG = {
    'enabled': True,
    'max_age_days': 30,
    'max_size_mb': 100,
    'run_interval': '1d',  # Daily
    'keep_minimum': 5  # Keep at least 5 most recent
}
```

---

## Summary

### What Each Monitor Means:

| Monitor | Purpose | Necessary? | Current Issue |
|---------|---------|-----------|---------------|
| Service State | Is service running? | ✅ Critical | None |
| Mode | Device connected? | ✅ Critical | None |
| Log Connection | How logs arrive | ✅ Important | Polling shows as warning ❌ |
| Watchdog Alert | Service hung? | ✅ Critical | None |
| Queue Depth | Commands waiting | ⚠️ Debug only | Too prominent |
| Result Backlog | Results waiting | ⚠️ Debug only | Too prominent |
| Inflight Commands | Pending responses | ⚠️ Debug only | Too prominent |
| Scheduled Commands | Recurring tasks | ⚠️ Nice to have | Too prominent |
| Watchdog History | Past issues | ⚠️ When events exist | Too prominent |
| Log Rotation | Disk cleanup | ✅ Production need | **Disabled** ⚠️ |

### Fixes Needed:

1. ✅ **MUST FIX:** Polling shows as warning (should be success/green)
2. ✅ **SHOULD DO:** Hide debug metrics in collapsible section
3. ✅ **SHOULD ENABLE:** Log rotation (prevent disk fill-up)

---

## Questions for You:

1. **Polling fix:** Change to green and remove "fallback" label?
2. **Debug metrics:** Hide in collapsible "Advanced" section?
3. **Log rotation:** Should I help enable it? (Needs backend config)

Ready to implement the polling fix immediately!
