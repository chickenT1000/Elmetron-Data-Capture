# Release correction specification - 1.0.0-beta.1

## Scope and release gates

Windows 10/11 x64, CX-505 via FTDI, local React UI, GPL-3.0-only source, per-user
installer, REST v1 and local read-only MCP over stdio. Users need neither Python
nor Node. Demo is visibly labeled and stored separately. Stable 1.0.0 requires
the real-hardware acceptance below; beta does not claim instrument validation.

## Corrections and acceptance evidence

| Priority / requirement | Required behavior | Verification |
| --- | --- | --- |
| P0: short sessions | Never automatically discard measurement sessions based on sample count or age | `test_short_session_is_preserved`, retention regression |
| P0: crash recovery | Journal flush/fsync precedes SQLite commit; stable UUID prevents repeated replay; incomplete/ambiguous journals retained | `test_journal_replay_is_idempotent_and_preserves_metrics`, partial journal and missing session tests |
| P0: atomic storage | Raw frame, measurement and derived metrics committed together; FK constraints active | Store transaction, FK-safe deletion tests |
| P0: migrations | Inspect schema; one backup before v2; future schema refused | Migration tests and v2 backup regression |
| P0: USB startup | Driver loads only on explicit hardware action; archive and MCP do not need FTDI | Pure decoding tests, archive/MCP acceptance |
| P0: process lifetime | Capture child has graceful stdin control; browser close leaves capture running; parent EOF stops; single data-home lock | Launcher/lock tests and process demo acceptance |
| P1: measurement semantics | Original unit/value and device time preserved; UTC PC axis; normalized conductivity; zero/negative temperature valid | Data contract and pagination regression |
| P1: complete read/export | Max 1000 rows per page, explicit next cursor; full statistics; chart sampling disclosed; snapshot export contains complete records | 1005-row regression, export ZIP checksums |
| P1: session controls | Real start/stop/rotation, rename/operator audit, explicit deletion only with capture stopped | API security/FK tests and browser demo |
| P1: calibration | Manual record only; label/author required | Calibration API regression and UI acceptance |
| P1: API security | Loopback bind, Host validation, same-origin CSRF or bearer authorization; no wildcard CORS | API rejection and valid mutation tests |
| P1: integrations | Shared REST/MCP values; eight read-only MCP tools; protocol-only stdout | In-process equality and packaged stdio acceptance |
| P1: installation | Shared PyInstaller directory, windowless desktop plus console CLI, Inno per-user setup; preserve user data | Install/update/uninstall smoke script |
| P1: reproducibility | Python/Node lockfiles, Windows build pipeline, checksums and matching source | CI and release manifest |
| P1: customization | Explicit user config/source map, USB/REST/MCP examples, migration and troubleshooting instructions | `CONFIGURATION.md`, examples |
| P2: release hygiene | Runtime records and destructive one-off maintenance scripts excluded from source distribution; license inventory included | Git tree and distribution review |

## Data and recovery design

SQLite schema v2 adds operator, audit source and unique measurement event identity.
The durable JSONL journal precedes database insertion. Recovery never invents a
session identity. Legacy rows without stable IDs are retained for manual recovery
unless an exact stored frame identity proves they were already written.
Malformed or ambiguous files remain in place and prevent new capture until checked.
Closing a session does not discard its measurements. Deletion explicitly removes
dependent records in one transaction and records a system audit event.

Demo home is `<home>/demo`, real home is `<home>`. REST and MCP select the same
archive. An explicit archive switch is permitted only with capture stopped.
Exports read an SQLite backup snapshot, include original and normalized fields,
and record SHA256 in local export history. PDF is a paginated Unicode summary.
ZIP includes CSV/JSON/XML/PDF and a file manifest with checksums.

## Hardware acceptance before stable

Record Windows/driver/CX-505 serial and firmware, commit/tag and raw sanitized
frames. Verify pH, redox and conductivity units against meter display; include
zero/negative temperature where hardware permits. Run 24 hours on hardware;
record timestamps, received/decoded/stored counts, gaps, reconnect events, CPU/RAM
and database integrity. Disconnect/reconnect the same meter, then test a different
serial (must not silently join the same session). Test graceful stop, browser
closure, application restart and forced power-loss recovery on a disposable home.
Check exported counts and values against SQLite and known meter readings.

## Soak acceptance

The simulator must run **24 elapsed hours**, not merely generate timestamps spanning
a day. Store count, gaps, resource usage and integrity results in a test artifact.
Accelerated tests may cover large archives and simulated timelines but do not
replace the elapsed-time soak. Pending results must remain explicitly pending.

## Beta limitations

No hardware or calibration accuracy is asserted. Other meters, BLE, Windows service
installation, remote access, multi-user permissions and regulated laboratory
certification are outside scope. Very large charts use quantity-separated extrema
sampling; exports and statistics use full data. Session offset pagination should
be used against a quiescent archive for a stable multi-page listing.

Actual command results and remaining gates belong in `VALIDATION.md`; do not mark
unexecuted tests as passed. Historical specifications in `docs/history` do not
override this release specification.
