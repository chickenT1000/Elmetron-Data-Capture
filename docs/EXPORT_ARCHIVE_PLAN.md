# Export Archive Automation

## Overview
The exporter CLI now produces distribution-ready bundles that include the artefacts, manifest, checksums, and an archive summary. The helper script `scripts/build_release_bundle.py` wraps these options so release engineers can generate a consistent payload in a single command.

## Workflow
1. Ensure the capture database and configuration files reflect the sessions you intend to publish.
2. Run the release helper (example exports the latest session):
   ```powershell
   python scripts/build_release_bundle.py --latest 1 --manifest-version 1.0.0
   ```
   Options:
   - `--session/--sessions/--session-range/--latest` select the sessions.
   - `--formats` controls file formats (defaults to `csv json xml pdf`).
   - `--no-gzip` disables gzip compression if downstream systems expect plain files.
   - `--prefix` sets a filename prefix; otherwise the exporter uses `session_<id>` tokens.
   - `--stamp` overrides the timestamped release directory inside `exports/releases/`.
3. The script writes to `exports/releases/<stamp>/`:
   - `<prefix>_archive.zip` containing artefacts, manifest, and checksums.
   - `<prefix>_archive_summary.json` describing the archive metadata (size, checksum, manifest snapshot).
   - `release_bundle.json` top-level summary for automation pipelines.

## Manifest & Checksum Contents
- `manifest.json` captures tool metadata (name, version, Python, platform), config/protocol fingerprints, artefact inventory, and aggregate sizes.
- `<prefix>_sha256.txt` lists SHA256 hashes for each artefact plus the manifest entry (`MANIFEST …`).
- When the archive is built, the summary JSON records the archive checksum, size, and relative file path; use it when publishing to external systems.

## Automation Notes
- Invoke the script from CI/CD after tagging a release; upload both the archive (`*_archive.zip`) and the summary (`*_archive_summary.json`) along with `release_bundle.json`.
- Pass `--manifest-version` with the application version so consumers can trace the bundle origin.
- The script honours `config/app.toml` and `config/protocols.toml` by default; override paths via `--config/--protocols` when using alternate locations.
- Use `--dry-run` first to inspect the underlying exporter command before execution.

## Testing
- Unit coverage lives in `tests/test_reporting_exporters.py`; integration tests should invoke `python scripts/build_release_bundle.py --dry-run` and full runs against fixture databases.
- Validate resulting archives by recomputing checksums (e.g. `Get-FileHash archive.zip -Algorithm SHA256`) in deployment pipelines.
