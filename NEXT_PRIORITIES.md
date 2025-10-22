# Next Priority Tasks - 2025-10-02

**Status:** Crash-resistant buffering ✅ COMPLETED  
**Next Focus:** UI/UX and Real-time Features

---

## 🔥 HIGH PRIORITY - Ready to Start

### 1. **Surface Live Measurements on Landing View** 🎯 **RECOMMENDED NEXT**

**Priority:** High  
**Category:** User Interface  
**Effort:** 2-3 days  
**Impact:** Major UX improvement

**Description:**
Replace the current connectivity-first layout with primary readouts for pH, Redox, Conductivity, and Solution Temperature, updating in real-time from the active session.

**Why This Task:**
- Most impactful user-facing feature
- Transforms dashboard from admin tool to measurement display
- Foundation for subsequent chart/export features
- Users immediately see live readings

**Technical Requirements:**
- Update DashboardPage.tsx to prioritize measurement display
- Create large, readable measurement cards
- Real-time WebSocket or polling updates
- Handle "no data" states gracefully
- Show units and sensor status

**Acceptance Criteria:**
- [ ] Dashboard shows 4 primary measurements prominently
- [ ] Values update in real-time (<1 second latency)
- [ ] Clear "No Device" state when CX505 offline
- [ ] Responsive layout for different screen sizes
- [ ] Accessible (screen reader friendly)

**Dependencies:**
- ✅ Archive mode handling (completed)
- ✅ Live status endpoint (completed)
- Needs: Live measurement streaming or efficient polling

---

### 2. **Add 10-Minute Rolling Charts Beneath Live Readouts**

**Priority:** High  
**Category:** User Interface  
**Effort:** 2-3 days  
**Impact:** High - enables trend visualization

**Description:**
Auto-refresh plots for each measured channel; continue plotting even when a channel has no frames (gap visualization).

**Why This Task:**
- Natural extension of live measurements
- Critical for monitoring trends
- Users expect graphical view of data
- Completes the "live dashboard" experience

**Technical Requirements:**
- Use charting library (Recharts, Chart.js, or D3)
- 10-minute sliding window
- Auto-scroll as new data arrives
- Handle data gaps gracefully
- 4 synchronized charts (one per measurement)

**Acceptance Criteria:**
- [ ] Charts display last 10 minutes of data
- [ ] Auto-update as measurements arrive
- [ ] Time axis synchronized across charts
- [ ] Gaps visible when no data available
- [ ] Performant (60fps with 600 data points)

**Dependencies:**
- ✅ Live measurement data feed
- Needs: Task #1 (live measurements) completed

---

### 3. **Auto-Start Continuous Session Recording on Launch**

**Priority:** High  
**Category:** Capture Service  
**Effort:** 1 day  
**Impact:** High - removes manual step

**Description:**
Ensure measurement logging begins immediately; provide context so users know recording is live without manual action.

**Why This Task:**
- Eliminates user confusion about capture state
- Prevents data loss from "forgot to start"
- Professional continuous monitoring behavior
- Builds on crash-resistant buffering system

**Technical Requirements:**
- Modify launcher.py to start capture immediately
- Add visual "Recording" indicator to UI
- Create new session automatically on startup
- Close session cleanly on shutdown
- Handle device reconnection gracefully

**Acceptance Criteria:**
- [ ] Session starts automatically when device detected
- [ ] UI shows "Recording Active" indicator
- [ ] Session ID displayed in UI
- [ ] Clean session close on shutdown
- [ ] Auto-resume if device reconnects

**Dependencies:**
- ✅ Crash-resistant buffering (completed)
- ✅ Archive mode handling (completed)

---

### 4. **Add Session Timeline Notes with Chart Annotations**

**Priority:** High  
**Category:** User Interface + Data Persistence  
**Effort:** 3-4 days  
**Impact:** High - critical for lab workflows

**Description:**
Allow users to drop timestamped notes (up to 400 chars) that render as numbered pointers beneath the time axis. Notes can be scheduled in the future and are stored with the session.

**Why This Task:**
- Essential for documenting calibrations, observations
- Enables experiment annotation
- Professional lab software feature
- Differentiates from basic loggers

**Technical Requirements:**
- UI component for adding notes
- Database schema for note storage
- Chart annotation rendering
- Export notes with session data
- Search/filter notes

**Acceptance Criteria:**
- [ ] Add note button on dashboard
- [ ] Notes appear on chart timeline
- [ ] Notes stored in database
- [ ] Notes included in exports
- [ ] Future-scheduled notes supported

**Dependencies:**
- Recommended: Task #2 (charts) completed first
- Database schema update needed

---

## 🟡 MEDIUM PRIORITY - Important but Can Wait

### 5. **Add FTDI Device Open Retry/Back-off Logic**

**Priority:** Medium  
**Category:** Hardware Connection  
**Effort:** 1-2 days  
**Impact:** Medium - improves reliability

