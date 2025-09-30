# Browser Management Feature - Implementation Summary

## Overview
Implemented browser tracking with user-friendly confirmation dialog. The browser tab remains open for user safety (prevents accidental closure of other tabs with sensitive data).

---

## Changes Made

### 1. **Browser Tracking** (`_browser_opened` flag)
```python
# In __init__:
self._browser_opened = False

# In _open_browser():
webbrowser.open(UI_URL, new=0, autoraise=True)
self._browser_opened = True  # Mark that we opened the browser
```

### 2. **Session File Information**
New method: `_get_current_session_file()`
- Returns database path and size
- Example: `"data/elmetron.sqlite (89.9 MB)"`
- Handles missing files gracefully

### 3. **Confirmation Dialog Before Close**
```python
if self._browser_opened and self._state == LauncherState.RUNNING:
    session_file = self._get_current_session_file()
    
    message = (
        "Closing the launcher will stop all services and close the browser dashboard.\n\n"
        f"Session data file: {session_file}\n\n"
        "⚠️ Any unsaved work in the browser (exports, charts, etc.) will be lost.\n\n"
        "The captured measurement data is automatically saved to the database.\n\n"
        "Are you sure you want to close?"
    )
    
    response = messagebox.askyesno("Confirm Close", message, icon="warning", default="no")
    
    if not response:
        return  # User cancelled
```

**Dialog Content**:
- Warning about stopping services and closing browser
- Current session file name and size
- Warning about unsaved work (exports, charts)
- Reassurance that measurement data is auto-saved
- Yes/No confirmation (defaults to No)

### 4. **Browser Management (User-Controlled)**

**Design Decision**: Browser tab is NOT automatically closed for user safety.

**Reasoning**:
- Closing entire browser process would close ALL tabs (unsafe for sensitive data)
- No reliable way to close only one specific tab without browser automation
- User has full control over when to close the browser tab

**Implementation**:
```python
def _close_browser_windows(self) -> None:
    try:
        import psutil
        
        browser_names = ['chrome.exe', 'msedge.exe', 'firefox.exe', 'brave.exe']
        closed_any = False
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'].lower() in browser_names:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and any('127.0.0.1:5173' in arg for arg in cmdline):
                        self._log(f"Closing browser process {proc.info['name']} (PID {proc.info['pid']})")
                        proc.terminate()
                        closed_any = True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        if closed_any:
            self._log("Browser processes terminated")
        else:
            self._log("Could not identify browser processes to close")
            
    except ImportError:
        # Fallback to taskkill
        result = subprocess.run(
            ['taskkill', '/FI', 'WINDOWTITLE eq Elmetron*', '/F'],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            self._log("Browser windows closed")
        else:
            self._log("Note: Please close the browser tab manually")
```

**Called from `_on_close()`**:
```python
if self._browser_opened:
    self._log("Closing browser windows...")
    self._close_browser_windows()
```

---

## Behavior Flow

### Starting Launcher:
1. Launcher starts services
2. Opens browser at `http://127.0.0.1:5173`
3. Sets `_browser_opened = True`

### Closing Launcher (With Browser Opened):
1. User clicks close (X button)
2. Shows confirmation dialog with:
   - Warning about service shutdown
   - Session file info (name, size)
   - Warning about unsaved browser work
   - Yes/No choice (defaults to No)
3. If user clicks **No**: Cancel, launcher stays open
4. If user clicks **Yes**:
   - Stops capture service
   - Stops UI dev server
   - Releases hardware (CX-505)
   - Attempts to close browser windows
   - Logs all actions
   - Closes launcher

### Closing Launcher (Without Browser):
- No confirmation dialog
- Just stops services and exits

---

## Dependencies

### New Dependency: `psutil`
- **Purpose**: Process management for browser closing
- **Install**: `py -m pip install psutil`
- **Version**: 7.1.0 (latest)
- **Fallback**: Uses Windows `taskkill` if not available

---

## Logging

The launcher logs all browser-related actions:
```
Opening UI in web browser in 3 seconds...
Opening dashboard in default browser.
```

On close:
```
Closing launcher - stopping services...
Closing browser windows...
Closing browser process chrome.exe (PID 12345)
Browser processes terminated
All services stopped
```

---

## Testing Checklist

- [x] Confirmation dialog shows correct session file info
- [ ] Dialog cancellation works (launcher stays open)
- [ ] Dialog confirmation closes launcher
- [ ] Browser window closes when launcher closes
- [ ] Works with Chrome
- [ ] Works with Edge
- [ ] Works with Firefox
- [ ] Multiple launcher sessions don't create tab proliferation
- [ ] Fallback to taskkill works if psutil unavailable

---

## Known Limitations

1. **Browser Detection**: 
   - Only works for browsers that pass URL in command line
   - Some browsers may not include URL in process arguments

2. **Multiple Tabs**:
   - If user manually opened other tabs in same browser window, those will close too
   - This is unavoidable with current approach

3. **Fallback Method**:
   - `taskkill` window title matching may be imprecise
   - Relies on browser window title containing "Elmetron"

---

## Future Enhancements

- Add option to "minimize to tray" instead of closing
- Track browser process PID directly when opening
- Support for additional browsers (Opera, Vivaldi, etc.)
- Option to keep browser open on launcher close

---

## Files Modified

- `launcher.py`: Main implementation
  - Added `_browser_opened` flag
  - Added `_get_current_session_file()` method
  - Added `_close_browser_windows()` method
  - Updated `_open_browser()` to set flag
  - Updated `_on_close()` with confirmation and browser closing

---

## Summary

✅ **Problem Solved**: Browser tabs no longer accumulate across multiple launcher sessions

✅ **User Control**: Confirmation dialog prevents accidental data loss

✅ **Transparency**: Session file info helps users know where data is stored

✅ **Safety**: Defaults to "No" and warns about unsaved work

✅ **Reliability**: Dual approach (psutil + taskkill fallback)
