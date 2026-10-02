# Building and testing

Use Python 3.13 x64, Node 22 and Inno Setup 6.7.3 on Windows.

```powershell
uv sync --extra dev --locked
cd ui
npm ci
npm run build
npm run lint
npm test -- --run
npm run build-storybook
npx playwright install chromium
npm run test:ui
npm run test:acceptance
cd ..
uv run python -m pytest
uv run python -m elmetron.cli.app validate-config --show-effective
uv run python scripts/collect_licenses.py
uv run pyinstaller --noconfirm packaging/elmetron.spec
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' packaging/elmetron.iss
```

For source development: `uv run python -m elmetron.cli.app serve --open-browser`.
For UI development run the backend first, then `npm run dev` in `ui`; its proxy
preserves local cookie/CSRF behavior. Production serves `ui/dist` with Waitress.

`Elmetron.exe` is the browser launcher. `elmetron-cli.exe` is the console executable
for serve, MCP, config validation, USB discovery and exports. Both share `_internal`
resources and must remain in one directory. No FTDI DLL is bundled.

Build output: `dist/Elmetron`, installer: `dist/installers`.
Run `scripts/test_installer.ps1` with explicit disposable install/data directories.
Run `scripts/soak.py --hours 24 --data-dir PATH` for an elapsed-time simulator soak;
the JSON result is written only when completed or interrupted. Hardware gate is
described in [RELEASE_SPEC.md](RELEASE_SPEC.md).

The CI publishes build artifacts on pull requests; release publication is controlled
by a version tag. Visual baselines belong to the Windows Chromium runner. Dependency
license inventory must be regenerated after dependency changes.

After committing the exact tested source, `uv run python scripts/release_artifacts.py`
creates the source ZIP, source commit record and SHA256SUMS in `dist/installers`.
The tagged CI repeats installer and packaged MCP checks before publishing a beta.
