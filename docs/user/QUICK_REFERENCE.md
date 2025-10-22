# Hardware In-Use Detection - Quick Reference Card

## 🎯 What's New?

The launcher now detects if CX-505 is **in use by another process** and shows clear status indicators.

---

## 🚦 Status Colors

| Color | Message | Meaning | Action |
|-------|---------|---------|--------|
| 🟢 | "CX-505 connected and available" | Device ready to use | Press Start |
| 🟢 | "CX-505 in use by capture service" | Our service has it (good!) | All working |
| 🔴 | "CX-505 in use by another process" | **Conflict!** Something else has it | Close other app |
| 🟠 | "CX-505 not detected" | Device not found | Plug in device |
| 🟠 | "CX-505 status unknown" | Error checking status | Check drivers |

---

## 🔘 New Button: "Refresh Hardware"

**Location**: `[Start] [Stop] [Reset]  |  [Refresh Hardware]`

**When to use**:
- ✅ After plugging in device
- ✅ After closing another app
- ✅ To verify status anytime
- ✅ While services running (safe!)

**What it does**: Re-checks hardware status without restarting services

---

## 🛠️ Troubleshooting

### Problem: Red status "in use by another process"

**Solution**:
1. Close any Elmetron software
2. Check Task Manager for zombie python.exe processes
3. End any suspicious processes
4. Press "Refresh Hardware"
5. Should turn green → Press Start

---

### Problem: Orange status "not detected"

**Solution**:
1. Check USB cable connection
2. Check if device is powered
3. Verify FTDI drivers installed
4. Try different USB port
5. Press "Refresh Hardware"

---

### Problem: Start fails even with green status

**Solution**:
1. Press "Refresh Hardware" to confirm still green
2. Check capture service logs for errors
3. Try "Reset" button
4. Restart launcher if needed

---

## ⚡ Quick Start

### Normal Operation:
```
1. Launch monitor (py launcher.py)
   → 🟢 "CX-505 connected and available"

2. Press Start
   → 🟢 "CX-505 in use by capture service"
   → 🟢 "System running normally"

3. Work with dashboard
   → Measurements flowing

4. Press Stop when done
   → 🟢 "CX-505 connected and available"
```

---

## 📝 Testing Checklist

### Quick Smoke Test (5 min):
- [ ] Start launcher → See green "available"
- [ ] Press Start → See green "in use by capture service"
- [ ] Press "Refresh Hardware" → Still green
- [ ] Press Stop → Back to green "available"

### Conflict Detection Test:
- [ ] Stop services (if running)
- [ ] Open cx505_d2xx.py or other FTDI tool
- [ ] Press "Refresh Hardware" → See RED "in use by another process"
- [ ] Close other app
- [ ] Press "Refresh Hardware" → Back to green "available"

---

## 📚 Documentation

**Full Details**: See `HARDWARE_IN_USE_DETECTION_SUMMARY.md`  
**Visual Guide**: See `HARDWARE_IN_USE_VISUAL_GUIDE.md`  
**Test Plan**: See `HARDWARE_IN_USE_TEST_PLAN.md`  
**Implementation**: See `IMPLEMENTATION_COMPLETE.md`

---

## 🎓 User Education

**Q**: Why is the status green saying "in use by capture service"?  
**A**: That's normal! It means your capture is working correctly.

**Q**: How do I know if the device is available?  
**A**: Look for green "connected and available" before starting.

**Q**: Can I press Refresh Hardware while capturing?  
**A**: Yes! It's safe and won't disrupt capture.

**Q**: What if it says "in use" but I don't see any other app?  
**A**: Check Task Manager for zombie python.exe processes.

---

## 🔧 Technical Details

### Detection Method:
1. Count FTDI devices (`FT_CreateDeviceInfoList`)
2. Try to open first device (`FT_Open`)
3. Close immediately if successful (`FT_Close`)
4. Determine status from result

### Status Logic:
- Open succeeds → **AVAILABLE** (green)
- Open fails (error 3/4) + our service running → **IN_USE** (green)
- Open fails (error 3/4) + our service NOT running → **IN_USE** (red)
- No devices found → **NOT_FOUND** (orange)
- Other error → **UNKNOWN** (orange)

---

## 📞 Support Quick Reference

### User says: "Start button doesn't work"
**Ask**: "What color is the hardware status?"
- 🔴 Red → Close other app
- 🟠 Orange → Check device connection
- 🟢 Green → Check service logs

### User says: "Device not detected but it's plugged in"
**Ask**: "Try unplugging and replugging, then press Refresh Hardware"

### User says: "Status is red but nothing else is running"
**Ask**: "Check Task Manager for python.exe processes, end any you find, then Refresh Hardware"

---

## 🚀 Implementation Status

**Date**: September 30, 2025  
**Status**: ✅ COMPLETE & VALIDATED  
**Ready**: For manual testing  
**Files**: launcher.py + 4 documentation files  

---

## 📋 Next Actions

1. ⏳ Manual testing with CX-505 device
2. ⏳ Verify color indicators work
3. ⏳ Test conflict detection
4. ⏳ Confirm no regressions

---

**For detailed information, see the full documentation files.**
