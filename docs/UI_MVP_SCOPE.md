
# UI MVP Scope

## Goals
- Deliver a live monitoring console with real-time values, multi-parameter plots, and recording controls (title, annotations, bookmarks).
- Enable guided calibrations with history and audit capture.
- Provide session evaluation tools (overlay alignment, trimming, metrics) and export of overlays (image/JSON/CSV/PDF).
- Offer export job orchestration (formats, archives, manifests) and service health diagnostics within a unified UI.

## Primary Users
- **Lab Technician:** monitors readings, records sessions, triggers calibrations, evaluates sessions.
- **Process/QA Engineer:** reviews overlays, extracts metrics, prepares reports.
- **Service Operator:** tracks device/service health, manages configurations, monitors command queues.

## Core UI Surfaces
1. **Live Monitoring & Recording**
   - Measurement cards, status header, alerts.
   - Multi-trace plot with toggles, zoom, crosshair, and annotation markers.
   - Recording controls (start/stop, title, notes, bookmark shortcuts) and active session list.
2. **Session Evaluation & Overlays**
   - Session selector with previews/tags.
   - Overlay workspace for alignment, trimming, and metrics comparison.
   - Export panel supporting PNG/SVG, JSON, CSV, PDF outputs plus template selection.
3. **Calibration Center**
   - Command catalogue, detail drawer, trigger modal, audit log.
4. **Exports & Archives**
   - Session/overlay selection, format options (CSV/JSON/XML/PDF/image), archive toggles, job history, artefact downloads.
5. **Service Health & Settings**
   - Watchdog metrics, config snapshot, event log, command queue management.

## API & Data Requirements
- **Telemetry:** WebSocket/SSE providing measurement payloads + device status; REST fallback for latest snapshot.
- **Recording:** Endpoint to create/close sessions with title/notes, receive bookmark events, persist overlay metadata.
- **Session Data:** REST for session list, metadata, annotations; endpoints for aligned overlay data and trimming operations.
- **Calibration:** List/trigger endpoints with result payload and audit note submission.
- **Exports:** Job creation/status endpoints supporting overlay export formats and archive bundle metadata.
- **Files:** Download endpoints for artefacts, manifests, archives, overlay exports, and archive summary JSON.
- **Health/Logs:** `/health` extension plus event/log streaming for watchdog and command queue.

## Technical Assumptions
- React + TypeScript SPA (Vite) with MUI design system; eventually package via Electron for kiosk installs.
- Backend exposes REST + WebSocket; long-running tasks use async jobs with status polling.
- Operator identification captured client-side for calibration/export/recording actions (until auth added).
- Charting via Recharts with accessibility-friendly data-table fallback; download via canvas export utilities.

## Open Questions
- Annotation taxonomy (tags, colours, severity) and persistence format.
- Requirements for comparing sessions from different devices/models.
- Should session evaluation support computed metrics (e.g., deltas, area-under-curve) beyond current analytics?
- Approval workflow needed before exporting overlay reports?

## Next Actions
- Wireframe & prototype references: `docs/UI_WIREFRAME_OUTLINE.md`.
- UI design system guidance: `docs/UI_DESIGN_SYSTEM.md`.
- Integration milestones: `docs/UI_INTEGRATION_PLAN.md`.
- Confirm API contracts with backend team, create implementation tickets, and prioritise Live Monitoring + Recording for first sprint.
