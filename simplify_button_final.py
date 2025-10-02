"""Simplify reopen browser button - user's excellent suggestion!"""

with open('launcher.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find _reopen_browser method
start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if 'def _reopen_browser(self)' in line:
        start_idx = i
    elif start_idx is not None and line.strip().startswith('def ') and 'self' in line:
        end_idx = i
        break

if start_idx and end_idx:
    # Replace with simple version
    new_method = '''    def _reopen_browser(self) -> None:
        """Reopen the browser tab with the UI dashboard."""
        # Simple: button is only enabled when UI is ready, so just open browser
        self._log("[Browser] Reopening dashboard in browser...")
        try:
            webbrowser.open(UI_URL)
            self.status_rows["browser"].set("Dashboard opened", STATUS_PALETTE["success"])
            self._browser_opened = True
            self._log("[Browser] Dashboard opened successfully")
        except Exception as e:
            self._log(f"[Browser] Failed to open dashboard: {e}")
            messagebox.showerror("Browser Error", f"Failed to open browser:\\\\n\\\\n{e}")
    
    def _update_button_states(self) -> None:
        """Update button enabled/disabled state based on service state."""
        # Check if UI is actually responding
        ui_ready = False
        try:
            if self._state == LauncherState.RUNNING and "ui" in self._processes:
                ui_process = self._processes["ui"]
                if ui_process.poll() is None:  # Process still running
                    # Quick check if UI is responding
                    with urllib.request.urlopen(UI_URL, timeout=1) as response:
                        ui_ready = 200 <= response.getcode() < 300
        except Exception:
            ui_ready = False
        
        # Enable/disable Reopen Browser button
        try:
            if ui_ready:
                self.reopen_browser_button.config(state="normal")
            else:
                self.reopen_browser_button.config(state="disabled")
        except Exception:
            pass  # Button may not exist yet during init

'''
    
    lines = lines[:start_idx] + [new_method] + lines[end_idx:]
    
    with open('launcher.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("[OK] Simplified 'Reopen Browser' button (user's suggestion!)") 
    print("")
    print("Before: Complex validation + error dialogs")
    print("After:  Gray button when not ready, simple click when ready")
    print("")
    print("Now need to call _update_button_states() periodically...")
    print("Let me add that next...")
else:
    print("[ERROR] Could not find _reopen_browser method")
