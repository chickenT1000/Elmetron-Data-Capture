# Session Evaluation UI Improvements - Implementation Plan

## User Requirements

1. **Change session catalog from list to dropdown menu**
2. **Add filtering by:**
   - Operator name
   - Date range (start date to end date)
   - Chart type (pH, Redox, Conductivity - NOT temperature)
   - "Most data points" option
3. **Add session rename functionality** (already exists in backend)
4. **Add operator name editing for sessions**

## Current State Analysis

### Database Schema (sessions table):
- `id` - INTEGER PRIMARY KEY
- `instrument_id` - INTEGER NOT NULL  
- `started_at` - TEXT NOT NULL
- `ended_at` - TEXT NULL
- `note` - TEXT NULL (used for session name)
- `created_at` - TEXT NULL

**Issue:** NO operator field exists in the database!

### Current UI (SessionEvaluationPage.tsx):
- Uses `useRecentSessions(10)` hook
- Displays sessions as checkable list items
- Shows session ID, note, timestamps, instrument, measurement counts
- Supports multi-select for overlay comparison

### Existing Backend APIs:
- ✅ GET `/api/sessions?limit=20` - List sessions
- ✅ GET `/api/sessions/<id>` - Get session details
- ✅ PATCH `/api/sessions/<id>/rename` - Rename session (updates note)
- ❌ NO operator field support
- ❌ NO filtering by date range
- ❌ NO filtering by parameter type (pH/redox/conductivity)

## Implementation Strategy

### Phase 1: Backend Enhancements ✅

1. **Add operator field support:**
   - Option A: Add `operator_name` column to sessions table (requires migration)
   - Option B: Store in note field with format "Operator: Name | Session: Note"
   - Option C: Create separate operators table (over-engineering)
   
   **Decision:** Use Option A - add operator_name column (cleanest solution)

2. **Enhance GET /api/sessions endpoint with filters:**
   ```python
   Query params:
   - limit: int (default 20, max 100)
   - operator: string (filter by operator name)
   - start_date: ISO string (filter sessions started after)
   - end_date: ISO string (filter sessions started before)
   - has_ph: boolean (has pH measurements)
   - has_redox: boolean (has Redox measurements)
   - has_conductivity: boolean (has Conductivity measurements)
   - sort_by: string (measurement_count, duration, started_at)
   - order: string (asc, desc)
   ```

3. **Add PATCH /api/sessions/<id>/operator endpoint:**
   ```python
   Request body: {"operator_name": "New Operator"}
   Updates operator_name field
   ```

### Phase 2: Frontend UI Redesign ✅

1. **Replace session list with dropdown + filters:**
   ```tsx
   <Card>
     <CardContent>
       <Typography variant="subtitle1">Session Selection</Typography>
       
       {/* Filter Panel */}
       <Stack spacing={2}>
         <TextField
           label="Operator Name"
           value={operatorFilter}
           onChange={...}
         />
         
         <Stack direction="row" spacing={2}>
           <DatePicker
             label="Start Date"
             value={startDateFilter}
             onChange={...}
           />
           <DatePicker
             label="End Date"
             value={endDateFilter}
             onChange={...}
           />
         </Stack>
         
         <FormControl>
           <InputLabel>Chart Type</InputLabel>
           <Select value={chartTypeFilter} onChange={...}>
             <MenuItem value="all">All Parameters</MenuItem>
             <MenuItem value="ph">pH</MenuItem>
             <MenuItem value="redox">Redox</MenuItem>
             <MenuItem value="conductivity">Conductivity</MenuItem>
             <MenuItem value="most_data">Most Data Points</MenuItem>
           </Select>
         </FormControl>
         
         <FormControl>
           <InputLabel>Sort By</InputLabel>
           <Select value={sortBy} onChange={...}>
             <MenuItem value="started_at">Date (Newest First)</MenuItem>
             <MenuItem value="started_at_asc">Date (Oldest First)</MenuItem>
             <MenuItem value="measurement_count">Most Measurements</MenuItem>
             <MenuItem value="duration">Longest Duration</MenuItem>
           </Select>
         </FormControl>
       </Stack>
       
       {/* Session Dropdown (Multi-Select) */}
       <Autocomplete
         multiple
         options={filteredSessions}
         getOptionLabel={(option) => 
           `Session ${option.id}: ${option.note || 'Unnamed'} (${option.operator_name || 'No Operator'})`
         }
         renderOption={(props, option) => (
           <Box component="li" {...props}>
             <Stack direction="row" spacing={2} alignItems="center" sx={{ width: '100%' }}>
               <Checkbox checked={selectedIds.includes(option.id)} />
               <Stack sx={{ flex: 1 }}>
                 <Typography variant="body2" fontWeight={600}>
                   Session {option.id}: {option.note || 'Unnamed'}
                 </Typography>
                 <Typography variant="caption" color="text.secondary">
                   Operator: {option.operator_name || 'Unknown'} • 
                   Started: {formatDateTime(option.started_at)} • 
                   {option.counts?.measurements} measurements
                 </Typography>
               </Stack>
             </Stack>
           </Box>
         )}
         renderTags={(value, getTagProps) =>
           value.map((option, index) => (
             <Chip
               label={`Session ${option.id}`}
               {...getTagProps({ index })}
               onDelete={() => removeSession(option.id)}
             />
           ))
         }
         value={selectedSessions}
         onChange={(_, newValue) => setSelectedSessions(newValue)}
       />
       
       {/* Session Management Actions */}
       {selectedIds.length === 1 && (
         <Stack direction="row" spacing={1} sx={{ mt: 2 }}>
           <Button
             startIcon={<EditIcon />}
             onClick={() => setRenameDialogOpen(true)}
           >
             Rename Session
           </Button>
           <Button
             startIcon={<PersonIcon />}
             onClick={() => setOperatorDialogOpen(true)}
           >
             Edit Operator
           </Button>
         </Stack>
       )}
     </CardContent>
   </Card>
   ```

