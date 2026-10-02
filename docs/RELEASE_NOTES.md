# 1.0.0-beta.1

First self-contained Windows beta with per-user installer and GPL-3.0-only source.

- Durable capture journal, idempotent recovery, schema-v2 backup and preservation
  of short sessions. Retention affects system logs only.
- Separate demo archive, explicit capture controls, reconnect heartbeat and graceful
  stop. Browser closure leaves capture running; Close service exits the backend.
- Shared REST v1 / read-only stdio MCP data, original units and time provenance,
  normalized conductivity, paginated complete reads and full-data statistics.
- Full snapshot exports and ZIP manifest/checksums; Unicode paginated PDF summary.
- Manual calibration records with required author/label; unverified commands removed.
- Clear configuration/source file map and USB, REST and MCP examples.
- Reproducible build, dependency locks, license inventory and CI.

**Files for your own application:** `config/app.toml`, `config/protocols.toml` and
`config/templates/session_report.fmt` are explicitly marked user configuration.
The [configuration/source map](https://github.com/chickenT1000/Elmetron-Data-Capture/blob/v1.0.0-beta.1/docs/CONFIGURATION.md)
also identifies UI, protocol and integration customization points.

Hardware acceptance and the 24 elapsed-hour soak are pending until actual results
are recorded in [VALIDATION.md](https://github.com/chickenT1000/Elmetron-Data-Capture/blob/v1.0.0-beta.1/docs/VALIDATION.md). This is a prerelease, not stable
1.0.0. Installer is unsigned; publisher authenticity is established by the GitHub
release's artifact hashes. FTDI drivers are obtained separately from FTDI.
