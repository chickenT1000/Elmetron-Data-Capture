# Session Overlay Management - Redesign Plan

## User Requirements

### 1. Session Selector Behavior Change
**Current:** Dropdown shows selected sessions as chips/tags
**New:** Dropdown shows available sessions to ADD (not already selected ones)
- Dropdown should be single-select or simple list
- When you select a session, it gets added to the overlay list
- Dropdown resets after adding
- Selected sessions appear in the redesigned statistics section

### 2. Statistics Summary → Selected Sessions List
**Rename:** "Statistics summary" → "Selected Sessions"

**Show for each session:**
1. **Session Name** (note field) - **FIRST/PRIMARY**
2. **Session Number** (ID) - secondary
3. **Session Start Date** (formatted)
4. **Session Length** (duration: ended_at - started_at)
5. **Main Parameter** (dominant parameter: pH/Redox/Conductivity - NOT temperature)
6. **Data Points** (measurement count)

**Action Buttons per Session:**
- 🗑️ **Remove from Overlay** - Removes session from comparison (not from database)
- 👁️ **Toggle Visibility** - Show/Hide session in chart (keeps in list but hides from chart)
- ✏️ **Rename Session** - Opens rename dialog
- 👤 **Edit Operator** - Opens operator dialog
- ⚠️ **Delete from Database** - PERMANENTLY deletes session (with confirmation!)

### 3. Layout Structure
```
┌─────────────────────────────────────────────────────────────┐
│ Session Selection & Filters Card (LEFT)                     │
│ - Filters (operator, date, chart type, sort)               │
│ - Dropdown: "Add Session to Overlay" (single select)       │
│   Shows only non-selected sessions                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Chart Card (RIGHT/BOTTOM)                                    │
│ - Alignment selector                                         │
│ - Export buttons                                             │
│ - Chart visualization                                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Selected Sessions Card (BOTTOM - FULL WIDTH)                │
│                                                              │
│ Selected Sessions (3)                                        │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ Session Name: "Calibration Test Alpha"                  │ │
│ │ ID: 86 • Started: Oct 29, 2025 12:25 PM               │ │
│ │ Duration: 2h 35m • Main: Conductivity • Points: 1,632 │ │
│ │                                                          │ │
│ │ [👁️ Visible] [Remove] [Rename] [Edit Operator]        │ │
│ │ [⚠️ Delete from Database]                              │ │
│ └────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ Session Name: "Test Run 5"                             │ │
│ │ ID: 85 • Started: Oct 29, 2025 11:46 AM              │ │
│ │ Duration: 1h 15m • Main: pH • Points: 1,976           │ │
│ │                                                          │ │
│ │ [👁️ Hidden] [Remove] [Rename] [Edit Operator]         │ │
│ │ [⚠️ Delete from Database]                              │ │
│ └────────────────────────────────────────────────────────┘ │
│                                                              │
│ (Statistics section moved below - per session stats)        │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Details

### 1. Session Selector Changes

**Current Autocomplete:**
```tsx
<Autocomplete
  multiple  // REMOVE THIS
  value={sessions.filter(s => selectedIds.includes(s.id))}  // REMOVE THIS
  // Shows selected sessions
/>
```

**New Select Dropdown:**
```tsx
<FormControl fullWidth size="small">
  <InputLabel>Add Session to Overlay</InputLabel>
  <Select
    value=""  // Always empty after selection
    onChange={(e) => {
      const sessionId = e.target.value as number;
      if (!selectedIds.includes(sessionId)) {
        setSelectedIds([...selectedIds, sessionId]);
      }
    }}
  >
    {sessions
      .filter(s => !selectedIds.includes(s.id))  // Show only non-selected
      .map(session => (
        <MenuItem key={session.id} value={session.id}>
          {session.note || `Session ${session.id}`} - {session.operator_name || 'No Operator'}
        </MenuItem>
      ))
    }
  </Select>
</FormControl>

<Typography variant="caption" color="text.secondary">
  {selectedIds.length} session(s) added to overlay
