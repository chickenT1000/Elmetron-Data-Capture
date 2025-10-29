"""Diagnostic tool for CX-505 FTDI device connection issues."""

import ctypes
import ctypes.wintypes as wintypes
import sys
import time
import io

# Fix encoding for Windows console
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def check_ftdi_dll():
    """Check if FTDI D2XX DLL is available."""
    print("=" * 60)
    print("FTDI D2XX DLL Check")
    print("=" * 60)
    
    try:
        ftd2xx = ctypes.WinDLL('ftd2xx.dll')
        print("[OK] ftd2xx.dll loaded successfully")
        return ftd2xx
    except Exception as e:
        print(f"[FAIL] Failed to load ftd2xx.dll: {e}")
        print("\nInstall FTDI D2XX drivers from:")
        print("https://ftdichip.com/drivers/d2xx-drivers/")
        return None

def enumerate_devices(ftd2xx):
    """Enumerate FTDI devices."""
    print("\n" + "=" * 60)
    print("Device Enumeration")
    print("=" * 60)
    
    _ft_create_list = ftd2xx.FT_CreateDeviceInfoList
    _ft_create_list.argtypes = [ctypes.POINTER(ctypes.c_ulong)]
    _ft_create_list.restype = ctypes.c_ulong
    
    count = ctypes.c_ulong()
    status = _ft_create_list(ctypes.byref(count))
    
    if status != 0:
        print(f"[FAIL] FT_CreateDeviceInfoList failed with status={status}")
        return 0
    
    print(f"[OK] Found {count.value} FTDI device(s)")
    return count.value

def test_device_open(ftd2xx, device_index=0):
    """Try to open the first FTDI device."""
    print("\n" + "=" * 60)
    print(f"Testing Device Open (index {device_index})")
    print("=" * 60)
    
    _ft_open = ftd2xx.FT_Open
    _ft_open.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.wintypes.HANDLE)]
    _ft_open.restype = ctypes.c_ulong
    
    _ft_close = ftd2xx.FT_Close
    _ft_close.argtypes = [ctypes.wintypes.HANDLE]
    _ft_close.restype = ctypes.c_ulong
    
    handle = ctypes.wintypes.HANDLE()
    status = _ft_open(device_index, ctypes.byref(handle))
    
    if status == 0:
        print("[OK] Device opened successfully")
        print(f"  Handle: {handle.value}")
        
        # Try to close it
        close_status = _ft_close(handle)
        if close_status == 0:
            print("[OK] Device closed successfully")
        else:
            print(f"[FAIL] Device close failed with status={close_status}")
        return True
    else:
        error_messages = {
            1: "FT_INVALID_HANDLE",
            2: "FT_DEVICE_NOT_FOUND",
            3: "FT_DEVICE_NOT_OPENED",
            4: "FT_IO_ERROR",
            5: "FT_INSUFFICIENT_RESOURCES",
            6: "FT_INVALID_PARAMETER",
            7: "FT_INVALID_BAUD_RATE",
            8: "FT_DEVICE_NOT_OPENED_FOR_ERASE",
            9: "FT_DEVICE_NOT_OPENED_FOR_WRITE",
            10: "FT_FAILED_TO_WRITE_DEVICE",
            11: "FT_EEPROM_READ_FAILED",
            12: "FT_EEPROM_WRITE_FAILED",
            13: "FT_EEPROM_ERASE_FAILED",
            14: "FT_EEPROM_NOT_PRESENT",
            15: "FT_EEPROM_NOT_PROGRAMMED",
            16: "FT_INVALID_ARGS",
            17: "FT_NOT_SUPPORTED",
            18: "FT_OTHER_ERROR",
            19: "FT_DEVICE_LIST_NOT_READY",
        }
        error_msg = error_messages.get(status, f"UNKNOWN_ERROR_{status}")
        print(f"[FAIL] Device open failed: {error_msg} (status={status})")
        
        if status == 3:
            print("\n  Possible causes:")
            print("  - Device is already opened by another program")
            print("  - Multiple instances of your app are running")
            print("  - Check Task Manager for other python.exe processes")
        elif status == 2:
            print("\n  Possible causes:")
            print("  - Device not connected")
            print("  - USB cable issue")
            print("  - Device powered off")
        elif status == 4:
            print("\n  Possible causes:")
            print("  - USB connection unstable")
            print("  - Bad USB cable")
            print("  - USB port power issue")
            print("  - Try different USB port")
        
        return False

