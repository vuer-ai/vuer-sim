## Why

<!-- What problem does this change solve? The diff already shows what changed. -->

## Checks

PR CI runs lint, typecheck and the fast unit tests only.

- [ ] Ran `./scripts/local-checks.sh` (MuJoCo smoke tests, USD round trips, vuer handlers, example), or dispatched the `heavy` workflow, if this touches `physics`, `usd`, `table`, `sensor`, `scene` or `viewer`
- [ ] Updated the editor screenshot (`scripts/screenshot.py` in vuer-ai/vuer-sim-ts) if the editor protocol or the sample scene changed
- [ ] Updated `docs/pages/**` and ran `pnpm --dir docs gen:llms` (commits the regenerated `skills/vuer-sim/`)
- [ ] Added a `CHANGELOG.md` entry for user-visible changes
