# Open Live Dashboard in New Tab - Implementation Plan

## Problem Solved

**User workflow:**
1. Working in Session Evaluation (comparing sessions, adding markers)
2. Needs to check Live Dashboard
3. Currently: Clicks Dashboard → Navigates away → Loses work ❌
4. New: Opens Dashboard in new tab → Work preserved ✅

## Solution: Simple Navigation Change

### Option 1: Add "Open in New Tab" Icon ⭐ **RECOMMENDED**

Add small icon next to Dashboard link that opens in new tab.

**UI:**
```
┌─────────────────────────┐
│ 📊 Live Dashboard    ⧉  │  ← Icon opens new tab
│ 📈 Session Evaluation   │
│ 🎯 Calibrations        │
└─────────────────────────┘
```

**Implementation:**
```tsx
// In AppLayout.tsx - Add icon button
<ListItemButton
  key={route.path}
  selected={isActive}
  onClick={() => {
    navigate(route.path);
    setMobileOpen(false);
  }}
  sx={{ pr: 1 }} // Make room for icon
>
  <ListItemIcon>
    <route.icon color={isActive ? 'primary' : 'inherit'} />
  </ListItemIcon>
  <ListItemText primary={route.label} />
  
  {/* Show "open in new tab" icon for Dashboard */}
  {route.path === '/' && (
    <Tooltip title="Open in new tab">
      <IconButton
        size="small"
        onClick={(e) => {
          e.stopPropagation(); // Don't trigger main button
          window.open(route.path, '_blank');
        }}
        sx={{ ml: 'auto' }}
      >
        <OpenInNewIcon fontSize="small" />
      </IconButton>
    </Tooltip>
  )}
</ListItemButton>
```

**Pros:**
- ✅ Clear visual indicator
- ✅ Normal click = navigate, icon click = new tab
- ✅ Doesn't break existing behavior
- ✅ Works for keyboard users

**Cons:**
- Takes up space in navigation

---

### Option 2: Ctrl+Click or Middle-Click (Native Browser)

Make the navigation use proper links so browser shortcuts work.

**Implementation:**
```tsx
// Change from onClick to proper Link component
import { Link as RouterLink } from 'react-router-dom';

<ListItemButton
  key={route.path}
  selected={isActive}
  component={RouterLink}
  to={route.path}
  onClick={() => setMobileOpen(false)}
  // Ctrl+Click and middle-click now work automatically!
>
  <ListItemIcon>
    <route.icon color={isActive ? 'primary' : 'inherit'} />
  </ListItemIcon>
  <ListItemText primary={route.label} />
</ListItemButton>
```

**Pros:**
- ✅ Native browser behavior (Ctrl+Click, middle-click)
- ✅ No UI changes needed
- ✅ Clean implementation
- ✅ Right-click → "Open in new tab" works

**Cons:**
- ❌ Not obvious to users
- ❌ Requires knowledge of keyboard shortcuts

---

### Option 3: Add Button in Session Evaluation Page

Add prominent button on Session Evaluation page itself.

**Location:** Top of Session Evaluation page near filters

**UI:**
```tsx
<Card>
  <CardContent>
    <Stack direction="row" justifyContent="space-between" alignItems="center">
      <Typography variant="h5">Session Evaluation</Typography>
      
      <Button
        variant="outlined"
        startIcon={<DashboardIcon />}
        endIcon={<OpenInNewIcon />}
        onClick={() => window.open('/', '_blank')}
      >
        Open Live Dashboard
      </Button>
    </Stack>
  </CardContent>
</Card>
```

**Pros:**
- ✅ Very obvious and discoverable
- ✅ Contextually relevant (on the page where it matters)
- ✅ Clear call-to-action
- ✅ Can add tooltip explaining benefit

**Cons:**
- Takes up space on Session Evaluation page
- Only helps from that specific page

---

### Option 4: Hybrid - Both Navigation Icon + Page Button

Combine best of both:
1. Small icon in navigation (always available)
2. Prominent button on Session Evaluation page (discoverable)

**Best user experience!**

---

## Recommended Implementation: **Option 4 (Hybrid)**

### Part 1: Navigation Sidebar Icon

**File:** `ui/src/layouts/AppLayout.tsx`

