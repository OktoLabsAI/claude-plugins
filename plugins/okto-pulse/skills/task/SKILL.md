---
name: task
description: Use this skill when okto-pulse:flow routes to current_stage=card and owns the parallel fan-out per dependency wave. Builds a DAG-based parallel fan-out that dispatches each in-progress card to the matching specialist subagent in waves and aggregates JSON reports.
disable-model-invocation: false
user-invocable: true
allowed-tools: Bash, Read, Write, Task, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_list_cards_by_status, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_card, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_card_dependencies, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_task_context, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_move_card, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_sprint, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_list_sprints, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_move_sprint
---

# okto-pulse:task

Card stage skill. Builds a dependency DAG over all `in_progress` cards in the active sprint, then dispatches each wave (cards whose dependencies are all satisfied) as ONE message containing N parallel `Task` calls. Aggregates the `===REPORT===` JSON from each agent between waves, then advances the flow to validation.

## Card-type → agent map

| Card type | `subagent_type` | Agent `MODE` (if needed) |
|---|---|---|
| `implementation` | `okto-pulse:implementer` | — |
| `test` / `qa` | `okto-pulse:qa-engineer` | `MODE=card` |
| `architecture` | `okto-pulse:architect` | — |
| `knowledge` / `docs` | `okto-pulse:kg-curator` | — |
| `planning` | `okto-pulse:sprint-planner` | — |

If a card's type is not in this table, mark it blocked with reason `"unsupported card type"` and skip — do NOT call `AskUserQuestion` (this skill is zero-confirmation since it operates inside a fan-out coordinator).

## Workflow

### 0. Resolve per-project state

```bash
STATE_DIR=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/resolve_project_state.py" --cwd "$PWD")
```

`STATE_DIR` is the per-project state directory under `${CLAUDE_PLUGIN_DATA}/projects/<key>/`.

### 1. Read sprint id

Read `$STATE_DIR/flow-state.json` and extract `current_artifact.id` as `SPRINT_ID`.

### 2. Snapshot cards + dependencies

- `okto_pulse_list_cards_by_status` with `sprint_id=SPRINT_ID`, `status=in_progress`. Capture the card list as `OPEN`.
- For each card in `OPEN`:
  - `okto_pulse_get_card` to capture full payload (id, type, title).
  - `okto_pulse_get_card_dependencies` to capture the dep list.

### 3. Build DAG

For each card, mark its `unmet_deps` as the subset of dependency ids that are not currently in status `done`. (Other statuses — `in_progress`, `blocked`, etc. — count as unmet.)

### 4. Wave loop

Repeat until `OPEN` is empty:

1. **Compute wave** — `WAVE` = every card in `OPEN` whose `unmet_deps` is empty.
2. **Cycle detection** — if `WAVE` is empty but `OPEN` is not: a cycle or universally-blocked dependency exists. Mark each remaining card `blocked` with reason `"unresolvable dependency: <list>"` and break out of the loop.
3. **Fan out the wave as ONE message** containing N parallel `Task` calls. Each call uses:
   - `subagent_type`: from the card-type → agent map.
   - `description`: `"[CARD-<CARD_ID>] <short title>"` — the `[CARD-<id>]` prefix is **MANDATORY**: the `task-completed-card-sync.sh` hook scans `task_subject` for this exact prefix to discover which Pulse card to move on TaskCompleted. Without it, the hook silent-exits and the card never advances.
   - `run_in_background`: `true`.
   - `prompt`: heredoc with all keys the agent needs:

   ```
   Task →
     subagent_type: "<from map>"
     description: "[CARD-<CARD_ID>] <title>"
     run_in_background: true
     prompt: |
       BOARD_ID=<board_id>
       SPRINT_ID=<SPRINT_ID>
       CARD_ID=<card_id>
       CARD_TYPE=<card.type>
       MODE=card
       PLUGIN_ROOT=${CLAUDE_PLUGIN_ROOT}
   ```

   Note: `MODE=card` is required for `qa-engineer`; including it on every agent is harmless because non-qa agents ignore it.

4. **Wait** for all parallel Task returns. Parse `===REPORT===` JSON from each.
5. **Reconcile card status**: for each card in this wave, call `okto_pulse_get_card`. If the agent's report says `moved_to: "done"` but the card is not actually `done`, call `okto_pulse_move_card` to `done`. If the report says `blocked`, call `okto_pulse_move_card` to `blocked` with the agent's reason. (Agents are expected to move their own cards; this is a defensive sweep.)
6. **Update DAG**: for each newly-`done` card, remove it from `OPEN` and remove its id from every other card's `unmet_deps`.

### 5. Close the active sprint

When `OPEN` is empty:

- Call `okto_pulse_get_sprint` to confirm all cards are `done` (or `blocked` with reason).
- Call `okto_pulse_move_sprint` to `closed` for `SPRINT_ID`.
- Capture the sprint's `spec_id` from the response.

### 6. Multi-sprint cascade

After closing the sprint, decide where flow goes next:

- Call `okto_pulse_list_sprints` for `spec_id`.
- If ≥1 sprint on the spec is in `draft` status → cascade back to **sprint stage** so the sprint skill (continuation mode) activates the next draft. Atomic flow-state write:

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/atomic_write.py" \
    "$STATE_DIR/flow-state.json" \
    '{"current_stage":"sprint","current_artifact":{"type":"spec","id":"<spec_id>"},"last_handoff":{"from_skill":"task","at":"<iso8601>","reason":"sprint <SPRINT_ID> closed; draft sprints remain"}}'
  ```

- If all sprints are `closed` → advance to **validation** for the spec as a whole:

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/atomic_write.py" \
    "$STATE_DIR/flow-state.json" \
    '{"current_stage":"validation","current_artifact":{"type":"sprint","id":"<SPRINT_ID>"},"last_handoff":{"from_skill":"task","at":"<iso8601>","reason":"all sprints closed"}}'
  ```

If `OPEN` is empty BUT the wave loop reduced to "all remaining cards blocked" (no progress possible), do not close the sprint. Instead write flow-state with `current_stage: "card"` and a `blockers` note for the user, then stop.

## Invariants

- One message per wave. Inside that message, N parallel `Task` calls with `run_in_background: true`.
- Never serialize the wave — that defeats the whole point of the DAG.
- Never spawn a card-agent with anything other than its own `CARD_ID`. No batching.
- Cycle detection: never loop forever. If a wave is empty but `OPEN` is not, mark survivors blocked and exit.
- The skill never writes code, never calls `okto_pulse_submit_task_validation`, never calls `okto_pulse_link_task_to_*`. Those belong to the agents.
- Self-contained prompts: each agent's prompt must contain every key it needs.
