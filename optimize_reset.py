"""Optimize Reset to be faster - skip long port waits."""

with open('launcher.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the port waiting in reset with shorter timeout
old_reset_wait = '''                # Wait for ports to be freed before restarting
                self._log("Waiting for service ports to be freed...")
                self._wait_for_port_free(8050, max_wait=15)  # Data API
                self._wait_for_port_free(8051, max_wait=15)  # Capture Service
                self._wait_for_port_free(5173, max_wait=15)  # UI Server
                self._log("Ports freed, restarting services...")'''

new_reset_wait = '''                # Wait briefly for ports to be freed before restarting
                self._log("Waiting for service ports to be freed...")
                # Shorter waits - processes already terminated gracefully
                self._wait_for_port_free(8050, max_wait=3)  # Data API
                self._wait_for_port_free(8051, max_wait=3)  # Capture Service  
                self._wait_for_port_free(5173, max_wait=3)  # UI Server
                self._log("Restarting services...")'''

if old_reset_wait in content:
    content = content.replace(old_reset_wait, new_reset_wait)
    with open('launcher.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("[OK] Optimized Reset - reduced port wait from 15s to 3s per port")
    print("     - Total max wait: 9 seconds instead of 45 seconds")
    print("     - Services already exited gracefully, ports should free quickly")
    print("     - If port still busy, we continue anyway (new process will retry)")
else:
    print("[WARN] Could not find reset wait section to optimize")
