# Protocol Registry Schema

This project reads device communication profiles from either `DEFAULT_PROFILES` (in code) or an external registry file (`config/protocols.toml`). Each profile entry is keyed by an identifier (e.g. `cx505`) and may contain the fields below:

| Field | Type | Description |
| --- | --- | --- |
| `description` | string | Human-readable label for the instrument profile. |
| `transport` | string | Communication transport (`ftdi`, `ble`, etc.). Defaults to `ftdi` if omitted. |
| `poll_hex` | string | Space-separated hex bytes sent to poll the instrument. Optional for transports that push measurements. |
| `poll_interval_s` | float | Seconds between poll frames. |
| `handshake` | string | Optional handshake directive (e.g. `connect` for BLE bridges). |
| `baud`, `data_bits`, `stop_bits`, `parity` | serial params | Standard UART settings applied when the profile is active. |
| `latency_timer_ms` | int | FTDI latency timer override. |
| `read_timeout_ms`, `write_timeout_ms` | int | Read/write timeouts for the transport. |
| `chunk_size` | int | Read buffer size. |

Values specified in a profile are applied to `DeviceConfig` when `device.use_profile_defaults` is `True`. The CLI also allows overriding any field at runtime.

## Built-in Profiles

The `DEFAULT_PROFILES` constant ships with:

- **`cx505`** - baseline FTDI CX-505 configuration used throughout development.
- **`cx705`** - example profile for the CX-705 dissolved oxygen meter.
- **`ph_ble_handheld`** - placeholder for Bluetooth LE bridges used by handheld pH/ORP meters.

Extend `config/protocols.toml` with additional `[profiles.*]` sections and load them by passing `--protocols path/to/registry.toml` to the capture or service runners.

## Command Definitions

Add nested tables such as `[profiles.cx505.commands.calibrate_ph7]` to describe command or calibration sequences. Supported keys include:

| Field | Type | Description |
| --- | --- | --- |
| `description` | string | Human-readable command name. |
| `category` | string | Optional classification (`calibration`, `control`, etc.) used for audit logging. |
| `write_hex` | string | Space-separated hex payload written before reading a response. |
| `write_ascii` | string | ASCII payload alternative to `write_hex`. |
| `post_delay_s` | float | Optional delay (seconds) after writing before reading. |
| `read_duration_s` | float | Seconds to keep the link open and collect frames. |
| `expect_hex` | string | Optional hex prefix expected in the first frame (used for simple validation). |
| `default_max_retries` | int | Number of automatic retries the acquisition service should attempt when invoking the command (overridable per schedule). |
| `default_retry_backoff_s` | float | Delay (seconds) between retries; the service multiplies this by the attempt index for linear backoff. |
| `calibration_label` | string | Tag recorded with calibration/audit events (e.g. `ph7_buffer`). |

Commands are exposed via `ProtocolProfile.commands` and can be executed with `run_protocol_command.py`. The acquisition service can invoke them automatically through two mechanisms:

- `acquisition.startup_commands` - a simple list of command names executed once when a session starts.
- `[[acquisition.scheduled_commands]]` - rich schedule entries that enable retries, backoff, recurring intervals, and calibration tagging. Each entry references the command name defined in the active profile.

See `config/app.toml` for an example that triggers `calibrate_ph7` on startup and every 24 hours with retry/backoff behaviour.

## Transport Support

Set `transport` to choose the hardware adapter used by the acquisition layer:

- `ftdi` (default) -> `CX505Interface` talking to the USB D2XX bridge.
- `ble` -> `BleBridgeInterface`, which relies on a BLE adapter factory (for example one built on top of `bleak`). Provide the factory via `create_interface(..., adapter_factory=...)` when running services or CLIs.

BLE profiles typically also set `handshake = "connect"` so the bridge emits its initial link request after connecting.
## Validation

Use `validate_protocols.py` to lint custom registries before deploying them:

```bash
python validate_protocols.py config/protocols.toml
```

Add `--warnings-as-errors` to fail fast when optional fields (such as missing `transport`) should be treated as blocking issues.



