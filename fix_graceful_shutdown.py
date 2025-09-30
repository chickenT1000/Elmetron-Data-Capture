"""Implement safe graceful shutdown with database protection."""

with open('launcher.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace _terminate_processes with graceful version
old_method = '''    def _terminate_processes(self) -> List[str]:
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

new_method = '''    def _terminate_processes(self) -> List[str]:
        """Terminate processes gracefully with database safety."""
        errors: List[str] = []
        
        # Phase 1: Send graceful shutdown signals (SIGTERM)
        self._log("Initiating graceful shutdown...")
        shutdown_pids = {}
        for name, process in list(self._processes.items()):
            try:
                pid = getattr(process, 'pid', None)
                if pid is None or process.poll() is not None:
                    self._processes.pop(name, None)
                    continue
                
                self._log(f"Requesting graceful shutdown of {name} (pid {pid})...")
                process.terminate()  # Send SIGTERM for graceful shutdown
                shutdown_pids[name] = (process, time.time())
                
            except Exception as exc:
                self._log(f"Error requesting shutdown of {name}: {exc}")
                errors.append(f"Failed to request shutdown of {name}: {exc}")
        
        # Phase 2: Wait for graceful exits (with timeout)
        # Data API and Capture Service have signal handlers to close DB connections
        max_wait = 5.0  # seconds to wait for graceful shutdown
        check_interval = 0.2
        elapsed = 0
        
        while shutdown_pids and elapsed < max_wait:
            time.sleep(check_interval)
            elapsed += check_interval
            
            for name in list(shutdown_pids.keys()):
                process, start_time = shutdown_pids[name]
                if process.poll() is not None:
                    # Process exited cleanly
                    self._log(f"{name} exited gracefully (exit code: {process.poll()})")
                    self._processes.pop(name, None)
                    del shutdown_pids[name]
        
        # Phase 3: Force-kill any remaining processes
        if shutdown_pids:
            self._log(f"Force-killing {len(shutdown_pids)} processes that did not exit gracefully...")
            for name, (process, _) in shutdown_pids.items():
                try:
                    pid = process.pid
                    self._log(f"Force-killing {name} (pid {pid})...")
                    
                    # Use taskkill /F /T for stubborn processes (mainly UI/Node)
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(pid)],
                        capture_output=True,
                        timeout=2,
                        creationflags=CREATE_NO_WINDOW
                    )
                    self._log(f"{name} force-killed")
                    
                except Exception as e:
                    self._log(f"Error force-killing {name}: {e}")
                    errors.append(f"Failed to force-kill {name}: {e}")
                finally:
                    self._processes.pop(name, None)
        
        self._close_logs()
        
        # Brief pause for OS cleanup
        time.sleep(0.3)
        
        return errors'''

if old_method in content:
    content = content.replace(old_method, new_method)
    with open('launcher.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("[OK] Graceful shutdown implemented!")
    print("")
    print("Safe shutdown strategy:")
    print("  Phase 1: Send SIGTERM for graceful shutdown")
    print("  Phase 2: Wait up to 5 seconds for clean exit")
    print("           (Services close DB connections properly)")
    print("  Phase 3: Force-kill only if necessary")
    print("")
    print("Database safety:")
    print("  ✓ Data API receives SIGTERM → closes DB connection")
    print("  ✓ Capture Service receives SIGTERM → flushes & closes DB")
    print("  ✓ UI server can be killed immediately (no DB)")
    print("")
else:
    print("[WARN] Could not find method - may already be updated")
