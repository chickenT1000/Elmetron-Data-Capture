"""Complete fix for _do_reset indentation and threading."""
import re

with open('launcher.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find _do_reset method and rewrite it completely
in_reset = False
reset_start = None
reset_end = None

for i, line in enumerate(lines):
    if 'def _do_reset(self) -> None:' in line:
        reset_start = i
        in_reset = True
    elif in_reset and line.strip() and not line.startswith(' ') and not line.startswith('\t'):
        # Found start of next top-level item
        reset_end = i
        break
    elif in_reset and line.strip().startswith('def ') and 'self' in line:
        # Found next method
        reset_end = i
        break

if reset_start is not None and reset_end is not None:
    # Replace entire _do_reset method
    new_reset = '''    def _do_reset(self) -> None:
        """Reset services by stopping and restarting them."""
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
                
                # Terminate processes gracefully
                errors = self._terminate_processes()
                if errors:
                    for error in errors:
                        self._log(f"ERROR during stop: {error}")
                
                # Force cleanup if needed
                self._force_cleanup()
                
                # Wait for ports to be freed before restarting
                self._log("Waiting for service ports to be freed...")
                self._wait_for_port_free(8050, max_wait=15)  # Data API
                self._wait_for_port_free(8051, max_wait=15)  # Capture Service
                self._wait_for_port_free(5173, max_wait=15)  # UI Server
                self._log("Ports freed, restarting services...")
                
                # Reset to IDLE and restart on GUI thread
                self._post(lambda: self._transition_to(LauncherState.IDLE))
                self._post(lambda: self._set_initial_statuses())
                self._post(lambda: self._do_start())
                
            except Exception as e:
                self._log(f"ERROR in reset thread: {e}")
                self._post(lambda: self._set_status("system", f"Reset failed: {e}", "error"))
                self._post(lambda: self._transition_to(LauncherState.FAILED))
        
        threading.Thread(target=reset_thread, daemon=True).start()

'''
    
    # Replace the method
    lines = lines[:reset_start] + [new_reset] + lines[reset_end:]
    
    with open('launcher.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("[OK] Completely rewrote _do_reset method")
    print("     - Runs in background thread")
    print("     - GUI stays responsive")
    print("     - Proper graceful shutdown")
else:
    print("[ERROR] Could not find _do_reset method boundaries")
