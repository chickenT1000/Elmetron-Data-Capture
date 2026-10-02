# Unified Logging System - Implementation Plan

## Problem Statement

### Current Issues:
1. **session_id is mandatory** - Can't log system-wide events (startup, shutdown, device connection)
2. **Logs don't persist** - Service Health shows 0 events in database (stored in memory only)
3. **False crash recovery events** - Every session shows "Recovered session data from buffer file after crash" even when there was no crash
4. **Risk of fragmented logging** - Need single source of truth for launcher AND backend logs

### User Requirements:
- ✅ Single unified logging system for both launcher UI and backend
- ✅ Single export point (Diagnostic Bundle)
- ✅ Session-specific logs stay with sessions
- ✅ System-wide logs persist independently
- ✅ No false "recovery" events during normal operation

---

## Solution Architecture

### Unified Audit Events Table

```sql
CREATE TABLE audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NULL,              -- ✅ Now optional!
    level TEXT NOT NULL,                  -- DEBUG, INFO, WARNING, ERROR, CRITICAL
    category TEXT NOT NULL,               -- system, session, instrument, capture, recovery, etc.
    message TEXT NOT NULL,
    payload_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    source TEXT DEFAULT 'backend',        -- NEW: 'backend', 'launcher', 'api'
    
    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_events_session ON audit_events(session_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_created ON audit_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_level ON audit_events(level);
CREATE INDEX IF NOT EXISTS idx_audit_events_category ON audit_events(category);
```

### Event Categories

#### System Events (session_id = NULL):
- **system**: Service startup, shutdown, configuration changes
- **device**: Device connection/disconnection (before session starts)
- **health**: Watchdog alerts, performance warnings
- **recovery**: ACTUAL crash recovery (only when recovering from unexpected shutdown)
- **retention**: Data cleanup operations

#### Session Events (session_id = <number>):
- **session**: Session started, ended, paused
- **instrument**: Instrument metadata updates
- **capture**: Measurement capture events
- **calibration**: Calibration operations
- **marker**: User markers added

---

## Implementation Plan

### Phase 1: Database Schema Migration (HIGH PRIORITY)

**File:** `migrate_audit_events_nullable_session.py` (new file)

```python
#!/usr/bin/env python3
"""
Migrate audit_events table to support system-wide logs.
Makes session_id nullable and adds source column.
"""

import sqlite3
from pathlib import Path

def migrate():
    db_path = Path(__file__).parent / 'measurements.db'
    conn = sqlite3.connect(str(db_path))
    
    # Check current schema
    cursor = conn.execute("PRAGMA table_info(audit_events)")
    columns = {row[1]: row for row in cursor.fetchall()}
    
    if 'audit_events' not in [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]:
        print("audit_events table doesn't exist - will be created by database.py")
        conn.close()
        return
    
    # SQLite doesn't support ALTER COLUMN, so we need to recreate table
    print("Migrating audit_events table...")
    
    conn.execute("BEGIN TRANSACTION")
    
    try:
        # Create new table with nullable session_id
        conn.execute("""
            CREATE TABLE audit_events_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NULL,
                level TEXT NOT NULL,
                category TEXT NOT NULL,
                message TEXT NOT NULL,
                payload_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                source TEXT DEFAULT 'backend',
                
                FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE SET NULL
            )
        """)
        
        # Copy existing data
        conn.execute("""
            INSERT INTO audit_events_new 
                (id, session_id, level, category, message, payload_json, created_at, source)
            SELECT 
                id, session_id, level, category, message, payload_json, created_at, 'backend'
            FROM audit_events
        """)
        
        # Drop old table and rename
        conn.execute("DROP TABLE audit_events")
        conn.execute("ALTER TABLE audit_events_new RENAME TO audit_events")
        
        # Create indexes
        conn.execute("CREATE INDEX idx_audit_events_session ON audit_events(session_id)")
        conn.execute("CREATE INDEX idx_audit_events_created ON audit_events(created_at DESC)")
        conn.execute("CREATE INDEX idx_audit_events_level ON audit_events(level)")
        conn.execute("CREATE INDEX idx_audit_events_category ON audit_events(category)")
        
        conn.execute("COMMIT")
        print("✓ Migration complete!")
        
    except Exception as e:
        conn.execute("ROLLBACK")
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
```