**Description:**
Recover from stale FTDI handles by retrying with exponential back-off.

**Technical Needs:**
- Add retry logic to device opening
- Exponential back-off (1s, 2s, 4s, 8s)
- Handle "device in use" errors
- Log retry attempts

---

### 6. **Implement Delta-Based Measurement Storage**

**Priority:** Medium  
**Category:** Data Persistence  
**Effort:** 2-3 days  
**Impact:** Medium - storage optimization

**Description:**
Only store measurements when value changes by >threshold (e.g., pH ±0.01); reduces storage by 50-80% for stable readings.

**Why Wait:**
- Not blocking any features
- Optimization, not core functionality
- Need to understand data patterns first

---

### 7. **Optimize payload_json Field**

**Priority:** Medium  
**Category:** Data Persistence  
**Effort:** 1-2 days  
**Impact:** Medium - ~80% storage reduction

**Description:**
Current: ~1,457 bytes/measurement; Optimized: ~200-300 bytes by removing redundant fields.

---

### 8. **Enable Adjustable Chart Scales and Time Axes**

**Priority:** Medium  
**Category:** User Interface  
**Effort:** 1-2 days  
**Impact:** Medium - improves data analysis

**Description:**
Allow users to tune vertical ranges per channel and switch between absolute timestamps and local clock labels.

**Dependencies:**
- Requires: Task #2 (charts) completed

---

## 📊 Analysis of Next Task

### ✅ RECOMMENDED: Task #1 - Surface Live Measurements

**Reasons to prioritize:**
1. **Immediate User Value** - Transforms app from admin tool to measurement display
2. **Foundation Feature** - Required for subsequent tasks (charts, exports)
3. **Quick Win** - Can be completed in 2-3 days
4. **High Visibility** - Users will immediately notice and appreciate
5. **Low Risk** - Builds on existing archive mode work
6. **Natural Progression** - Completes the "robust UI" storyline

**Implementation Approach:**
```typescript
// 1. Create MeasurementCard component
<MeasurementCard
  label="pH"
  value={7.12}
  unit=""
  status="good"
  lastUpdated={timestamp}
/>

// 2. Update DashboardPage layout
<Grid container spacing={3}>
  <Grid item xs={12} md={6}>
    <MeasurementCard label="pH" {...data.ph} />
  </Grid>
  <Grid item xs={12} md={6}>
    <MeasurementCard label="Redox" {...data.redox} />
  </Grid>
  <Grid item xs={12} md={6}>
    <MeasurementCard label="Conductivity" {...data.conductivity} />
  </Grid>
  <Grid item xs={12} md={6}>
    <MeasurementCard label="Temperature" {...data.temperature} />
  </Grid>
</Grid>

// 3. Add real-time data fetching
useEffect(() => {
  const interval = setInterval(async () => {
    if (!isArchiveMode) {
      const latest = await fetchLatestMeasurements();
      setMeasurements(latest);
    }
  }, 1000);
  return () => clearInterval(interval);
}, [isArchiveMode]);
```

**Success Metrics:**
- Users can see live measurements immediately
- Update latency <1 second
- Clean "Archive Mode" fallback
- Zero JavaScript errors
- Passes accessibility audit

---

## 🎯 Suggested Work Order

1. **Task #1: Surface Live Measurements** (2-3 days) → **START HERE** ⭐
2. **Task #3: Auto-Start Recording** (1 day) → Quick win, completes capture workflow
3. **Task #2: Add 10-Minute Charts** (2-3 days) → Natural extension of #1
4. **Task #4: Session Notes** (3-4 days) → Completes lab workflow
5. **Task #8: Adjustable Chart Scales** (1-2 days) → Polish for charts
6. **Task #5: FTDI Retry Logic** (1-2 days) → Reliability improvement
7. **Task #6: Delta Storage** (2-3 days) → Optimization
8. **Task #7: Optimize payload_json** (1-2 days) → Further optimization

**Total Estimated Time:** ~3 weeks for top 5 priorities

---

## 📈 Progress Tracking

**Completed (Last Session):**
- ✅ Crash-resistant session buffering
- ✅ Archive mode handling
- ✅ UI robustness improvements
- ✅ Database cleanup
- ✅ Documentation reorganization

**Next Milestone:** **Live Measurement Dashboard** (Tasks #1-3)

**After That:** **Session Annotation & Export** (Task #4)

---

## 🚀 Ready to Start?

**Recommended next command:**
```
Implement live measurement display on dashboard (Task #1)
```

This will:
- Create compelling user-facing feature
- Build on recently completed work
- Set foundation for charting/export
- Provide immediate value to users

**Questions before starting:**
1. Design preference for measurement cards? (Material-UI default, custom styling, or shadcn/ui?)
2. Polling interval? (Current: 5 seconds, Recommended: 1 second for live feel)
3. Should we show historical trend sparklines in the cards?

---

**Updated:** 2025-10-02  
**Status:** Ready for Task #1 Implementation
