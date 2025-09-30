# Architecture Redesign: Separation of Concerns

## Problem Statement

**Current Issue:** Users cannot access archived session data when the CX505 device is not connected.

The current monolithic architecture requires:
1. ✅ CX505 device present
2. ✅ Capture service running
3. ✅ Health API available
4. → **THEN** UI can start

**User Story:**
> "I want to review yesterday's measurements, but the device is in another lab. I can't access my data!"

---

## Proposed Architecture: Three-Tier System

### 🎯 Design Goals

1. **Always-On Data Access** - View archived data anytime, anywhere
2. **Graceful Degradation** - UI shows "offline" mode when device unavailable
3. **Independent Services** - Each service can start/stop independently
4. **Clear Separation** - Device capture ≠ Data access

---

## New Service Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                      (React + Vite + MUI)                       │
│                                                                 │
│  • Session browser (archived data)                             │
│  • Live measurements (when device online)                      │
│  • Device status indicator                                     │
│  • Automatic fallback to archive mode                          │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ HTTP API calls
                              │
┌─────────────────────────────┴───────────────────────────────────┐
│                                                                 │
│  ┌──────────────────────┐         ┌────────────────────────┐   │
│  │  DATABASE API SERVER │         │   LIVE CAPTURE SERVICE │   │
│  │   (Always Running)   │         │  (Device-Dependent)    │   │
│  ├──────────────────────┤         ├────────────────────────┤   │
│  │ Port: 8050           │         │ Requires: CX505        │   │
│  │                      │         │                        │   │
│  │ Endpoints:           │         │ Functions:             │   │
│  │ • GET /sessions      │         │ • Device polling       │   │
│  │ • GET /sessions/:id  │         │ • Data acquisition     │   │
│  │ • GET /measurements  │         │ • Frame parsing        │   │
│  │ • GET /statistics    │         │ • DB writes            │   │
│  │ • GET /health        │         │ • Status broadcast     │   │
│  │ • GET /export        │         │                        │   │
│  │                      │         │ Status:                │   │
│  │ Access: SQLite DB    │◄────────┤ • POST /status/live    │   │
│  │ Mode: Read + Query   │  Writes │   (heartbeat)          │   │
│  └──────────────────────┘         └────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ SQLite Database
                              ▼
                    ┌──────────────────────┐
                    │  measurements.db     │
                    ├──────────────────────┤
                    │ • sessions           │
                    │ • measurements       │
                    │ • raw_frames         │
                    │ • device_info        │
                    └──────────────────────┘
```

---

## Service Definitions

### 1️⃣ **Database API Server** (`data_api_service.py`)

**Purpose:** Provide read/query access to archived data

**Startup Requirements:** 
- ✅ SQLite database exists (creates if missing)
- ❌ NO device required

**Endpoints:**
```python
# Session Management
GET  /api/sessions                    # List all sessions
GET  /api/sessions/{id}               # Get session details
GET  /api/sessions/{id}/measurements  # Get measurements for session
GET  /api/sessions/{id}/statistics    # Session statistics
POST /api/sessions/{id}/export        # Export session (CSV/JSON)

# Live Status
GET  /api/live/status                 # Current capture status
GET  /api/live/device                 # Device info (if connected)

# Health
GET  /health                          # API health check

# Future: Historical Analysis
GET  /api/analytics/trends            # Trends across sessions
GET  /api/analytics/compare           # Compare sessions
```

**Database Access:** 
- Read-only for archived data
- Write access for live status updates (in-memory or temporary table)

**Startup Mode:**
- Always succeeds (creates DB if missing)
- Starts on port 8050
- Independent of device presence

---

### 2️⃣ **Live Capture Service** (`cx505_capture_service.py`)

**Purpose:** Communicate with CX505 device and write measurements

**Startup Requirements:**
- ✅ CX505 device detected
- ✅ Database API server running (for status updates)

**Functions:**
- Poll device for measurements
- Parse protocol frames
- Write to database
- Send heartbeat to Database API (`POST /api/live/status`)

**Startup Mode:**
- **Option A (Recommended):** 
  - Start anyway, enter "waiting for device" mode
  - Retry device connection in background
  - Become active when device appears
  
- **Option B (Current):**
  - Fail if device not present
  - Require manual restart when device connected

**Graceful Degradation:**
```python
if device_available:
    status = "capturing"
    # Normal capture loop
else:
    status = "offline"
    # Keep retrying connection
    # UI shows "Device offline - viewing archived data"