**Actions:**
1. Create migration script
2. Run migration on existing database
3. Test: Insert event with session_id=NULL
4. Test: Insert event with session_id=<number>

---

### Phase 2: Update Database Module (HIGH PRIORITY)

**File:** `elmetron/storage/database.py`

**Changes:**

1. **Update table creation:**
```python
# Line ~124 in initialise()
CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NULL,  -- Changed from NOT NULL
    level TEXT NOT NULL,
    category TEXT NOT NULL,
    message TEXT NOT NULL,
    payload_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    source TEXT DEFAULT 'backend',
    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE SET NULL
);
```

2. **Add system-level logging method:**
```python
def append_system_audit_event(self, event: AuditEvent, source: str = 'backend') -> None:
    """Log system-wide event (not tied to any session)."""
    conn = self.connect()
    payload_json = None
    if event.payload is not None:
        payload_json = json.dumps(event.payload, ensure_ascii=False)
    with conn:
        conn.execute(
            """
            INSERT INTO audit_events (session_id, level, category, message, payload_json, source)
            VALUES (NULL, ?, ?, ?, ?, ?)
            """,
            (event.level, event.category, event.message, payload_json, source),
        )
```

3. **Update existing append_audit_event:**
```python
def append_audit_event(self, session_id: Optional[int], event: AuditEvent, source: str = 'backend') -> None:
    """Log event (session-specific or system-wide)."""
    conn = self.connect()
    payload_json = None
    if event.payload is not None:
        payload_json = json.dumps(event.payload, ensure_ascii=False)
    with conn:
        conn.execute(
            """
            INSERT INTO audit_events (session_id, level, category, message, payload_json, source)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, event.level, event.category, event.message, payload_json, source),
        )
```

4. **Update recent_audit_events filter:**
```python
def recent_audit_events(
    self,
    *,
    limit: int = 20,
    since_id: Optional[int] = None,
    level: Optional[str] = None,
    session_id: Optional[int] = None,  # NEW: Filter by session
    system_only: bool = False,          # NEW: Only system events
) -> list[Dict[str, Any]]:
    """Return recent audit events.
    
    Args:
        limit: Maximum events to return
        since_id: Only return events with id > since_id
        level: Minimum log level filter (INFO, WARNING, ERROR, CRITICAL)
        session_id: Filter by specific session (None = all)
        system_only: If True, only return system events (session_id IS NULL)
    """
    # ... add WHERE clauses for session_id and system_only
```

---

### Phase 3: Fix False Recovery Events (HIGH PRIORITY)

**Problem:** Buffer recovery runs on EVERY session start, even when there was no crash.

**File:** `elmetron/storage/session_buffer.py`

**Root Cause Analysis:**

```python
# Line ~529 - This runs after EVERY buffer recovery, even normal cleanup
recovery_event = AuditEvent(
    level='info',
    category='recovery',
    message='Recovered session data from buffer file after crash',  # ❌ WRONG!
    payload={...}
)
```

**Fix Strategy:**

