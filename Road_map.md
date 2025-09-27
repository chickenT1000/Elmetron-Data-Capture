# Road Map

## Completed
- Added `--quiet` flag and status handler in `cx505_d2xx.py` to separate diagnostics from data output.
- Introduced `startup_commands` support in configuration and acquisition service to execute protocol commands at session start.
- Updated capture CLI, README, and protocol docs to describe the workflow; added pytest coverage for startup command handling.
- Verified builds with `python -m compileall` and tests via `python -m pytest`.
- Implemented scheduled command execution with retries/backoff, calibration tagging, and audit logging across config, acquisition service, and tests.
- Added analytics engine with derived metric persistence and multi-format exports (CSV/JSON/XML/PDF) plus regression coverage.
- Bundled default export templates in `config/templates/` and refreshed operator/service documentation to reference the new workflow guidance.
- Implemented `--archive` export bundling with summary metadata for distribution workflows.
- Added `scripts/build_release_bundle.py` to automate archive generation for release workflows.
- Documented log rotation scheduling and release automation workflow (docs/WINDOWS_SERVICE_GUIDE.md, docs/RELEASE_AUTOMATION.md).
- Published Sprint 4 release notes and operator/service quick-reference documentation.
- Surfaced `/health` log rotation diagnostics in the Service Health UI with live polling.
- Added /health/logs endpoint and wired the Service Health UI event stream to show live audit events.
- Extended Service Health UI with watchdog timeline and command queue metrics.
- Implemented `/health/logs/stream` SSE delivery with automatic fallback messaging and UI connection status chips.
- Surfaced diagnostic bundle manifest summaries in the Service Health UI and introduced jsdom-based Vitest coverage for the new components.
- Added diagnostic bundle downloads in the Service Health UI, exposing the `/health/bundle` support archive endpoint.

## Next Up
- BLE transport validation on hold until a Bluetooth-capable meter is available; revisit scheduling when hardware is secured.
- Integrate Service Health UI manifest summaries with backend diagnostics API and expand Vitest coverage beyond component scope.

## Risks & Dependencies
- FTDI D2XX drivers remain mandatory for local testing.
- Asynchronous command execution now shares the device handle with analytics; monitor long-running metrics jobs to avoid starving capture windows.
- Accurate protocol registry entries remain critical; validation tooling still needed to catch malformed command definitions.
- Advanced exports (PDF templating, LIMS schemas) may require additional third-party libraries and packaging review.





