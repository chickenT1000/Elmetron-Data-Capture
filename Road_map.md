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
| High | Monitor live CX-505 session after bottleneck removal; track `/health` frames/bytes growth (session 17) | Latest check 2025-09-27: frames 154, bytes 15338 |
| Medium | Add FTDI device open retry/back-off logic in harness/service to recover from stale handles | Pending |
| Medium | Ensure clean FTDI handle shutdown and add pre-flight process checks before launching harness | Completed (auto-close + harness process guard 2025-09-27) |

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
| High | Ship graphical launch monitor guide in `docs/OPERATOR_PLAYBOOK.md` | Completed (`start.bat`, Launch Monitor, Appendix A fallback) |
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
| High | Build Windows launch monitor GUI for non-technical operators | Completed (`launcher.py` with status dashboard) |
| High | Investigate live Service Health UI connectivity failures (intermittent 404/stale data during harness runs) | Completed (CORS headers + launcher/env fixes 2025-09-27) |
| High | Keep Service Health UI available post-bottleneck fix; run dev server at 127.0.0.1:5173 with `VITE_API_BASE_URL=http://127.0.0.1:8050` | Live check 2025-09-27 confirmed UI load |
| High | Resume live CX-505 testing after PC reboot (relaunch harness, verify /health, reconnect UI) | Urgent next session startup |
| High | Surface live CX-505 measurements on the landing view | Replace the current connectivity-first layout with primary readouts for pH/Redox/Conductivity/Solution temperature, updating in real time from the active session. |
| High | Add 10-minute rolling charts beneath the live readouts | Auto-refresh plots for each measured channel; continue plotting even when a channel has no frames (gap visualization). |
| High | Auto-start continuous session recording on launch | Ensure measurement logging begins immediately; provide context so users know recording is live without manual action. |
| High | Enable adjustable chart scales and time axes | Allow users to tune vertical ranges per channel and switch between absolute timestamps and local clock labels. |
| Medium | Show live connectivity indicator for CX-505 | Present a green icon (with tooltip) when instrument link is healthy, so operators confirm streaming status immediately. |
| Medium | Display autosave status indicator | Reuse the connectivity-style icon to confirm session logging is active; provide hover text describing autosave behaviour. |
| Medium | Provide interactive export tooling for sessions | Default to the active session, allow picking historical sessions, and select channel subsets for export (pH, Redox, Conductivity, Temp). |
| Medium | Add graphical time-range selection to exports | Let users crop the export window via chart brushing plus manual start/end timestamps; reflect selected range in previews. |
| Medium | Support multiple export formats (CSV, PNG charts, etc.) | Offer CSV for data tables and PNG (possibly PDF/SVG) renders for charts; respect channel choices and time range selections. |
| Medium | Annotate mode transitions across the UI | Persist data for all channels and mark intervals where a channel was inactive (e.g., mode switches), both in live view and exports. |
| High | Add session timeline notes with chart annotations | Allow users to drop timestamped notes (up to 400 chars) that render as numbered pointers beneath the time axis, showing a short label while full text lives in a notes log; notes can be scheduled in the future and are stored with the session. |
| High | Sync notes into session data at creation/edition time | Every note addition or edit should be written immediately to the session record so exports and downstream tools capture the updated metadata. |
| High | Freeze the UI contract with shared design tokens (`ui/tokens.json`) and publish component API specs that cover default, loading, empty, and error states | Establishes the source of truth agents will rely on for component generation. |
| High | Lock the UI stack to shadcn/ui + Radix + Tailwind and remove bespoke styling until post-v2 | Ensures consistent primitives for component lab work and future spec automation. |
| High | Stand up the component lab (Storybook or Ladle) with Chromatic/Percy diffs, Playwright component screenshots, and a `pnpm ui:check` guard | Blocks merges on visual regressions and gives agents a fast self-test loop. |
| Medium | Keep a lean Cypress/Playwright E2E suite that exercises 5–10 production flows with trace review | Maintains end-to-end confidence without slowing component iteration. |
| Medium | Provide a structured UI JSON DSL plus deterministic mocks for agents | Lets automated contributors define components via contract instead of the full app surface. |
| Medium | Add launcher session controller that keeps the window open and terminates capture/UI processes when closed | Prevents orphaned backend processes when operators stop work from the browser. |





