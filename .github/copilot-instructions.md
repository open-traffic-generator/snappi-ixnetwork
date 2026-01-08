## Quick orientation for AI assistants

This file gives focused, actionable guidance for editing and extending the snappi-ixnetwork repo.

Highlights
- Purpose: an adapter implementing the snappi API for Keysight IxNetwork. Main code lives in `snappi_ixnetwork/`.
- Typical runtime: create an API handle via `snappi.api(location=..., ext='ixnetwork')` → build `config()` → call `api.set_config(cfg)` → use `api.control_state()` and `api.get_metrics()`.

Where to look first
- `snappi_ixnetwork/snappi_api.py` — primary implementation and entry points (session management, helpers, and features like `capture`, `vport`, `traffic_item`).
- `snappi_ixnetwork/ixnetworkconfig.py` — example of OpenApi-style iterators and typed setters used across the package.
- `tests/conftest.py` and `tests/utils/common.py` — canonical test fixtures, settings handling and helpers (`settings` singleton, `configure_credentials`, `start_traffic`, `wait_for`).
- `tests/settings.json` — concrete runtime values used by integration tests (API server address, ports, credentials).

Developer workflows & commands
- Setup dev environment: `scripts/setup-env.sh` (or follow `contributing.md`). The repo uses Python >=3.7 and `requirements.txt`/`pyproject.toml`.
- Install editable package for development: `python -m pip install -e '.[dev]'`.
- Run tests: `python -m pytest tests/` (tests expect a live IxNetwork API Server unless you mock `snappi.api`).
- Override test settings: set `SETTINGS_FILE=/path/to/file.json` or pass pytest CLI options (registered in `tests/conftest.py`, e.g. `--location`, `--ports`).

Code & style conventions specific to this project
- Use the builder/chained API pattern already present: e.g. `cfg = api.config(); tx, rx = cfg.ports.port(...).port(...); flow.tx_rx.port.tx_name = tx.name`.
- OpenApi iterator pattern: follow `snappi.snappi.OpenApiIter` implementations in `ixnetworkconfig.py` when adding collection-like helpers.
- Tests centralize runtime behavior in `tests/utils/common.py`: add helpers there rather than duplicating logic in tests.
- Logging and credentials: tests call `utl.configure_credentials(api, username, psd)` to set `api.username`/`api.password` — avoid hardcoding secrets in code.

Integration notes & gotchas
- Many tests are integration tests and require a reachable IxNetwork API (`tests/settings.json.location`). If access is unavailable, provide a mocked `api` implementing `set_config`, `set_control_state`, and `get_metrics`.
- Dependency versions matter (`snappi`, `ixnetwork-restpy`) — use the versions in `requirements.txt` for reproducibility.

When suggesting edits
- Prefer minimal, low-risk changes: unit tests, small refactors, doc updates. If changing public API, update tests and `snappi_ixnetwork.egg-info/SOURCES.txt` as needed.
- For new features that interact with IxNetwork, include an offline-friendly unit test or a clear integration-only label.

If anything is missing or unclear, tell me which slice to expand (examples: a mock `api` fixture, a sample unit test, or more patterns from `snappi_ixnetwork/snappi_api.py`).
