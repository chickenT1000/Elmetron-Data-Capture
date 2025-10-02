"""Fix indentation in launcher.py _terminate_processes method."""

with open('launcher.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and fix the indentation issues around line 775-780
fixed_lines = []
fixing = False

for i, line in enumerate(lines):
    # Detect the problematic section
    if 'if name == "ui":' in line and 'self._log(f"Force-killing' in lines[i+1] and not lines[i+1].startswith('                        '):
        fixing = True
        fixed_lines.append(line)
        continue
    
    if fixing:
        # Fix lines that need proper indentation (should have 24 spaces = 6 levels of 4-space indent)
        if 'self._log(f"Force-killing' in line or 'process.kill()' in line or 'timeout = 2' in line:
            # Add 4 more spaces
            fixed_lines.append('    ' + line)
        elif 'else:' in line and not line.strip().startswith('#'):
            fixed_lines.append(line)
        elif 'process.terminate()' in line or 'timeout = 5' in line:
            # Add 4 more spaces
            fixed_lines.append('    ' + line)
        elif 'try:' in line and fixing:
            # Add 4 more spaces
            fixed_lines.append('    ' + line)
        elif 'process.wait(timeout=timeout)' in line and fixing:
            # Add 8 more spaces (inside try block)
            fixed_lines.append('        ' + line)
            fixing = False  # Done fixing
        else:
            fixed_lines.append(line)
    else:
        fixed_lines.append(line)

# Write back
with open('launcher.py', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print("[OK] Fixed indentation in launcher.py")
print("The Reset button should now work without hanging!")
