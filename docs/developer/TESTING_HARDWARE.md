# Hardware In-Use Detection - Test Plan

## Overview
This document provides a comprehensive manual test plan for the new hardware in-use detection feature.

---

## Prerequisites

### Hardware
- [ ] CX-505 device available
- [ ] USB cable for connecting/disconnecting
- [ ] FTDI drivers installed

### Software
- [ ] Latest launcher.py with hardware detection
- [ ] Access to cx505_d2xx.py or other FTDI test tool
- [ ] Task Manager available for process inspection

### Environment
- [ ] Windows OS
- [ ] Python 3.x installed
- [ ] No other launcher instances running

---

## Test Scenarios

### TEST 1: Device Available on Startup

**Preconditions**:
- CX-505 connected via USB
- No software using device
- Launcher not running

**Steps**:
1. Start launcher: `python launcher.py`
2. Observe hardware status row

**Expected Results**:
- [ ] Hardware row shows: "CX-505 connected and available"
- [ ] Status color is GREEN
- [ ] Activity log shows: "CX-505 connected and available"

**Actual Results**:
```
[Record observations here]
```

---

### TEST 2: Device Not Connected on Startup

**Preconditions**:
- CX-505 NOT connected
- Launcher not running

**Steps**:
1. Ensure device is unplugged
2. Start launcher: `python launcher.py`
3. Observe hardware status row

**Expected Results**:
- [ ] Hardware row shows: "CX-505 not detected (OK for archived sessions)"
- [ ] Status color is ORANGE
- [ ] Activity log shows same message
- [ ] Launcher allows Start button (for archive viewing)

**Actual Results**:
```
[Record observations here]
```

---

### TEST 3: Normal Service Start Cycle

**Preconditions**:
- CX-505 connected
- Launcher running, showing "available"
- Services in IDLE state

**Steps**:
1. Press "Start" button
2. Wait for services to start
3. Observe hardware status during startup
4. Verify final state

**Expected Results**:
- [ ] Hardware initially: "CX-505 connected and available" (green)
- [ ] During startup: Brief flicker possible
- [ ] After startup: "CX-505 in use by capture service" (green)
- [ ] Overall Status: "System running normally"

**Actual Results**:
```
[Record observations here]
```

---

### TEST 4: Manual Refresh While Running

**Preconditions**:
- Services RUNNING
- Hardware status: "CX-505 in use by capture service" (green)

**Steps**:
1. Press "Refresh Hardware" button
2. Observe log and status

**Expected Results**:
- [ ] Log shows: "Refreshing hardware status..."
- [ ] Status remains: "CX-505 in use by capture service" (green)
- [ ] No service disruption
- [ ] Refresh completes in <1 second

**Actual Results**:
```
[Record observations here]
```

---

### TEST 5: Another Application Has Device

**Preconditions**:
- CX-505 connected
- Launcher running, services STOPPED
- No other software using device

**Steps**:
1. Open another FTDI application (e.g., run cx505_d2xx.py script)
2. In launcher, press "Refresh Hardware"
3. Observe status

**Expected Results**:
- [ ] Status changes to: "CX-505 in use by another process"
- [ ] Status color is RED
- [ ] Log shows the status change

**Actual Results**:
```
[Record observations here]
```

---

### TEST 6: Start Attempt While Device Busy

**Preconditions**:
- CX-505 connected
- Another app has device open
- Launcher showing RED status

**Steps**:
1. Press "Start" button
2. Observe behavior

