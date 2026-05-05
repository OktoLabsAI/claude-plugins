---
name: flow
description: Use this skill when the user wants to continue or start an SDLC flow — it acts as the state-machine router that reads flow-state.json, dispatches every non-card stage to the matching specialist agent via the Task tool, and loads the task skill via the Skill tool for card-stage parallel fan-out. Automatically routes to the correct stage based on current flow state.
disable-model-invocation: false
user-invocable: true
allowed-tools: Bash, Read, AskUserQuestion, Task, Skill, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_my_profile, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_list_blockers
---

# okto-pulse:flow

State-machine router for the Pulse SDLC flow. Reads `flow-state.json`, determines the current stage, and dispatches to the matching agent (or, for card stage, the matching skill). Agents run in zero-confirmation isolated context and load their paired procedural skill via the Skill tool.

## Architecture

```
Non-card stages:
  okto-pulse:flow  (router)
      └─► Task → okto-pulse:<stage-agent>  (zero-confirmation, isolated)
                    └─► Skill → okto-pulse:<paired-skill>  (procedural inline)

Card stage:
  okto-pulse:flow  (router)
      └─► Skill → okto-pulse:task  (DAG fan-out coordinator)
                    └─► Task × N (one message, parallel, run_in_background)
                          └─► okto-pulse:<card-agent>
                                  └─► Skill → okto-pulse:<role-loop skill>

Spec arch-missing branch (inside the spec skill, loaded by spec-writer):
  spec skill
      └─► Task → okto-pulse:architect
                    └─► Skill → okto-pulse:architect-loop
```

The router never writes flow-state. Each procedural skill writes its own next-stage entry via `scripts/atomic_write.py`. The router only READS flow-state.

## Stages

`draft → ideation → refinement → spec → sprint → card → validation → release`

## Workflow

### 0. Auth preflight

Call `okto_pulse_get_my_profile` as the very first MCP call. This catches stale or scope-mismatched tokens before they surface mid-stage (Family 2 in the historical scan: 8 cases of `list_my_boards` failing mid-session despite `kg_health` having worked moments earlier).

If the call errors, print the error message followed by:

> Auth failed against Pulse MCP. Run `/okto-pulse:doctor` and choose `pulse_api_token_set` to clear and re-prompt for the API token. ABORTING — no stage will be dispatched until auth is healthy.

Then stop. Do NOT dispatch any stage.

### 1. Read flow state

Resolve the per-project state directory and read flow-state from there:

```bash
STATE_DIR=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/resolve_project_state.py" --cwd "$PWD")
```

```
Read "$STATE_DIR/flow-state.json"
```

If the file does not exist, treat `current_stage` as `draft`. Per-project state means the resolver returns
`${CLAUDE_PLUGIN_DATA}/projects/<key>/` (key derived from `git rev-parse --show-toplevel`, falling back to absolute
cwd) — switching projects no longer inherits another project's flow state.

### 1b. Blocker preflight

After reading flow-state but BEFORE dispatching, call `okto_pulse_list_blockers` for the active board (read from `$STATE_DIR/active-board.json`). Pulse exposes typed blockers: `dependency_blocked, on_hold, stale, spec_pending_validation, spec_no_cards, uncovered_scenario`.

- If `total > 0`, especially when a blocker references the artifact in `current_artifact`, surface a triage line per blocker (`<type>: <artifact_id> — <reason>`) and ask the user via `AskUserQuestion` whether to:
  - "Address blockers first" — stop dispatch, suggest `/okto-pulse:status` for the full list.
  - "Proceed to <stage>" — continue dispatch.
- If `total == 0`, continue silently.

Do not silently advance into a stage when known blockers exist on the artifact.

### 2. Tiebreaker

When `current_stage` is ambiguous (e.g., still has open Q&A on the current artifact), stay on the current stage rather than advancing. The agent invoked next will resolve the ambiguity.

### 3. Dispatch

For non-card stages, issue exactly one `Task` call with `subagent_type` from this table. The agent will load its paired procedural skill via the Skill tool and execute it end-to-end.

| `current_stage` | Dispatch shape | Target |
|---|---|---|
| `draft` (no state) | Task → agent | `okto-pulse:ideation-analyst` |
| `ideation` | Task → agent | `okto-pulse:ideation-analyst` |
| `refinement` | Task → agent | `okto-pulse:refinement-investigator` |
| `spec` | Task → agent | `okto-pulse:spec-writer` |
| `sprint` | Task → agent | `okto-pulse:sprint-planner` |
| `card` | Skill → skill | `okto-pulse:task` |
| `validation` | Task → agent | `okto-pulse:qa-engineer` (with `MODE=validation`) |
| `release` | Task → agent | `okto-pulse:kg-curator` (final consolidation), then flow complete |

#### 3a. Non-card stages — Task call shape

```
Task →
  subagent_type: "okto-pulse:<agent>"
  description: "<stage> stage"
  prompt: |
    BOARD_ID=<active board id>
    <stage-specific keys>
    PLUGIN_ROOT=${CLAUDE_PLUGIN_ROOT}
```

Stage-specific keys per the input contract on each agent:

- `ideation-analyst`: `IDEATION_ID` (omit if creating new)
- `refinement-investigator`: `IDEATION_ID`, `REFINEMENT_ID` (omit if creating new)
- `spec-writer`: `REFINEMENT_ID`, `SPEC_ID` (omit if deriving fresh)
- `sprint-planner`: `SPEC_ID`
- `qa-engineer` at validation: `MODE=validation`, `SPRINT_ID`
- `kg-curator` at release: `ARTIFACT_TYPE`, `ARTIFACT_ID` (read from flow-state)

After the agent returns its `===REPORT===` JSON, the router re-reads `$STATE_DIR/flow-state.json` to verify the agent's procedural skill advanced the stage. If `status=FAIL` in the report, surface the blockers to the user via `AskUserQuestion` and stop — do not auto-retry.

#### 3b. Card stage — Skill call shape

```
Skill →
  skill: "okto-pulse:task"
```

The `task` skill performs DAG-based parallel fan-out internally (one message containing N parallel Task calls per dependency wave) and writes flow-state to `validation` when complete.

## Safety

- Always run the **auth preflight (Step 0)** first; it is the cheapest signal that the MCP wiring is healthy.
- Always run the **blocker preflight (Step 1b)** before dispatching, even when the active board is "quiet" — `list_blockers` is server-side and free to call.
- Always read `$STATE_DIR/flow-state.json` before dispatching — never infer the stage from conversation context.
- If `current_stage` is not in the valid enum, ask the user via `AskUserQuestion` to reset flow state. Do not guess.
- Never call `okto_pulse_*` MCP tools directly from this skill — that's the agents' (and their loaded skills') job.
- Never spawn more than one agent per router invocation (except via the `task` skill's documented fan-out, which runs in its own context).
- The router never writes flow-state. If something goes wrong mid-dispatch, the procedural skill's atomic write is the source of truth.
