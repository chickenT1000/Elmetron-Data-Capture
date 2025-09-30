# Hardware In-Use Detection - Visual Guide

## New UI Layout

```
┌─────────────────────────────────────────────────────────────┐
│         Elmetron Launch Monitor                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Elmetron CX-505 Data Capture Service                      │
│  Start the background service and open the UI dashboard    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Status                                               │  │
│  ├─────────────────────────────────────────────────────┤  │
│  │ 🔵 CX-505 Hardware:    CX-505 connected and available│ GREEN
│  │ 🔵 Prerequisites:      Prerequisites ready            │  │
│  │ 🔵 Capture Service:    Running on port 8050          │  │
│  │ 🔵 Service Health UI:  Available at 127.0.0.1:5173   │  │
│  │ 🔵 Dashboard:          Browser opened                 │  │
│  │ 🔵 Overall Status:     System running normally        │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  [Start] [Stop] [Reset]  |  [Refresh Hardware]             │ << NEW!
│                                                             │
│  Activity log                                               │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ 2025-09-30 10:15:42: Starting services...           │  │
│  │ 2025-09-30 10:15:43: Checking prerequisites...       │  │
│  │ 2025-09-30 10:15:43: CX-505 connected and available  │  │ << NEW!
│  │ 2025-09-30 10:15:44: Capture service started (8050)  │  │
│  │ 2025-09-30 10:15:45: UI server started (5173)        │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  Closing this window keeps services running.                │
│  Use Stop to end capture before exiting.                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Hardware Status Colors & Messages

### ✅ Scenario 1: Device Available (GREEN)
```
┌────────────────────────────────────────────────────┐
│ 🟢 CX-505 Hardware:  CX-505 connected and available│
└────────────────────────────────────────────────────┘
```
**When**: Device connected, no software using it  
**Action**: Safe to start capture service

---

### ✅ Scenario 2: Our Service Running (GREEN)
```
┌─────────────────────────────────────────────────────┐
│ 🟢 CX-505 Hardware:  CX-505 in use by capture service│
└─────────────────────────────────────────────────────┘
```
**When**: Capture service successfully started  
**Action**: Everything working as expected

---

### ❌ Scenario 3: Other Process Using Device (RED)
```
┌──────────────────────────────────────────────────────┐
│ 🔴 CX-505 Hardware:  CX-505 in use by another process│
└──────────────────────────────────────────────────────┘
```
**When**: Another application has opened the device  
**Action**: Close the other app, press "Refresh Hardware"

---

### ⚠️ Scenario 4: Device Not Found (ORANGE)
```
┌────────────────────────────────────────────────────────────────────┐
│ 🟠 CX-505 Hardware:  CX-505 not detected (OK for archived sessions)│
└────────────────────────────────────────────────────────────────────┘
```
**When**: Device unplugged or driver not installed  
**Action**: 
- For live capture: Connect device, press "Refresh Hardware"
- For archived sessions: This is normal, UI can still open

---

### ⚠️ Scenario 5: Status Unknown (ORANGE)
```
┌───────────────────────────────────────────────┐
│ 🟠 CX-505 Hardware:  CX-505 status unknown    │
└───────────────────────────────────────────────┘
```
**When**: FTDI driver error or unexpected state  
**Action**: Check drivers, restart launcher

---

## User Workflow Examples

### Example 1: Fresh Start (All Good!)
```
1. Launch monitor
   → 🟢 "CX-505 connected and available"

2. Press Start
   → 🟢 "CX-505 in use by capture service"
   → 🟢 "System running normally"

3. Work with UI dashboard
   → All measurements flowing

4. Press Stop when done
   → 🟢 "CX-505 connected and available" (back to idle)
```

---

### Example 2: Conflict with Other App
```
1. Launch monitor
   → 🟢 "CX-505 connected and available"

2. Meanwhile, user opens Elmetron proprietary software
   → (Other app grabs device)

3. User presses Start in launcher
   → ❌ Start FAILS
   → 🔴 "CX-505 in use by another process"
   → Log shows: "Failed to open device"

4. User closes other app
   → Press [Refresh Hardware]
   → 🟢 "CX-505 connected and available"

5. Press Start again
   → ✅ Success!
```

---

### Example 3: Checking Status During Operation
```
1. Services running normally
   → 🟢 "CX-505 in use by capture service"

2. User wants to verify hardware
   → Press [Refresh Hardware]
   → Log: "Refreshing hardware status..."
   → Still 🟢 "CX-505 in use by capture service"

3. Confirms everything is working
```

---

### Example 4: Working with Archives (No Device)
```
1. Device unplugged
   → 🟠 "CX-505 not detected (OK for archived sessions)"

2. Press Start
   → Capture service starts normally (using archived data)
   → UI opens
   → Can view historical sessions

3. Note: Live capture won't work, but that's expected
```

---

### Example 5: Troubleshooting Stale Handle
```
1. Capture service crashed ungracefully
   → Device handle not released