2. **Add Rename Dialog:**
   ```tsx
   <Dialog open={renameDialogOpen} onClose={...}>
     <DialogTitle>Rename Session {selectedId}</DialogTitle>
     <DialogContent>
       <TextField
         fullWidth
         label="Session Name"
         value={newName}
         onChange={(e) => setNewName(e.target.value)}
       />
     </DialogContent>
     <DialogActions>
       <Button onClick={...}>Cancel</Button>
       <Button onClick={handleRename} variant="contained">Save</Button>
     </DialogActions>
   </Dialog>
   ```

3. **Add Operator Dialog:**
   ```tsx
   <Dialog open={operatorDialogOpen} onClose={...}>
     <DialogTitle>Edit Operator for Session {selectedId}</DialogTitle>
     <DialogContent>
       <TextField
         fullWidth
         label="Operator Name"
         value={newOperator}
         onChange={(e) => setNewOperator(e.target.value)}
       />
     </DialogContent>
     <DialogActions>
       <Button onClick={...}>Cancel</Button>
       <Button onClick={handleUpdateOperator} variant="contained">Save</Button>
     </DialogActions>
   </Dialog>
   ```

### Phase 3: Smart Filtering Logic ✅

**"Most Data Points" Option:**
- When selected, fetch all sessions
- Determine which parameter (pH/redox/conductivity) has the most measurements per session
- Display only sessions where that parameter is dominant
- Or: Auto-select the chart type with most total measurements across all sessions

**Chart Type Filtering:**
- Backend returns measurement counts per parameter type
- Frontend filters sessions that have measurements for selected type
- Updates available sessions dynamically

## Database Migration Required

```sql
-- Add operator_name column to sessions table
ALTER TABLE sessions ADD COLUMN operator_name TEXT NULL;

-- Add index for faster filtering
CREATE INDEX IF NOT EXISTS idx_sessions_operator ON sessions(operator_name);
CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions(started_at);
```

## API Additions Required

### 1. Enhanced GET /api/sessions
```python
@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    # Add filter parameters
    operator = request.args.get('operator', type=str)
    start_date = request.args.get('start_date', type=str)
    end_date = request.args.get('end_date', type=str)
    has_ph = request.args.get('has_ph', 'false', type=str).lower() == 'true'
    has_redox = request.args.get('has_redox', 'false', type=str).lower() == 'true'
    has_conductivity = request.args.get('has_conductivity', 'false', type=str).lower() == 'true'
    sort_by = request.args.get('sort_by', 'started_at', type=str)
    order = request.args.get('order', 'desc', type=str)
    
    # Build SQL with filters
    # Return sessions with measurement_counts per type
```

### 2. New PATCH /api/sessions/<id>/operator
```python
@app.route('/api/sessions/<int:session_id>/operator', methods=['PATCH'])
def update_session_operator(session_id: int):
    data = request.get_json()
    operator_name = data.get('operator_name')
    
    # Validate and update
    # Return updated session
```

### 3. Enhanced session response
```json
{
  "id": 83,
  "started_at": "2025-10-29T10:05:04",
  "ended_at": "2025-10-29T11:30:00",
  "note": "Test Session",
  "operator_name": "John Doe",
  "instrument": {...},
  "counts": {
    "measurements": 500,
    "ph_measurements": 200,
    "redox_measurements": 150,
    "conductivity_measurements": 150,
    "frames": 500
  },
  "dominant_parameter": "ph"  // Parameter with most measurements
}
```

## Implementation Steps

1. ✅ Database migration (add operator_name column)
2. ✅ Backend API enhancements (filters, operator endpoint)
3. ✅ Frontend API functions (fetch with filters, update operator)
4. ✅ UI redesign (dropdown, filters, dialogs)
5. ✅ Testing (all filters, rename, operator edit)
6. ✅ Documentation

## Benefits

- **Better UX:** Dropdown is cleaner than long scrolling list
- **Powerful filtering:** Find sessions quickly by operator, date, measurement type
- **Data organization:** Operator tracking enables better session management
- **Flexibility:** "Most data points" helps identify high-quality sessions
- **Maintainability:** Clear separation of concerns, reusable components

## Timeline Estimate

- Database migration: 15 min
- Backend API: 1 hour
- Frontend UI: 2 hours
- Testing: 30 min
- **Total: ~4 hours**

## Next Steps

Should I proceed with implementation? I recommend starting with:
1. Database migration (add operator_name column)
2. Backend API enhancements
3. Frontend UI redesign

Let me know if you want me to begin!
