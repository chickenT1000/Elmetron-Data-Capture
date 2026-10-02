# Contributing

Contributions are accepted under GPL-3.0-only. By submitting a contribution you
confirm you can license it on those terms. Do not include laboratory records,
operator names, tokens, logs or local configuration in a pull request.

Use Python 3.13 and Node 22. Run `uv sync --extra dev --locked`, `npm ci` in `ui`,
then `uv run pytest`, `npm run build`, `npm run lint`, and `npm test -- --run`.
See [BUILD.md](docs/BUILD.md) for Windows packaging and browser acceptance tests.

Explain the behavior changed, the validation performed and any hardware tested.
Changes to capture, storage or recovery need failure-path regression tests.
Protocol changes need actual CX-505 traces with identifying data removed and a
documented hardware test. Never infer an instrument command from a mock.
