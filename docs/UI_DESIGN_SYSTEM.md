# UI Design System & Tech Stack

## Technology Selection
- **Front-end framework:** React 18 with TypeScript for rich stateful UI and strong typing aligned with our Python backend contracts.
- **Bundler/build:** Vite for fast dev server, HMR, and straightforward integration with TypeScript and Material UI.
- **Component library:** Material UI (MUI) v6 for accessible components, theming capabilities, and rapid prototyping.
- **State/data:** React Query for server state (REST/SSE/WebSocket), Zustand for lightweight local UI state where needed.
- **Charts:** Recharts (React-based) for live measurement trends; D3-based fallback for advanced visualizations.
- **Styling:** MUI theme + CSS-in-JS (emotion) backed by `ui/tokens.json` (colors, spacing, radii, typography) so React components, stories, and Playwright snapshots share the same source of truth.
- **Testing:** Vitest + React Testing Library for unit tests; Playwright for end-to-end scenarios.
- **Component lab & visual QA:** Storybook 9.x (Vite builder) with Chromatic publishing for hosted previews/diffs and Playwright component snapshots checked into `ui/playwright`.

## Theming & Layout
- Base theme derived from lab color palette (primary: navy #0A3D62, secondary: teal #16A085, accent for status states).
- Typography: Roboto for main UI, monospace fallback for data tables.
- Layout grid:
  - App shell with persistent sidebar navigation (Dashboard, Calibrations, Exports, Service).
  - Top bar showing device status summary and operator context.
  - Content area uses 12-column responsive grid with breakpoints (lg: 1440+, md: 1024+, sm: 768+).

## Iconography & Feedback
- Material Icons (Outlined) via MUI icon pack.
- Status states (success, warning, error) mapped to analytics/health badges.
- Global snackbar/toast service for command/ export feedback.

## Accessibility & Internationalisation
- WCAG 2.1 AA targets (color contrast, keyboard navigation) enforced via MUI components.
- i18n-ready using `react-i18next`; initial release in English, structure allows locales.

## Deployment Approach
- Build static assets via Vite; served by capture service (FastAPI/Flask) from `/ui` route during initial phase.
- Future packaging through Electron wrapper for dedicated kiosk deployments (reuse same React bundle).

## Component Lab & Visual Regression
- `npm run storybook` launches the local component lab; stories cover the dashboard widgets (`MeasurementPanel`, `CommandHistory`, `LogFeed`) and composite dashboard views.
- `npm run test:ui` runs Playwright in component mode, mounting Storybook iframes and diffing screenshots against the committed baselines.
- `npm run chromatic` publishes Storybook to Chromatic when `CHROMATIC_PROJECT_TOKEN` is provided; CI (see `.github/workflows/ui-visual.yml`) keeps remote baselines in sync.

## Next Steps
1. Layer rolling measurement charts and advanced analytics widgets into the dashboard stories (tie into real-time telemetry once charting is finalised).
2. Expand the design tokens to cover elevation, shadows, and chart color ramps before shipping the analytics views.
3. Connect agent-written JSON DSL specs to Storybook story generators so automated contributors can publish new component states directly.
