# Configuration and customization map

**User-editable files are explicitly labeled below and in the installer resources.**
Installed defaults are read-only application resources. On first launch they are
copied into `%LOCALAPPDATA%\Elmetron\config`. Edit those copies with capture stopped.
Updates never overwrite them. `--data-dir` / `ELMETRON_DATA_DIR` selects an alternate
home. Relative paths resolve against that home. Demo uses its own `demo` subdirectory.

| File | Role | Customization |
| --- | --- | --- |
| `config/app.toml` **USER CONFIG** | Device selection, operator, storage, analytics and report paths | Set device serial/index, default operator and paths. Profile defaults override serial parameters while `use_profile_defaults=true`. |
| `config/protocols.toml` **USER CONFIG** | CX-505 link parameters and polling bytes; simulator profile | Set a known transport profile. Only CX-505 FTDI and demo are in beta scope. Unknown commands require hardware verification. |
| `config/templates/session_report.fmt` **USER TEMPLATE** | PDF summary text; `{default_text}`, `{summary_*}` placeholders | Customize labels and report text; font and pagination remain automatic. PDF is a summary, complete records are in CSV/JSON/XML. Jinja templates can iterate `measurements` once as a stream; `recent_measurements` is a bounded list. |
| `config/templates/session_lims.xml.fmt` **LEGACY TEMPLATE** | Original standalone exporter XML layout | Used by the legacy reporting CLI. The v1 REST exporter uses the documented full-data XML schema and automatic escaping. |
| `config/api-token` **GENERATED SECRET** | Bearer token for REST mutations | Keep private; remove with service stopped to generate a new one. Not included in diagnostic bundles. |
| `ui/src/contexts/settings.ts` **SOURCE CUSTOMIZATION** | UI defaults and operator validation | Adjust chart defaults when building your own UI. Browser preferences persist locally. |
| `ui/tokens.json`, `ui/src/theme.ts`, `ui/src/locales/*.json` **SOURCE CUSTOMIZATION** | Appearance and Polish/English text | Rebuild UI after editing. |
| `ui/src/config.ts` **SOURCE CUSTOMIZATION** | Relative API/health URLs | Production is same-origin. Vite proxies the backend for development. |
| `elmetron/protocols/cx505.py` **SOURCE CUSTOMIZATION** | Pure frame grammar and decoding | Extend parsers with recorded frames and tests. No USB dependency. |
| `elmetron/data.py`, `openapi.json` **INTEGRATION CONTRACT** | Shared normalized data, REST schemas | Use the REST example or local MCP when building another application. |
| `examples/mcp-host.json` **HOST CONFIG EXAMPLE** | Launching the read-only MCP server | Replace executable/data paths; do not launch the desktop EXE as a stdio server. |

Validate before starting: `elmetron-cli.exe validate-config --show-effective`.
Explicit missing files fail validation. `--config PATH --protocols PATH` are optional
arguments to `validate-config`. Migration to SQLite schema v2 creates a `.pre-v2.bak`
backup once. Copy an existing database with SQLite's backup API, or copy it only
after all old services have stopped; include WAL files when preserving a raw copy.
Keep a separate backup of the entire old home before importing.

Capture ignores startup and scheduled command lists in this beta. Calibration is
performed on the instrument and recorded with a required label and author in UI.
Experimental examples in `docs/history` are historical, not supported commands.