1. **Distinguish between crash recovery and normal cleanup:**
```python
@classmethod
def recover_from_buffer(
    cls,
    buffer_path: Path,
    database,
    delete_after_recovery: bool = True,
    was_crash: bool = True,  # NEW parameter
) -> Dict[str, Any]:
    """Recover session from buffer file.
    
    Args:
        was_crash: True if recovering from unexpected crash,
                   False if cleaning up after normal session end
    """
    # ... recovery logic ...
    
    # Only log if it was an actual crash
    if was_crash and session_handle:
        recovery_event = AuditEvent(
            level='warning',  # Changed from 'info'
            category='recovery',
            message='Recovered session data after unexpected shutdown',
            payload={
                'buffer_file': str(buffer_path),
                'measurements_recovered': measurements_recovered,
                'audit_events_recovered': audit_events_recovered,
            }
        )
        session_handle.append_audit_event('warning', 'recovery', 
            'Recovered session data after unexpected shutdown',
            payload={...})
```

2. **Update callers to specify crash vs cleanup:**

**File:** `elmetron/acquisition/service.py` (or wherever recovery is called)

```python
# On service startup - check for orphaned buffers (actual crashes)
orphaned_buffers = SessionBuffer.find_orphaned_buffers(captures_dir)
for buffer_path in orphaned_buffers:
    result = SessionBuffer.recover_from_buffer(
        buffer_path, 
        database, 
        was_crash=True  # ✅ This is a real crash recovery
    )

# On normal session end - cleanup buffer
if session_buffer:
    session_buffer.close(ended_at=datetime.utcnow())
    # Buffer is auto-deleted or recovered with was_crash=False
    # No recovery event logged
```

3. **Add detection logic:**
```python
@classmethod
def is_orphaned(cls, buffer_path: Path) -> bool:
    """Check if buffer is orphaned (session didn't close properly)."""
    try:
        with open(buffer_path, 'r') as f:
            # Read records backwards to find session_closed
            records = [json.loads(line) for line in f if line.strip()]
            if records:
                # Check if last record is session_closed
                last_record = records[-1]
                if last_record.get('type') == 'session_closed':
                    return False  # Clean shutdown
        return True  # No clean shutdown marker = orphaned
    except:
        return True  # Can't read = assume orphaned
```

---

### Phase 4: Add System Event Logging (MEDIUM PRIORITY)

**Files to Update:**

#### 4.1. Service Lifecycle Events

**File:** `elmetron/acquisition/service.py`

```python
def __init__(self, ...):
    # ... existing code ...
    
    # Log service startup
    if self.database:
        self.database.append_system_audit_event(
            AuditEvent(
                level='info',
                category='system',
                message='Capture service initialized',
                payload={'version': self._version if hasattr(self, '_version') else None}
            ),
            source='backend'
        )

def request_stop(self):
    # ... existing code ...
    
    # Log shutdown
    if self.database:
        self.database.append_system_audit_event(
            AuditEvent(
                level='info',
                category='system',
                message='Capture service shutdown requested',
            ),
            source='backend'
        )
```

#### 4.2. Device Connection Events

**File:** `elmetron/hardware/device_manager.py`

```python
def connect_device(self, ...):
    # ... existing code ...
    
    if success and self.database:
        self.database.append_system_audit_event(
            AuditEvent(
                level='info',
                category='device',
                message=f'Device connected: {device_info}',
                payload={'device_type': device_type, 'serial': serial}
            ),
            source='backend'
        )

def disconnect_device(self):
    # ... existing code ...
    
    if self.database:
        self.database.append_system_audit_event(
            AuditEvent(
                level='info',
                category='device',
                message='Device disconnected',
            ),
            source='backend'
        )
```

#### 4.3. Launcher Events

**File:** `launcher.py`

