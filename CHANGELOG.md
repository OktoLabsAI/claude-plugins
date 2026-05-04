# Changelog

All notable changes to the **oktolabs-plugins** marketplace and the
flagship **okto-pulse** plugin live here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the
versions track the okto-pulse pip release 1:1 (per business rule
`br_967ba381`).

## [Unreleased]

### Added

- **R2.2 — Bootstrap & ops impl.**
  - `plugins/okto-pulse/bin/bootstrap-local-pip.sh` (card `c12b1506`)
    -- python 3.12 probe, idempotent pip-install at `OKTO_PULSE_PIN_VERSION`,
    `okto-pulse init --agents`, optional background `okto-pulse serve`,
    `/readyz` polling. Documented exit codes 0/2/10/20/30 and SIGINT
    trap. NDJSON progress events on stdout, human-readable on stderr.
    Test seam `OKTO_PULSE_FORCE_NO_SERVE=1` skips the serve spawn.
  - `plugins/okto-pulse/bin/bootstrap-docker.sh` (card `da60159b`) plus
    `plugins/okto-pulse/deploy/docker-compose.yml` -- daemon probe,
    `docker pull`, `docker compose up -d`, `/readyz` polling on 8101.
    Compose template uses the **unprefixed** `okto-pulse-data` volume
    name per `tr_650168fd` / memory `project_okto_pulse_local_volume_gotcha`.
  - `plugins/okto-pulse/bin/bootstrap-remote.sh` (card `303d0e09`) --
    URL-shape regex, `/readyz` probe with Bearer header, MCP `kg_health`
    probe; no install or container ops. 401/403 -> exit 20, anything
    else -> exit 30, bad shape -> exit 10.
  - `plugins/okto-pulse/bin/doctor.sh` + `plugins/okto-pulse/skills/doctor/SKILL.md`
    (card `6a776702`) -- 11 deploy-mode-aware checks emitting one NDJSON
    line per check + a final summary; always exits 0. Doctor SKILL
    documents the 7-fix reversible auto-remediation matrix
    (BR `br_98c485f6`).
  - `plugins/okto-pulse/skills/setup/SKILL.md` (card `75184926`) with
    `disable-model-invocation: true` per FR1 / TR `tr_28ef09f0` so an
    agent cannot trigger first-run setup without consent.
  - `plugins/okto-pulse/hooks/hooks.json` (card `ca6353f5`) wires
    EXACTLY four hooks: `SessionStart` (matchers `startup` + `resume`),
    `PreCompact`, `Stop`, `TaskCompleted`. Every command path uses
    `${CLAUDE_PLUGIN_ROOT}/scripts/...sh` per `tr_e323eacd`. NO
    `UserPromptSubmit` (BR `br_be257eac`). All four scripts are
    bash 3.2-compatible, mode 0755 (`tr_198b3164`), and never block
    the session except for `Stop` returning a deliberate
    `{"decision":"block"}` per TR `tr_3004a6fc`.
  - `plugins/okto-pulse/scripts/ensure-pulse-up.sh` (card `1ad51f44`,
    SessionStart) probes `kg_health` + `get_unseen_summary` and emits
    a single system-reminder line; exits 0 even on Pulse-unreachable.
  - `plugins/okto-pulse/scripts/consolidate-on-compact.sh` (card
    `ca61ca5c`, PreCompact) calls `kg_begin_consolidation` ->
    `kg_commit_consolidation`, falling back to
    `kg_abort_consolidation` on either failure.
  - `plugins/okto-pulse/scripts/stop-validation-gate.sh` (card
    `7c92da9e`, Stop) lists `validation_pending` cards, fetches each
    card's task validation, and emits `decision=block` only when at
    least one returns `status=failed`.
  - `plugins/okto-pulse/scripts/task-completed-card-sync.sh` (card
    `8db215b6`, TaskCompleted) reads stdin event payload, exits silently
    when `metadata.pulse_card_id` is missing, otherwise calls
    `move_card` + `add_comment`.
  - `plugins/okto-pulse/scripts/atomic_write.py` -- plugin-local copy of
    `tools/state/atomic_write.atomic_write_json` so the installed plugin
    can persist `active-board.json` / `deploy-mode.json` without
    depending on the repo-level helper package.
  - All hook + helper scripts use a `MCP_CURL` indirection seam so tests
    can swap in a stub HTTP client without spinning up a real Pulse.
- **R2.2 -- interleaved tests.**
  - `tests/test_local_pip_serve_running.py` (card `d9a4c3a8`,
    scenario `ts_8e08df58`) -- exercises the script's branching all the
    way to `wait_readyz`; the full live-serve smoke is skipped on dev
    boxes that lack `okto-pulse` against python3.12.
  - `tests/test_doctor_autofix_restart_serve.py` (card `4973a709`,
    scenario `ts_988b5d64`) -- asserts NDJSON shape + at-least-one-red
    when no Pulse is reachable. Live restart-and-recover loop is
    skipped on the dev box.
  - `tests/test_stop_hook_blocks_only_on_failure.py` (card `7825b6ba`,
    scenario `ts_1d631873`) -- two sub-cases: failing validation -> block
    decision JSON; clean validations -> silent stdout. Mocks MCP via
    a stub `MCP_CURL` script.
