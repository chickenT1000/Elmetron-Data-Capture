# Repository Guidelines

## Project Structure & Module Organization
The workspace centers on scripting direct FTDI access for the Elmetron CX-505.
- `cx505_d2xx.py` exposes the D2XX bindings and command-line interface.
- `probe_commands.py` reuses the transport to sweep command frames.
- `connectivity_report.json` archives raw probe metrics for replay.
- `usbpcap*.pcapng` store USB handshake captures gathered with USBPcap/Wireshark.
Cache files produced by runs (`capture.log`, `*.pcapng`) stay alongside the scripts; prefer naming runs with timestamps (for example `usbpcap_20250925T1129.pcapng`) to avoid overwrites.

## Build, Test, and Development Commands
- `python cx505_d2xx.py --list` enumerates FTDI interfaces and validates driver visibility.
- `python cx505_d2xx.py --baud 115200 --parity E --log logs\\session.bin` reproduces the legacy link parameters while recording raw bytes.
- `python probe_commands.py` sweeps the current STX/ETX payload set and prints any responses.
- `tshark -i \\USBPcap1 -a duration:30 -w captures\\handshake.pcapng` records the vendor handshake for later decoding.
Keep scripts runnable on bare Python 3.11 without external dependencies.

## Coding Style & Naming Conventions
Follow PEP 8 and type-hint new functions. Keep modules and files in `snake_case`. Document non-obvious protocol constants with short comments. Prefer using reusable helpers in `cx505_d2xx` instead of duplicating ctypes boilerplate. Generated artifacts should use lowercase, hyphen-free filenames (e.g., `connectivity_report.json`).

## Testing Guidelines
No automated tests exist yet; add `tests/` with `pytest` as scenarios emerge. Cover both successful reads and error handling around FTDI status codes. When adding new command sequences, provide fixtures that mock `_ft_read` / `_ft_write` so unit tests can run without hardware.

## Commit & Pull Request Guidelines
Adopt conventional commits (e.g., `feat: add amplitude sweep parser`) to clarify intent. Each PR should summarize scope, note captured hardware scenarios, and attach sample logs or pcaps when behavior changes. Reference task IDs or issue numbers in the body, list manual validation steps (`python probe_commands.py`, `tshark ...`), and highlight any new dependencies.

## Capture & Analysis Workflow
Always start captures after the legacy S457s app has begun exchanging data to ensure the initial handshake is recorded. Store raw `.pcapng` in versioned directories (e.g., `captures/2025-09-25/`) and annotate findings in `connectivity_report.json` so later agents can replay conditions accurately.
