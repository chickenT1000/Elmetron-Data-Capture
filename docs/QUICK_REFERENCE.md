# Operator & Service Quick Reference

Use this sheet during daily operations with the Elmetron capture stack.

## Operator: Start of Shift
- Connect the CX-505 via USB and set the intended measurement mode before starting software.
- Launch the capture service:
  `python cx505_capture_service.py --config config/app.toml --protocols config/protocols.toml --health-api-port 8050 --watchdog-timeout 30 --health-log`
- Confirm the console reports `status=running`; note the session ID written to `data/elmetron.sqlite`.
- Trigger calibrations only when required via `python trigger_calibration.py` (prompts for the specific protocol command).

## Operator: During Session
- Monitor the live dashboard (or service log) for alarms or watchdog resets.
- Use `Ctrl+C` in the service shell to end a run; the session closes automatically and exports remain available.
- Restart the service if you change meter mode or reconnect USB after faults.
- Use the Service Health > Command Queue "Download Diagnostic Bundle" to grab a zipped support archive before escalating issues.

## Operator: Export & Reporting
- Default templates live in `config/templates/`; `config/app.toml` points to `session_report.fmt` (PDF) and `session_lims.xml.fmt` (XML).
- For ad hoc exports, run:
  `python -m elmetron.reporting.exporters export-session --latest 1 --formats csv pdf xml --gzip --outdir exports/<stamp>`
- Manifests and checksums are enabled by default; add `--no-manifest --no-checksums` to suppress them.
- Add `--config` / `--protocols` to stamp manifest metadata with file checksums, or override the tool identity via `--manifest-tool-name` / `--manifest-version`.
- Append `--archive` to bundle outputs as a zip with a summary JSON for downstream delivery.

## Service Engineering
- Run Windows services under a dedicated account (for example `elmetron_svc`) with modify access to `C:\Elmetron`, `captures`, `exports`, and `logs`.
- Point NSSM/stdout logging at `C:\Elmetron\logs\capture.log` and schedule rotation (see `docs/WINDOWS_SERVICE_GUIDE.md`; use `scripts/rotate_logs.ps1`) to keep ~30 days of history.
- After configuration updates, restart the Windows service and rerun any required calibration commands.
- Configure `[monitoring]` in `config/app.toml` to surface the log rotation task status via `/health` (`log_rotation.status`).
- Validate protocol TOML files with `python validate_protocols.py` before deployment.

## Status & Follow-ups
- BLE transport validation remains on hold until Bluetooth-capable hardware arrives.
- Archive automation enhancements (manifests, packaging) will continue post-release.
- Report issues or escalation needs through the ops Slack channel or `ops@elmetron.local`.

