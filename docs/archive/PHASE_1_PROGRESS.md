# Phase 1: Architecture Redesign - Progress Report

## 🎯 Goal
Redesign the Elmetron Data Capture software to separate data access from device dependency, enabling archived session browsing without the CX505 device connected.

---

## ✅ Completed Tasks (Today)

### 1. Created Data API Service (`data_api_service.py`)

**What it does:**
- Standalone Flask REST API server
- Runs on port 8050 (same as current health API)
- **NO device required** - database-only operations
- Always available for UI to access data

**API Endpoints Implemented:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Service health check |
| `/api/live/status` | GET | Check if live capture service is running |
| `/api/sessions` | GET | List recent sessions |
| `/api/sessions/:id` | GET | Get session details |
| `/api/sessions/:id/measurements` | GET | Get measurements for a session |
| `/api/sessions/:id/export` | GET | Export session data (CSV/JSON) |
| `/api/instruments` | GET | List known instruments |
| `/api/stats` | GET | Database statistics |

**Features:**
- ✅ Graceful shutdown (SIGINT/SIGTERM handlers)
- ✅ Comprehensive logging to `captures/data_api_service.log`
- ✅ CORS enabled for browser access
- ✅ Query parameter support (limit, offset, order)
- ✅ CSV and JSON export formats
- ✅ Live/Archive mode detection via status file

**Status File Communication:**
- Uses `.live_capture_status.json` for capture service communication
- Updates every second when capture service is active
- API checks file age (stale if >10 seconds old)
- Enables automatic mode switching in UI

**Testing Results:** ✅ ALL TESTS PASSED
- Service runs without errors on port 8050
- Database connectivity verified (4.02 MB, 1566 measurements)
- All 8 REST endpoints functional
- Archive mode detection working (correctly shows "mode": "archive" when no device)
- No Unicode encoding errors (fixed for Polish Windows console)
- See `DATA_API_SERVICE_SUCCESS.md` for full test report

**Fixes Applied:**
1. ✅ Unicode encoding issues (replaced emojis with text labels for cp1250)
2. ✅ Config path loading (added explicit path to `config/app.toml`)
3. ✅ Flask dependencies installed (`flask`, `flask-cors`)

---

## 📋 Next Steps (Remaining Phase 1 Tasks)

### Task 1.3: Modify Capture Service to Write Status File ⏳

**What needs to be done:**
Modify `cx505_capture_service.py` to write live status information:

```python
# Add to capture service main loop:
import json
from pathlib import Path

STATUS_FILE = Path("captures/.live_capture_status.json")

def update_status_file(active: bool, device_connected: bool, session_id: int = None):
    status = {
        'active': active,
        'device_connected': device_connected,
        'session_id': session_id,
        'last_update': datetime.utcnow().isoformat() + 'Z'
    }
    STATUS_FILE.write_text(json.dumps(status, indent=2))

# Call this every second in main loop
# Call with active=False on shutdown
```

---

### Task 1.4: Update Launcher for Three-Service Architecture ⏳

**Current Architecture:**
```
launcher.py starts:
  1. CX505 Capture Service (port 8050) ← Requires device
  2. UI Server (port 5173)
```

**New Architecture:**
```
launcher.py starts:
  1. Data API Service (port 8050) ← ALWAYS RUNS
  2. CX505 Capture Service (port 8051) ← Optional, device-dependent
  3. UI Server (port 5173) ← ALWAYS RUNS
```

**Changes needed in `launcher.py`:**

1. Start Data API first (always required)
2. Try to start Capture Service (optional - show warning if device missing)
3. Start UI server
4. Update health checks to use Data API `/health` endpoint
5. Add "Archive Mode" indicator when capture service isn't running

---

### Task 1.5: Update UI to Detect Archive/Live Mode ⏳

**Current UI:**
- Polls `/health` endpoint from capture service
- Shows error if service unavailable

**New UI behavior:**
- Poll `/api/live/status` from Data API
- Show "Archive Mode" banner when `live_capture_active: false`
- Show "Live Mode" indicator when `live_capture_active: true`
- Disable live measurement streaming in archive mode
- Enable session browsing in both modes

**UI Changes needed:**
- `ui/src/hooks/useHealthCheck.ts` - change endpoint to `/api/live/status`
- `ui/src/layouts/AppLayout.tsx` - add mode indicator
- `ui/src/components/ModeBanner.tsx` - NEW component showing current mode

---

### Task 1.6: Test Archive Mode ⏳

**Test Scenario:**
1. Stop all services
2. Start only Data API service
3. Start UI server
4. Open browser → should see "Archive Mode"
5. Verify can browse historical sessions
6. Verify cannot start new capture session

---

### Task 1.7: Test Live Mode ⏳

**Test Scenario:**
1. Connect CX505 device
2. Start all services (Data API + Capture + UI)
3. Open browser → should see "Live Mode"
4. Verify can start new capture session
5. Verify measurements appear in real-time
6. Stop capture service → should switch to "Archive Mode" automatically

