# Live Dashboard Settings - Integration Plan

## Overview
This document outlines the integration plan for the Live Dashboard Settings panel, which provides real-time control over session management and chart display preferences.

---

## Features Implemented (Mockup)

### 1. **Session Name Editor**
- Text field with current session name (e.g., "Session #68")
- Save button (icon) to persist name changes
- Real-time validation and feedback

### 2. **New Session Button**
- Large, prominent button to start new capture session
- Creates new session in database
- Automatically switches to the new session

### 3. **Chart Time Range Slider**
- Range: 1-60 minutes
- Labeled markers at: 1, 10, 30, 60 min
- Real-time preview with tooltip
- Current value display below slider

---

## Backend Integration Requirements

### API Endpoints Needed

#### 1. Update Session Name
```http
PATCH /api/sessions/{session_id}
Content-Type: application/json

{
  "name": "Custom Session Name"
}

Response 200:
{
  "id": 68,
  "name": "Custom Session Name",
  "started_at": "2025-10-04T18:42:18Z",
  "updated_at": "2025-10-04T19:15:22Z"
}

Response 404:
{
  "detail": "Session not found"
}

Response 400:
{
  "detail": "Invalid session name"
}
```

**Validation Rules:**
- Max length: 100 characters
- Trim whitespace
- No special characters that could break file systems: `< > : " / \ | ? *`
- Must not be empty after trimming

---

#### 2. Create New Session
```http
POST /api/sessions
Content-Type: application/json

{
  "name": "Session #69",  // Optional, auto-generate if not provided
  "operator": "Jan Kowalski"  // From settings context
}

Response 201:
{
  "id": 69,
  "name": "Session #69",
  "operator": "Jan Kowalski",
  "started_at": "2025-10-04T19:20:00Z",
  "measurement_count": 0,
  "is_active": true
}

Response 400:
{
  "detail": "Cannot create session in Archive mode"
}
```

**Business Logic:**
- Can only create sessions in Live Mode
- Automatically mark previous session as inactive
- Generate sequential name if not provided: "Session #{next_id}"
- Associate with current operator from settings
- Initialize empty measurement log

---

#### 3. Get Current Session Info
```http
GET /api/sessions/current

Response 200:
{
  "id": 68,
  "name": "Session #68",
  "operator": "Jan Kowalski",
  "started_at": "2025-10-04T18:42:18Z",
  "measurement_count": 1247,
  "is_active": true,
  "last_measurement_at": "2025-10-04T19:15:22Z"
}

Response 404:
{
  "detail": "No active session"
}
```

---

### Chart Time Range Integration

The time range slider affects the `RollingChartsPanel` component. Two integration approaches:

#### **Option A: Context-Based (Recommended)**
Create a `DashboardContext` to share settings between components:

```typescript
// ui/src/contexts/DashboardContext.tsx
interface DashboardContextValue {
  chartTimeRange: number;
  setChartTimeRange: (minutes: number) => void;
  currentSessionId: number | null;
  currentSessionName: string;
  updateSessionName: (name: string) => Promise<void>;
  createNewSession: () => Promise<void>;
}

// Usage in RollingChartsPanel.tsx
const { chartTimeRange } = useDashboard();
<RollingChartsPanel windowMinutes={chartTimeRange} />
```

#### **Option B: Props Drilling**
Pass chartTimeRange as prop from DashboardPage:

```typescript
// DashboardPage.tsx
const [chartTimeRange, setChartTimeRange] = useState(10);

<MeasurementPanel 
  state={measurementState} 
  chartTimeRange={chartTimeRange}
  onChartTimeRangeChange={setChartTimeRange}
/>
<RollingChartsPanel windowMinutes={chartTimeRange} />
```

**Recommendation**: Use Option A (Context) for cleaner architecture and future extensibility.

---

## Frontend Implementation Steps

### Phase 1: Context Setup
1. Create `DashboardContext.tsx`
   - Manage chartTimeRange state
   - Manage current session info
   - API call wrappers for session operations

2. Wrap DashboardPage with provider:
   ```tsx
   <DashboardProvider>
     <DashboardPage />
   </DashboardProvider>
   ```

### Phase 2: Session Management
1. **Fetch current session on mount:**
   ```typescript
   useEffect(() => {
     fetchCurrentSession();
   }, []);
   ```

2. **Save Session Name:**
   ```typescript
   const updateSessionName = async (name: string) => {
     setLoading(true);
     try {
       await api.patch(`/sessions/${currentSessionId}`, { name });
       setCurrentSessionName(name);
       showSuccessToast('Session name updated');
     } catch (error) {
       showErrorToast('Failed to update session name');
     } finally {
       setLoading(false);
     }
   };
   ```

3. **Create New Session:**
   ```typescript
   const createNewSession = async () => {
     if (mode !== 'live') {
       showErrorToast('Can only create sessions in Live Mode');
       return;
     }
     
     try {
       const newSession = await api.post('/sessions', {
         operator: settings.operatorName
       });
       setCurrentSessionId(newSession.id);
       setCurrentSessionName(newSession.name);
       showSuccessToast(`Started ${newSession.name}`);
     } catch (error) {
       showErrorToast('Failed to create session');
     }
   };
   ```

