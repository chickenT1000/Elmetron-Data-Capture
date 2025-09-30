"""Fix critical indentation bug in launcher.py run() method."""

with open('launcher.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the run() method and fix indentation
fixed = False
for i in range(len(lines)):
    # Look for the problematic section
    if i < len(lines) - 5:
        if ('def run(self) -> None:' in lines[i] and
            'try:' in lines[i+1] and
            '# Start periodic button state updates' in lines[i+2]):
            
            # Fix the indentation - lines after try: should be indented
            lines[i+2] = '            # Start periodic button state updates\n'  # Inside try
            lines[i+3] = '            self._schedule_button_update()\n'  # Inside try
            # Remove duplicate lines
            if 'self._schedule_button_update()' in lines[i+4]:
                lines[i+4] = ''  # Remove duplicate
            if '# Start periodic button state updates' in lines[i+4]:
                lines[i+4] = ''  # Remove duplicate comment
            if 'self.root.mainloop()' in lines[i+5]:
                lines[i+5] = '            self.root.mainloop()\n'  # Inside try
            elif 'self.root.mainloop()' in lines[i+4]:
                lines[i+4] = '            self.root.mainloop()\n'  # Inside try
            
            fixed = True
            break

if fixed:
    # Remove empty lines created by removing duplicates
    lines = [line for line in lines if line.strip() or line == '\n']
    
    with open('launcher.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("[OK] Fixed indentation in run() method!")
    print("     - Indented code inside try block")
    print("     - Removed duplicate lines")
else:
    print("[ERROR] Could not find the problematic section")