---

### Task 1.8: Update Documentation ⏳

**Documents to update:**
- `README.md` - new architecture description
- `ARCHITECTURE_REDESIGN.md` - implementation notes
- `TROUBLESHOOTING.md` - new service startup order
- Create `DEPLOYMENT_GUIDE.md` for production setup

---

## 🔧 Installation Instructions

### Install Data API Dependencies

Before running the Data API service, install Flask:

**Option 1: Using existing Python environment**
```bash
# From command prompt or PowerShell
cd C:\Users\EKO\Desktop\GitHub\Elmetron-Data-Capture

# Find your Python executable (same one used by launcher)
# Then install:
[your-python] -m pip install -r requirements_data_api.txt
```

**Option 2: Manual installation**
```bash
[your-python] -m pip install flask>=3.0.0 flask-cors>=4.0.0
```

**What Python to use?**
- Same Python that runs `launcher.py`
- Check `launcher.py` → it uses `sys.executable`
- Or check your IDE's Python interpreter path

---

## 🧪 Testing the Data API (Standalone)

Once Flask is installed, test the API service standalone:

```bash
# Start Data API service
[your-python] data_api_service.py

# Should see:
# ============================================================
# 🚀 Elmetron Data API Service Starting
# ============================================================
#    Root: C:\Users\EKO\Desktop\GitHub\Elmetron-Data-Capture
#    Port: 8050
#    Mode: Always-On (No Device Required)
#
# ✅ Database initialized: ...
# ✅ Data API Service Ready!
```

**Test endpoints:**
```bash
# Health check
http://localhost:8050/health

# List sessions
http://localhost:8050/api/sessions

# Database stats
http://localhost:8050/api/stats

# Live status (should show archive mode)
http://localhost:8050/api/live/status
```

---

## 📊 Current Status

| Task | Status | Priority |
|------|--------|----------|
| Data API Service Created | ✅ Complete | High |
| REST API Endpoints Implemented | ✅ Complete | High |
| Flask Dependencies Listed | ✅ Complete | High |
| Modify Capture Service (status file) | ⏳ Pending | High |
| Update Launcher (3-service arch) | ⏳ Pending | High |
| Update UI (mode detection) | ⏳ Pending | High |
| Test Archive Mode | ⏳ Pending | High |
| Test Live Mode | ⏳ Pending | High |
| Update Documentation | ⏳ Pending | Medium |

**Progress:** 3/9 tasks complete (33%)

---

## 🎯 Expected Outcomes

After Phase 1 completion:

### ✅ Archive Mode (No Device)
- Data API running → UI accessible
- Can browse all historical sessions
- Can view measurements from past sessions
- Can export data to CSV/JSON
- Banner shows "Archive Mode - Device Not Connected"

### ✅ Live Mode (Device Connected)
- All services running
- Can start new capture sessions
- Real-time measurement streaming
- All archive mode features still available
- Banner shows "Live Mode - Device Connected"

### ✅ Graceful Degradation
- If capture service crashes → automatic switch to archive mode
- If device disconnected → capture service stops, but UI stays up
- No more "Can't access data because device isn't connected" problems

---

## 🚀 Next Immediate Action

**Step 1: Install Flask**
```bash
# Find Python executable
where python

# Install dependencies
python -m pip install -r requirements_data_api.txt
```

**Step 2: Test Data API standalone**
```bash
python data_api_service.py
# Open http://localhost:8050/health in browser
```

**Step 3: Once working, proceed to Task 1.3** (modify capture service)

---

## 📁 New Files Created

1. `data_api_service.py` - Standalone REST API server (800+ lines)
2. `requirements_data_api.txt` - Flask dependencies
3. `PHASE_1_PROGRESS.md` - This file
4. `COMMERCIAL_ARCHITECTURE_OPTIONS.md` - Architecture analysis (already created)

---

## 🎉 What We Achieved Today

1. ✅ Decided on commercial architecture (Electron Desktop App)
2. ✅ Started Phase 1 implementation
3. ✅ Created complete Data API service
4. ✅ Implemented 8 REST API endpoints
5. ✅ Designed status file communication protocol
6. ✅ Planned three-service architecture
7. ✅ Created comprehensive roadmap (33 tasks across 5 phases)

**This is HUGE progress!** We've laid the foundation for a professional, commercial-grade architecture.

---

## Questions?

**Q: Can I test the Data API now?**
A: Yes! Install Flask, run `data_api_service.py`, and access http://localhost:8050/health

**Q: Will this break the current launcher?**
A: No. The Data API uses the same port (8050) and supports the existing `/health` endpoint

**Q: What about the capture service?**
A: Next step is to modify it to run on port 8051 and write status updates

**Q: How long until Phase 1 is done?**
A: ~3-5 more days of work (6 remaining tasks)

---

*Last Updated: 2025-09-30*
*Phase: 1 of 5*
*Status: In Progress (33% complete)*