```python
import sqlite3
from elmetron.storage.database import Database, AuditEvent

def log_launcher_event(level: str, category: str, message: str, payload=None):
    """Log launcher events to unified audit system."""
    try:
        from pathlib import Path
        db_path = Path(__file__).parent / 'measurements.db'
        
        # Use Database class for consistency
        from elmetron.config import StorageConfig
        config = StorageConfig(database_path=db_path)
        database = Database(config)
        
        database.append_system_audit_event(
            AuditEvent(level, category, message, payload),
            source='launcher'
        )
    except Exception as e:
        print(f"Warning: Could not log launcher event: {e}")

# Use throughout launcher.py:
log_launcher_event('info', 'system', 'Elmetron launcher started')
log_launcher_event('info', 'system', 'Backend service started', {'port': 8050})
log_launcher_event('info', 'system', 'Frontend dev server started', {'port': 3000})
log_launcher_event('info', 'system', 'Browser opened', {'url': dashboard_url})
log_launcher_event('warning', 'system', 'Backend service crashed', {'exit_code': code})
log_launcher_event('info', 'system', 'Elmetron launcher stopped')
```

---

### Phase 5: Update Diagnostic Bundle Export (LOW PRIORITY)

**File:** `elmetron/api/diagnostics.py`

**Verify it already exports audit_events:**

```python
# Should already be present around line ~143
def build_diagnostic_bundle(monitor: HealthMonitor, ...) -> ...:
    # ...
    
    # Export audit events (already exported, just verify)
    events = database.recent_audit_events(limit=1000)  # Increase limit
    archive.writestr('health/log_events.json', json.dumps(events, indent=2))
```

**Enhancement: Separate system vs session logs in export:**

```python
# Export system logs
system_events = database.recent_audit_events(limit=500, system_only=True)
archive.writestr('health/system_events.json', json.dumps(system_events, indent=2))

# Export recent session logs
session_events = database.recent_audit_events(limit=500, system_only=False)
archive.writestr('health/session_events.json', json.dumps(session_events, indent=2))
```

---

### Phase 6: Add Retention Policy (LOW PRIORITY)

**File:** `elmetron/storage/database.py`

```python
def apply_retention(self, now: datetime) -> None:
    """Apply retention policies - delete old data."""
    # ... existing session cleanup ...
    
    # NEW: Clean up old audit events (keep 30 days)
    if self._retention_days > 0:
        cutoff = now - timedelta(days=self._retention_days)
        cutoff_iso = cutoff.isoformat()
        
        conn = self.connect()
        with conn:
            # Delete old system events (session_id IS NULL)
            cursor = conn.execute(
                """
                DELETE FROM audit_events 
                WHERE session_id IS NULL 
                AND created_at < ?
                """,
                (cutoff_iso,)
            )
            deleted_system = cursor.rowcount
            
            # Session events are kept with their sessions
            # They're deleted when the session is deleted
            
            if deleted_system > 0:
                self.append_system_audit_event(
                    AuditEvent(
                        level='info',
                        category='retention',
                        message=f'Deleted {deleted_system} old system log events',
                        payload={'cutoff_date': cutoff_iso, 'retention_days': self._retention_days}
                    ),
                    source='backend'
                )
```

**Call this during service startup:**

```python
# In elmetron/acquisition/service.py __init__() or start()
from datetime import datetime
database.apply_retention(datetime.utcnow())
```

---

## Testing Checklist

### Phase 1: Database Migration
- [ ] Run migration on test database
- [ ] Verify session_id accepts NULL
- [ ] Verify source column exists with default 'backend'
- [ ] Verify existing data preserved
- [ ] Verify indexes created

### Phase 2: Database Module
- [ ] Test append_system_audit_event() with session_id=NULL
- [ ] Test append_audit_event() with session_id=<number>
- [ ] Test recent_audit_events() filters (system_only, session_id, level)
- [ ] Verify both backend and launcher can write logs

### Phase 3: Fix False Recovery Events
- [ ] Verify orphan detection logic works
- [ ] Start service → No recovery events (clean start)
- [ ] Crash service mid-session → Recovery event appears (actual crash)
- [ ] Normal session end → No recovery event
- [ ] Test with existing buffer files

### Phase 4: System Event Logging
- [ ] Service startup event logged
- [ ] Service shutdown event logged
- [ ] Device connection/disconnection logged
- [ ] Launcher events logged
- [ ] All events show correct source ('backend' or 'launcher')

