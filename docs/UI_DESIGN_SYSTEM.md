# UI Design System & Tech Stack

## Technology Selection
- **Front-end framework:** React 18 with TypeScript for rich stateful UI and strong typing aligned with our Python backend contracts.
- **Bundler/build:** Vite for fast dev server, HMR, and straightforward integration with TypeScript and Material UI.
- **Component library:** Material UI (MUI) v6 for accessible components, theming capabilities, and rapid prototyping.
- **State/data:** React Query for server state (REST/SSE/WebSocket), Zustand for lightweight local UI state where needed.
- **Charts:** Recharts (React-based) for live measurement trends; D3-based fallback for advanced visualizations.
- **Styling:** MUI theme + CSS-in-JS (emotion) with design tokens (colors, spacing) documented per brand requirements.
- **Testing:** Vitest + React Testing Library for unit tests; Playwright for end-to-end scenarios.

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

## Next Steps
1. Set up `ui/` workspace with Vite React+TS template, commit lint/test tooling (ESLint, Prettier, Vitest).
2. Create shared theme module (`theme.ts`) defining palette, typography, spacing tokens.
3. Implement layout shell (sidebar/top bar) and stub pages for core flows.
