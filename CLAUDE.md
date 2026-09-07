# tuya-ble-sdk

Python SDK speaking the Tuya BLE GATT protocol directly. Standalone — knows
nothing about Home Assistant. See `README.md` for the session model (one read =
connect, handshake, collect, disconnect), the public API, and the CLI.

## Releasing (footgun)

Versioning is automated by release-please (`release-please-config.json`,
`.release-please-manifest.json`). **Never hand-edit `version` in `pyproject.toml`
or the manifest** — a merged commit `chore: let release-please own the version`
handed that job away. Commits must be Conventional Commits; their `type:`
picks the changelog section and drives the bump.

Release flow (`.github/workflows/release.yml`): a push to `main` with green CI
lets release-please groom/tag a release PR and publish the tag to PyPI. A PR
with green CI does **not** cut a release (`workflow_run.event == 'push'` guards
it). `uv.lock` is refreshed on the release branch so it lands with the new
version.

## Downstream coupling

Consumed by the `ha-tuya-ble` integration, which pins this from its
`manifest.json`. Changing the public API (`src/tuya_ble_sdk/__init__.py`) breaks
it. Runtime dependencies carry a `>=` floor and **nothing else** (no `==`, no
upper bound): HA pins its own transitive deps exactly, so any tighter pin here
eventually contradicts HA's and the integration stops installing. Rationale is
in the comment above `dependencies` in `pyproject.toml`.

## Gotchas in the protocol

Signed datapoint reports (`0x8004` / `0x8005`) are recognised and logged, not
parsed — see README "Not implemented". A device using them reads back as no
datapoints with the command name in the debug log.
