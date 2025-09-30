"""Final comprehensive fix for launcher.py termination logic."""

with open('launcher.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the entire problematic section with correct version
old_section = '''                self._log(f"Stopping {name} (pid {pid})...")
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
                        self._log(f"{name} did not exit in time; forcing termination.")
                        process.kill()
                        try:
                            process.wait(timeout=5)'''

new_section = '''                self._log(f"Stopping {name} (pid {pid})...")
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
                            process.wait(timeout=3)'''

if old_section in content:
    content = content.replace(old_section, new_section)
    with open('launcher.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("[OK] Final fix applied!")
    print("   - UI server: force-killed immediately (2s wait)")
    print("   - Other services: graceful terminate first (5s wait)")
    print("   - Reduced final kill timeout to 3s")
else:
    print("[INFO] Section not found - manual fix may be needed")
