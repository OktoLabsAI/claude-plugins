# Contributing to oktolabs-plugins

Thanks for sending a patch. This is the **oktolabs-plugins** Claude Code
plugin marketplace; today it ships the **okto-pulse** flagship plugin.
The repo is mirrored 1:1 with the [okto-pulse](https://github.com/OktoLabsAI/okto-pulse)
pip release (business rule `br_967ba381`).

## Dev setup

```bash
git clone https://github.com/oktolabsai/claude-plugins.git
cd claude-plugins
python3.12 -m venv .venv
. .venv/bin/activate
pip install -e ".[test]"
pytest -v
```

You should see **8 passed** locally. Tests that depend on the
`claude` CLI or a live Pulse daemon will `pytest.skip` when those are
not present; CI is the strict gate.

## The 7 CI checks

Every PR runs **all seven** checks plus pytest, on both Ubuntu and
macOS (per business rule `br_86ef48d7` and technical requirement
`tr_c59d0fd0`). The full gate is hard -- no `continue-on-error`.

| # | Check | What it does |
|---|-------|--------------|
| 1 | `tools/ci/validate_plugin.sh` | `claude plugin validate plugins/okto-pulse`; fails on non-zero or any `WARN` line. |
| 2 | `tools/ci/marketplace_lint.py` | Asserts `marketplace.json` shape (name, owner email not example.com, plugins[] required fields, category=workflow) plus presence of `CHANGELOG.md` / `CONTRIBUTING.md`. |
| 3 | `tools/ci/kebab_case_check.py` | Walks `plugins/**/skills`, `agents`, `commands`; every component must match `^[a-z0-9]+(-[a-z0-9]+)*$`. |
| 4 | `tools/ci/userconfig_completeness.py` | Every `${user_config.X}` reference must resolve to a key declared in `plugin.json#userConfig`. |
| 5 | `tools/ci/version_consistency_check.py` | `plugin.json#version` and `compatible-pulse-range` (read from the sibling `.claude-plugin/oktolabs-meta.json`) must agree with the installed `okto-pulse` pip version. |
| 6 | `tools/ci/secret_scan.sh` | Runs `gitleaks` if installed (CI installs it; local dev gets a soft notice and skip). |
| 7 | `tools/ci/smoke_install.sh` | `claude plugin marketplace add` + `claude plugin install okto-pulse@oktolabs-plugins`. Skips locally if `claude` is missing. |

`pytest -v` is the eighth gate.

## Naming conventions

- All directory and file names under `plugins/<plugin>/skills/`,
  `agents/`, and `commands/` are **kebab-case**:
  `^[a-z0-9]+(-[a-z0-9]+)*$`. Hidden files, `__init__.py`, and
  top-level `*.md` files are exempt. CI fails the PR otherwise.
- Skills declared in `plugin.json#skills` resolve from the directory
  whose name matches the skill id.

## Hybrid source policy

`marketplace.json` ships two flavours of the same content:

- **On `main`** the entry uses a relative `source: "./plugins/okto-pulse"`.
  Direct clones of `main` work end-to-end with no extra build step.
- **On a tagged release** (`vX.Y.Z`) the release artifact is generated
  by `tools/release/build_tagged_marketplace.py`, which deep-copies
  the manifest and rewrites every `source` to a GitHub-pinned form:
  ```json
  { "source": "github", "repo": "oktolabsai/claude-plugins",
    "ref": "vX.Y.Z", "path": "plugins/okto-pulse" }
  ```
- The release artifact lands at `dist/marketplace-vX.Y.Z.json`.

Cutting a release:

```bash
python tools/release/build_tagged_marketplace.py \
    --tag v0.1.14 \
    --output dist/marketplace-v0.1.14.json
```

The script dogfoods `tools.state.atomic_write.atomic_write_json` so
that a partial write never lands in `dist/`.

## State files

Plugin state lives at runtime under **`${CLAUDE_PLUGIN_DATA}`**, NOT
`${CLAUDE_PLUGIN_ROOT}`. The plugin tree on disk is read-only at
runtime; state belongs in the per-installation data dir. Schemas:

- `plugins/okto-pulse/state/schemas/active-board.schema.json`
- `plugins/okto-pulse/state/schemas/deploy-mode.schema.json`
- `plugins/okto-pulse/state/schemas/flow-state.schema.json`
- `plugins/okto-pulse/state/schemas/doctor-cache.schema.json`

All state writes go through `tools.state.atomic_write.atomic_write_json`
so a SIGKILL never produces a partial or empty file (BR `br_a427fe32`,
TRs `tr_0bca8958`, `tr_2dbe4461`, `tr_a9c5f04f`).

## SDLC lineage

Every test in `tests/` carries `@pytest.mark.scenario / card / sprint /
spec` marks pointing back to the Pulse board
`39eecda7-ced0-4450-8b7c-9267b60826cb`. Don't add a new test without
a Pulse scenario id; don't change a scenario id without a Pulse
artifact update.
