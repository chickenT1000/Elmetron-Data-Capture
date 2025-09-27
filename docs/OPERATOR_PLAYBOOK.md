# Operator Playbook

## Prerequisites
- Install FTDI D2XX drivers and confirm the CX-505 enumerates in Device Manager (USB Serial Converter).
- Review `config/app.toml` for the correct `device.index`, database path, and `acquisition.startup_commands`/`scheduled_commands`.
- Keep `captures/` and `exports/` directories on the workstation; create date-stamped subfolders per session.
- Place any custom protocol profiles in `config/protocols.toml` and validate with `python validate_protocols.py config/protocols.toml` before use.

## Daily Startup Checklist
1. Connect the CX-505 and verify the display shows the target measurement mode (pH, conductivity, O2, etc.).
2. Run `python cx505_capture_service.py --config config/app.toml --protocols config/protocols.toml --health-api-port 8050 --watchdog-timeout 30 --health-log`.
3. Wait for `ServiceRunner` to report `status=running` and `watchdog=healthy` (displayed on stdout unless `--quiet` is active).
4. Confirm the first session appears in `data/elmetron.sqlite` (table `sessions`) using `sqlite3` or DB Browser for SQLite.
5. Record the session identifier in the lab logbook.

## Scheduled Commands & Calibrations
- Startup commands defined in `acquisition.startup_commands` execute automatically once the device connects; monitor stdout for `startup_command=<name> completed` events.
- The default workstation config leaves `[[acquisition.scheduled_commands]]` empty so operators choose when to calibrate; use the CLI to run calibrations on demand.
- When schedules are required, add `[[acquisition.scheduled_commands]]` entries and verify next-run times in the console or the `audit_events` table.
- Trigger calibrations on-demand with `python trigger_calibration.py` (interactive selection) or `python trigger_calibration.py --command <name> --yes`; use `run_protocol_command.py` for lower-level command execution when required.

## Monitoring & Analytics Exports
- Use `python cx505_capture_service.py --health-api-port 8050 --health-log` to keep watchdog updates in the console; the `/health` endpoint returns JSON status for dashboards.
- Export the latest session immediately after measurements:
- With `[monitoring]` enabled, verify `/health.log_rotation.status` reads `ok` (or check the Service Health > Log Rotation card). `stale` or `failed` indicates the Windows scheduled task needs attention.
- Review the Service Health > Event Log Stream card to confirm capture/calibration events arrive; the status chip shows Streaming (green), Polling fallback (amber), or Stream error (red). When the stream falls back to polling the list continues updating every 5 seconds and the UI raises a warning until SSE reconnects.
- Use the Event Log Stream refresh button when you need an immediate snapshot; it queries /health/logs on demand regardless of the streaming state.
- Click the Service Health > Command Queue "Download Diagnostic Bundle" button to save a support archive (health snapshot, recent events, config) generated from `/health/bundle`.
- Check the Service Health > Watchdog Timeline card for recent timeouts/recoveries before restarting hardware.
```powershell
python -m elmetron.reporting.exporters export-session --session <ID> --formats csv json pdf --outdir exports/$(Get-Date -Format 'yyyyMMdd_HHmm')
```
- Add `--csv-mode full` when you need payload/analytics JSON columns for diagnostics.
- Use `--latest 1`, `--sessions <ID ...>`, or `--session-range <start> <end>` to batch-export multiple sessions in one invocation.
- Pass `--gzip` (optionally `--gzip-level 9`) when archiving or shipping datasets offsite.
- Manifests (`<prefix>_manifest.json`) and checksum lists (`<prefix>_sha256.txt`) are written automatically; customise with `--manifest-name` / `--checksum-name` or disable via `--no-manifest` / `--no-checksums`.
- Capture configuration fingerprints when needed by passing `--config` / `--protocols`; override manifest identity with `--manifest-tool-name` / `--manifest-version`.
- Use `--archive` to produce a zip bundle and review `<prefix>_archive_summary.json` for distribution metadata before sharing datasets.
- Default templates live under `config/templates/`. Update `export.pdf_template` / `export.lims_template` in `config/app.toml` or pass overrides per export when you customise `docs/EXPORT_TEMPLATES.md` samples.
- Add `--pdf-template <path>` or `--lims-template <path>` when operators need custom PDF/XML layouts.
- Inspect CSV/JSON files for derived metrics (stability indices, compensated values) before sharing with LIMS or QA.

## Shutdown Procedure
1. Use `Ctrl+C` in the capture console; wait for `ServiceRunner` to report `shutdown=complete`.
2. Disconnect probes and rinse per SOP.
3. Archive the day's `captures/<date>` directory and exported reports to the lab share.

## Troubleshooting Checklist
- **No device detected**: Re-seat USB, check Device Manager, and rerun `python cx505_capture_service.py --list-devices`.
- **Session stalls**: Look for watchdog warnings; if present, restart the service and confirm startup commands are not blocking. Review `audit_events` for failing scheduled commands.
- **Invalid data**: Open raw frames from `captures/<date>/raw.log` and compare with protocol expectations. Re-run calibration commands and confirm buffer values.
- **Export errors**: Ensure the `exports/` subfolder exists and that PDF support libraries are installed. Re-run exporter with `--formats csv json` to isolate the failing format.
- **Configuration mismatch**: Validate TOML files with `python validate_protocols.py` and double-check `transport`/`poll_hex` fields.






