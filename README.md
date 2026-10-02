# Elmetron Data Capture

Local CX-505 measurement capture and archives for Windows 10/11 x64. Browser UI,
CSV/JSON/XML/PDF/ZIP exports, REST v1 and read-only MCP. GPL-3.0-only.

**1.0.0-beta.1:** hardware acceptance and the elapsed 24-hour soak are separate
release gates. See [validation](docs/VALIDATION.md) for actual results.

## Install and run

1. Download the Windows x64 setup from [GitHub Releases](https://github.com/chickenT1000/Elmetron-Data-Capture/releases).
2. Run setup for your Windows user and open **Elmetron** from the Start menu.
3. Use **Start demo** to try synthetic measurements in a separate database.
4. For real capture, install [FTDI's official D2XX driver](https://ftdichip.com/drivers/d2xx-drivers/), connect CX-505 and click **Start CX-505**.
5. Use **Stop** before updating. **Close service** stops capture and the backend;
   closing a browser tab alone leaves capture running.

No Python or Node installation is required by the Windows package. The local UI is
`http://127.0.0.1:8050`. Installation is per user in `%LOCALAPPDATA%\Programs\Elmetron`.
Data and config are separate in `%LOCALAPPDATA%\Elmetron`; uninstall preserves them.
Only one service may use a data home. A port occupied by another app fails with a
log location rather than silently launching an unrelated UI.

## Files to configure for your own application

**[Configuration and customization map](docs/CONFIGURATION.md)** explicitly labels
user config, report templates, source customization and integration contracts.
Start with `config/app.toml`, `config/protocols.toml`, `examples/read_api.py` and
`examples/mcp-host.json`. Stop capture before changing user config.

- [Correction specification and release gates](docs/RELEASE_SPEC.md)
- [CX-505 frame grammar and USB example](docs/PROTOCOL_CX505.md)
- [REST/OpenAPI](openapi.json) and [API/MCP guide](docs/INTEGRATIONS.md)
- [Build and test instructions](docs/BUILD.md)
- [Contribution guide](CONTRIBUTING.md), [security](SECURITY.md), [license](LICENSE)
- [Beta release notes](docs/RELEASE_NOTES.md)

Original values, units and device timestamps remain available. PC timestamps are
UTC; device timezone is unknown. Read views normalize conductivity to µS/cm.
Full exports use a consistent database snapshot. Large charts explicitly sample
points while statistics and exported records remain complete. Calibration records
refer to calibration performed manually on the meter.

Historical scripts and specifications are not release instructions. Other meters,
BLE and experimental remote commands are outside this beta's supported scope.
This community project makes no regulatory certification claim; see [NOTICE](NOTICE).
