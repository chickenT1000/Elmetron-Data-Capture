# Operator Playbook

## Prerequisites
- Install FTDI D2XX drivers and confirm the CX-505 enumerates in Device Manager (USB Serial Converter).
- Review `config/app.toml` for the correct `device.index`, database path, and `acquisition.startup_commands`/`scheduled_commands`.
- Keep `captures/` and `exports/` directories on the workstation; create date-stamped subfolders per session.
- Place any custom protocol profiles in `config/protocols.toml` and validate with `python validate_protocols.py config/protocols.toml` before use.

## Daily Startup Checklist
1. Connect the CX-505 and verify the display shows the target measurement mode (pH, conductivity, O2, etc.).
2. Double-click `start.bat` in the project root to open the Elmetron Launch Monitor. It starts the capture service, launches the Service Health UI, and opens the dashboard once both are healthy.
3. Wait for the monitor to show "All services online", then click **OK** to close it. (If automation fails, fall back to the manual commands listed in Appendix A.)
4. Confirm the Service Health > Overview card reports `status=running` and `watchdog=healthy`.
5. Verify the first session appears in `data/elmetron.sqlite` (table `sessions`) using `sqlite3`, DB Browser, or the dashboard's Recent Sessions list.
6. Record the session identifier in the lab logbook.

## Handshake & Poll Reference
- The CX-505 expects the canonical poll handshake `01 23 30 23 30 23 30 23 03`. The capture service writes it once on connect and then every second.
- Quick sanity check:
```bash
py -3 cx505_d2xx.py --serial <SERIAL> --baud 115200 --databits 8 --stopbits 1 --parity E --duration 10 --write-hex "01 23 30 23 30 23 30 23 03" --poll-hex "01 23 30 23 30 23 30 23 03" --json
```
  Decoded frames appearing immediately confirm the handshake succeeded. Use `--hex` when you only need byte-level output.
- Instrument must be streaming: clear faults (for example `Error1` when the pH probe is missing) or switch to a measurement mode such as REDOX before polling.
- Either `stop_bits = 2.0` (profile default) or `--stop-bits 1` works once the device is healthy; only toggle the override while diagnosing cabling or firmware quirks.
## Scheduled Commands & Calibrations
- Startup commands defined in `acquisition.startup_commands` execute automatically once the device connects; monitor stdout for `startup_command=<name> completed` events.
- The default workstation config leaves `[[acquisition.scheduled_commands]]` empty so operators choose when to calibrate; use the CLI to run calibrations on demand.
- When schedules are required, add `[[acquisition.scheduled_commands]]` entries and verify next-run times in the console or the `audit_events` table.
- Trigger calibrations on-demand with `python trigger_calibration.py` (interactive selection) or `python trigger_calibration.py --command <name> --yes`; use `run_protocol_command.py` for lower-level command execution when required.

## Monitoring & Analytics Exports
- Keep `python cx505_capture_service.py --health-api-port 8050 --health-log` running; `/health` powers the dashboard widgets and CLI diagnostics.
- Export the latest session immediately after measurements:
- With `[monitoring]` enabled, verify `/health.log_rotation.status` reads `ok` (or check Service Health > Log Rotation). `stale`/`failed` means the Windows scheduled task needs attention.
- Service Health > Event Log Stream shows capture/calibration events. The status chip indicates Streaming (green), Polling fallback (amber), or Stream error (red). Polling continues refreshing every 5 s and raises a warning until SSE reconnects.
- Use the Event Log Stream Refresh button or filters (`level`, `category`) for tailored snapshots; download the raw feed via `/health/logs.ndjson` when QA needs archives.
- Service Health > Command Queue provides "Download Diagnostic Bundle" (from `/health/bundle`) plus queue depth history - capture this bundle before escalating issues.
- Watch the Watchdog Timeline and Interface Lock cards for timeouts or lock contention before restarting hardware.
- The Analytics Profile card highlights frame throughput, throttling, and processing times - investigate spikes before approving datasets.
- Session Evaluation (UI) lets operators compare overlays, view calibration markers, and export PNG/JSON artifacts for sign-off.
- Retention sweeps log `category=retention` events; review payloads for deleted sessions and archive them with the rest of the audit trail.
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

### Live Telemetry Dashboard Quick Reference
- **Dashboard**: Real-time frames/bytes, watchdog status, interface lock metrics, recent sessions.
- **Service Health**: Event Log Stream (SSE + NDJSON fallback), command queue metrics, diagnostic bundle download, log rotation state, retention alerts.
- **Session Evaluation**: Overlay charts, calibration markers, measurement analytics, PNG/JSON export toolbar.
- **Log Filters**: Apply level/category filters or pull `/health/logs.ndjson` for offline review.
- **Retention Log**: Automated purges write to the "Retention log" session; include its audit entries when handing off QA evidence.

### Bench Harness & Live Test Aids
- Dry-run captures with `config/bench_harness.toml` (`transport = "sim"`) before touching live hardware.
- Execute `python scripts/run_bench_harness.py --config config/live_rehearsal.toml --protocols config/protocols.toml --database data/live_rehearsal.sqlite --health-port 8052 --watchdog-timeout 10 --window 2 --idle 1` for rehearsal runs; monitor `captures/live_ui_harness.log` and `/health` snapshots.
- Follow `docs/CX505_BENCH_HARNESS.md` for simulation details and `docs/CX505_LIVE_TEST_CHECKLIST.md` for acceptance criteria and archival expectations.
- Capture health snapshots (`Invoke-WebRequest http://127.0.0.1:8052/health`) and database summaries (`scripts/_temp_db_summary_ui.py`) to validate rehearsal results before production sign-off.

## Appendix A: Manual startup fallback
- Run `python cx505_capture_service.py --config config/app.toml --protocols config/protocols.toml --health-api-port 8050 --watchdog-timeout 30 --health-log`.
- Launch the dashboard with `cd ui && set VITE_API_BASE_URL=http://127.0.0.1:8050 && npm run dev -- --host 127.0.0.1 --port 5173`.
- Open `http://127.0.0.1:5173/` in a browser once the `/health` endpoint returns `state = "running"`.

## Shutdown Procedure
1. Use `Ctrl+C` in the capture console; wait for `ServiceRunner` to report `shutdown=complete`.
2. Disconnect probes and rinse per SOP.
3. Archive the day's `captures/<date>` directory and exported reports to the lab share.

## Troubleshooting Checklist
- **No frames after connect**: Ensure the meter display is not showing fault codes (attach the probe or switch to REDOX), then resend the poll handshake with the low-level CLI above. If traffic resumes only with `--stop-bits 1`, leave that override in place for the session and log the behaviour for maintenance.
- **No device detected**: Re-seat USB, check Device Manager, and rerun `python cx505_capture_service.py --list-devices`.
- **Session stalls**: Look for watchdog warnings; if present, restart the service and confirm startup commands are not blocking. Review `audit_events` for failing scheduled commands.
- **Invalid data**: Open raw frames from `captures/<date>/raw.log` and compare with protocol expectations. Re-run calibration commands and confirm buffer values.
- **Export errors**: Ensure the `exports/` subfolder exists and that PDF support libraries are installed. Re-run exporter with `--formats csv json` to isolate the failing format.
- **Configuration mismatch**: Validate TOML files with `python validate_protocols.py` and double-check `transport`/`poll_hex` fields.