2. Launch monitor
   → 🔴 "CX-505 in use by another process"
   → (No other visible apps!)

3. Check Task Manager
   → Find zombie python.exe process
   → End Process

4. Press [Refresh Hardware]
   → 🟢 "CX-505 connected and available"

5. Success! Start services normally
```

---

## Button Behavior

### Refresh Hardware Button

**Location**: Right side of button row after separator  
**Enabled**: Always (even while services running)  
**Function**: Re-check hardware status without restarting services  
**Log Output**: "Refreshing hardware status..."  

**Use Cases**:
- ✅ Verify device connection after plugging in
- ✅ Confirm other app released device
- ✅ Check if our service has device (during operation)
- ✅ Diagnose hardware issues without disrupting capture

**Keyboard Shortcut**: None (could add Alt+H if requested)

---

## Technical Details

### Detection Method
```python
1. Enumerate devices (FT_CreateDeviceInfoList)
   → Returns count of FTDI devices

2. If count == 0:
   → NOT_FOUND

3. Try to open device (FT_Open)
   → Open succeeds:  AVAILABLE (close immediately)
   → Open fails (3): IN_USE
   → Open fails (4): IN_USE  
   → Other error:    UNKNOWN
```

### Smart Logic
```python
if status == IN_USE:
    if our_service_running:
        → GREEN (expected)
    else:
        → RED (problem!)
```

### Safety
- ✅ Non-destructive: Test-open immediately closed
- ✅ No data transfer during check
- ✅ Takes ~50ms (imperceptible)
- ✅ No interference with active capture

---

## Error Messages Decoded

### FTDI Error Codes
- **0 (FT_OK)**: Success → Device available
- **2 (FT_DEVICE_NOT_FOUND)**: No device → Not detected
- **3 (FT_DEVICE_NOT_OPENED)**: Busy → In use
- **4 (FT_IO_ERROR)**: I/O failed → Usually means busy
- **Other**: Unexpected → Unknown status

---

## UI State Machine

```
                    ┌─────────┐
                    │ STARTUP │
                    └────┬────┘
                         │
                         ▼
              Check Hardware Status
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
  ┌──────────┐    ┌───────────┐    ┌──────────┐
  │AVAILABLE │    │ NOT_FOUND │    │  IN_USE  │
  │  GREEN   │    │  ORANGE   │    │ SMART    │
  └──────────┘    └───────────┘    └────┬─────┘
                                         │
                              ┌──────────┴──────────┐
                              │                     │
                              ▼                     ▼
                    Our Service Running?      
                       YES          NO
                        │            │
                        ▼            ▼
                    ┌───────┐   ┌─────────┐
                    │ GREEN │   │   RED   │
                    └───────┘   └─────────┘
```

---

## User Education

### What users need to know:

1. **Green = Good** (device ready or in use by us)
2. **Red = Problem** (something else has the device)
3. **Orange = FYI** (no device, but that's sometimes OK)

### Common questions:

**Q**: Why does it say "in use by capture service" (green)?  
**A**: That's expected! Your capture is running normally.

**Q**: It says "in use by another process" (red) but I don't see anything!  
**A**: Check Task Manager for zombie python.exe or old Elmetron software.

**Q**: Can I use Refresh Hardware while capture is running?  
**A**: Yes! It's safe and won't disrupt capture.

**Q**: Why orange when device is unplugged?  
**A**: Orange means "heads up" not "error". You can still view archives.

---

## Comparison: Before vs After

### BEFORE
- ❌ Only knew: "Device present" or "not present"
- ❌ No way to detect conflicts with other apps
- ❌ Mysterious start failures when device busy
- ❌ No manual refresh capability

### AFTER  
- ✅ Four states: Available, In-Use-By-Us, In-Use-By-Other, Not-Found
- ✅ Clear distinction between expected and problem states
- ✅ Red alert when another app has the device
- ✅ Manual refresh button anytime
- ✅ Color-coded for instant understanding
- ✅ Smart context-aware messages

---

## Future Enhancements (Optional)

1. **Identify which process** has the device (if possible via Windows API)
2. **Force release button** for advanced users
3. **Automatic periodic refresh** (if user enables it)
4. **Tooltip on hover** explaining each status
5. **Hardware info button** showing FTDI details (serial, description)
6. **History log** of hardware status changes

---

## Success Metrics

### User Experience
- ✅ Immediately see if device is available
- ✅ Understand why Start button fails
- ✅ Self-diagnose "device busy" without support
- ✅ Confidence in system state

### Support Benefits  
- ✅ Fewer "why won't it start?" calls
- ✅ Better bug reports with status details
- ✅ Faster troubleshooting

### Professional Polish
- ✅ Industry-standard conflict detection
- ✅ Clear, actionable messages
- ✅ Responsive manual controls

---

**Implementation Complete!** ✅  
**Ready for Testing** 🧪
