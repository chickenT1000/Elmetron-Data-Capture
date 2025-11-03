# Session Evaluation State Persistence - Plan

## Problem

When navigating: Session Evaluation → Live Dashboard → Back to Session Evaluation
- All selected sessions are lost
- Filters reset
- Chart settings reset
- Marker placement mode cancelled
- User has to start over

## Current State (What Gets Lost)

### Critical State:
1. **Selected Session IDs** - Which sessions are in the overlay
2. **Session visibility** - Which sessions are hidden/visible
3. **Anchor mode** - 'start' or 'calibration'
4. **Selected parameter** - 'ph', 'redox', or 'conductivity'
5. **Show temperature** - Boolean toggle

### Filter State:
6. **Operator filter** - Text input
7. **Date range filters** - Start/end dates
8. **Chart type filter** - All/pH/Redox/Conductivity/Most Data
9. **Sort settings** - Sort by and order

### Temporary State (OK to lose):
- Marker placement mode (should cancel on navigate)
- Open dialogs (should close)
- Hover states

## Solution Options

### Option 1: URL Query Parameters ⭐ **RECOMMENDED**

Store critical state in URL:
```
/session-evaluation?sessions=86,87,88&anchor=start&param=ph&hidden=87
```

**Pros:**
- Sharable URLs - can bookmark or share exact view
- Browser back/forward works
- No storage needed
- Most professional solution

**Cons:**
- URL can get long with many selections
- Need to parse/serialize data

**Implementation:**
```tsx
import { useSearchParams } from 'react-router-dom';

// Read from URL
const [searchParams, setSearchParams] = useSearchParams();
const sessionIds = searchParams.get('sessions')?.split(',').map(Number) || [];
const anchor = searchParams.get('anchor') || 'start';

// Write to URL
setSearchParams({
  sessions: selectedIds.join(','),
  anchor: anchor,
  param: selectedParameter,
  hidden: Array.from(hiddenSessions).join(',')
});
```

### Option 2: LocalStorage

Store state in browser localStorage:
```typescript
localStorage.setItem('sessionEval_selectedIds', JSON.stringify(selectedIds));
```

**Pros:**
- Persists across browser sessions
- Survives page reload
- Simple to implement

**Cons:**
- Not sharable
- Can get stale
- Need to handle JSON serialization

### Option 3: React Context (Global State)

Create a context to store state across navigation:
```tsx
<SessionEvaluationContext.Provider value={state}>
  {children}
</SessionEvaluationContext.Provider>
```

**Pros:**
- State persists while app is open
- Can be accessed from other components
- Clean React pattern

**Cons:**
- Lost on page reload
- More complex setup
- Overkill for this use case

### Option 4: Zustand/Redux (State Manager)

Use external state management library.

**Pros:**
- Professional solution for large apps
- DevTools support
- Can persist to localStorage

**Cons:**
- Adds dependency
- Overkill for this feature
- Learning curve

## Recommended Solution: Hybrid Approach

**Combine URL params + localStorage for best UX**

### Store in URL (Priority 1):
- Selected session IDs
- Anchor mode
- Selected parameter
- Hidden sessions

### Store in localStorage (Priority 2):
- Filter settings (operator, dates, chart type, sort)
- Show temperature toggle
- Last used settings

### Never persist:
- Marker placement mode
- Open dialogs
- Loading states
- Errors

## Implementation Plan

### Phase 1: URL Query Parameters (Critical State)

**File:** `ui/src/pages/SessionEvaluationPage.tsx`

**1. Add URL param hooks:**
```tsx
import { useSearchParams } from 'react-router-dom';

export default function SessionEvaluationPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  
  // Initialize from URL
  const initialSessionIds = useMemo(() => {
    const ids = searchParams.get('sessions');
    return ids ? ids.split(',').map(Number).filter(Boolean) : [];
  }, []);
  
  const initialAnchor = useMemo(() => {
    const anchor = searchParams.get('anchor');
    return anchor === 'calibration' ? 'calibration' : 'start';
  }, []);
  
  const initialParameter = useMemo(() => {
    const param = searchParams.get('param');
    if (param === 'redox' || param === 'conductivity') return param;
    return 'ph';
  }, []);
  
  // Use initial values
  const [selectedIds, setSelectedIds] = useState<number[]>(initialSessionIds);
  const [anchor, setAnchor] = useState<'start' | 'calibration'>(initialAnchor);
  const [selectedParameter, setSelectedParameter] = useState(initialParameter);
  
  // ... rest of state
}
```

**2. Update URL when state changes:**
```tsx
// Effect to sync state to URL
useEffect(() => {
  const params: Record<string, string> = {};
  
  if (selectedIds.length > 0) {
    params.sessions = selectedIds.join(',');
  }
  
  if (anchor !== 'start') {
    params.anchor = anchor;
  }
  
  if (selectedParameter !== 'ph') {
    params.param = selectedParameter;
  }
  
  if (hiddenSessions.size > 0) {
    params.hidden = Array.from(hiddenSessions).join(',');
  }
  
  setSearchParams(params, { replace: true }); // replace = don't add to history
}, [selectedIds, anchor, selectedParameter, hiddenSessions, setSearchParams]);
```

