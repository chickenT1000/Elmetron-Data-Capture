"""Quick patch to fix Reset button hanging issue."""
import re

# Read the launcher file
with open('launcher.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern to find and replace the terminate logic
old_pattern = r'''(\s+)self\._log\(f"Stopping \{name\} \(pid \{pid\}\)\."\)
(\s+)if process\.poll\(\) is None:
(\s+)process\.terminate\(\)
(\s+)try:
(\s+)process\.wait\(timeout=10\)'''

new_code = r'''\1self._log(f"Stopping {name} (pid {pid})...")
\2if process.poll() is None:
\3# Force-kill UI server immediately (Vite/Node is slow on Windows)
\3if name == "ui":
\4self._log(f"Force-killing UI server...")
\4process.kill()
\4timeout = 2
\3else:
\4process.terminate()
\4timeout = 5
\3
\3try:
\4process.wait(timeout=timeout)'''

# Apply the patch
content_new = re.sub(old_pattern, new_code, content, count=1)

if content_new != content:
    # Backup original
    with open('launcher.py.backup', 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Write patched version
    with open('launcher.py', 'w', encoding='utf-8') as f:
        f.write(content_new)
    
    print("[OK] Patch applied successfully!")
    print("   - UI server will be force-killed immediately")
    print("   - Reduced timeouts: UI=2s, others=5s")
    print("   - Backup saved to launcher.py.backup")
else:
    print("[WARN] Pattern not found - may already be patched or structure changed")
