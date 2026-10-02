# Session Management Redesign - Inline Editing

## Overview
This document outlines the implemented session management workflow with inline editing for better UX and cleaner database structure.

## ✅ IMPLEMENTATION STATUS: COMPLETE (Frontend Mockup)

### **Final Specifications (Updated)**
- **Character limit**: 50 characters (enforced)
- **Session closing**: Manual via Recording toggle in header
- **Name uniqueness**: Enforced (backend validation required)
- **Old sessions**: Can only rename current session
- **Deletion**: Archive only (no deletion)
- **Confirmation**: Not required for Start New Session (user inputs name → clicks OK)

---

## Current vs. Proposed UX

### **Current Flow (Dashboard Settings)**
```
┌────────────────────────────────┐
│ Current Session Name           │
│ [Session 69      ] [save]      │
├────────────────────────────────┤
│ [+ Start New Session]          │
└────────────────────────────────┘
```

**Problems:**
- Always shows text field even when not editing
- Confusing: what's the current session vs. what am I typing?
- No clear separation between rename and new session

---

### **Proposed Flow**

#### **State 1: Default (Not Editing)**
```
┌────────────────────────────────┐
│ [Rename Current Session]       │
├────────────────────────────────┤
│ [+ Start New Session]          │
└────────────────────────────────┘
```

#### **State 2a: Renaming (After clicking "Rename")**
```
┌────────────────────────────────┐
│ [Session 69          ] [OK]    │  ← TextField with current name
├────────────────────────────────┤
│ [+ Start New Session]          │  ← Disabled while editing
└────────────────────────────────┘
```

#### **State 2b: New Session (After clicking "Start New")**
```
┌────────────────────────────────┐
│ [Rename Current Session]       │  ← Disabled while creating
├────────────────────────────────┤
│ [Session 70          ] [OK]    │  ← TextField with next number
└────────────────────────────────┘
```

---

## Database Schema Changes

### **Current Schema (Assumed)**
```sql
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    operator TEXT,
    measurement_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    -- ... other fields
);
```

### **Proposed Schema**
```sql
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_number INTEGER UNIQUE NOT NULL,  -- Sequential, never reused
    name TEXT,                                -- User-editable, can be NULL
    started_at TEXT NOT NULL,
    ended_at TEXT,
    operator TEXT,
    measurement_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    -- ... other fields
);

-- Index for fast lookup
CREATE INDEX idx_sessions_number ON sessions(session_number);
CREATE INDEX idx_sessions_active ON sessions(is_active);
```

### **Schema Design Decisions**

#### **1. Separate `session_number` and `name`**
✅ **Recommendation: YES**

**Rationale:**
- `session_number`: Permanent, sequential identifier (1, 2, 3, ...)
- `name`: Optional, user-friendly label ("Calibration Run", "Experiment A")
- Allows renaming without losing identity
- Easy to generate "Session #70" display name

**Display Logic:**
```typescript
const displayName = session.name || `Session ${session.session_number}`;
```

#### **2. UNIQUE constraint on `session_number`**
✅ **Recommendation: YES**

**Rationale:**
- Prevents duplicates
- Ensures consistent numbering
- Better than relying on `id` (which might have gaps from deletions)

#### **3. Auto-incrementing `session_number`**
✅ **Recommendation: Use trigger or application logic**

**Option A: Database Trigger (SQLite)**
```sql
CREATE TRIGGER auto_session_number 
AFTER INSERT ON sessions
WHEN NEW.session_number IS NULL
BEGIN
    UPDATE sessions 
    SET session_number = (SELECT COALESCE(MAX(session_number), 0) + 1 FROM sessions)
    WHERE id = NEW.id;
END;
```

**Option B: Application Logic (Recommended)**
```python
def create_session(db, name=None, operator=None):
    # Get next session number
    result = db.execute("SELECT MAX(session_number) FROM sessions").fetchone()
    next_number = (result[0] or 0) + 1
    
    # Insert new session
    db.execute("""
        INSERT INTO sessions (session_number, name, operator, started_at, is_active)
        VALUES (?, ?, ?, datetime('now'), 1)
    """, (next_number, name, operator))
    
    return next_number
```