### Phase 3: Chart Time Range
1. **Update RollingChartsPanel:**
   - Remove hardcoded `windowMinutes={10}`
   - Read from context: `const { chartTimeRange } = useDashboard();`
   - Re-fetch chart data when range changes

2. **Debounce slider changes:**
   ```typescript
   const debouncedTimeRangeChange = useMemo(
     () => debounce((value: number) => {
       setChartTimeRange(value);
     }, 300),
     []
   );
   ```

### Phase 4: Persistence
**Optional**: Store chartTimeRange in localStorage:
```typescript
useEffect(() => {
  const saved = localStorage.getItem('chartTimeRange');
  if (saved) setChartTimeRange(parseInt(saved));
}, []);

useEffect(() => {
  localStorage.setItem('chartTimeRange', chartTimeRange.toString());
}, [chartTimeRange]);
```

---

## UI/UX Enhancements

### Loading States
- Show spinner on save button while updating session name
- Disable "Start New Session" button while creating
- Show loading indicator while charts re-fetch data

### Error Handling
- Display toast notifications for success/failure
- Show validation errors inline (e.g., "Name too long")
- Disable controls in Archive Mode with tooltip explanation

### Confirmations
**New Session Button** should show confirmation dialog:
```
⚠️ Start New Session?

This will close the current session "Session #68" 
and start a new capture session.

Previous data will be preserved and can be viewed 
in the Sessions tab.

[Cancel]  [Start New Session]
```

### Visual Feedback
- Session name save: Show checkmark icon briefly after save
- Chart updates: Brief loading overlay on chart panel
- New session: Smooth transition with success message

---

## Testing Checklist

### Unit Tests
- [ ] Session name validation (length, special chars)
- [ ] Chart time range bounds (1-60)
- [ ] API error handling

### Integration Tests
- [ ] Create session → name appears in UI
- [ ] Rename session → persists across refresh
- [ ] Time range change → charts update correctly
- [ ] New session → measurements start logging to new session

### E2E Tests
- [ ] Complete workflow: Rename → New Session → Adjust time range
- [ ] Archive mode: All controls properly disabled
- [ ] Error scenarios: Network failure, invalid input
- [ ] Session continuity: Measurements associated with correct session

---

## Security Considerations

### Session Name Sanitization
```typescript
const sanitizeSessionName = (name: string): string => {
  return name
    .trim()
    .replace(/[<>:"/\\|?*]/g, '') // Remove filesystem-unsafe chars
    .substring(0, 100); // Enforce max length
};
```

### Authorization
- Verify user can modify session (not just any session ID)
- Check if device is in Live Mode before allowing new sessions
- Rate limit session creation (prevent spam)

---

## Performance Considerations

### Chart Re-fetching
When time range changes:
1. Cancel any pending chart data requests
2. Show loading state
3. Fetch new data range
4. Update charts with new data

Use **React Query** or similar for:
- Automatic request cancellation
- Caching
- Background refetch

### Debouncing
- Slider changes: 300ms debounce
- Session name input: 500ms debounce (before showing validation)

---

## Migration Strategy

### Phase 1: Mockup (✅ Complete)
- UI components functional with local state
- Console logging for actions

### Phase 2: Backend API
- Implement session management endpoints
- Add validation and error handling
- Test with Postman/curl

### Phase 3: Frontend Integration
- Replace mockup with real API calls
- Add loading states and error handling
- Connect time range to charts

### Phase 4: Polish
- Add confirmations and toasts
- Improve error messages
- Performance optimization
- User testing and feedback

---

## Future Enhancements

### Session Features
- Session tags/categories
- Session notes/comments
- Session export (PDF report)
- Session archival

### Chart Features
- Multiple time range presets (15s, 30s, 1m, 5m, 10m, 30m, 1h)
- Auto-scroll toggle (keep latest data in view)
- Chart zoom/pan controls
- Export chart as image

### Advanced Controls
- Auto-save interval configuration
- Measurement rate limiting
- Alert thresholds
- Data export formats

---

## Questions for Backend Team

1. **Session Lifecycle**: Should we auto-close sessions after inactivity? What's the timeout?
2. **Concurrent Sessions**: Can multiple users have active sessions simultaneously?
3. **Session Limits**: Any limits on number of sessions or measurements per session?
4. **Name Uniqueness**: Should session names be unique? Or allow duplicates?
5. **Historical Data**: How long do we retain session data? Any archival/cleanup policy?

---

## Summary

**Current Status**: ✅ Mockup complete with all UI components functional

**Next Steps**:
1. Backend: Implement session management API endpoints
2. Frontend: Create DashboardContext for state management
3. Integration: Connect UI to real APIs
4. Testing: Full E2E testing of session workflow
5. Polish: Loading states, error handling, confirmations

**Estimated Effort**:
- Backend API: 4-6 hours
- Frontend Integration: 3-4 hours
- Testing & Polish: 2-3 hours
- **Total**: ~10-13 hours

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-04  
**Author**: Droid (Factory AI)
