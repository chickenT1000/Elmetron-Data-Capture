# Sprint 4 Release Notes

## Highlights
- Bundled export templates (`config/templates/session_report.fmt`, `config/templates/session_lims.xml.fmt`) are now active defaults in `config/app.toml`.
- Operator, service, and Windows deployment guides updated to cover template-driven exports, calibration tooling, and service-account/log-retention requirements.
- Added archive bundling (`--archive`) with summary JSON, manifest metadata, and optional checksums for downstream distribution.
- Published an operator/service quick-reference sheet for shift handovers (`docs/QUICK_REFERENCE.md`).
- `/health` now reports scheduled log-rotation status when `[monitoring]` is configured, closing the service-ops follow-up.

## Documentation Package
- `docs/OPERATOR_PLAYBOOK.md` details full operating procedures.
- `docs/WINDOWS_SERVICE_GUIDE.md` outlines service install, account preparation, log rotation, update, and troubleshooting steps.
- `docs/EXPORT_TEMPLATES.md` explains template anatomy, supported placeholders, and customisation workflow.
- `docs/QUICK_REFERENCE.md` provides the condensed checklist distributed with this release.

## Publication Checklist
- [x] Finalise quick-reference sheet for operators and service engineers.
- [x] Summarise template customisation guidance in the release bundle.
- [x] Align Windows-service deployment notes with customer-specific account permissions and log retention policies.

## Known Follow-ups
- Export automation: adopt `scripts/build_release_bundle.py` in CI to publish archive bundles (see `docs/EXPORT_ARCHIVE_PLAN.md`).
- BLE transport: validation deferred until Bluetooth-capable meter hardware is available.
- Testing: extend watchdog/exporter end-to-end scenarios post-release.

