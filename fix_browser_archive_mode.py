"""Fix browser reopen to work in archive mode (no capture service)."""

with open('launcher.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix _reopen_browser to check data_api instead of capture service
old_code = '''        # Check if processes are actually alive
        capture_alive = "capture" in self._processes and self._processes["capture"].poll() is None
        ui_alive = "ui" in self._processes and self._processes["ui"].poll() is None
        
        if not capture_alive or not ui_alive:
            self._log("[Browser] Cannot reopen browser - service processes not responding")
            missing = []
            if not capture_alive:
                missing.append("capture service")
            if not ui_alive:
                missing.append("UI server")'''

new_code = '''        # Check if processes are actually alive
        # In archive mode, capture service may not be running - check Data API + UI only
        data_api_alive = "data_api" in self._processes and self._processes["data_api"].poll() is None
        ui_alive = "ui" in self._processes and self._processes["ui"].poll() is None
        
        if not data_api_alive or not ui_alive:
            self._log("[Browser] Cannot reopen browser - service processes not responding")
            missing = []
            if not data_api_alive:
                missing.append("Data API service")
            if not ui_alive:
                missing.append("UI server")'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('launcher.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("[OK] Fixed browser reopen for archive mode")
    print("     - Now checks Data API + UI (not capture service)")
    print("     - Works in both archive and live modes")
else:
    print("[WARN] Could not find code to fix")
