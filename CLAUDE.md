# Conventions for coding agents

- Python: `uv` only. `make check` runs what PR CI runs (lint, typecheck, fast tests).
  `./scripts/local-checks.sh` runs the heavy tests (MuJoCo, USD, vuer) and the example.
- PR CI stays cheap: no MuJoCo, USD, rendering, screenshots or GPU in PR workflows.
  Heavy tests carry the `mujoco`, `usd` or `viewer` marker and skip without the dependency.
- The core (`vuer_sim`) imports only numpy. Import `mujoco`, `pxr` and `vuer` inside the
  functions or modules that need them (`usd.py`, `viewer.py`, `scene.py`).
- Stored JSON uses `vuer_sim._fmt.dumps`: sorted keys, 2-space indent, trailing newline.
  The TS package (`@vuer-ai/vuer-sim`) writes byte-identical text; change both together.
- Every change after the first commit goes through a PR. Commit as Ge Yang <ge@fortyfive.ai>.
- Release: `Release vX.Y.Z` PR bumps `pyproject.toml` and `CHANGELOG.md`; after merge,
  `make release` tags and publishes. Do not publish from a branch.

## Docs (dockit)

- Doc pages live at `docs/pages/<slug>/+Page.mdx` (Vike file routing).
- Frontmatter: `{ title, section, order, description, draft?, hidden?, noindex? }`. Flat values only.
- The sidebar derives from frontmatter; `docs/site.config.ts` holds `initDocs(...)`, the
  section order and the skill triggers.
- `skills/vuer-sim/` is generated: run `pnpm --dir docs gen:llms` after editing pages and
  commit the result. `pnpm --dir docs check:llms` fails when it drifts (docs CI runs it).
- Product changes update the docs, the skill and the example in the same PR.
