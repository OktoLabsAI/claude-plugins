# Changelog

All notable changes to the **oktolabs-plugins** marketplace and the
flagship **okto-pulse** plugin live here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the
versions track the okto-pulse pip release 1:1 (per business rule
`br_967ba381`).

## [Unreleased]

### Added

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