**Recommendation: Use application logic** - More explicit, easier to test, better error handling

---

## API Endpoints

### **1. Get Current Session**
```http
GET /api/sessions/current

Response 200:
{
  "id": 123,
  "session_number": 69,
  "name": null,  // or "My Custom Name"
  "display_name": "Session 69",  // Computed: name || "Session {number}"
  "operator": "Jan Kowalski",
  "started_at": "2025-10-04T18:42:18Z",
  "measurement_count": 1247,
  "is_active": true
}

Response 404:
{
  "detail": "No active session"
}
```

### **2. Rename Session**
```http
PATCH /api/sessions/{session_number}/rename
Content-Type: application/json

{
  "name": "Calibration Test"
}

Response 200:
{
  "id": 123,
  "session_number": 69,
  "name": "Calibration Test",
  "display_name": "Calibration Test",
  "updated_at": "2025-10-04T19:15:22Z"
}

Response 404:
{
  "detail": "Session not found"
}

Response 400:
{
  "detail": "Invalid name: must be 1-100 characters"
}
```

**Validation Rules:**
- Can be `null` or empty string (clears name, reverts to "Session {number}")
- If provided: 1-100 characters
- Trim whitespace
- No filesystem-unsafe characters: `< > : " / \ | ? *`

### **3. Create New Session**
```http
POST /api/sessions
Content-Type: application/json

{
  "name": "New Experiment",  // Optional
  "operator": "Jan Kowalski"
}

Response 201:
{
  "id": 124,
  "session_number": 70,
  "name": "New Experiment",
  "display_name": "New Experiment",
  "operator": "Jan Kowalski",
  "started_at": "2025-10-04T19:20:00Z",
  "measurement_count": 0,
  "is_active": true
}

Response 400:
{
  "detail": "Cannot create session in Archive mode"
}

Response 409:
{
  "detail": "A session is already active"
}
```

**Business Logic:**
- Can only create in Live Mode
- Auto-deactivate previous session (`is_active = 0`)
- Generate next `session_number` atomically
- If name not provided: leave as `null` (display will show "Session 70")
- Associate with current operator

### **4. Get Next Session Number (Helper)**
```http
GET /api/sessions/next-number

Response 200:
{
  "next_number": 70
}
```

**Purpose:** 
- Frontend can pre-fill "Session 70" when user clicks "Start New Session"
- No need to wait for creation to know the number

---

## Frontend Implementation

### **Component State**

```typescript
type EditMode = 'none' | 'renaming' | 'creating';

interface SessionEditState {
  mode: EditMode;
  editValue: string;
  loading: boolean;
  error: string | null;
}

const [editState, setEditState] = useState<SessionEditState>({
  mode: 'none',
  editValue: '',
  loading: false,
  error: null,
});
```

### **User Flows**

#### **Flow 1: Rename Current Session**

1. **User clicks "Rename Current Session"**
   ```typescript
   const handleRenameClick = () => {
     setEditState({
       mode: 'renaming',
       editValue: currentSession.name || `Session ${currentSession.session_number}`,
       loading: false,
       error: null,
     });
   };
   ```

2. **User edits text field**
   - Real-time validation
   - Character count (max 100)
   - Show error for invalid characters

3. **User clicks "OK"**
   ```typescript
   const handleRenameConfirm = async () => {
     setEditState(prev => ({ ...prev, loading: true, error: null }));
     
     try {
       const sanitized = sanitizeName(editState.editValue);
       await api.patch(`/sessions/${currentSession.session_number}/rename`, {
         name: sanitized || null  // Empty string → null
       });
       
       // Refresh current session
       await refetchCurrentSession();
       
       setEditState({ mode: 'none', editValue: '', loading: false, error: null });
       showSuccessToast('Session renamed');
     } catch (error) {
       setEditState(prev => ({ 
         ...prev, 
         loading: false, 
         error: error.message 
       }));
     }
   };
   ```

4. **User presses ESC or clicks outside**
   - Cancel editing
   - Revert to button state

#### **Flow 2: Start New Session**

