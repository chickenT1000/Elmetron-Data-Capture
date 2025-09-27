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
- Integrated `scripts/build_release_bundle.py` with the CI workflow to publish artefacts after successful tests.
- Added interface lock monitoring with analytics profiling and per-minute frame rate limits.
- Implemented auto profile fallback on repeated decode failures in the acquisition layer.
- Surfaced command metrics history and response-time telemetry in the health API.
- Added `/health/logs.ndjson` endpoint with filtering for integrations and contracted SSE tests for `/health/logs/stream`.
- Connected the dashboard to live health telemetry with NDJSON log fallback, loading states, and Vitest coverage for new hooks.
- Delivered session evaluation overlays with calibration alignment, JSON/PNG exports, and supporting API endpoints.
- Enhanced lab retry configuration for startup/scheduled commands with richer error diagnostics and expanded tests.
- Introduced schema migration with overlay/session comparison indexes and migration tests.
- Implemented protocol definition validator CLI with detailed rule checks and automated coverage.
- Created live rehearsal configuration (`config/live_rehearsal.toml`) and bench harness script updates to support CX-505 hardware runs.
- Executed CX-505 live rehearsal capture, archived health snapshot/database summary artifacts, and validated watchdog/telemetry stability.
- Authored CX-505 live test checklist documenting setup, acceptance criteria, and post-run archival steps.

## Work plan by area

### 1. Hardware & acquisition layer
| Priority | Task | Notes |
| --- | --- | --- |
| High | Expand startup/scheduled command test scenarios with detailed error reporting and automatic retry in the lab configuration | Completed |
| Medium | Prepare a fallback procedure to switch CX-505 profiles when malformed frames are detected | Completed |
| High | Assemble CX-505 bench test harness with full telemetry logging and watchdog monitoring | Completed |
| High | Execute end-to-end CX-505 rehearsal capture using lab buffers and record validation artifacts | Completed |

### 2. Ingestion, analytics & export
| Priority | Task | Notes |
| --- | --- | --- |
| High | Extend the analytics pipeline with performance profiling and per-minute frame rate limits | Completed |
| Medium | Implement a protocol definition validator (`validate_protocols.py`) with operator-facing reporting | Completed |
| Medium | Add JSON/CSV exports for new derived metrics (temperature compensation) | Keeps reports consistent with UI analytics |

### 3. Health API & diagnostics
| Priority | Task | Notes |
| --- | --- | --- |
| High | Extend `/health` with response-time metrics and historical command queue load data | Completed |
| Medium | Add an endpoint for fetching recent logs in NDJSON format for service integrations | Completed |
| Medium | Cover SSE scenarios (heartbeat intervals, reconnects) with contract tests | Completed |

### 4. Data persistence & SQLite
| Priority | Task | Notes |
| --- | --- | --- |
| High | Introduce a schema migration that adds indexes supporting overlay and session comparison queries | Completed |
| Medium | Implement an automated retention report (data removed) and write outputs to `audit_events` | Increases transparency for QA and auditors |
| Low | Evaluate SQLCipher integration with a proof-of-concept encryption flow | Optional path for regulated deployments |

### 5. Documentation & operational materials
| Priority | Task | Notes |
| --- | --- | --- |
| High | Update `docs/OPERATOR_PLAYBOOK.md` with the new UI views and diagnostic tooling | Should follow completion of the UI integration |
| Medium | Add a "Troubleshooting export bundles" guide to `docs/EXPORT_ARCHIVE_PLAN.md` | Captures common packaging failure modes |
| Low | Produce a short instructional video covering the Service Health Dashboard | Useful onboarding asset for new operators |
| Medium | Draft CX-505 live test procedure checklist and capture acceptance criteria | Completed |

### 6. User interface
| Priority | Task | Notes |
| --- | --- | --- |
| High | Connect the dashboard to live endpoints (telemetry, logs, manifest) with full loading/error state management | Completed |
| High | Implement the Session Evaluation screen with overlay alignment and PNG/JSON export options | Completed |
| Medium | Add component tests (Vitest + RTL) and configure Playwright smoke tests | Vitest coverage added for API/hooks; Playwright automation pending |
| Low | Introduce kiosk/Electron packaging and offline operation | Targeted for post-MVP deployments |





