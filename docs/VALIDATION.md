# Beta validation record

Executed locally on Windows x64 on 2026-10-02, Python 3.13.15 and Node 22.23.3.
The beta is intended for Windows 10/11 x64; this record does not assert testing
on both operating system versions or on a physical CX-505.

| Check | Executed result |
| --- | --- |
| `uv run python -m pytest -q` | 107 passed; three deprecation warnings in earlier analytics/acquisition code |
| UI production build and ESLint | Passed |
| `npm test -- --run` | 9 passed |
| Real backend browser acceptance | 2 passed: demo/start/stop/archive/chart/manual calibration/full export/settings/CSRF |
| Windows Chromium Storybook comparison | 8 passed; changed baselines reviewed, component render errors also rejected |
| Source MCP stdio client and legacy negotiation | Passed: eight read-only tools, two resources, OpenAPI and protocol 2025-11-25 negotiation |
| Final local self-contained installer smoke | Install, demo with only Windows binaries on PATH, refusal to update while recording, update and uninstall preservation passed |
| Final local packaged MCP stdio | Passed; no Python/Node required by the executable; all inventoried license texts present |
| Windowless desktop launcher | Passed with Python/Node removed from PATH; correct data home and graceful backend shutdown |
| Unicode PDF | Rendered and visually inspected; Polish text, wrapping, pagination and embedded font checked |
| `npm audit` and locked runtime `pip-audit` | No known vulnerabilities reported at execution time |
| Workflow YAML | Parsed successfully |

Final publication is gated by the GitHub build of the tagged commit. It repeats
Python tests on Linux and Windows, builds the UI/package/installer, runs packaged
MCP and installs the resulting installer to verify capture and data preservation.
The workflow logs are the authoritative evidence for the downloadable artifact.
The release includes matching Git source, `SOURCE_COMMIT.txt` and SHA256 checksums.

## Pending acceptance

- **Physical CX-505 and FTDI:** not performed. Verify readings, time provenance,
  reconnect identity, recovery and exported values following RELEASE_SPEC.md.
- **24 elapsed-hour simulator soak:** started 2026-10-02 at 12:27 UTC; still running
  when this record was prepared. More than 30 minutes and 9,000 frames were observed
  without an error, which is not a 24-hour pass. The original monitor measured the
  Windows virtual-environment redirector rather than the worker; its CPU/RAM fields
  are not acceptance evidence. The script now aggregates child processes for future
  runs. Keep the existing run's result and repeat with corrected resource monitoring
  before claiming the full soak gate.
- **Code signing:** the installer is unsigned. Checksums detect altered downloads;
  they do not replace a publisher signature.

Stable 1.0.0 must wait for the pending hardware and full soak evidence. This beta
does not claim calibration accuracy, certification or support for experimental meters.
