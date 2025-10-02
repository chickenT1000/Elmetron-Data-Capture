"""Add periodic button state updates."""

with open('launcher.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add button state update to _transition_to
old_transition = '''    def _transition_to(self, state: LauncherState) -> None:
        self._state = state
        self._update_controls()'''

new_transition = '''    def _transition_to(self, state: LauncherState) -> None:
        self._state = state
        self._update_controls()
        # Update button states when state changes
        self._post(lambda: self._update_button_states())'''

if old_transition in content:
    content = content.replace(old_transition, new_transition)
    print("[OK] Added button state update to _transition_to()")
else:
    print("[WARN] Could not find _transition_to()")

# Add periodic button state check during RUNNING
# Find the run method
old_run = '''        self.root.mainloop()'''
new_run = '''        # Start periodic button state updates
        self._schedule_button_update()
        self.root.mainloop()'''

if old_run in content:
    content = content.replace(old_run, new_run)
    print("[OK] Added periodic button update scheduling")
else:
    print("[WARN] Could not find mainloop()")

# Add the scheduler method after _update_button_states
old_method_end = '''            pass  # Button may not exist yet during init

    def _do_start(self) -> None:'''

new_method_end = '''            pass  # Button may not exist yet during init

    def _schedule_button_update(self) -> None:
        """Schedule periodic button state updates."""
        try:
            self._update_button_states()
        except Exception:
            pass
        # Check every 2 seconds
        self.root.after(2000, self._schedule_button_update)

    def _do_start(self) -> None:'''

if old_method_end in content:
    content = content.replace(old_method_end, new_method_end)
    print("[OK] Added _schedule_button_update() method")
else:
    print("[WARN] Could not add scheduler method")

with open('launcher.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("")
print("Summary:")
print("  - Button state updates on state transitions")
print("  - Periodic check every 2 seconds")
print("  - Button grays out when UI crashes")
print("  - Button re-enables when UI recovers")
