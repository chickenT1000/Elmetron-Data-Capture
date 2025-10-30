# Calibration Marker Feature - Implementation Progress

## Status: IN PROGRESS (50% Complete)

---

## ✅ Completed

### 1. Database Migration
- ✅ Added `event_type` column to audit_events
- ✅ Added `event_timestamp` column to audit_events
- ✅ Added `measurement_id` column to audit_events (optional link)
- ✅ Created index: `idx_audit_events_type_session`
- ✅ Backfilled event_timestamp from created_at for existing records

### 2. Backend API Endpoints
**File:** `data_api_service.py`

✅ **GET `/api/sessions/{id}/markers`**
- Fetches all manual markers for a session
- Returns markers with sequential numbering (1, 2, 3...)
- Sorted by timestamp

✅ **POST `/api/sessions/{id}/markers`**
- Creates new manual marker
- Validates 99 marker limit per session
- Auto-calculates marker_number
- Body: `{ event_timestamp, offset_seconds, note? }`

✅ **DELETE `/api/sessions/{id}/markers/{marker_id}`**
- Deletes specific marker
- Remaining markers auto-renumbered on next GET

### 3. Backend Evaluation Anchor Logic
✅ **Updated `/api/sessions/{id}/evaluation`**
- Supports `anchor='start'` (default - session start)
- Supports `anchor='first_marker'` (first marker or first measurement)
- Supports `anchor='last_marker'` (last marker or last measurement)
- Fallback logic when no markers exist

### 4. Frontend API Functions
**File:** `ui/src/api/sessions.ts`

✅ Added `SessionMarker` interface
✅ Added `fetchSessionMarkers(sessionId)`
✅ Added `addSessionMarker(sessionId, timestamp, offset, note?)`
✅ Added `deleteSessionMarker(sessionId, markerId)`

### 5. Frontend Anchor Options
✅ Updated ANCHOR_OPTIONS dropdown:
- "Align by session start"
- "Align by first marker"
- "Align by last marker"

---

## ⏳ Remaining Work

### 6. Frontend State Management
**File:** `ui/src/pages/SessionEvaluationPage.tsx`

Need to add state variables:
```typescript
// Marker placement mode
const [markerPlacementMode, setMarkerPlacementMode] = useState(false);
const [sessionForMarker, setSessionForMarker] = useState<number | null>(null);

// Marker data
const [sessionMarkers, setSessionMarkers] = useState<Map<number, SessionMarker[]>>(new Map());

// Marker dialog
const [markerDialogOpen, setMarkerDialogOpen] = useState(false);
const [pendingMarker, setPendingMarker] = useState<{ 
  sessionId: number; 
  timestamp: string; 
  offset_seconds: number; 
  offset_minutes: number 
} | null>(null);
const [markerNote, setMarkerNote] = useState('');
```

### 7. Fetch Markers on Session Load
Need to fetch markers when sessions are loaded/selected

### 8. Add "Add Marker" Button
In Selected Sessions card, add button after "Edit Operator":
```typescript
<Tooltip title="Add marker">
  <IconButton 
    size="small" 
    onClick={() => handleStartMarkerPlacement(session.id)}
  >
    <AddLocationIcon fontSize="small" />
  </IconButton>
</Tooltip>
```

### 9. Marker Placement Mode UI
- Show instructions banner when mode active
- Grey out all UI except chart
- Change cursor to crosshair
- Show cancel button
- Grey out other sessions' lines (strokeOpacity=0.2)

### 10. Chart Click Handler
- Intercept click events on ResponsiveContainer
- Extract clicked point coordinates
- Calculate timestamp and offset
- Open marker confirmation dialog

### 11. Marker Confirmation Dialog
- Show calculated time
- Optional note input
- Confirm/Cancel buttons

### 12. Marker Display on Chart
Use scatter points or custom SVG overlay:
```typescript
{sessionMarkers.get(evaluation.session.id)?.map((marker) => (
  <circle
    cx={xScale(marker.offset_minutes)}
    cy={yScale(marker.value)}  
    r={15}
    fill={color}
    stroke="#fff"
    strokeWidth={2}
  />
  <text
    x={xScale(marker.offset_minutes)}
    y={yScale(marker.value)}
    textAnchor="middle"
    dy="0.3em"
    fill="#fff"
    fontSize={12}
    fontWeight="bold"
  >
    {marker.marker_number}
  </text>
))}
```

### 13. Marker Management in Selected Sessions
Show markers below session metadata:
```typescript
{session.markers && session.markers.length > 0 && (
  <Stack direction="row" spacing={0.5} flexWrap="wrap">
    <Typography variant="caption" color="text.secondary">
      Markers:
    </Typography>
    {session.markers.map((m) => (
      <Chip
        key={m.id}
        label={`${m.marker_number}: ${formatMinutes(m.offset_seconds)} min`}
        size="small"
        onDelete={() => handleDeleteMarker(session.id, m.id)}
      />
    ))}
  </Stack>
)}
```

### 14. Handler Functions
Need to implement:
```typescript
handleStartMarkerPlacement(sessionId)
handleCancelMarkerPlacement()
handleChartClick(event)
handleConfirmMarker()
handleDeleteMarker(sessionId, markerId)
```

### 15. Integration with Evaluation Query
Update sessionEvaluationQueryOptions to use new anchor values

---

## Files Modified

### Backend
- ✅ `data_api_service.py` - Added marker endpoints and anchor logic
- ✅ `migrate_add_marker_fields.py` - Database migration script

### Frontend
- ✅ `ui/src/api/sessions.ts` - Added marker API functions
- ⏳ `ui/src/pages/SessionEvaluationPage.tsx` - UI implementation (in progress)

---

## Testing Checklist

Once complete, test:
- [ ] Add marker via chart click
- [ ] Marker appears as numbered bubble
- [ ] Marker shows in session card with delete option
- [ ] Delete marker
- [ ] Add multiple markers (up to 99)
- [ ] Try to add 100th marker (should error)
- [ ] Switch to "Align by first marker"
- [ ] Switch to "Align by last marker"
- [ ] Verify alignment changes offset calculations
- [ ] Test with session that has no markers (falls back to measurements)
- [ ] Grey out UI during marker placement
- [ ] Cancel marker placement
- [ ] Chart click only works during placement mode
- [ ] Other sessions greyed out during placement

---

## Next Immediate Steps

1. Add marker state variables to SessionEvaluationPage
2. Add "Add Marker" button to Selected Sessions card
3. Implement marker placement mode with UI feedback
4. Implement chart click handler
5. Add marker confirmation dialog
6. Display markers on chart as numbered bubbles
7. Show markers in Selected Sessions card
8. Test all functionality

**Estimated Time Remaining:** ~2 hours

---

## Notes

- Using existing audit_events table as requested
- Markers stored with event_type='manual_marker'
- Marker numbering is dynamic (calculated on GET)
- 99 marker limit per session enforced on backend
- Fallback logic ensures alignment works even without markers
- Chart interaction during placement mode only
