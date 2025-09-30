"""Simplify 'Reopen Browser' button - just enable/disable based on UI state."""

with open('launcher.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the complex _reopen_browser with a simple version
old_reopen = '''    def _reopen_browser(self) -> None:
        """Reopen the browser tab with the UI dashboard."""
        if self._state != LauncherState.RUNNING:
            self._log("[Browser] Cannot reopen browser - service not running")
            messagebox.showwarning(
                "Service Not Running",
                "The capture service must be running to open the dashboard.\\n\\nPlease click 'Start' first."
            )
            return
        
        # Check if processes are actually alive
        # In archive mode, capture service may not be running - check Data API + UI only
        data_api_alive = "data_api" in self._processes and self._processes["data_api"].poll() is None
        ui_alive = "ui" in self._processes and self._processes["ui"].poll() is None
        
        if not data_api_alive or not ui_alive:
            self._log("[Browser] Cannot reopen browser - service processes not responding")
            missing = []
            if not data_api_alive:
                missing.append("Data API service")
            if not ui_alive:
                missing.append("UI server")
            
            messagebox.showerror(
                "Service Error",
                f"The {' and '.join(missing)} stopped unexpectedly.\\n\\n"
                "Please click 'Stop' to clean up, then 'Start' to restart services."
            )
            return
        
        # Check if UI is actually responding
        try:
            with urllib.request.urlopen(UI_URL, timeout=2) as response:
                if not (200 <= response.getcode() < 300):
                    self._log(f"[Browser] UI server returned status {response.getcode()}")
                    messagebox.showwarning(
                        "UI Not Ready",
                        f"The UI server is not responding properly (HTTP {response.getcode()}).\\n\\n"
                        "Please wait a moment or try clicking 'Reset'."
                    )
                    return
        except Exception as e:
            self._log(f"[Browser] Cannot reach UI server: {e}")
            messagebox.showerror(
                "UI Not Accessible",
                f"The UI server is not accessible at {UI_URL}.\\n\\n"
                f"Error: {e}\\n\\n"
                "Please click 'Reset' to restart services."
            )
            return
        
        self._log("[Browser] Reopening dashboard in browser...")
        try:
            webbrowser.open(UI_URL, new=0, autoraise=True)
            self.status_rows["browser"].set("Dashboard opened", STATUS_PALETTE["success"])
            self._browser_opened = True
            self._log("[Browser] Dashboard opened successfully")
        except Exception as e:
            self._log(f"[Browser] Failed to open browser: {e}")
            messagebox.showerror("Browser Error", f"Failed to open browser:\\n\\n{e}")'''

new_reopen = '''    def _reopen_browser(self) -> None:
        """Reopen the browser tab with the UI dashboard."""
        # Button should only be enabled when UI is ready, so just open browser
        self._log("[Browser] Reopening dashboard in browser...")
        try:
            webbrowser.open(UI_URL, new=0, autoraise=True)
            self.status_rows["browser"].set("Dashboard opened", STATUS_PALETTE["success"])
            self._browser_opened = True
            self._log("[Browser] Dashboard opened successfully")
        except Exception as e:
            self._log(f"[Browser] Failed to open browser: {e}")
            messagebox.showerror("Browser Error", f"Failed to open browser:\\n\\n{e}")
    
    def _update_button_states(self) -> None:
        """Update button enabled/disabled state based on current service state."""
        # Check if UI is actually responding
        ui_ready = False
        try:
            if self._state == LauncherState.RUNNING and "ui" in self._processes:
                ui_process = self._processes["ui"]
                if ui_process.poll() is None:  # Process is running
                    # Quick check if UI is responding
                    with urllib.request.urlopen(UI_URL, timeout=1) as response:
                        ui_ready = 200 <= response.getcode() < 300
        except Exception:
            ui_ready = False
        
        # Enable/disable Reopen Browser button based on UI state
        if ui_ready:
            self.reopen_browser_button.config(state="normal")
        else:
            self.reopen_browser_button.config(state="disabled")'''

if old_reopen in content:
    content = content.replace(old_reopen, new_reopen)
    
    # Also update _transition_to to call _update_button_states
    old_transition_end = '''        self._state = new_state
        self._log(f"[State] => {new_state.name}")'''
    
    new_transition_end = '''        self._state = new_state
        self._log(f"[State] => {new_state.name}")
        # Update button states when state changes
        try:
            self._update_button_states()
        except Exception:
            pass  # Don't let button state update crash state transition'''
    
    if old_transition_end in content:
        content = content.replace(old_transition_end, new_transition_end)
    
    with open('launcher.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("[OK] Simplified 'Reopen Browser' button!")
    print("")
    print("Changes:")
    print("  - Removed all validation logic from button click")
    print("  - Button just opens browser (no error dialogs)")
    print("  - Added _update_button_states() method")
    print("  - Button grayed out when UI not ready")
    print("  - Button enabled when UI is responding")
    print("")
    print("User experience:")
    print("  - Gray button = UI not ready (can't click)")
    print("  - Active button = UI ready (click to open)")
    print("  - No confusing error messages!")
else:
    print("[WARN] Could not find code to replace")
