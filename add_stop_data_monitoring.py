"""Add missing _stop_data_monitoring method."""

with open('launcher.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find where to insert the method (right before _terminate_processes)
insert_index = None
for i, line in enumerate(lines):
    if 'def _terminate_processes(self)' in line:
        insert_index = i
        break

if insert_index:
    # Insert the new method
    new_method = '''    def _stop_data_monitoring(self) -> None:
        """Stop data monitoring thread if active."""
        if hasattr(self, '_data_monitor_active'):
            self._data_monitor_active = False
        if hasattr(self, '_data_monitor_thread') and self._data_monitor_thread:
            # Thread will exit when it sees _data_monitor_active = False
            try:
                self._data_monitor_thread.join(timeout=2)
            except Exception:
                pass

'''
    lines.insert(insert_index, new_method)
    
    with open('launcher.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("[OK] Added _stop_data_monitoring method")
    print(f"     Inserted at line {insert_index + 1}")
else:
    print("[ERROR] Could not find _terminate_processes method")