def continuous_monitor(ftd2xx, duration=30):
    """Monitor device connection continuously."""
    print("\n" + "=" * 60)
    print(f"Continuous Monitoring ({duration} seconds)")
    print("=" * 60)
    print("Watching for device connection changes...")
    print("Press Ctrl+C to stop\n")
    
    _ft_create_list = ftd2xx.FT_CreateDeviceInfoList
    _ft_create_list.argtypes = [ctypes.POINTER(ctypes.c_ulong)]
    _ft_create_list.restype = ctypes.c_ulong
    
    last_count = -1
    start_time = time.time()
    
    try:
        while time.time() - start_time < duration:
            count = ctypes.c_ulong()
            status = _ft_create_list(ctypes.byref(count))
            
            if status == 0 and count.value != last_count:
                timestamp = time.strftime("%H:%M:%S")
                if count.value > last_count and last_count >= 0:
                    print(f"[{timestamp}] Device CONNECTED (count: {last_count} → {count.value})")
                elif count.value < last_count:
                    print(f"[{timestamp}] Device DISCONNECTED (count: {last_count} → {count.value})")
                else:
                    print(f"[{timestamp}] Devices detected: {count.value}")
                last_count = count.value
            
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
    
    print(f"\nFinal device count: {last_count}")

def main():
    """Run all diagnostics."""
    print("\n")
    print("=" * 60)
    print("CX-505 FTDI Device Diagnostic Tool")
    print("=" * 60)
    print()
    
    # Step 1: Check DLL
    ftd2xx = check_ftdi_dll()
    if not ftd2xx:
        print("\n[FAIL] Cannot proceed without FTDI D2XX DLL")
        input("\nPress Enter to exit...")
        return 1
    
    # Step 2: Enumerate devices
    device_count = enumerate_devices(ftd2xx)
    if device_count == 0:
        print("\n[FAIL] No FTDI devices found!")
        print("\nTroubleshooting:")
        print("1. Check USB cable is connected")
        print("2. Check device is powered on")
        print("3. Try different USB port")
        print("4. Check Device Manager for FTDI device")
        print("5. Reinstall FTDI drivers if needed")
        input("\nPress Enter to exit...")
        return 1
    
    # Step 3: Test opening device
    can_open = test_device_open(ftd2xx, 0)
    
    # Step 4: Continuous monitoring
    if can_open:
        print("\n[OK] Device is working!")
        print("\nWould you like to monitor for connection stability? (30 seconds)")
        response = input("Monitor? (y/n): ").lower()
        if response == 'y':
            continuous_monitor(ftd2xx, duration=30)
    else:
        print("\n[FAIL] Device cannot be opened")
        print("\nRunning quick stability check (10 seconds)...")
        continuous_monitor(ftd2xx, duration=10)
    
    # Summary
    print("\n" + "=" * 60)
    print("Diagnostic Summary")
    print("=" * 60)
    print(f"[OK] FTDI DLL: Loaded")
    print(f"[OK] Devices Found: {device_count}")
    print(f"[{'OK' if can_open else 'FAIL'}] Device Open: {'Success' if can_open else 'Failed'}")
    print()
    
    if can_open:
        print("[OK] Device appears to be working correctly")
        print("\nNext steps:")
        print("1. Close this diagnostic tool")
        print("2. Click 'Reset' in the launcher to restart services")
        print("3. The device should now be detected")
    else:
        print("[FAIL] Device has connection issues")
        print("\nNext steps:")
        print("1. Close ALL Python processes (check Task Manager)")
        print("2. Unplug and replug the USB cable")
        print("3. Try a different USB port (preferably USB 2.0)")
        print("4. Run this diagnostic again")
        print("5. If still failing, reinstall FTDI drivers")
    
    input("\nPress Enter to exit...")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n[FAIL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)
