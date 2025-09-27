# UI Integration Plan & Milestones

## Backend Requirements
- **Live Telemetry API**
  - SSE/WebSocket endpoint streaming measurement payloads (value, unit, temperature, stability, timestamp) + device status flags.
  - Fallback REST endpoint returning latest measurement snapshot.
- **Calibration API**
  - GET `/api/calibrations` returns command metadata (name, description, last run, payload hints).
  - POST `/api/calibrations/{name}` triggers command, supports notes/operator ID, returns execution result and frame logs.
- **Export API**
  - POST `/api/exports` accepts session selection, formats, archive flags, config/protocol overrides; returns job ID.
  - GET `/api/exports/{job_id}` exposes status, artefact URLs, manifest/summary metadata.
- **Archives & Files**
  - Static file serving for artefacts (CSV, JSON, PDF, XML, manifest, checksums, zip, archive summary).
  - Optionally expose `/api/files?type=archive_summary` for UI to list generated summaries.
- **Service Health API**
  - Expand existing `/health` to include watchdog heartbeat, queue lengths, last warnings, scheduled command status.
  - `/health/logs/stream` now publishes recent events over SSE with automatic `/health/logs` polling fallback and connection-state diagnostics.

## Frontend Milestones
1. **Project Setup (Week 1)**
   - Bootstrap React/TypeScript project with Vite.
   - Integrate ESLint, Prettier, Vitest, React Testing Library.
   - Implement theme provider and global layout shell (sidebar + topbar).

2. **Data Layer & Services (Week 2)**
   - Configure React Query client, WebSocket/SSE hooks.
   - Implement API clients for telemetry, calibrations, exports, health.
   - Add mock data support for offline development.

3. **Core Screens (Week 3-4)**
   - Live Dashboard view with measurement cards, timeline, alerts.
   - Calibration Center list, detail drawer, trigger dialog.
   - Exports page with session selector, format options, job history, archive summary viewer.
   - Service health view with watchdog metrics, logs, command queue, and diagnostic bundle download actions.

4. **Interactivity & UX Polish (Week 5)**
   - Toast notifications, confirm dialogs, loading states.
   - Accessibility adjustments (keyboard nav, ARIA labels, color contrast).
   - Responsive tweaks for tablet layouts.

5. **Testing & Packaging (Week 6)**
   - Component/unit tests for critical flows.
   - Playwright end-to-end scripts (calibration trigger, export flow, archive download).
   - Build pipeline hooking into backend (static serving, optional Electron wrapper stub).

## Deliverables
- Updated API documentation reflecting new endpoints/fields.
- Frontend codebase in `ui/` with CI workflow (lint/test/build).
- UX artifact: high-fidelity mockups for each screen (Figma/PNG).
- Operator handout summarising UI features.

## Risks & Mitigations
- **API latency / streaming reliability:** start with polling fallback and backpressure handling.
- **Hardware availability for testing:** maintain mock adapters; schedule live validation once hardware accessible.
- **Scope creep:** adhere to MVP screens; backlog advanced features (annotations, multi-device management).

## Next Steps
1. Confirm backend endpoint ownership; create tickets for new APIs.
2. Kick off UI project scaffolding and integrate with existing repository.
3. Produce high-fidelity mockups using selected component library for stakeholder review.


