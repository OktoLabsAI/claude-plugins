---
description: Print a summary of the current flow state, board, blockers, and KG health.
when_to_use: Quick orientation check to see where you are in the SDLC flow and whether the active board has any open blockers.
disable-model-invocation: false
user-invocable: true
allowed-tools: Bash, Read, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_list_blockers, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_kg_health, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_ideation, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_refinement, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_spec, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_sprint, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_card
---

# okto-pulse:status

Prints the current flow state, the active board's blocker summary, and KG health in a human-readable summary. Read-only — never writes anything.

## Workflow

### 0. Resolve per-project state

```bash
STATE_DIR=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/resolve_project_state.py" --cwd "$PWD")
```

`STATE_DIR` resolves to `${CLAUDE_PLUGIN_DATA}/projects/<key>/` where `<key>` derives from `git rev-parse --show-toplevel` (or the absolute cwd for non-repo dirs). Each project keeps its own active board + flow state.

### 1. Read flow state + active board

- Read `$STATE_DIR/flow-state.json`. If missing, print `"No flow state found. Run /okto-pulse:flow to start."` and continue (do not abort — blockers + KG health may still be useful).
- Read `$STATE_DIR/active-board.json`. If missing, print `"No active board. Run /okto-pulse:setup."` and skip Step 2.

### 2. Blockers summary

Call `okto_pulse_list_blockers` against the active `board_id`. The server exposes typed blockers: `dependency_blocked, on_hold, stale, spec_pending_validation, spec_no_cards, uncovered_scenario`.

- If `total == 0`: print `"Blockers: none"`.
- If `total > 0`: print a per-type roll-up, then one line per blocker:

  ```
  Blockers: total=<N>  (dependency_blocked: 2, stale: 1, ...)
    - <type> <artifact_id>: <reason>
    - <type> <artifact_id>: <reason>
  ```

### 3. KG health

Call `okto_pulse_kg_health` with `board_id`. Print one line:

```
KG: <green|red>  nodes=<n>  edges=<m>  dead_letters=<k>
```

Mark red when any check fails, with the failing-check name(s) appended.

### 4. Current artifact

If flow-state has `current_artifact`, look up its current status with the matching `get_*`:

| `current_artifact.type` | tool |
|---|---|
| `ideation` | `okto_pulse_get_ideation` |
| `refinement` | `okto_pulse_get_refinement` |
| `spec` | `okto_pulse_get_spec` |
| `sprint` | `okto_pulse_get_sprint` |
| `card` | `okto_pulse_get_card` |

Print one line:

```
Artifact: <type> <id> v<version> status=<status>
```

### 5. Print full summary

```
Project state:    $STATE_DIR
Active board:     <board_name> (<board_id>)
Current stage:    <current_stage>
Artifact:         <type> <id> v<version> status=<status>
Last handoff:     <last_handoff.from_skill> at <last_handoff.at>
Blockers:         <summary line from Step 2>
                  (per-blocker lines if any)
KG:               <summary line from Step 3>
```

## Invariants

- Read-only. Never call `move_*`, `evaluate_*`, `submit_*`, `kg_begin_consolidation`, `kg_commit_consolidation`, `kg_dead_letter_reprocess`, or any other state-changing tool.
- Never edit `flow-state.json` or `active-board.json`.
- Empty / missing state files = informational message + continue. Don't abort the whole status print on a missing artifact.