</Typography>
```

### 2. Selected Sessions Card

**New State:**
```tsx
const [hiddenSessions, setHiddenSessions] = useState<Set<number>>(new Set());
const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
const [sessionToDelete, setSessionToDelete] = useState<number | null>(null);
```

**Card Structure:**
```tsx
<Card>
  <CardContent>
    <Typography variant="h6" fontWeight={600} gutterBottom>
      Selected Sessions ({selectedIds.length})
    </Typography>
    
    {selectedIds.length === 0 ? (
      <Typography variant="body2" color="text.secondary">
        No sessions selected. Use the dropdown above to add sessions for overlay comparison.
      </Typography>
    ) : (
      <Stack spacing={2}>
        {selectedIds.map(sessionId => {
          const session = sessions.find(s => s.id === sessionId);
          const evaluation = evaluations.find(e => e.session.id === sessionId);
          const isVisible = !hiddenSessions.has(sessionId);
          const color = colorBySession.get(sessionId);
          
          return (
            <Card key={sessionId} variant="outlined" sx={{ 
              borderLeft: `4px solid ${color}`,
              opacity: isVisible ? 1 : 0.5
            }}>
              <CardContent>
                <Stack spacing={1}>
                  {/* Primary: Session Name */}
                  <Typography variant="h6" fontWeight={600}>
                    {session?.note || 'Unnamed Session'}
                  </Typography>
                  
                  {/* Secondary Info */}
                  <Stack direction="row" spacing={2} flexWrap="wrap">
                    <Chip 
                      size="small" 
                      label={`ID: ${sessionId}`} 
                      variant="outlined"
                    />
                    <Chip 
                      size="small" 
                      label={formatDateTime(session?.started_at)} 
                      icon={<CalendarIcon />}
                    />
                    <Chip 
                      size="small" 
                      label={`Duration: ${formatDuration(evaluation?.duration_seconds)}`}
                      icon={<TimerIcon />}
                    />
                    <Chip 
                      size="small" 
                      label={`Main: ${session?.dominant_parameter || 'Unknown'}`}
                      icon={<TrendingUpIcon />}
                    />
                    <Chip 
                      size="small" 
                      label={`${session?.counts?.measurements || 0} points`}
                      icon={<DataPointIcon />}
                    />
                  </Stack>
                  
                  {/* Operator Info */}
                  {session?.operator_name && (
                    <Typography variant="body2" color="text.secondary">
                      Operator: {session.operator_name}
                    </Typography>
                  )}
                  
                  {/* Action Buttons */}
                  <Stack direction="row" spacing={1} flexWrap="wrap">
                    <Button
                      size="small"
                      variant={isVisible ? "contained" : "outlined"}
                      startIcon={isVisible ? <VisibilityIcon /> : <VisibilityOffIcon />}
                      onClick={() => toggleVisibility(sessionId)}
                    >
                      {isVisible ? 'Visible' : 'Hidden'}
                    </Button>
                    
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={<RemoveIcon />}
                      onClick={() => removeFromOverlay(sessionId)}
                    >
                      Remove
                    </Button>
                    
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={<EditIcon />}
                      onClick={() => openRenameDialog(sessionId)}
                    >
                      Rename
                    </Button>
                    
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={<PersonIcon />}
                      onClick={() => openOperatorDialog(sessionId)}
                    >
                      Edit Operator
                    </Button>
                    
                    <Button
                      size="small"
                      variant="outlined"
                      color="error"
                      startIcon={<DeleteForeverIcon />}
                      onClick={() => openDeleteConfirm(sessionId)}
                    >
                      Delete from Database
                    </Button>
                  </Stack>
                </Stack>
              </CardContent>
            </Card>
          );
        })}
      </Stack>
    )}
  </CardContent>
</Card>
```

### 3. Chart Visibility Logic

**Update Chart Rendering:**
```tsx
// Only render visible sessions
{evaluations
  .filter(evaluation => !hiddenSessions.has(evaluation.session.id))
  .map((evaluation) => {
    // Render line
  })
}
```

**Legend Update:**
```tsx
// Show all sessions in legend, but style hidden ones differently
{evaluations.map((evaluation) => {
  const isVisible = !hiddenSessions.has(evaluation.session.id);
  return (
    <Chip
      label={`Session ${evaluation.session.id}`}
      sx={{ 
        opacity: isVisible ? 1 : 0.4,
        textDecoration: isVisible ? 'none' : 'line-through'
      }}
    />
  );
})}
```

### 4. Delete from Database

**New API Endpoint Needed:**
```python
@app.route('/api/sessions/<int:session_id>', methods=['DELETE'])
def delete_session(session_id: int):
    """
    PERMANENTLY delete a session and all associated data.
    
    Deletes:
    - Session record
    - All measurements
    - All raw frames
    - All audit events
    - Session metadata
    
    Returns:
        204 No Content on success
    """
    # WITH CONFIRMATION AND CASCADE DELETE