**3. Read hidden sessions from URL:**
```tsx
const initialHiddenSessions = useMemo(() => {
  const hidden = searchParams.get('hidden');
  return hidden ? new Set(hidden.split(',').map(Number).filter(Boolean)) : new Set<number>();
}, []);

const [hiddenSessions, setHiddenSessions] = useState<Set<number>>(initialHiddenSessions);
```

### Phase 2: LocalStorage (Filter State)

**File:** `ui/src/pages/SessionEvaluationPage.tsx`

**1. Create localStorage key:**
```tsx
const STORAGE_KEY = 'sessionEvaluationFilters';
```

**2. Load filters from storage:**
```tsx
// Load saved filters on mount
useEffect(() => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const filters = JSON.parse(saved);
      setOperatorFilter(filters.operator || '');
      setStartDateFilter(filters.startDate ? new Date(filters.startDate) : null);
      setEndDateFilter(filters.endDate ? new Date(filters.endDate) : null);
      setChartTypeFilter(filters.chartType || 'all');
      setSortBy(filters.sortBy || 'started_at');
      setSortOrder(filters.sortOrder || 'desc');
      setShowTemperature(filters.showTemperature || false);
    }
  } catch (error) {
    console.error('Failed to load saved filters:', error);
  }
}, []);
```

**3. Save filters when they change:**
```tsx
// Save filters when they change (debounced)
useEffect(() => {
  const timer = setTimeout(() => {
    const filters = {
      operator: operatorFilter,
      startDate: startDateFilter?.toISOString(),
      endDate: endDateFilter?.toISOString(),
      chartType: chartTypeFilter,
      sortBy,
      sortOrder,
      showTemperature
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(filters));
  }, 500); // Debounce 500ms
  
  return () => clearTimeout(timer);
}, [operatorFilter, startDateFilter, endDateFilter, chartTypeFilter, sortBy, sortOrder, showTemperature]);
```

### Phase 3: Custom Hook (Optional - Clean Up)

**File:** `ui/src/hooks/useSessionEvaluationState.ts`

```tsx
import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

const STORAGE_KEY = 'sessionEvaluationFilters';

export function useSessionEvaluationState() {
  const [searchParams, setSearchParams] = useSearchParams();
  
  // URL state (critical - shareable)
  const initialSessionIds = useMemo(() => {
    const ids = searchParams.get('sessions');
    return ids ? ids.split(',').map(Number).filter(Boolean) : [];
  }, [searchParams]);
  
  const [selectedIds, setSelectedIds] = useState<number[]>(initialSessionIds);
  const [anchor, setAnchor] = useState<'start' | 'calibration'>(
    searchParams.get('anchor') === 'calibration' ? 'calibration' : 'start'
  );
  
  // Sync to URL
  useEffect(() => {
    const params: Record<string, string> = {};
    if (selectedIds.length > 0) params.sessions = selectedIds.join(',');
    if (anchor !== 'start') params.anchor = anchor;
    setSearchParams(params, { replace: true });
  }, [selectedIds, anchor, setSearchParams]);
  
  // LocalStorage state (filters)
  const [filters, setFilters] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  });
  
  // Save filters
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(filters));
  }, [filters]);
  
  return {
    selectedIds,
    setSelectedIds,
    anchor,
    setAnchor,
    filters,
    setFilters
  };
}
```

## Benefits

### For User:
✅ Work is preserved when switching pages
✅ Can bookmark specific analysis views
✅ Can share URLs with colleagues
✅ Filters persist across sessions
✅ No accidental loss of work

### For Developer:
✅ Clean separation of concerns
✅ URL reflects application state
✅ Easy to debug (check URL)
✅ Testable (can set URL params in tests)
✅ Professional solution

## Example URLs

**Single session, pH view:**
```
/session-evaluation?sessions=86&param=ph&anchor=start
```

**Multiple sessions overlay:**
```
/session-evaluation?sessions=86,87,88&param=conductivity&hidden=87
```

**With calibration anchor:**
```
/session-evaluation?sessions=86,87&anchor=calibration&param=redox
```

## Edge Cases to Handle

1. **Invalid session IDs in URL:**
   - Filter out non-existent sessions
   - Show warning message

2. **Too many sessions in URL:**
   - Limit to reasonable number (e.g., 10)
   - Show warning if exceeded

3. **Corrupted localStorage:**
   - Wrap in try/catch
   - Fall back to defaults

4. **URL too long:**
   - Browser limit ~2000 chars
   - Use shortened format if needed

## Implementation Time

- Phase 1 (URL params): 1 hour
- Phase 2 (localStorage): 30 minutes
- Phase 3 (Custom hook): 30 minutes
- Testing: 30 minutes
- **Total: ~2.5 hours**

## Testing Checklist

- [ ] Navigate away and back - state preserved
- [ ] Refresh page - state preserved
- [ ] Share URL - recipient sees same view
- [ ] Bookmark URL - opens correct view
- [ ] Invalid URL params - graceful fallback
- [ ] No URL params - shows defaults
- [ ] LocalStorage disabled - URL still works
- [ ] Very long URL - handles gracefully

---

## Approval Questions

1. **URL format OK?** `/session-evaluation?sessions=86,87,88&anchor=start&param=ph`
2. **Which state to persist?** Suggested: sessions, anchor, parameter, filters
3. **Clear on navigate?** Should marker placement mode cancel? (Yes, recommended)
4. **Share URL feature?** Add "Copy Share Link" button?

Ready to implement?
