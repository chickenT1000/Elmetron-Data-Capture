# Release Automation Checklist

Use this checklist when packaging a capture dataset for distribution via CI/CD or manual release.

## Prerequisites
- Latest code merged into the release branch; version stamped in `SPEC.md` and `config/app.toml`.
- Capture database (`data/elmetron.sqlite`) contains the sessions to publish; run exports/analytics smoke tests beforehand.
- Ensure `config/templates/` holds the correct PDF/LIMS templates for the release.

## Steps
1. (Optional) Dry-run the exporter to verify selection:
   ```powershell
   python scripts/build_release_bundle.py --dry-run --latest 1 --manifest-version <version>
   ```
2. Generate the release bundle (CI can pass `--stamp ${{ github.run_id }}` or similar):
   ```powershell
   python scripts/build_release_bundle.py --latest 1 --manifest-version <version>
   ```
   - Replace `--latest 1` with `--session`, `--sessions`, or `--session-range` for explicit selection.
   - Add `--config` / `--protocols` if the pipeline uses non-default paths.
   - Use `--no-gzip` when downstream tooling cannot handle `.gz` assets.
3. Collect artefacts from `exports/releases/<stamp>/`:
   - `<prefix>_archive.zip`
   - `<prefix>_archive_summary.json`
   - `<prefix>_manifest.json`
   - `<prefix>_sha256.txt`
   - `release_bundle.json`
4. Publish artefacts to the release destination (GitHub Release, shared drive, or LIMS uploader) together with `release_bundle.json`.
5. Record the manifest checksum in release notes or ticketing system for traceability.

## CI Integration Tips
- Cache the Python environment so the exporter imports resolve quickly; install optional deps (`jinja2`, `reportlab`) as needed for templates.
- Set `ELMETRON_EXPORTER_VERSION` environment variable and pass it to `--manifest-version`.
- Post-run verification: `python -m json.tool exports/releases/<stamp>/release_bundle.json` to ensure JSON integrity.
- Add a pipeline step that runs `Get-FileHash` (or `sha256sum`) on the archive and compare with `<prefix>_sha256.txt`.

## Follow-ups
- Update `docs/SPRINT4_NOTES.md` once CI jobs consume this checklist.
- Extend automated tests to include a smoke run of `scripts/build_release_bundle.py` against fixture databases.
