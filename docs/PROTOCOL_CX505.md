# CX-505 protocol used by this implementation

This describes the implementation and observed grammar, not a manufacturer's
complete protocol specification. Verify modifications against your own instrument.
Hardware acceptance for this beta is pending.

FTDI D2XX USB bridge; defaults **115200 baud, 8 data bits, even parity, 2 stop bits**.
Poll bytes: `01 23 30 23 30 23 30 23 03` (hex), normally once per second.
The driver is loaded lazily from Windows System32 when actual USB access starts.
Archive, exports, demo and MCP work without that driver.

```text
SOH header ETB STX measurement RS ETX CR LF
01         17  02             1E 03 0D 0A
header example: #CX-505 S/N SIM-DEVICE#READY#RANGE#PH
measurement example: #0001# 7.015 pH# 24.7 C# 02-10-2026# 13:32:18
```

`#` separates fields. The parser extracts model/serial, value/unit, temperature,
device date and device time. Buffer extraction tolerates fragmented USB reads and
multiple frames. Original bytes are preserved in SQLite and capture journals.

PC capture time is UTC and is the chart axis. Device time is preserved separately
with timezone `unknown`; the application does not invent a meter timezone.
Original values/units remain immutable. Read views normalize `mS/cm` to `µS/cm`
by multiplying by 1000; `S/cm` by 1,000,000. `µ` and `μ` variants are recognized.
Statistics group by normalized unit. Zero and negative temperatures remain valid.
Unknown units receive a quality flag instead of being reinterpreted as pH.

See [USB example](../examples/read_usb.py), [REST example](../examples/read_api.py),
[configuration map](CONFIGURATION.md) and [OpenAPI](../openapi.json).
Remote calibration bytes from the historical registry were unverified and have
been removed from shipped defaults.