```

---

### 3️⃣ **UI Frontend** (`ui/`)

**Purpose:** Display data and control capture

**Startup Requirements:**
- ✅ Database API server running
- ❌ NO device required
- ❌ NO capture service required

**Modes of Operation:**

#### 🟢 **Live Mode** (Device connected)
```
┌──────────────────────────────────┐
│ 🟢 Live Capture Active           │
│ Device: CX505 (S/N: EL680921)    │
│ Session #42: 1,234 measurements  │
│                                  │
│ [Real-time Chart]                │
│ [Stop Capture] [View Archive]   │
└──────────────────────────────────┘
```

#### 🔵 **Archive Mode** (Device offline)
```
┌──────────────────────────────────┐
│ 🔵 Archive Mode                  │
│ Device: Offline                  │
│ Viewing historical data          │
│                                  │
│ [Session List]                   │
│ [Connect Device to Capture]     │
└──────────────────────────────────┘
```

**Feature Detection:**
```typescript
// UI checks live status every 5 seconds
const liveStatus = await fetch('/api/live/status')

if (liveStatus.device_connected) {
  showLiveMode()
} else {
  showArchiveMode()
}
```

---

## Implementation Plan

### Phase 1: Split Services ⚡ **HIGH PRIORITY**

**Tasks:**
1. ✅ Create `data_api_service.py`
   - Extract database query logic from `cx505_capture_service.py`
   - Implement REST API endpoints
   - Add session/measurement query methods
   
2. ✅ Modify `cx505_capture_service.py`
   - Keep device communication only
   - Remove HTTP server (health API moves to data API)
   - Add status reporting to data API
   
3. ✅ Update `launcher.py`
   - Start Database API first (always succeeds)
   - Start Capture Service second (optional, device-dependent)
   - Start UI third (always succeeds if Database API running)

**Success Criteria:**
- ✅ UI loads without device present
- ✅ Can browse archived sessions without device
- ✅ "Device offline" message shows when appropriate
- ✅ Live capture activates automatically when device connected

---

### Phase 2: UI Enhancements 🎨

**Tasks:**
1. ✅ Add mode indicator (Live vs Archive)
2. ✅ Add device status indicator
3. ✅ Auto-detect mode switching
4. ✅ Graceful error messages

**UI Changes:**
```tsx
// New component: DeviceStatusBanner
<DeviceStatusBanner 
  status={liveStatus} 
  onConnect={() => startCaptureService()}
/>

// Modified: Session browser
<SessionList 
  mode={isLive ? 'live' : 'archive'}
  currentSession={liveStatus?.session_id}
/>
```

---

### Phase 3: Advanced Features 🚀 (Future)

1. **Hot-plug Support**
   - Detect device connection/disconnection
   - Auto-start capture when device appears
   - Graceful handling of device removal

2. **Remote Access**
   - Database API accessible over network
   - Multi-user access to archived data
   - Read-only mode for analysts

3. **Background Service Mode**
   - Capture service runs as Windows service
   - Always available for device connection
   - Data API always running

---

## Migration Strategy

### Step 1: Create New Services (No Breaking Changes)

```bash
# New files to create:
data_api_service.py          # Database API server
elmetron/api/data_server.py  # API implementation
```

### Step 2: Update Launcher Logic

```python
# launcher.py changes

def _do_start(self):
    # 1. Start Database API (always succeeds)
    self._start_database_api()
    if not self._wait_for_url(DATABASE_API_URL, 40):
        raise RuntimeError("Database API failed to start")
    
    # 2. Start Capture Service (optional)
    try:
        self._start_capture_service()
        self.capture_mode = "live"
    except DeviceNotFoundError:
        self._log("Device not found - starting in archive mode")
        self.capture_mode = "archive"
    
    # 3. Start UI (always succeeds if DB API running)
    self._start_ui_server()
