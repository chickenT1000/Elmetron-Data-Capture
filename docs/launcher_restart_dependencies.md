# Launcher launcher restart dependency map

## Current flow overview

- The Tk main thread owns all UI widgets, status labels, and the auto-close timer.  All UI updates must be scheduled via `root.after`.
- A single background worker thread (`threading.Thread(target=self._launch_sequence, daemon=True)`) performs the launch pipeline so the UI stays responsive.
- `_launch_sequence` executes the service bootsteps sequentially, updating the UI by calling `_set_status`, and exits when both services are online or when an unrecoverable error occurs.
- When the happy path completes, `_schedule_auto_close` arranges for the window to close 1.5 s later while allowing the user to abort closure via `WM_DELETE_WINDOW`.

## External prerequisites

| Dependency | Where it is resolved | Notes |
| --- | --- | --- |
| Python interpreter | `sys.executable` | Used to spawn `cx505_capture_service.py`; assumes virtualenv/environment already active.
| `npm` executable | `shutil.which("npm")` | Mandatory for the UI server (`npm run dev`). Failure raises immediately.
| Directories | `captures/` (created if missing) | Stores combined stdout/stderr logs for both child processes.
| Config files | `config/app.toml`, `config/protocols.toml` | Passed to capture service when spawning the Python process.
| Network ports | `8050` (health API), `5173` (UI dev server) | Checked via HTTP GET loops to block until services are reachable.

## Process lifecycle

1. **Capture service**
   - Command: `[sys.executable, cx505_capture_service.py, --config, --protocols, --health-api-port 8050, --watchdog-timeout 30, --health-log]`.
   - Stdout/stderr streamed into `captures/live_ui_dev.log` and `captures/live_ui_dev.err.log` (handles stored in `_log_files`).
   - `CREATE_NO_WINDOW` prevents extra console windows on Windows.
   - Health check: `_wait_for_url(HEALTH_URL, …)` polls `/health` up to 40 times (1 s sleep). If the process dies early, the exit code is recorded and the launch fails.

2. **UI dev server**
   - `npm run dev -- --host 127.0.0.1 --port 5173 --strictPort` spawned with environment variables that point the UI at the health API.
   - Stdout/stderr logged to `captures/live_ui_dev_ui.log` and `captures/live_ui_dev_ui.err.log`.
   - On first run, `node_modules/` is bootstrap-installed inside `ui/`.
   - Availability gated on `_wait_for_url(UI_URL, …)`.

3. **Browser kick-off**
   - `webbrowser.open(UI_URL)` launches the default browser once both services are healthy.

## Shared state and clean-up duties

- `_processes`: dictionary keyed by `'capture'` and `'ui'` storing the `subprocess.Popen` objects that must be terminated during shutdown or failure.
- `_log_files`: list of open file handles that must be closed before the launcher exits.
- `_auto_close_job`: keeps track of the pending `root.after` auto-close callback so failures can cancel it.
- `_ellipsis_job`: repeated UI animation job that must be cancelled before switching status text.

### Normal completion

1. `_schedule_auto_close` arms the close timer.
2. `_close_success` cancels outstanding jobs, writes one more log entry, closes files, and destroys the Tk root.

### Error handling path (`_fail`)

1. Cancels auto-close, stops ellipsis animation, sets UI colour to error.
2. Records the error in the in-memory log buffer and pops an `ErrorDialog` via `root.after` to keep UI thread safe.
3. Child processes remain running until the user closes the dialog; `_cleanup` is invoked during `WM_DELETE_WINDOW`.

### Manual window close (`_on_close`)

1. Cancels auto-close if present, stops animation, records intent to log.
2. Calls `_cleanup` to close log files.
3. Destroys root without touching child processes (intentional: services keep running for operators).

## Considerations for restart support

| Area | Existing behaviour | Considerations before introducing restart |
| --- | --- | --- |
| Thread model | Only one worker thread ever runs (`_launch_sequence`). | A restart routine must avoid spawning concurrent workers. All follow-on work should be queued onto the Tk thread via `root.after`.
| Process ownership | Child PIDs tracked inside `_processes`. | Restart must synchronously terminate both entries before spawning replacements. Blocking waits should run outside the Tk thread.
| Log file handles | Persist in `_log_files` until `_cleanup` is invoked. | Restart should close and reopen handles to prevent file descriptor leaks and to avoid log interleaving across sessions.
| Auto-close timer | Armed on successful launch to exit the GUI. | Restart should cancel this timer and keep the launcher window open while services cycle.
| Status updates | `_set_status` manipulates UI labels directly (must run on main thread). | Any restart queue should centralise status transitions to avoid race conditions with background threads.
| Browser launch | Always fires after both services start. | Decide whether restart should reopen the browser or rely on already-open tab; add guard to prevent repeated launches.
| Failure dialogs | `_fail` shows a modal dialog containing the log buffer. | Restart flow should honour the same dialog path for partial failures (e.g., capture restarts but UI fails).

## Suggested restart sequence (based on current dependencies)

1. Disable interactive controls (`Start`, `Stop`, future `Restart`) and cancel existing timers/animations on the Tk thread.
2. Spawn a background worker to:
   - call `_terminate_processes(update_ui=True)`
   - wait for both child processes to exit (with timeout/kill fallback)
   - call `_cleanup_logs()`
3. Once the teardown completes, `root.after` should schedule a fresh `_start_services` run and re-enable the controls when it reports success.
4. Any failure during restart should funnel through `_handle_failure` so the existing UI error surfaces are reused.

Capturing these dependencies up front should keep future tickets focused on discrete changes (e.g., button wiring, state machine refactor) without rediscovering the underlying launch contract each time.
