"""Fix the run() method indentation and duplicates."""

with open('launcher.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix lines 975-976 - they need 12 spaces (inside try block)
# And remove duplicate line 975
if len(lines) > 977:
    # Line 975 (index 974) - duplicate, should be removed OR properly indented
    # Line 976 (index 975) - mainloop, needs proper indent
    # Line 977 (index 976) - finally, correct
    
    # Check if line 975 is the duplicate schedule call
    if 'self._schedule_button_update()' in lines[974] and lines[974].strip() == 'self._schedule_button_update()':
        # Remove duplicate
        del lines[974]
        print("[OK] Removed duplicate _schedule_button_update() call")
    
    # Now check mainloop indentation (should be at index 974 after deletion, or 975 if no deletion)
    for i in range(974, 977):
        if 'self.root.mainloop()' in lines[i]:
            # Should have 12 spaces (inside try block)
            lines[i] = '            self.root.mainloop()\n'
            print(f"[OK] Fixed mainloop() indentation at line {i+1}")
            break
    
    with open('launcher.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("[OK] Fixed run() method!")
else:
    print("[ERROR] File shorter than expected")
