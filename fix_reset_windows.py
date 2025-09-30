"""Replace process termination with Windows taskkill for instant killing."""

with open('launcher.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the _terminate_processes method with Windows-optimized version
old_method = '''    def _terminate_processes(self) -> List[str]:
        errors: List[str] = []
        for name, process in list(self._processes.items()):
            try:
                # Verify process object is valid
                pid = getattr(process, 'pid', None)
                if pid is None:
                    self._log(f"Skipping {name}: invalid process object.")
                    self._processes.pop(name, None)
                    continue
                
                self._log(f"Stopping {name} (pid {pid})...")
                if process.poll() is None:
                    # Force-kill UI server immediately (Vite/Node is slow on Windows)
                    if name == "ui":
                        self._log(f"Force-killing UI server...")
                        process.kill()
                        timeout = 2
                    else:
                        process.terminate()
                        timeout = 5
                    
                    try:
                        process.wait(timeout=timeout)
                    except subprocess.TimeoutExpired:
                        self._log(f"{name} did not exit in time; forcing kill...")
                        process.kill()
                        try:
                            process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            errors.append(f"{name} process did not exit after kill().")
                exit_code = process.poll()
                self._log(f"{name} stopped with code {exit_code}.")
            except OSError as exc:
                errors.append(f"Failed to terminate {name}: {exc}")
            finally:
                self._processes.pop(name, None)
        self._close_logs()
        return errors'''

new_method = '''    def _terminate_processes(self) -> List[str]:
        """Terminate all managed processes using Windows taskkill for instant kill."""
        errors: List[str] = []
        for name, process in list(self._processes.items()):
            try:
                # Verify process object is valid
                pid = getattr(process, 'pid', None)
                if pid is None:
                    self._log(f"Skipping {name}: invalid process object.")
                    self._processes.pop(name, None)
                    continue
                
                # Check if already dead
                if process.poll() is not None:
                    self._log(f"{name} (pid {pid}) already exited.")
                    self._processes.pop(name, None)
                    continue
                
                self._log(f"Force-killing {name} (pid {pid}) using taskkill...")
                
                # Use Windows taskkill to force-kill process tree immediately
                # /F = force, /T = tree (kill children too), /PID = process ID
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(pid)],
                        capture_output=True,
                        timeout=2,
                        creationflags=CREATE_NO_WINDOW
                    )
                    self._log(f"{name} force-killed successfully.")
                except subprocess.TimeoutExpired:
                    self._log(f"WARNING: taskkill timed out for {name}")
                except Exception as e:
                    self._log(f"WARNING: taskkill failed for {name}: {e}")
                
                # Don't wait - just mark as done
                self._processes.pop(name, None)
                
            except Exception as exc:
                self._log(f"Error terminating {name}: {exc}")
                errors.append(f"Failed to terminate {name}: {exc}")
                self._processes.pop(name, None)
        
        self._close_logs()
        
        # Give OS a moment to clean up
        time.sleep(0.5)
        
        return errors'''

if old_method in content:
    content = content.replace(old_method, new_method)
    with open('launcher.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("[OK] Replaced termination logic with Windows taskkill!")
    print("     - Uses taskkill /F /T for instant process tree kill")
    print("     - No more waiting/blocking")
    print("     - Reset should complete in ~1-2 seconds")
else:
    print("[WARN] Could not find method to replace - may need manual edit")
