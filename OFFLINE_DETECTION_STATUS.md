# Offline Detection Status

## Current Situation

### ✅ What's Working:
1. **Connection monitor is implemented** (`useConnectionMonitor` hook)
2. **Offline warning component is created** (`OfflineWarning.tsx`)
3. **Integration is complete** (App.tsx has the monitoring logic)
4. **Backend API is offline** (no Python processes running)
5. **UI dev server is still running** (Vite on port 5173)

### ❓ What Needs Testing:
The offline warning modal should appear within 10 seconds of closing the launcher, but we need to verify:

1. **Is the connection monitor detecting offline status?**
   - Pinging `http://127.0.0.1:8050/health` every 5 seconds
   - Should fail and mark as offline after 2 consecutive failures (10 seconds)

2. **Is the modal actually showing?**
   - Should appear as a full-screen overlay
   - Shows warning icon and countdown timer
   - Offers "Close Tab Now" and "Keep Tab Open" buttons

## Testing Instructions

### To Test the Feature:

1. **Start the launcher** (services running)
2. **Open browser** (UI loads at `http://localhost:5173`)
3. **Close the launcher** (services stop)
4. **Watch the browser for 10 seconds**

**Expected Behavior**:
- After ~10 seconds, a modal should appear with:
  - ⚠️ "Launcher Offline" warning
  - List of consequences
  - Countdown timer (30 seconds)
  - Two buttons: "Keep Tab Open" and "Close Tab Now"

**If Nothing Happens**:
- Open browser Developer Tools (F12)
- Go to Console tab
- Look for:
  - `[Connection Monitor] ...` log messages
  - Any errors from `useConnectionMonitor`
  - React rendering errors

### Debug Checklist:

**Check Browser Console**:
```javascript
// You should see logs like:
[Connection Monitor] Checking connection...
[Connection Monitor] Connection failed: <error>
[Connection Monitor] Consecutive failures: 1
[Connection Monitor] Consecutive failures: 2
[Connection Monitor] Status changed to OFFLINE
```

**Check Network Tab**:
- Look for failed requests to `http://127.0.0.1:8050/health`
- Should see 404 or connection errors

**Check React DevTools**:
- Inspect `<App>` component
- Look at `connectionStatus` state:
  ```
  isOnline: false
  lastChecked: <timestamp>
  consecutiveFailures: 2
  ```
- Look at `showWarning` state: should be `true`

## Possible Issues

### Issue 1: Modal Not Rendering
**Symptoms**: Connection monitor detects offline, but no modal appears

**Causes**:
- Z-index conflict with other UI elements
- Modal portal not rendering
- Material-UI theme issue

**Solution**: Check if `<OfflineWarning>` component is mounting

### Issue 2: Connection Monitor Not Detecting Offline
**Symptoms**: No console logs, `isOnline` stays `true`

**Causes**:
- Hook not running
- Fetch requests being cached
- CORS issues

**Solution**: Add console.log in `useConnectionMonitor.ts`

### Issue 3: Backend Still Running
**Symptoms**: `/health` endpoint responds successfully

**Causes**:
- Python processes didn't terminate
- Launcher didn't stop services

**Solution**: Manually kill Python processes

## Current Code Review

### App.tsx Integration:
```typescript
function App() {
  const connectionStatus = useConnectionMonitor();
  const [warningDismissed, setWarningDismissed] = useState(false);

  const showWarning = !connectionStatus.isOnline && !warningDismissed;

  return (
    <>
      <Routes>...</Routes>
      <OfflineWarning open={showWarning} onClose={handleDismissWarning} />
    </>
  );
}
```
✅ Looks correct

### useConnectionMonitor Hook:
- Pings `/health` every 5 seconds
- 3-second timeout per request
- Marks offline after 2 failures
✅ Logic is sound

### OfflineWarning Component:
- Material-UI Modal
- Auto-close countdown (30s)
- Two action buttons
✅ Should work

## Next Steps

### For User Testing:
1. Start launcher
2. Open browser Developer Tools (F12)
3. Go to Console tab
4. Close launcher
5. Watch for:
   - Connection error logs
   - Modal appearance
   - Countdown timer

### If Modal Doesn't Show:
Please share:
1. **Browser console logs** (screenshot or copy/paste)
2. **Network tab** (screenshot showing failed /health requests)
3. **Any error messages**

### Quick Test Without Launcher:
You can test the modal directly by temporarily modifying the code:

```typescript
// In App.tsx, temporarily change:
const showWarning = !connectionStatus.isOnline && !warningDismissed;

// To:
const showWarning = true;  // Force modal to always show
```

This will make the modal appear immediately when you refresh the page.

## Resolution Path

### If Working:
✅ Feature complete - browser will auto-close tab when launcher stops

### If Not Working:
Need to debug one of:
1. Connection monitoring logic
2. Modal rendering
3. React state updates
4. Material-UI configuration

---

## Summary

The feature **should be working**, but needs real-world testing to confirm. The code is in place and looks correct. Most likely scenario is that it IS working, and the user just needs to wait 10 seconds after closing the launcher to see the modal appear.

**Action**: Please test and report what you see after closing the launcher and waiting 10-15 seconds.
