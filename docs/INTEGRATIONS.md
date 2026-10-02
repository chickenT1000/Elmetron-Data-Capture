# REST and local MCP

Run the desktop app or `elmetron-cli.exe serve`. REST base: `http://127.0.0.1:8050/api/v1`.
The machine-readable contract is `/openapi.json`. GET reads need no token; mutations
need `Authorization: Bearer <config/api-token>` or the UI's same-origin CSRF cookie
and `X-Elmetron-CSRF` header. The token is generated in the selected data home.

Sessions return `sessions` and `next_cursor`; cursor is an offset into the selected
sort/filter. Measurements return `measurements`, `limit`, `next_cursor`; their cursor
is the last measurement ID. Follow pages until `next_cursor=null`. Session page max
1000; measurement page max 1000. List sessions while capture is stopped when you
need a stable multi-page archive listing. Statistics scan all matching records.

Measurement fields: original `value`/`unit`, `normalized_value`/`normalized_unit`,
`captured_at` UTC, original `device_timestamp`, `device_timezone=unknown`, raw
`frame_hex`, decoded `payload`, `analytics`, `quality`. Chart evaluation includes
`samples`, `displayed_samples`, `downsampled`. Never treat chart series as a full
export. `/sessions/{id}/export?format=zip` returns full snapshot CSV/JSON/XML/PDF
with SHA256 manifest. Individual exports include `X-Content-SHA256`. Export history
is local, and diagnostics omit the database and authentication token.

MCP command: `elmetron-cli.exe --data-dir PATH mcp`. Use the console executable,
not the desktop launcher. It serves stdio only and starts neither browser nor USB.
Eight tools: `get_status`, `list_instruments`, `list_sessions`, `get_session`,
`get_measurements`, `get_statistics`, `get_markers`, `get_calibrations`.
Resources: `elmetron://capabilities`, `elmetron://openapi`. All tools are read-only
and annotated as such. The SDK provides current and legacy MCP negotiation.
The process's Windows user determines access to the archive; launching it grants
the host that read access. stdout is reserved for protocol; logging uses stderr.

See [host config example](../examples/mcp-host.json). Replace YOUR_USER and paths.
Both APIs use the same active archive selected in UI; demo remains separate.
No SQL execution, shell execution, mutation or hardware-command tool is exposed.