1. **User clicks "Start New Session"**
   ```typescript
   const handleNewSessionClick = async () => {
     // Fetch next session number
     setEditState({ mode: 'creating', editValue: '', loading: true, error: null });
     
     try {
       const { next_number } = await api.get('/sessions/next-number');
       setEditState({
         mode: 'creating',
         editValue: `Session ${next_number}`,
         loading: false,
         error: null,
       });
     } catch (error) {
       showErrorToast('Failed to get next session number');
       setEditState({ mode: 'none', editValue: '', loading: false, error: null });
     }
   };
   ```

2. **User edits text field**
   - Can customize the name before creating
   - e.g., "Session 70" → "Calibration Run"

3. **User clicks "OK"**
   ```typescript
   const handleNewSessionConfirm = async () => {
     setEditState(prev => ({ ...prev, loading: true, error: null }));
     
     try {
       const sanitized = sanitizeName(editState.editValue);
       const newSession = await api.post('/sessions', {
         name: sanitized || null,
         operator: settings.operatorName
       });
       
       // Refresh current session and UI
       await refetchCurrentSession();
       
       setEditState({ mode: 'none', editValue: '', loading: false, error: null });
       showSuccessToast(`Started ${newSession.display_name}`);
     } catch (error) {
       setEditState(prev => ({ 
         ...prev, 
         loading: false, 
         error: error.message 
       }));
     }
   };
   ```

---

## UI Mockup Code

```typescript
<Stack spacing={2}>
  {editState.mode === 'none' ? (
    <>
      {/* Rename Button */}
      <Button
        variant="outlined"
        fullWidth
        onClick={handleRenameClick}
        disabled={!currentSession || mode === 'archive'}
        sx={{ height: '32px', textTransform: 'none' }}
      >
        <Typography variant="caption">
          Rename Current Session
        </Typography>
      </Button>

      {/* Start New Button */}
      <Button
        variant="outlined"
        fullWidth
        startIcon={<AddIcon fontSize="small" />}
        onClick={handleNewSessionClick}
        disabled={mode === 'archive'}
        sx={{ height: '32px', textTransform: 'none' }}
      >
        <Typography variant="caption">
          Start New Session
        </Typography>
      </Button>
    </>
  ) : (
    <>
      {/* Editing State */}
      {editState.mode === 'renaming' && (
        <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'stretch' }}>
          <TextField
            size="small"
            fullWidth
            autoFocus
            value={editState.editValue}
            onChange={(e) => setEditState(prev => ({ 
              ...prev, 
              editValue: e.target.value 
            }))}
            placeholder="Enter session name..."
            disabled={editState.loading}
            error={!!editState.error}
            helperText={editState.error}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleRenameConfirm();
              if (e.key === 'Escape') setEditState({ mode: 'none', ... });
            }}
            sx={{ 
              flex: 1,
              '& .MuiInputBase-root': { height: '32px' }
            }}
          />
          <Button
            variant="outlined"
            onClick={handleRenameConfirm}
            disabled={editState.loading}
            sx={{ minWidth: 'auto', px: 1.5, height: '32px' }}
          >
            {editState.loading ? <CircularProgress size={16} /> : (
              <Typography variant="caption">OK</Typography>
            )}
          </Button>
        </Box>
      )}

      {editState.mode === 'creating' && (
        <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'stretch' }}>
          <TextField
            size="small"
            fullWidth
            autoFocus
            value={editState.editValue}
            onChange={(e) => setEditState(prev => ({ 
              ...prev, 
              editValue: e.target.value 
            }))}
            placeholder="Enter session name..."
            disabled={editState.loading}
            error={!!editState.error}
            helperText={editState.error}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleNewSessionConfirm();
              if (e.key === 'Escape') setEditState({ mode: 'none', ... });
            }}
            sx={{ 
              flex: 1,
              '& .MuiInputBase-root': { height: '32px' }
            }}
          />
          <Button
            variant="outlined"
            onClick={handleNewSessionConfirm}
            disabled={editState.loading}
            sx={{ minWidth: 'auto', px: 1.5, height: '32px' }}
          >
            {editState.loading ? <CircularProgress size={16} /> : (
              <Typography variant="caption">OK</Typography>
            )}
          </Button>
        </Box>
      )}

      {/* Show disabled button for the other action while editing */}
      <Button
        variant="outlined"
        fullWidth
        disabled
        sx={{ height: '32px', textTransform: 'none' }}
      >
        <Typography variant="caption" color="text.disabled">
          {editState.mode === 'renaming' ? 'Start New Session' : 'Rename Current Session'}
        </Typography>
      </Button>
    </>
  )}
</Stack>
```

