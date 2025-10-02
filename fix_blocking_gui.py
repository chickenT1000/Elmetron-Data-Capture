"""Fix GUI blocking by running termination in background thread."""

with open('launcher.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace _do_stop to run in background thread
old_do_stop = '''    def _do_stop(self) -> None:
        if not self._processes and not self._logs:
            self._log("Services already stopped (no active resources).")
            self._mark_idle_statuses()
            self._transition_to(LauncherState.IDLE)
            return
        self._transition_to(LauncherState.STOPPING)
        self._set_status("system", "Stopping services...", "waiting")
        
        # Stop data monitoring
        self._stop_data_monitoring()
        
        # Log resource state before cleanup for debugging
        self._log_resource_state()
        
        errors = self._terminate_processes()
        if errors:
            for error in errors:
                self._log(f"ERROR: {error}")
            self._set_status("system", "Stop completed with errors", "error")
            self._transition_to(LauncherState.FAILED)
        else:
            self._mark_idle_statuses()
            self._set_status("system", "Services stopped", "pending")
            self._transition_to(LauncherState.IDLE)'''

new_do_stop = '''    def _do_stop(self) -> None:
        if not self._processes and not self._logs:
            self._log("Services already stopped (no active resources).")
            self._mark_idle_statuses()
            self._transition_to(LauncherState.IDLE)
            return
        
        # Run termination in background thread to avoid blocking GUI
        def stop_thread():
            try:
                self._post(lambda: self._transition_to(LauncherState.STOPPING))
                self._post(lambda: self._set_status("system", "Stopping services...", "waiting"))
                
                # Stop data monitoring
                self._stop_data_monitoring()
                
                # Log resource state before cleanup for debugging
                self._log_resource_state()
                
                errors = self._terminate_processes()
                
                # Update UI from background thread using _post
                if errors:
                    for error in errors:
                        self._log(f"ERROR: {error}")
                    self._post(lambda: self._set_status("system", "Stop completed with errors", "error"))
                    self._post(lambda: self._transition_to(LauncherState.FAILED))
                else:
                    self._post(lambda: self._mark_idle_statuses())
                    self._post(lambda: self._set_status("system", "Services stopped", "pending"))
                    self._post(lambda: self._transition_to(LauncherState.IDLE))
            except Exception as e:
                self._log(f"ERROR in stop thread: {e}")
                self._post(lambda: self._set_status("system", f"Stop failed: {e}", "error"))
                self._post(lambda: self._transition_to(LauncherState.FAILED))
        
        threading.Thread(target=stop_thread, daemon=True).start()'''

if old_do_stop in content:
    content = content.replace(old_do_stop, new_do_stop)
    print("[OK] Fixed _do_stop to run in background thread")
else:
    print("[WARN] Could not find _do_stop method")

# Replace _do_reset to run in background thread
old_do_reset = '''    def _do_reset(self) -> None:
        self._log("Executing reset: stop then start.")
        was_running = self._state == LauncherState.RUNNING
        
        # Force cleanup regardless of current state
        self._do_stop()
        
        # Check if stop succeeded
        if self._state not in {LauncherState.IDLE, LauncherState.FAILED}:
            self._log("Reset aborted; stop did not complete cleanly.")
            return
        
        # Force cleanup of any lingering resources if in failed state
        if self._state == LauncherState.FAILED:
            self._log("Forcing resource cleanup after failed state.")
            self._force_cleanup()
        
        # Wait for ports to be freed before restarting'''

new_do_reset = '''    def _do_reset(self) -> None:
        self._log("Executing reset: stop then start.")
        
        # Run reset in background thread to avoid blocking GUI
        def reset_thread():
            try:
                # Stop phase
                self._post(lambda: self._transition_to(LauncherState.STOPPING))
                self._post(lambda: self._set_status("system", "Stopping services...", "waiting"))
                
                # Stop data monitoring
                self._stop_data_monitoring()
                self._log_resource_state()
                
                errors = self._terminate_processes()
                if errors:
                    for error in errors:
                        self._log(f"ERROR during stop: {error}")
                
                # Force cleanup if needed
                self._force_cleanup()
                
                # Wait for ports to be freed before restarting'''

if old_do_reset in content:
    content = content.replace(old_do_reset, new_do_reset)
    
    # Now add the restart logic
    old_restart_part = '''        # Wait for ports to be freed before restarting
        self._log("Waiting for service ports to be freed...")
        if not self._wait_for_ports_freed():
            self._log("WARNING: Some ports may still be in use")
        else:
            self._log("Ports freed, restarting services...")
        
        # Restart
        self._do_start()'''
    
    new_restart_part = '''                
                # Wait for ports to be freed before restarting
                self._log("Waiting for service ports to be freed...")
                if not self._wait_for_ports_freed():
                    self._log("WARNING: Some ports may still be in use")
                else:
                    self._log("Ports freed, restarting services...")
                
                # Restart on GUI thread
                self._post(lambda: self._do_start())
                
            except Exception as e:
                self._log(f"ERROR in reset thread: {e}")
                self._post(lambda: self._set_status("system", f"Reset failed: {e}", "error"))
                self._post(lambda: self._transition_to(LauncherState.FAILED))
        
        threading.Thread(target=reset_thread, daemon=True).start()'''
    
    if old_restart_part in content:
        content = content.replace(old_restart_part, new_restart_part)
        print("[OK] Fixed _do_reset to run in background thread")
    else:
        print("[WARN] Could not find reset restart part")
else:
    print("[WARN] Could not find _do_reset method")

# Write back
with open('launcher.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("")
print("Summary:")
print("  - Stop button now runs termination in background thread")
print("  - Reset button now runs termination in background thread")
print("  - GUI stays responsive during shutdown")
print("  - Uses _post() to update UI from background thread safely")
