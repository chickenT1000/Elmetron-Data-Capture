# Repository Guidelines

## Project Structure & Module Organization
`elmetron/` mirrors the architecture described in SPEC.md:
- `elmetron/hardware/device_manager.py` handles the FTDI CX-505 link layer.
- `elmetron/acquisition/service.py` orchestrates capture windows, reconnect logic, session metadata, and audit logging.
- `elmetron/ingestion/pipeline.py` decodes frames, enriches metadata, and surfaces decode failures.
- `elmetron/storage/database.py` owns the SQLite schema (instruments, sessions, metadata, raw frames, measurements, annotations, audit events).
- `elmetron/protocols/registry.py` loads profile registries (`config/protocols.toml`); see `docs/PROTOCOLS.md` for the schema.
- `elmetron/api/` and `elmetron/service/` provide the health monitor, watchdog, supervisor, runner, and console/Windows-service stubs.
- `elmetron/reporting/session.py` streams session summaries and measurements for exports/dashboards.
Support scripts live at the root (`cx505_d2xx.py`, `cx505_capture_service.py`, `probe_commands.py`). Config files live in `config/`; capture/export artifacts belong in `captures/` and `exports/`.

## Build, Test, and Development Commands
- `python cx505_capture_service.py --list-devices` validates D2XX visibility.
- `python cx505_capture_service.py --config config/app.toml --protocols config/protocols.toml --watchdog-timeout 30 --health-api-port 8050 --health-log` runs the acquisition supervisor with watchdog logging and the `/health` endpoint.
- `python run_protocol_command.py --config config/app.toml --protocols config/protocols.toml calibrate_ph7` fires a command/calibration sequence defined in the active profile.
- `python -c "from elmetron.reporting.exporters import export_session_csv; export_session_csv(Path('data/elmetron.sqlite'), 1, Path('exports/session1.csv'))"` exports a session snapshot for quick analysis.
- `python elmetron/service/windows_service.py --config config/app.toml --protocols config/protocols.toml --watchdog-timeout 30 --health-api-port 8050` exercises the forthcoming Windows-service wrapper from the console.
- `python -m compileall elmetron cx505_capture_service.py` performs a quick syntax check.
Add richer tests with `pytest` under `tests/` once suites are stubbed.

## Coding Style & Naming Conventions
Follow PEP 8 with type hints on public APIs. Keep modules `snake_case`; export symbols via `__all__`. Document non-obvious protocol constants and schema changes with concise comments. Avoid embedding meter-specific values outside the protocol registry.

## Testing Guidelines
Adopt `pytest`. Minimum coverage: (1) `FrameIngestor.handle_frame` with synthetic frames and failure cases, (2) storage retention/audit logic using in-memory SQLite, (3) watchdog/supervisor/health API behaviour via mocked `AcquisitionService` stats. For hardware-dependent tests, inject fakes through `ServiceRunner`.

## Commit & Pull Request Guidelines
Use conventional commits (`feat:`, `fix:`, `refactor:`). PRs should summarise scope, record manual validation (`python cx505_capture_service.py ...`), attach relevant JSON/SQLite excerpts, and mention driver prerequisites. Document schema migrations and protocol registry updates explicitly.