---

## UX Enhancements

### **1. Keyboard Shortcuts**
- **Enter**: Confirm (same as clicking OK)
- **Escape**: Cancel editing, revert to button state
- **Auto-focus**: Text field gets focus immediately when entering edit mode

### **2. Validation Feedback**
- Real-time character count: "45/100"
- Red border + error text for invalid input
- Disable OK button if invalid

### **3. Loading States**
- Show spinner in OK button while processing
- Disable text field while loading
- Prevent accidental double-submit

### **4. Success Feedback**
- Toast notification: "Session renamed to 'Calibration Test'"
- Toast notification: "Started Session 70"
- Smooth transition back to button state

### **5. Cancel/Revert**
- Clicking outside text field = cancel (optional)
- ESC key = cancel
- Returns to button state without changes

### **6. Error Handling**
- Network error: "Failed to rename session. Try again."
- Validation error: "Name contains invalid characters"
- Conflict error: "A session is already active"
- Keep in edit mode on error (don't lose user's input)

---

## Database Migration

### **Migration Script**
```sql
-- Step 1: Add new columns
ALTER TABLE sessions ADD COLUMN session_number INTEGER;
ALTER TABLE sessions ADD COLUMN name TEXT;

-- Step 2: Populate session_number for existing sessions
-- Use `id` as initial session_number for simplicity
UPDATE sessions SET session_number = id WHERE session_number IS NULL;

-- Step 3: Make session_number NOT NULL (SQLite doesn't support ALTER COLUMN)
-- Create new table with constraints
CREATE TABLE sessions_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_number INTEGER UNIQUE NOT NULL,
    name TEXT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    operator TEXT,
    measurement_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    -- ... copy other columns
);

-- Copy data
INSERT INTO sessions_new SELECT 
    id, session_number, name, started_at, ended_at, operator, 
    measurement_count, is_active, created_at, updated_at
FROM sessions;

-- Replace old table
DROP TABLE sessions;
ALTER TABLE sessions_new RENAME TO sessions;

-- Recreate indexes
CREATE INDEX idx_sessions_number ON sessions(session_number);
CREATE INDEX idx_sessions_active ON sessions(is_active);
```

---

## Recommendations Summary

### **Database**
1. ✅ **Add `session_number` as separate field** - Sequential, immutable identifier
2. ✅ **Add `name` as nullable field** - User-editable label
3. ✅ **Use application logic for numbering** - More control than triggers
4. ✅ **Display logic: `name || "Session {number}"`** - Fallback to number if no name

### **API**
1. ✅ **Separate rename endpoint** - `PATCH /sessions/{number}/rename`
2. ✅ **Helper endpoint for next number** - `/sessions/next-number`
3. ✅ **Allow null/empty name** - Clears custom name, reverts to number
4. ✅ **Atomic session creation** - Lock during number generation

### **UX**
1. ✅ **Inline editing pattern** - Click button → show input → confirm/cancel
2. ✅ **Pre-fill next session number** - User sees "Session 70" before creating
3. ✅ **Keyboard shortcuts** - Enter to confirm, Escape to cancel
4. ✅ **Auto-focus on edit** - Immediate typing without clicking
5. ✅ **Disable other actions while editing** - Prevent confusion
6. ✅ **Keep error state in edit mode** - Don't lose user input

### **Implementation Order**
1. **Phase 1: Database** - Add columns, migration script, update queries
2. **Phase 2: Backend** - Implement 3 endpoints (current, rename, create)
3. **Phase 3: Frontend** - State management, inline editing UI
4. **Phase 4: Polish** - Validation, keyboard shortcuts, error handling

