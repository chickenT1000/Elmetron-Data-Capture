# Elmetron Data Acquisition and Analysis Suite - Software Specification

## 1. Product Overview
The Elmetron Data Acquisition and Analysis Suite is a Windows-native application for direct communication with Elmetron multifunction meters (CX-505 series, dedicated pH controllers, conductivity meters, etc.). The suite replaces legacy tooling by delivering reliable data capture, structured storage, and rich analysis for laboratory and industrial users.

## 2. Goals and Non-Goals
- Acquire authenticated measurements via USB/serial bridges (Phase 1) and future BLE transports (Phase 3).
- Provide continuous background logging with zero data loss and automatic reconnection.
- Offer interactive dashboards, editing, annotations, derived calculations, and alerting for analytical workflows.
- Support structured exports to LIMS, CSV, JSON, PDF, and custom templates.
- Non-goals for Phase 1: remote cloud gateway, mobile companion applications, and embedded firmware updates.

## 3. Personas
- Lab Technician: performs measurements, applies calibration, enters sample metadata, flags anomalies.
- Process Engineer: analyses time-series trends, compares devices, prepares process reports.
- Quality Manager: audits historical records, verifies calibration compliance, signs off on reports.

## 4. System Architecture
1. Hardware Interface Layer: transport factory with FTDI D2XX (USB) support today and BLE bridge adapters via `elmetron.hardware.create_interface`. Encapsulates device discovery, handshake, polling scripts, and low-level logging.
2. Acquisition Service: Windows background service handling scheduling, watchdog, buffering, protocol-driven startup commands, and bulk storage of raw frames.
3. Ingestion Pipeline: Parses frames into structured measurement records, applies metadata enrichment (device, operator, calibration context).
4. Core Services: Business rules, derived metric calculations, calibration management, rules engine, audit logging.
5. Presentation Layer: WinUI/WPF desktop client for visualisation, editing, reporting, and configuration.

## 5. Communication Strategy
- Enumerate devices via vendor/product IDs (FTDI) or adapter metadata (BLE), assert DTR/RTS where applicable, and send protocol-defined poll/handshake sequences sourced from the registry.
- Provide abstraction for per-device command sets to simplify future meter onboarding.
- Record raw USB traces for diagnostics; expose diagnostic console for support engineers.

## 6. Data Management
- Storage: SQLite (with optional SQLCipher). Tables: Instruments, Sessions, Measurements, CalibrationEvents, DerivedMetrics, Annotations, Attachments. Derived metrics are stored as JSON snapshots per measurement to capture moving averages, stability indices, and compensation metadata.
- Retention: Raw frames stored alongside decoded records for traceability; automatic pruning policy configurable per site.
- Versioning: Edits tracked with user, timestamp, reason; ability to roll back to previous revisions.
- Backup: Scheduled encrypted ZIP export and manual snapshot wizard; configurable retention and remote share support.

## 7. Functional Modules
- Device Manager: connection status, firmware, calibration reminders, diagnostics, protocol overrides.
- Protocol Command Orchestrator: executes profile-defined startup commands and scheduled workflows (with retries/backoff), validates responses, and feeds decoded frames into the capture pipeline before steady-state logging.
- Acquisition Console: live readings, charting, sample tagging, operator notes, start/stop controls.
- Data Review: filterable grid, batch editing, anomaly detection, derived calculations, compare sessions.
- Visualisation Suite: time-series, scatter, correlation matrix, histogram, heatmap, custom dashboard layouts.
- Reporting and Export: template-driven PDF/CSV/JSON/LIMS XML, email delivery, scheduler, electronic signatures. CLI utilities now emit CSV/JSON/XML/PDF dumps with embedded analytics payloads and write manifest/checksum packages for downstream tooling.
- Configuration and Calibration: calibration wizard, coefficient import/export, drift analysis, reminder scheduling, plus an operator-facing CLI (`trigger_calibration.py`) for on-demand command execution.
- User and Audit Management: role-based access (Technician/Engineer/Admin/Viewer), audit trail, electronic signature workflow, event log viewer.