### Phase 5: Diagnostic Bundle
- [ ] Verify audit_events exported
- [ ] Check system_events.json contains system logs only
- [ ] Check session_events.json contains session logs only
- [ ] Verify export includes source column

### Phase 6: Retention Policy
- [ ] Create old test events (30+ days ago)
- [ ] Run retention → Old system events deleted
- [ ] Session events NOT deleted (kept with sessions)
- [ ] Retention event logged

---

## Implementation Order

### Priority: HIGH (Do First)
1. **Phase 1: Database Migration** (~30 min)
   - Create and run migration script
   - Test nullable session_id

2. **Phase 2: Update Database Module** (~1 hour)
   - Update schema in database.py
   - Add append_system_audit_event()
   - Update filtering methods

3. **Phase 3: Fix False Recovery Events** (~1-2 hours)
   - Add orphan detection
   - Add was_crash parameter
   - Update recovery logging
   - Test crash vs normal scenarios

### Priority: MEDIUM (Do Second)
4. **Phase 4: Add System Event Logging** (~2-3 hours)
   - Service lifecycle events
   - Device connection events
   - Launcher event logging
   - Test unified logging works

### Priority: LOW (Do Last)
5. **Phase 5: Verify Diagnostic Bundle** (~30 min)
   - Check export already works
   - Add separate system/session exports

6. **Phase 6: Add Retention Policy** (~1 hour)
   - Implement retention logic
   - Add to service startup
   - Test old event deletion

---

## Timeline Estimate

- **Phase 1-2:** 1.5 hours (database schema)
- **Phase 3:** 2 hours (fix false recovery events)
- **Phase 4:** 3 hours (system event logging)
- **Phase 5-6:** 1.5 hours (export + retention)
- **Testing:** 2 hours (comprehensive testing)
- **Total:** ~10 hours

---

## Benefits After Implementation

### ✅ Single Source of Truth
- All logs (backend + launcher) in one table
- Single export point (Diagnostic Bundle)
- No fragmented logging systems

### ✅ System-Wide Events
- Service lifecycle tracked
- Device connections logged
- Can debug "what happened before session started?"

### ✅ Better Debugging
- Historical logs persist
- Can review issues from days/weeks ago
- Source tracking (backend vs launcher vs api)

### ✅ Accurate Event Logs
- No false "crash recovery" events
- Only logs actual problems
- Clear distinction between crash and normal operation

### ✅ Data Management
- Retention policy prevents unbounded growth
- System logs auto-cleaned after 30 days
- Session logs tied to session lifecycle

---

## Risk Assessment

### Low Risk:
- Database migration (non-destructive, preserves data)
- Adding system events (new functionality)
- Retention policy (only deletes old logs)

### Medium Risk:
- Changing session_id to nullable (schema change)
- Updating recovery logic (could affect crash recovery)
  - **Mitigation:** Test thoroughly with orphaned buffers

### High Risk:
- None identified

---

## Rollback Plan

If issues arise:

1. **Database:** Keep backup before migration
   ```bash
   copy measurements.db measurements.db.backup
   ```

2. **Code:** Git revert to previous commit
   ```bash
   git revert HEAD
   ```

3. **Migration Failure:** Restore backup
   ```bash
   copy measurements.db.backup measurements.db
   ```

---

## Questions for User

1. **Retention period:** 30 days for system logs OK? Configurable?
2. **Log levels:** Should launcher events be INFO or DEBUG?
3. **Export format:** Separate files (system_events.json + session_events.json) or single file?
4. **Migration timing:** Run now or wait for maintenance window?

---

## Next Steps

**Ready to implement?** 

Choose implementation approach:
- **A)** Implement all phases (10 hours, full solution)
- **B)** Implement high-priority only (3.5 hours, core fixes)
- **C)** Review plan first, adjust based on feedback

Let me know and I'll start!
                
