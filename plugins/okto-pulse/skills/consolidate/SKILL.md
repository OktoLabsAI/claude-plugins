---
name: consolidate
description: Use this skill when a stage has just completed or the KG may be out of date — also chained into by okto-pulse:validate on the success path, and loaded by the okto-pulse:kg-curator agent. Begins consolidation, registers node/edge candidates for the current artifact, commits, verifies health, and reprocesses dead letters.
disable-model-invocation: false
user-invocable: true
allowed-tools: Bash, Read, Write, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_kg_begin_consolidation, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_kg_add_node_candidate, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_kg_add_edge_candidate, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_kg_commit_consolidation, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_kg_abort_consolidation, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_kg_health, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_kg_dead_letter_list, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_kg_dead_letter_reprocess
---

# okto-pulse:consolidate

Procedural KG consolidation skill. Loaded by the `okto-pulse:kg-curator` agent or chained into by `okto-pulse:validate` on the success path.

## Inputs

- `$STATE_DIR/flow-state.json` → `current_artifact.type` and `current_artifact.id`
- Optional override via parent prompt: `ARTIFACT_TYPE`, `ARTIFACT_ID`

## Workflow

### 0. Resolve per-project state

```bash
STATE_DIR=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/resolve_project_state.py" --cwd "$PWD")
```

### 1. Resolve target artifact

- Read `$STATE_DIR/flow-state.json`. Use `current_artifact.type` and `current_artifact.id` unless overridden by the parent prompt.

### 2. Capture pre-state

- Call `okto_pulse_kg_health`. Record node/edge counts as `before`.

### 3. Begin consolidation

- `okto_pulse_kg_begin_consolidation` for the artifact. Capture the consolidation handle.

### 4. Register candidates

For the artifact and its near neighborhood, add nodes and edges:

- `okto_pulse_kg_add_node_candidate` for the artifact and any newly created decisions, business rules, scenarios, contracts, cards, or design records.
- `okto_pulse_kg_add_edge_candidate` for relationships: artifact → derived_from, card → links_to_scenario, decision → considered_alternative, design → diagrams_spec, etc.

If candidate registration errors out unexpectedly, call `okto_pulse_kg_abort_consolidation` and report the failure.

### 5. Commit

- `okto_pulse_kg_commit_consolidation` to atomically merge candidates.

### 6. Health check

- `okto_pulse_kg_health`. All checks must be green.
- If red: examine the failing checks and decide whether the consolidation needs a rollback (`abort` is only valid pre-commit; for post-commit issues, surface the failure rather than auto-rollback).

### 7. Dead-letter cleanup

- `okto_pulse_kg_dead_letter_list`. If non-empty, `okto_pulse_kg_dead_letter_reprocess` and re-check health.

### 8. Return summary

When loaded by the `okto-pulse:kg-curator` agent, the agent will format the `===REPORT===` JSON. Provide:

- node_count_delta: `after.nodes - before.nodes`
- edge_count_delta: `after.edges - before.edges`
- health_status: `"green"` | `"red"` (with failing-check names)
- dead_letters_reprocessed: int

## Invariants

- Health MUST be green before declaring consolidation done.
- `abort` is pre-commit only.
- Never edit the graph file directly. Always go through MCP.