## 8. Interpretation and Analytics
- Rules engine with threshold checks, trend detection, and notification routing (email/Teams/OPC UA events).
- Calculation library: temperature compensation, ORP, conductivity conversions, pH stability indices, moving averages, regression. Session-scoped analytics engine maintains rolling histories and surfaces derived metrics into storage/export pipelines.
- Annotation system with tagging, attachments, and collaborative comments.
- Export pipeline for machine-learning datasets (labelled events, features, metadata).

## 9. User Experience Principles
- Ribbon/tabbed navigation with role-specific layouts.
- Real-time status indicators (device connectivity, logging state, backlog size).
- Inline editing, undo/redo, diff view for revisions, highlight computed vs. measured values.
- Theme support (light/dark/high-contrast) and localisation-ready resources.

## 10. Extensibility and Integrations
- Plugin interface (Python or .NET) for new meter protocols, analytics, alert actions.
- Local REST API for system integration; optional OPC-UA adapter in Phase 3.
- Scriptable export pipelines with Cron-style scheduling.

## 11. Security and Compliance
- Windows authentication integration or local credential store (PBKDF2/Argon2 hashing).
- Encryption at rest using SQLCipher and DPAPI for key storage.
- Audit logs meeting ISO 17025 and CFR 21 Part 11 requirements (user, timestamp, before/after values, signatures).
- Configurable retention, purge approval workflow, tamper detection using checksums.

## 12. Deployment and Operations
- Installer: signed MSIX/MSI bundle with driver dependencies; per-user or per-machine installation.
- Acquisition service auto-starts, monitors health, performs exponential backoff reconnects, exposes watchdog status, and supports quiet-mode diagnostics for clean machine-readable streams.
- Diagnostics: self-test wizard, exportable support bundle (logs, config, hardware info), optional telemetry (opt-in) for crash and performance metrics.
- Support bundles include a machine-readable manifest (timestamp, counts, source paths) that the Service Health console surfaces after download for quick triage.
- Operator procedures: see `docs/OPERATOR_PLAYBOOK.md` for daily capture workflow and `docs/WINDOWS_SERVICE_GUIDE.md` for service installation.

## 13. Testing Strategy
- Unit tests: protocol parsing, calculations, validation rules, security utilities.
- Integration tests: hardware-in-loop scenarios covering each meter model and firmware.
- UI automation: WinAppDriver/Playwright smoke suite for core workflows.
- Front-end unit tests run under Vitest with React Testing Library (jsdom) to cover component-level state and accessibility.
- Durability tests: 24 hour soak, high-frequency polling stress, database growth benchmarks.

## 14. Front-End Design System & Visual Workflow
- Design tokens live in `ui/tokens.json` and drive palette, spacing, radii, and typography consistently across MUI theme, global CSS, and component stories.
- Reusable dashboard widgets (`MeasurementPanel`, `CommandHistory`, `LogFeed`) expose typed contracts that the dashboard consumes directly and are documented via Storybook 9.x.
- Storybook serves as the canonical component lab; Chromatic publishes snapshots on each PR to guard regressions and provide hosted previews.
- Playwright component tests (`npm run test:ui`) mount Storybook iframes and capture deterministic screenshots for baseline diffing inside CI.
- Agents and contributors use these stories plus Chromatic/Playwright baselines as the source of truth before they touch page-level code, ensuring the UI contract stays frozen.

## 15. Delivery Roadmap
- Phase 1 (MVP): CX-505 support, background logging, basic charting/export, manual calibration logs.
- Phase 2: Additional meter catalog, calibration workflow, audit trail, advanced charts, plugin framework.
- Phase 3: Rules engine, REST/LIMS integration, OPC-UA adaptor, report scheduling, full BLE transport integration (beyond the adapter scaffolding delivered in Phase 2).
- Phase 4: Cloud sync optional module, predictive diagnostics, mobile dashboards, enterprise deployment tooling.

## 16. Open Questions
- Confirm exact meter models/firmware for launch and prioritised roadmap.
- Determine regulatory profile per deployment (GLP, ISO 17025, CFR 21 Part 11) to scope validation effort.
- Decide service topology (per station vs. central logger) and network backup policies.
- Clarify localisation requirements and documentation level.