```tsx
import OpenInNewIcon from '@mui/icons-material/OpenInNew';

// In the drawer list rendering:
{appRoutes.map((route) => {
  const isActive = location.pathname === route.path;
  const isDashboard = route.path === '/';
  
  return (
    <ListItemButton
      key={route.path}
      selected={isActive}
      onClick={() => {
        navigate(route.path);
        setMobileOpen(false);
      }}
      sx={{ pr: isDashboard ? 1 : 2 }}
    >
      <ListItemIcon>
        <route.icon color={isActive ? 'primary' : 'inherit'} />
      </ListItemIcon>
      <ListItemText primary={route.label} />
      
      {/* "Open in new tab" icon for Dashboard */}
      {isDashboard && (
        <Tooltip title="Open in new tab (keeps Session Evaluation work)">
          <IconButton
            size="small"
            onClick={(e) => {
              e.stopPropagation();
              window.open('/', '_blank');
            }}
            sx={{ ml: 'auto', opacity: 0.6, '&:hover': { opacity: 1 } }}
          >
            <OpenInNewIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      )}
    </ListItemButton>
  );
})}
```

### Part 2: Session Evaluation Page Button

**File:** `ui/src/pages/SessionEvaluationPage.tsx`

Add near the top, in the main content area:

```tsx
// After the title card, before filters
<Card>
  <CardContent>
    <Stack direction="row" spacing={2} alignItems="center" justifyContent="space-between">
      <Box>
        <Typography variant="h5" fontWeight={600}>
          Session Evaluation & Overlays
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Compare sessions, analyze trends, and export data
        </Typography>
      </Box>
      
      <Tooltip title="Open Live Dashboard in new tab - keeps your work here intact">
        <Button
          variant="outlined"
          startIcon={<DashboardIcon />}
          endIcon={<OpenInNewIcon />}
          onClick={() => window.open('/', '_blank')}
          sx={{ whiteSpace: 'nowrap' }}
        >
          Live Dashboard
        </Button>
      </Tooltip>
    </Stack>
  </CardContent>
</Card>
```

---

## Bonus: Make All Links Support Ctrl+Click

Convert all navigation to proper router links:

```tsx
<ListItemButton
  key={route.path}
  selected={isActive}
  component={RouterLink}
  to={route.path}
  onClick={() => setMobileOpen(false)}
  // Now Ctrl+Click, middle-click, and right-click → "Open in new tab" all work!
>
  <ListItemIcon>
    <route.icon color={isActive ? 'primary' : 'inherit'} />
  </ListItemIcon>
  <ListItemText primary={route.label} />
</ListItemButton>
```

---

## User Benefits

### Before:
```
Session Evaluation (3 sessions selected, 2 markers placed)
  ↓ Click Dashboard
Dashboard (navigated away)
  ↓ Click Session Evaluation  
Session Evaluation (EMPTY - lost all work!) ❌
```

### After:
```
Session Evaluation (3 sessions selected, 2 markers placed)
  ↓ Click "Live Dashboard" button (new tab)
Dashboard (opens in new tab)
  ← Switch back to Session Evaluation tab
Session Evaluation (STILL HAS ALL WORK!) ✅
```

---

## Implementation Time

- Part 1 (Navigation icon): 15 minutes
- Part 2 (Page button): 10 minutes
- Part 3 (Ctrl+Click support): 10 minutes
- Testing: 10 minutes
- **Total: 45 minutes**

---

## Testing Checklist

- [ ] Click Dashboard in sidebar → navigates normally
- [ ] Click "open in new tab" icon → opens in new tab
- [ ] Session Evaluation work preserved when opening dashboard
- [ ] "Live Dashboard" button on page works
- [ ] Ctrl+Click on navigation opens new tab
- [ ] Middle-click on navigation opens new tab
- [ ] Right-click → "Open in new tab" works
- [ ] Mobile view works (icon might hide on small screens)

---

## Alternative: Just Add Button to Session Evaluation

**Simplest option if you want quick fix:**

Just add one button to Session Evaluation page:

```tsx
<Button
  variant="outlined"
  startIcon={<DashboardIcon />}
  onClick={() => window.open('/', '_blank')}
>
  Open Live Dashboard (New Tab)
</Button>
```

**Time:** 5 minutes
**Solves:** 100% of the problem for Session Evaluation workflow

---

## My Recommendation

**Quick Fix (5 min):** Button on Session Evaluation page only

**Complete Solution (45 min):** Hybrid approach
- Icon in navigation (subtle, always available)
- Button on Session Evaluation page (obvious, discoverable)
- Ctrl+Click support (power users)

**What do you prefer?**
1. ⚡ Quick: Just button on Session Evaluation page (5 min)
2. ⭐ Complete: Navigation icon + page button + Ctrl+Click (45 min)
3. 🎯 Other: Tell me your preference