```

### Step 3: Update UI

```typescript
// ui/src/hooks/useDeviceStatus.ts
export function useDeviceStatus() {
  const [status, setStatus] = useState<'live' | 'archive'>('archive')
  
  useEffect(() => {
    const check = async () => {
      const response = await fetch('/api/live/status')
      setStatus(response.device_connected ? 'live' : 'archive')
    }
    
    check()
    const interval = setInterval(check, 5000)
    return () => clearInterval(interval)
  }, [])
  
  return status
}
```

---

## API Specification

### Database API Endpoints

#### `GET /api/sessions`
List all captured sessions

**Response:**
```json
{
  "sessions": [
    {
      "id": 42,
      "device_type": "CX505",
      "device_serial": "EL680921",
      "started_at": "2025-09-30T16:30:00Z",
      "ended_at": "2025-09-30T17:00:00Z",
      "measurement_count": 1234,
      "duration_seconds": 1800
    }
  ]
}
```

#### `GET /api/sessions/{id}`
Get detailed session information

**Response:**
```json
{
  "id": 42,
  "device_type": "CX505",
  "device_serial": "EL680921",
  "started_at": "2025-09-30T16:30:00Z",
  "ended_at": "2025-09-30T17:00:00Z",
  "measurement_count": 1234,
  "statistics": {
    "ph": {"min": 6.8, "max": 7.4, "avg": 7.1, "std": 0.15},
    "redox": {"min": -150, "max": -80, "avg": -110, "std": 12},
    "conductivity": {...},
    "temperature": {...}
  }
}
```

#### `GET /api/sessions/{id}/measurements`
Get measurements for a session

**Query Parameters:**
- `limit` (default: 1000) - Max measurements to return
- `offset` (default: 0) - Pagination offset
- `fields` - Comma-separated list of fields

**Response:**
```json
{
  "session_id": 42,
  "total": 1234,
  "measurements": [
    {
      "timestamp": "2025-09-30T16:30:00Z",
      "ph": 7.1,
      "redox": -110,
      "conductivity": 1450,
      "temperature": 22.5
    }
  ]
}
```

#### `GET /api/live/status`
Get current live capture status

**Response (Device Connected):**
```json
{
  "status": "capturing",
  "device_connected": true,
  "device": {
    "type": "CX505",
    "serial": "EL680921"
  },
  "current_session": {
    "id": 42,
    "started_at": "2025-09-30T16:30:00Z",
    "measurement_count": 1234
  }
}
```

**Response (Device Offline):**
```json
{
  "status": "offline",
  "device_connected": false,
  "message": "No device detected. Connect CX505 to start live capture."
}
```

---

## Benefits Summary

### ✅ User Benefits
- 📊 **Access Data Anytime** - View historical data without device
- 🔄 **Seamless Experience** - Automatic mode switching
- 💾 **No Data Loss** - Database always accessible
- 🚀 **Faster Startup** - UI loads immediately

### ✅ Developer Benefits
- 🏗️ **Clean Architecture** - Separation of concerns
- 🧪 **Easier Testing** - Independent service testing
- 🐛 **Better Debugging** - Clear service boundaries
- 📈 **Scalability** - Can add features without breaking existing code

### ✅ Operational Benefits
- 🛡️ **Resilience** - Services fail independently
- 🔧 **Maintainability** - Clear responsibilities
- 📡 **Remote Access** - Database API can be networked
- 🏢 **Multi-User** - Multiple users can view data simultaneously

---

## Timeline Estimate

| Phase | Task | Effort | Priority |
|-------|------|--------|----------|
| 1 | Create `data_api_service.py` | 4 hours | 🔴 HIGH |
| 1 | Extract database queries | 2 hours | 🔴 HIGH |
| 1 | Implement REST endpoints | 3 hours | 🔴 HIGH |
| 1 | Update launcher.py | 2 hours | 🔴 HIGH |
| 1 | Testing & debugging | 3 hours | 🔴 HIGH |
| **Phase 1 Total** | | **14 hours** | |
| 2 | UI mode detection | 2 hours | 🟡 MEDIUM |
| 2 | Device status indicator | 2 hours | 🟡 MEDIUM |
| 2 | Archive mode UI | 3 hours | 🟡 MEDIUM |
| **Phase 2 Total** | | **7 hours** | |
| 3 | Hot-plug support | 4 hours | 🟢 LOW |
| 3 | Remote access | 6 hours | 🟢 LOW |
| **Phase 3 Total** | | **10 hours** | |

**Total Estimated Effort: 31 hours (~1 week)**

---

## Decision Required

**Question for User:**

Should we implement this architecture redesign?

**Options:**

1. ✅ **Yes, full redesign** (Recommended)
   - Best long-term solution
   - Clean architecture
   - ~1 week effort

2. ⚡ **Quick fix only**
   - Make capture service optional in launcher
   - Show error message but start UI anyway
   - ~2 hours effort
   - Technical debt remains

3. 🔄 **Hybrid approach**
   - Phase 1 now (split services)
   - Phases 2-3 later
   - ~3 days effort

**What do you prefer?**
