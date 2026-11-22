#!/usr/bin/env bash
# Heavy checks that PR CI does not run: MuJoCo smoke tests, USD (pxr) round
# trips, the vuer event handlers, and the example script. Run before you open a
# PR that touches physics, usd, table, sensor, scene or viewer code, and tick
# the box in the PR template. The "heavy" workflow runs the same script by
# manual dispatch.
set -euo pipefail
cd "$(dirname "$0")/.."

uv sync --group dev --group heavy
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest            # all tests, heavy markers included
bundle="$(mktemp -d)"
cp -r examples/lab_table/. "$bundle"
uv run python examples/build_material_table.py "$bundle"
echo "local checks passed"
