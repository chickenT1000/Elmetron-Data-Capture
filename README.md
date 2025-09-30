
# Elmetron Data Acquisition and Analysis Suite

This project modernises Elmetron CX-505 data capture by replacing the legacy S457s tooling with a modular, scriptable stack that spans transport, decoding, persistence, analytics, and reporting.

## Architecture Overview
- **Hardware (`elmetron.hardware`)** - wraps the FTDI D2XX bridge and optional BLE adapters, drives DTR/RTS control, and injects poll/handshake sequences from the protocol registry.
- **Acquisition (`elmetron.acquisition`)** - supervises capture windows, reconnection, startup/scheduled command execution, and audit logging.
- **Ingestion (`elmetron.ingestion`)** - decodes CX-505 frames into structured measurements, enriches metadata, and records decode failures for diagnostics.
- **Storage (`elmetron.storage`)** - maintains the SQLite schema (instruments, sessions, raw frames, measurements, derived metrics, annotations, audit events).
- **Protocols (`elmetron.protocols`)** - loads profile registries (TOML/JSON/YAML), validates command definitions, and normalises device defaults.
- **Service Runtime (`elmetron.service`)** - hosts the capture supervisor, watchdog, health API, and Windows-service wrapper utilities.
- **Reporting (`elmetron.reporting`)** - streams session data, runs analytics/export pipelines, and exposes CLI tooling for CSV/JSON/XML/PDF outputs.

Configuration lives under `config/`, capture artefacts go to `captures/`, and exports are written to `exports/`.

## Quick Start
1. Install the FTDI D2XX drivers and confirm the CX-505 appears in Device Manager.
2. Adjust `config/app.toml` for the workstation (device index, database path, startup/scheduled commands) and validate custom profiles with `python validate_protocols.py config/protocols.toml`.
3. Launch continuous capture:
```bash
python cx505_capture_service.py \
  --config config/app.toml \
  --protocols config/protocols.toml \
  --watchdog-timeout 30 \
  --health-log \
  --health-api-port 8050
```
   The supervisor opens the transport, applies the selected profile, executes startup commands, and streams raw frames plus analytics into `data/elmetron.sqlite`.
4. Monitor `/health` (port 8050 by default) or the console watchdog output for status updates.
   `/health/logs/stream` provides a Server-Sent Events feed for audit entries; the operator UI automatically falls back to `/health/logs` polling and surfaces a warning when streaming is unavailable.
5. Export captured sessions with the reporting CLI (see Export Toolkit) and use `run_protocol_command.py` or `trigger_calibration.py` for ad-hoc protocol commands and calibration routines.

## Operational Guides
- `docs/OPERATOR_PLAYBOOK.md` - daily startup checklist, scheduled command monitoring, analytics exports, and troubleshooting steps for lab technicians.
- `docs/WINDOWS_SERVICE_GUIDE.md` - Windows service deployment using NSSM or PyWin32, log routing, account permissions, and restart procedures.
- `docs/EXPORT_TEMPLATES.md` - overview of the bundled PDF/LIMS templates and guidance for customising placeholders.
- `docs/UI_DESIGN_SYSTEM.md` - technology stack, theming, and component strategy for the operator UI.
- `docs/RELEASE_AUTOMATION.md` - CI/CD checklist for publishing exporter bundles.
- The Service Health dashboard exposes `/health/logs/stream` plus a one-click diagnostic bundle download (`/health/bundle`) for support escalations.

### Important Operational Notes
?? **Always stop services gracefully** - Never use `Stop-Process -Force` on the capture service as it can corrupt the SQLite database. Use the UI Stop button or `Ctrl+C` in terminal.

?? **Before Git operations** - Stop capture service and React dev server before switching branches to avoid file lock conflicts.

?? **Troubleshooting** - See `TROUBLESHOOTING.md` for common issues and solutions, and `FIXES_SUMMARY.md` for historical fixes.

## Export Toolkit
- Use `python scripts/build_release_bundle.py --latest 1` to generate release-ready archives (manifest, checksums, and zipped artefacts).
- Drive exports via `python -m elmetron.reporting.exporters export-session --session <ID> --formats csv json xml pdf --outdir exports/<stamp>` (swap `--session` for `--sessions`, `--session-range`, or `--latest N` when batch processing).
- Compact CSV exports are enabled by default (`export.csv_mode = "compact"`); use `--csv-mode full` to retain the raw JSON payload/analytics columns when needed.
- Pass `--gzip` (and optionally `--gzip-level`) to emit compressed `.gz` artefacts for archival transfers.
- Each export run writes a manifest (`<prefix>_manifest.json`) and checksum list (`<prefix>_sha256.txt`) covering all artefacts; customise with `--manifest-name` / `--checksum-name` or disable via `--no-manifest` / `--no-checksums`.
- Supply `--config` / `--protocols` to embed configuration fingerprints and override manifest metadata via `--manifest-tool-name` / `--manifest-version` when packaging archives.
- Add `--archive` to emit a zip containing the artefacts plus manifest/checksum, with `*_archive_summary.json` capturing checksum metadata for pipelines.
- Default templates live in `config/templates/`; adjust `export.pdf_template` / `export.lims_template` or supply overrides via CLI flags (see `docs/EXPORT_TEMPLATES.md` for field references).
- Use `--pdf-template` / `--lims-template` with `.tmpl` (string.Template) or `.jinja` files to render custom PDF/XML layouts; omit the flags to fall back to built-in summaries.

## Development Notes
- UI integration plan tracked in `docs/UI_INTEGRATION_PLAN.md`; see it for backend/API milestones.
- Configuration dataclasses live in `elmetron.config`; use `AppConfig.from_dict()` for custom loaders and `AppConfig.to_dict()` when emitting diagnostics.
- Archive manifest automation plan lives in `docs/EXPORT_ARCHIVE_PLAN.md` for pipeline integration work.
- Run `python -m compileall elmetron cx505_capture_service.py` and `python -m pytest` before committing to catch syntax and regression issues.
- Analytics controls (the `analytics` section in `config/app.toml`) tune moving averages, stability windows, and temperature compensation; derived metrics persist alongside each measurement and propagate into exports.
- CSV behaviour honours the `export.csv_*` options, while PDF/LIMS exports read optional templates (`export.pdf_template`, `export.lims_template`).
- Hardware runs require the FTDI D2XX runtime; BLE adapters can be enabled through the transport factory once compatible hardware is available.

### Front-end workflow
- Design tokens live in `ui/tokens.json` and are consumed by the MUI theme, global styles, and component contracts for measurement/dashboard widgets.
- Start the Storybook component lab with `npm run storybook` (from `ui/`); the baseline stories cover typography plus `MeasurementPanel`, `CommandHistory`, `LogFeed`, and the full dashboard composition.
- Run `npm run test:ui` to execute Playwright component screenshot tests and ensure visual diffs stay within the checked-in baselines.
- Publish the current Storybook to Chromatic with `npm run chromatic` (requires `CHROMATIC_PROJECT_TOKEN`), or let the `UI Visual Checks` workflow handle it in CI.