**Expected Results**:
- [ ] Start fails (service can't open device)
- [ ] Error in activity log
- [ ] Hardware status remains RED
- [ ] Launcher enters FAILED state
- [ ] Clear error message to user

**Actual Results**:
```
[Record observations here]
```

---

### TEST 7: Device Release and Refresh

**Preconditions**:
- Another app has device (RED status)
- Launcher showing: "CX-505 in use by another process"

**Steps**:
1. Close the other application
2. Press "Refresh Hardware"
3. Observe status change

**Expected Results**:
- [ ] Status changes to: "CX-505 connected and available" (green)
- [ ] Change happens immediately
- [ ] Log confirms status update

**Actual Results**:
```
[Record observations here]
```

---

### TEST 8: Device Unplug During Operation

**Preconditions**:
- Services RUNNING
- Device in use by capture service (green)

**Steps**:
1. Physically unplug CX-505
2. Press "Refresh Hardware"
3. Observe status

**Expected Results**:
- [ ] Status changes to: "CX-505 not detected" (orange)
- [ ] Capture service may error (expected)
- [ ] No launcher crash

**Actual Results**:
```
[Record observations here]
```

---

### TEST 9: Device Re-plug and Refresh

**Preconditions**:
- Device was unplugged (orange status)
- Services may be in error state

**Steps**:
1. Plug device back in
2. Wait 2 seconds for driver enumeration
3. Press "Refresh Hardware"
4. Observe status

**Expected Results**:
- [ ] Status changes to: "CX-505 connected and available" (green)
- [ ] Ready to restart services

**Actual Results**:
```
[Record observations here]
```

---

### TEST 10: Rapid Refresh Clicks

**Preconditions**:
- Any hardware state
- Launcher running

**Steps**:
1. Click "Refresh Hardware" rapidly 10 times
2. Observe behavior

**Expected Results**:
- [ ] No crashes
- [ ] Each click logs "Refreshing hardware status..."
- [ ] Final status is accurate
- [ ] No freeze or hang
- [ ] UI remains responsive

**Actual Results**:
```
[Record observations here]
```

---

### TEST 11: Stop Services and Verify Availability

**Preconditions**:
- Services RUNNING
- Hardware: "CX-505 in use by capture service" (green)

**Steps**:
1. Press "Stop" button
2. Wait for services to stop
3. Observe hardware status OR press "Refresh Hardware"

**Expected Results**:
- [ ] After stop: Hardware becomes "CX-505 connected and available" (green)
- [ ] Device properly released
- [ ] Ready to start again

**Actual Results**:
```
[Record observations here]
```

---

### TEST 12: Reset from Error State

**Preconditions**:
- Launcher in FAILED state (e.g., from TEST 6)
- Hardware status is RED or ORANGE

**Steps**:
1. Fix hardware issue (close other app, plug in device)
2. Press "Refresh Hardware" to verify green status
3. Press "Reset" button
4. Press "Start" button

**Expected Results**:
- [ ] Reset clears FAILED state
- [ ] Hardware shows green before Start
- [ ] Start succeeds
- [ ] Hardware shows "in use by capture service" (green)

**Actual Results**:
```
[Record observations here]
```

---

### TEST 13: Zombie Process Detection

**Preconditions**:
- Simulated zombie process holding device
- Launcher closed/crashed ungracefully (kill python.exe while device open)

**Steps**:
1. Open Task Manager
2. Find zombie python.exe process
3. Start new launcher instance
4. Observe hardware status

**Expected Results**:
- [ ] Hardware status: "CX-505 in use by another process" (RED)
- [ ] Clear indication device is busy
- [ ] User can identify need to clean up processes

**Actual Results**:
```
[Record observations here]
```

---

### TEST 14: Unknown Status Handling

**Preconditions**:
- Corrupt FTDI driver or unusual error condition
- (May be hard to reproduce)

**Steps**:
1. Trigger FTDI error (e.g., permission issue, driver conflict)
2. Press "Refresh Hardware"
3. Observe status

**Expected Results**:
- [ ] Status shows: "CX-505 status unknown" (orange)
- [ ] No crash
- [ ] Graceful error handling

**Actual Results**:
```
[Record observations here]
```

---

### TEST 15: Multiple Launcher Instance Prevention

**Preconditions**:
- One launcher already running
- Hardware in any state

**Steps**:
1. Try to start second launcher instance: `python launcher.py`
2. Observe behavior

**Expected Results**:
- [ ] Second instance detects existing launcher
- [ ] Error dialog: "Another instance...already running"
- [ ] Second instance exits cleanly
- [ ] First instance unaffected
- [ ] Hardware detection still works in first instance

**Actual Results**:
```
[Record observations here]
```

---

## Edge Cases

### EDGE 1: Fast Start/Stop Cycling
**Steps**:
1. Start services
2. Immediately press Stop
3. Immediately press Start again
4. Repeat 5 times

**Expected**: No deadlock, hardware status accurate after each cycle

---

### EDGE 2: Device Swap
**Steps**:
1. Start with device A
2. Unplug device A
3. Plug in device B (another CX-505)
4. Refresh hardware

**Expected**: Detects new device as available

---

### EDGE 3: Driver Reinstall During Operation
**Steps**:
1. Services running
2. Reinstall FTDI drivers (if safe to test)
3. Refresh hardware

**Expected**: Graceful handling, may show "not found" or "unknown"

---

### EDGE 4: USB Hub Disconnect
**Steps**:
1. Device connected via USB hub
2. Services running
3. Disconnect hub
4. Refresh hardware

**Expected**: Shows "not detected" (orange)

---

## Performance Checks

### PERF 1: Refresh Speed
- [ ] Refresh completes in <100ms (normal case)
- [ ] No UI freeze during refresh
- [ ] Acceptable during rapid clicks

### PERF 2: Startup Time
- [ ] Hardware check doesn't delay startup
- [ ] <500ms to complete hardware detection

### PERF 3: Memory/Resource Usage
- [ ] No memory leak from repeated refreshes
- [ ] FTDI handles properly closed
- [ ] No accumulation of stale resources

---

## UI/UX Validation

### UX 1: Button Visibility
- [ ] "Refresh Hardware" button clearly visible
- [ ] Separator makes button grouping clear
- [ ] Button enabled in all states

### UX 2: Status Clarity
- [ ] Green/Red/Orange colors distinct
- [ ] Messages are clear and actionable
- [ ] No confusing technical jargon

### UX 3: Log Readability
- [ ] Hardware status changes appear in log
- [ ] Timestamps visible
- [ ] Log doesn't flood with repeated refreshes

---

## Regression Checks

### REG 1: Existing Features Unaffected
- [ ] Start button still works
- [ ] Stop button still works
- [ ] Reset button still works
- [ ] Browser opening unchanged
- [ ] Service Health UI still loads

### REG 2: Single-Instance Still Works
- [ ] Lockfile mechanism intact
- [ ] PID validation working
- [ ] Error dialog for duplicate instance

### REG 3: Capture Service Functionality
- [ ] Device communication unaffected
- [ ] Data capture works normally
- [ ] No new errors in capture logs

---

## Documentation Checks

### DOC 1: User Guidance
- [ ] Error messages guide user actions
- [ ] Status meanings are intuitive
- [ ] Troubleshooting clear

### DOC 2: Technical Accuracy
- [ ] Implementation matches specification
- [ ] Status transitions documented
- [ ] FTDI error codes correct

---

## Bug Recording Template

**Bug ID**: [AUTO-INCREMENT]
**Test**: [Test number/name]
**Severity**: [Critical/High/Medium/Low]
**Description**: [What went wrong]
**Steps to Reproduce**:
1. 
2. 
3. 

**Expected**: [What should happen]
**Actual**: [What actually happened]
**Screenshots**: [Attach if applicable]
**Logs**: [Relevant log excerpts]

---

## Sign-Off Checklist

### Critical Tests (Must Pass)
- [ ] TEST 1: Device Available on Startup
- [ ] TEST 3: Normal Service Start Cycle
- [ ] TEST 5: Another Application Has Device
- [ ] TEST 7: Device Release and Refresh
- [ ] TEST 11: Stop Services and Verify Availability
- [ ] TEST 15: Multiple Launcher Instance Prevention

### Important Tests (Should Pass)
- [ ] TEST 2: Device Not Connected
- [ ] TEST 4: Manual Refresh While Running
- [ ] TEST 6: Start Attempt While Device Busy
- [ ] TEST 10: Rapid Refresh Clicks
- [ ] TEST 12: Reset from Error State

### Nice-to-Have Tests (Best Effort)
- [ ] TEST 8: Device Unplug During Operation
- [ ] TEST 9: Device Re-plug and Refresh
- [ ] TEST 13: Zombie Process Detection
- [ ] TEST 14: Unknown Status Handling

### All Edge Cases Reviewed
- [ ] EDGE 1-4 documented

### All Performance Checks Pass
- [ ] PERF 1-3 acceptable

### All Regression Checks Pass
- [ ] REG 1-3 no issues

---

## Test Environment Details

**Date**: _________________
**Tester**: _________________
**OS Version**: _________________
**Python Version**: _________________
**FTDI Driver Version**: _________________
**Launcher Version/Commit**: _________________

---

## Overall Test Results

**Total Tests**: 15 + 4 edge + 3 perf + 3 reg = 25
**Tests Passed**: ____
**Tests Failed**: ____
**Tests Skipped**: ____

**Critical Bugs Found**: ____
**Minor Bugs Found**: ____

**Ready for Production**: [ ] YES  [ ] NO  [ ] WITH CAVEATS

---

## Notes

```
[Add any additional observations, suggestions, or concerns here]
```

---

## Approval

**Tested By**: ____________________  **Date**: __________  
**Reviewed By**: ____________________  **Date**: __________  
**Approved By**: ____________________  **Date**: __________  

---

**END OF TEST PLAN**
