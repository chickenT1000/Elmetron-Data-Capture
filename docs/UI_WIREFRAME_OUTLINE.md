# UI Wireframe Outline

## Live Monitoring & Recording
- **Header bar:** Device/profile, connection status, operator context, real-time indicators for recording, elapsed time, and available storage warning.
- **Live parameter grid:** Latest values (value/unit, temperature, stability badge, timestamp) with per-parameter enable toggles and status pills.
- **Time-series plots:** Multi-trace chart (pH, temperature, conductivity, O₂, etc.) with auto-scaling, hover crosshair, zoom/pan, and parameter legend; ability to pin favourite traces.
- **Recording controls:** Start/stop buttons with optional countdown, session title/description inputs, tagging controls (sample ID, location), and bookmark hotkeys.
- **Timeline annotations:** Bookmark list showing markers (calibration, buffer insertions, operator notes) aligned to chart; clicking jumps timeline.
- **Session list:** Active/recent recordings with status (recording, completed), duration, annotation count, quick actions (open evaluation, export snapshot).
- **Alerts & notifications:** Panel for watchdog alerts, command failures, threshold breaches, calibration reminders.

## Session Evaluation & Overlays
- **Session selector:** Multi-select dropdown or gallery with metadata (date, operator, notes) and preview sparkline for each session.
- **Overlay workspace:** Layered plots showing selected sessions with colour-coded traces; drag-and-drop to align start markers or specify alignment event.
- **Cropping tools:** Range slider and numeric inputs to trim sessions, apply offsets, and snap to annotation markers; preview trimmed segments.
- **Metrics summary:** Table showing key statistics (min/max/avg, stability index, temperature compensation) for each overlay and differences between sessions.
- **Export panel:** Options to export overlay as PNG/SVG image, JSON payload (aligned samples, annotations), CSV (tabular data), and PDF report; include template selector.
- **Comparison notes:** Text area for operator conclusions saved alongside overlay export; track revision history.

## Calibration Center
- **Calibration catalogue:** Card/table view with command name, buffer label, category, last run, status, upcoming schedule.
- **Detail drawer:** Displays protocol payload, expected frames, safety notes, and retry/backoff history.
- **Trigger modal:** Collects operator ID, buffer confirmation, note entry, and optional reminder; show estimated duration/progress once triggered.
- **Audit log:** Filterable table of calibration events with status, operator, timestamp, result frames, exported evidence link.

## Exports & Archives
- **Session/overlay selector:** Browse by session, overlay bundle, date range, or tags; preview metadata and measurement counts.
- **Format options:** Accordion with checkboxes for CSV/JSON/XML/PDF/image, CSV mode toggle, template pickers, gzip, archive bundling, manifest overrides.
- **Job queue/history:** List of export jobs with progress indicator, status chips, download links for artefacts, manifest, archive summary, and action to rerun with previous settings.
- **Archive summary viewer:** JSON viewer with checksum/size data and ability to copy/share; highlight differences vs. previous archive.

## Service Health & Settings
- **Service status panel:** Watchdog heartbeat, runtime, restart controls, scheduled command queue length, D2XX driver status.
- **Configuration snapshot:** Key device/transport parameters, export defaults, calibrated buffers, next scheduled commands.
- **Events/log stream:** Console list with severity filters, search, ability to pin critical events; download log snippet.
- **Command queue monitor:** View pending/active protocol commands with ability to pause, reprioritize, or cancel.

## Navigation & Standard Features
- Persistent sidebar (Dashboard, Sessions, Calibrations, Exports, Service, Settings); topbar with breadcrumbs, help, theme toggle, operator menu.
- Global search (sessions, overlays, calibrations) from topbar; keyboard shortcuts for navigation and recording controls.
- Dark/light theme toggle with responsive layout (12-column grid collapsing to cards on tablet/mobile).
- Help & onboarding panel with quick tips, SOP links, and video walkthrough placeholders.

## Interaction Notes
- Real-time updates via WebSocket/SSE with 3s polling fallback; offline banner when connection drops.
- Undo/redo, toast notifications with drill-down links (e.g., open export job details).
- Confirmation dialogs for destructive actions (stop recording, discard overlay adjustments, restart service).
- Accessibility: WCAG 2.1 AA colours, keyboard navigation, focus indicators; all charts provide data table view.