- **R2.2 -- lifted R2.1 RED scaffolds.**
  - `tests/test_setup_one_prompt.py` -- now asserts the static
    deliverable shape (paths exist, scripts executable, frontmatter
    flags). Live `/okto-pulse:setup` driver harness deferred to R2.3.
  - `tests/test_remote_path_validates.py` -- parametrized URL-shape +
    unreachable-host cases; live-Pulse case is `pytest.skip`-ped.
  - `tests/test_precompact_consolidates_kg.py` -- happy-path and
    commit-fails-then-abort cases via the `MCP_CURL` mock.
  - `tests/test_helper_exit_codes.py` -- full failure-injection grid
    plus a real-SIGINT cancellation case (skipped on dev boxes that
    lack a Python 3.12 install of okto-pulse).

### Notes / quirks

- `set -e`/`pipefail` is **deliberately disabled** inside `doctor.sh`:
  every probe in the diagnostic encapsulates its own pass/fail decision,
  so a single failed sub-shell must not abort the whole inspection.
  All the bootstrap-* helpers keep `set -euo pipefail`.
- The `bootstrap-local-pip.sh` `OKTO_PULSE_FORCE_NO_SERVE` env var is a
  test-only seam (the JSON manifest does not surface it).
- macOS bash 3.2 baseline: no associative arrays, no `${var,,}`, no
  GNU `timeout`. Time budgets are enforced via `curl -m`.

- **R1.1 — RED-state pytest scaffolds.** Four leaf scenarios pinned in
  `tests/`: marketplace install (`ts_d3c447de`), kebab-case CI gate
  (`ts_e53d04fb`), version-consistency check (`ts_d6d14d62`), and
  no-token install across `local-pip` / `docker` deploy modes
  (`ts_659675c6`). Marked with `@pytest.mark.scenario/card/sprint/spec`
  so they map back to the Pulse SDLC lineage.
- **R1.2 — Foundation implementation.**
  - `.claude-plugin/marketplace.json` declaring the `oktolabs-plugins`
    marketplace and the `okto-pulse` plugin entry pointing at
    `./plugins/okto-pulse`.
  - `plugins/okto-pulse/.claude-plugin/plugin.json` per BR `br_cd626419`
    and decisions `dec_e4d8bae6`, `dec_90a662d2`, `dec_e59e2a08`,
    `dec_35c0f3ea`. Includes `mcpServers.okto-pulse` HTTP wiring and the
    `userConfig` block (`pulse_deploy_mode`, `pulse_mcp_url`,
    `pulse_api_token` (sensitive), `pulse_board_id`).
  - `plugins/okto-pulse/.claude-plugin/oktolabs-meta.json` sibling
    holding `compatible-pulse-range`, `support-channel`, and
    `dependencies`. **Spec deviation**: the R1.2 spec asked for these
    keys at the top level of plugin.json plus `enum` on the
    `pulse_deploy_mode` userConfig entry. The upstream Claude validator
    in CLI 2.1.126 rejects unknown top-level keys and unknown
    userConfig keys (`enum: Unrecognized key`, `agents/skills: Invalid
    input`). To keep `claude plugin validate` green (scenario
    `ts_a0e7dc6c`) the OktoLabs-specific fields were relocated to the
    sibling meta file; `enum` was dropped from `pulse_deploy_mode`
    (the deploy-mode constraint is still enforced by the
    `deploy-mode.schema.json` state schema and by the setup skill).
    `version_consistency_check.py` reads from the sibling first and
    falls back to plugin.json. The OktoLabs business-rule constraints
    those fields encoded are still enforced -- just from a file the
    Claude validator does not inspect.
  - `plugins/okto-pulse/state/schemas/{active-board,deploy-mode,flow-state,doctor-cache}.schema.json`
    JSON Schemas for the four state files.
  - `tools/state/atomic_write.py` (`atomic_write_text` /
    `atomic_write_json`) honouring the POSIX-rename atomicity contract
    from TRs `tr_0bca8958`, `tr_2dbe4461`, `tr_a9c5f04f` and BR
    `br_a427fe32`.
  - Seven CI checks under `tools/ci/`: `kebab_case_check.py`,
    `version_consistency_check.py`, `marketplace_lint.py`,
    `userconfig_completeness.py`, `secret_scan.sh`, `smoke_install.sh`,
    `validate_plugin.sh`.
  - `tools/release/build_tagged_marketplace.py` to produce the
    GitHub-pinned marketplace artifact for tagged releases (per
    scenario `ts_7bb8d426`).
  - GitHub Actions workflow `.github/workflows/ci.yml` running the full
    7-check suite plus pytest on the `[ubuntu-latest, macos-latest]`
    matrix (per TR `tr_c59d0fd0`, BR `br_86ef48d7`).
  - Three new R1.2 leaf scenarios: `ts_a0e7dc6c` (claude plugin
    validate clean), `ts_7bb8d426` (tagged-release marketplace pin),
    `ts_2bc10969` (atomic state write under SIGKILL).

## [0.1.14] - 2026-05-04

Initial public release of the `oktolabs-plugins` marketplace, mirroring
the `okto-pulse==0.1.14` pip release. Ships the marketplace manifest,
the okto-pulse plugin manifest, the four state-file schemas, the seven
CI checks, the tagged-release marketplace builder, the atomic-write
helper, and the leaf pytest scenarios above. Skill / agent / hook
bodies land in sprint R2.2.