---

## Alternative Approaches Considered

### **Option A: Modal Dialog for Editing**
❌ **Not recommended**

**Pros:**
- Clear focus on editing
- More space for validation messages

**Cons:**
- Requires extra click to close
- Modal overhead for simple text input
- Breaks flow of dashboard

### **Option B: Always-visible text field**
❌ **Not recommended** (current implementation)

**Pros:**
- No state transition
- Immediate editing

**Cons:**
- Takes up space when not needed
- Confusing what's being edited
- Looks unfinished

### **Option C: Inline editing (RECOMMENDED)**
✅ **Best choice**

**Pros:**
- Clean default state (buttons only)
- Intuitive click-to-edit pattern
- Minimal space usage
- Clear visual feedback
- Fast workflow

**Cons:**
- Slightly more complex state management
- Need to handle cancel/revert

---

## Security Considerations

### **1. Name Sanitization**
```typescript
function sanitizeName(input: string): string {
  return input
    .trim()
    .replace(/[<>:"/\\|?*]/g, '')  // Remove filesystem-unsafe chars
    .substring(0, 100);              // Enforce max length
}
```

### **2. SQL Injection Prevention**
- Use parameterized queries
- Never concatenate user input into SQL

### **3. Race Conditions**
- Use transaction for session number generation:
```python
with db.transaction():
    next_num = get_max_session_number() + 1
    create_session(next_num, name, operator)
```

### **4. Authorization**
- Verify user can modify session
- Check Live Mode before allowing new session
- Rate limit session creation

---

## Testing Checklist

### **Backend**
- [ ] Session number uniqueness constraint enforced
- [ ] Next session number correctly incremented
- [ ] Rename updates `name` and `updated_at`
- [ ] Empty/null name clears custom name
- [ ] New session auto-deactivates previous
- [ ] Cannot create session in Archive mode
- [ ] Character limit enforced (100 chars)
- [ ] Invalid characters rejected

### **Frontend**
- [ ] Click "Rename" shows text field with current name
- [ ] Click "Start New" shows text field with "Session {next}"
- [ ] Enter key confirms edit
- [ ] Escape key cancels edit
- [ ] OK button shows spinner while loading
- [ ] Error message displays without losing input
- [ ] Success toast shows after confirm
- [ ] Other button disabled while editing
- [ ] Text field auto-focused on edit

### **Integration**
- [ ] Renamed session updates immediately in UI
- [ ] New session switches active session
- [ ] Session list reflects changes
- [ ] Charts update with new session data
- [ ] Header shows updated session info

---

## Future Enhancements

### **Session Metadata**
- Session tags/categories
- Session description (longer than name)
- Session duration auto-calculated

### **Session Templates**
- "New session like this one"
- Copy settings from previous session

### **Bulk Operations**
- Rename multiple sessions
- Merge sessions
- Archive old sessions

### **Advanced Naming**
- Auto-increment suffix: "Calibration 1", "Calibration 2"
- Date-based: "Session 2025-10-04"
- Template variables: "{operator} - {date}"

---

## Questions for Team

1. **Session Closing**: Should we auto-close inactive sessions after timeout? Or manual close only?
2. **Session Limits**: Any limit on number of total sessions? Archive policy?
3. **Name Uniqueness**: Should session names be unique? Or allow duplicates?
4. **Bulk Rename**: Do we need ability to rename old sessions, or only current?
5. **Session Deletion**: Can sessions be deleted? Or only archived?
6. **Undo**: Should we support undo for rename? Or just let user rename again?

---

## Estimated Effort

**Backend:**
- Database migration: 2 hours
- API endpoints: 3 hours
- Testing: 2 hours
**Subtotal: 7 hours**

**Frontend:**
- State management: 2 hours
- Inline editing UI: 3 hours
- Validation & error handling: 2 hours
- Keyboard shortcuts: 1 hour
- Testing: 2 hours
**Subtotal: 10 hours**

**Total: ~17 hours** (2 days)

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-04  
**Author**: Droid (Factory AI)