```

**Frontend Delete Function:**
```tsx
const handleDeleteFromDatabase = async (sessionId: number) => {
  setDialogLoading(true);
  setDialogError(null);
  try {
    await deleteSession(sessionId);  // New API call
    
    // Remove from selected list
    setSelectedIds(prev => prev.filter(id => id !== sessionId));
    
    // Refresh session list
    await fetchSessions();
    
    setDeleteConfirmOpen(false);
  } catch (error) {
    setDialogError(error instanceof Error ? error.message : 'Failed to delete session');
  } finally {
    setDialogLoading(false);
  }
};
```

**Confirmation Dialog:**
```tsx
<Dialog open={deleteConfirmOpen}>
  <DialogTitle>
    <Stack direction="row" spacing={1} alignItems="center">
      <WarningIcon color="error" />
      <span>Permanently Delete Session?</span>
    </Stack>
  </DialogTitle>
  <DialogContent>
    <Alert severity="error" sx={{ mb: 2 }}>
      <AlertTitle>This action cannot be undone!</AlertTitle>
      This will permanently delete:
      <ul>
        <li>Session {sessionToDelete}</li>
        <li>All measurements ({session?.counts?.measurements} points)</li>
        <li>All raw frames</li>
        <li>All audit events</li>
        <li>All metadata</li>
      </ul>
    </Alert>
    
    <Typography variant="body2">
      Type <strong>DELETE</strong> to confirm:
    </Typography>
    <TextField
      fullWidth
      value={deleteConfirmText}
      onChange={(e) => setDeleteConfirmText(e.target.value)}
      placeholder="Type DELETE"
      sx={{ mt: 1 }}
    />
  </DialogContent>
  <DialogActions>
    <Button onClick={() => setDeleteConfirmOpen(false)}>Cancel</Button>
    <Button 
      color="error" 
      variant="contained"
      disabled={deleteConfirmText !== 'DELETE' || dialogLoading}
      onClick={() => handleDeleteFromDatabase(sessionToDelete!)}
    >
      {dialogLoading ? 'Deleting...' : 'Permanently Delete'}
    </Button>
  </DialogActions>
</Dialog>
```

### 5. Session Length Calculation

**Duration Formatting:**
```tsx
const formatSessionDuration = (session: SessionSummary): string => {
  if (!session.started_at) return 'Unknown';
  
  const start = new Date(session.started_at);
  const end = session.ended_at ? new Date(session.ended_at) : new Date();
  
  const durationMs = end.getTime() - start.getTime();
  const hours = Math.floor(durationMs / (1000 * 60 * 60));
  const minutes = Math.floor((durationMs % (1000 * 60 * 60)) / (1000 * 60));
  
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
};
```

### 6. Main Parameter Display

**Already Available:**
- Backend returns `dominant_parameter` field: 'ph', 'redox', 'conductivity', or 'none'
- Temperature is NOT included in this calculation
- Display formatted: "pH", "Redox", "Conductivity"

```tsx
const formatParameter = (param?: string): string => {
  switch (param) {
    case 'ph': return 'pH';
    case 'redox': return 'Redox';
    case 'conductivity': return 'Conductivity';
    default: return 'None';
  }
};
```

## Implementation Steps

1. ✅ **Backend: Add DELETE /api/sessions/<id> endpoint** (30 min)
   - Cascade delete all related data
   - Add transaction for atomicity
   - Return 204 on success

2. ✅ **Frontend: Update session selector** (15 min)
   - Change from Autocomplete to Select
   - Filter out already-selected sessions
   - Reset after adding

3. ✅ **Frontend: Create Selected Sessions card** (1 hour)
   - Rename statistics section
   - Build session card layout
   - Add all metadata displays
   - Format duration and parameters

4. ✅ **Frontend: Add visibility toggle** (20 min)
   - Add hiddenSessions state
   - Filter chart rendering
   - Update legend styling

5. ✅ **Frontend: Add remove from overlay** (10 min)
   - Simple button to remove from selectedIds
   - No database changes

6. ✅ **Frontend: Move rename/operator buttons** (15 min)
   - Remove from filter panel
   - Add to each session card
   - Update to work with specific session

7. ✅ **Frontend: Add delete confirmation** (30 min)
   - Create confirmation dialog
   - Require typing "DELETE"
   - Show what will be deleted

8. ✅ **Frontend: Add delete API call** (15 min)
   - Add deleteSession function
   - Handle errors
   - Refresh lists after delete

9. ✅ **Testing** (30 min)
   - Test all buttons per session
   - Test visibility toggle
   - Test delete with confirmation
   - Test edge cases

**Total Estimated Time: ~3.5 hours**

## Benefits

1. **Clearer UI**: Selected sessions clearly visible with all metadata
2. **Better Control**: Per-session visibility toggle for comparisons
3. **Easier Management**: All session actions in one place
4. **Data Cleanup**: Ability to permanently delete unwanted sessions
5. **Better Overview**: See session length, operator, parameter type at a glance
6. **Safer Deletion**: Strong confirmation prevents accidental data loss

## Safety Considerations

### Delete from Database
- **Confirmation dialog** with typed "DELETE" requirement
- **Warning message** showing exactly what will be deleted
- **Cascade delete** to maintain database integrity
- **Transaction** to ensure all-or-nothing deletion
- **Audit log** (optional) to track deletions

## Questions for Approval

1. **Delete Confirmation**: Require typing "DELETE" or just a double-confirm?
2. **Statistics Section**: Keep below or move elsewhere?
3. **Default Visibility**: All sessions visible by default?
4. **Color Coding**: Keep color-coded borders per session?
5. **Audit Trail**: Should we log session deletions?

---

## Ready to Proceed?

Please review and let me know:
- ✅ Approve as-is
- 🔄 Suggest changes
- ❓ Questions about specific features
