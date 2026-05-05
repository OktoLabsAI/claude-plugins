---
name: refine
description: Use this skill when okto-pulse:flow routes to current_stage=refinement, or when the okto-pulse:refinement-investigator agent loads it. Runs the deep-investigation Q&A loop on a Pulse refinement artifact and advances to spec.
disable-model-invocation: false
user-invocable: true
allowed-tools: Bash, Read, Write, AskUserQuestion, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_refinement_context, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_ideation_context, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_create_refinement, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_list_refinement_qa, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_ask_refinement_question, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_answer_refinement_question, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_add_refinement_knowledge, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_move_refinement
---

# okto-pulse:refine

Procedural skill for the Pulse refinement stage. Drives the deep-investigation Q&A protocol on a refinement artifact and advances the flow to spec.

Loaded by the `okto-pulse:refinement-investigator` agent (during flow routing) or invoked directly.

## Inputs

- `$STATE_DIR/flow-state.json` → ideation id, optional refinement id
- Active board id from `$STATE_DIR/active-board.json`

`$STATE_DIR` is the per-project state directory (`${CLAUDE_PLUGIN_DATA}/projects/<key>/`)
returned by `resolve_project_state.py`.

## Workflow

### 0. Resolve per-project state

```bash
STATE_DIR=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/resolve_project_state.py" --cwd "$PWD")
```

### 1. Load context

- If a refinement already exists: `okto_pulse_get_refinement_context`.
- Otherwise: `okto_pulse_get_ideation_context` to load the upstream ideation.

### 2. Create refinement (if needed)

- If no refinement exists yet: `okto_pulse_create_refinement` linked to the ideation. Capture the new `refinement_id`.

### 3. Deep-investigation loop

Repeat until `okto_pulse_list_refinement_qa` reports zero open questions AND refinement knowledge is rich:

1. Call `okto_pulse_list_refinement_qa` to inventory open questions.
2. Investigate each one. Investigation may include:
   - Re-reading ideation knowledge.
   - Querying the KG for prior decisions on similar topics (`okto_pulse_kg_get_related_context`-shaped reasoning is acceptable but optional here).
   - Asking the user via `AskUserQuestion` when human judgment is needed (e.g., trade-offs, prioritization).
3. Open new investigation questions via `okto_pulse_ask_refinement_question` whenever the deep dive reveals gaps that aren't covered by an existing question.
4. Answer every open question via `okto_pulse_answer_refinement_question`.
5. Persist findings (architectural assumptions, ruled-out alternatives, dependencies, risk register) via `okto_pulse_add_refinement_knowledge`.

### 4. Advance

> **Status state machine.** Refinement status flows `draft → in_progress → done`
> (also `cancelled`). Calling `move_refinement` with the same status the artifact already
> holds is wasted, and `move_refinement` itself rejects illegal hops.
>
> **Preflight.** Before any `okto_pulse_move_refinement` call, read the current status via
> `okto_pulse_get_refinement`. If `current == target`, skip the move. Only call `move_*`
> when a real transition is needed.

- Run the preflight above, then `okto_pulse_move_refinement` with status `validated` (or whichever post-`done` target the API accepts).

### 5. Atomic flow-state write

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/atomic_write.py" \
  "$STATE_DIR/flow-state.json" \
  '{"current_stage":"spec","current_artifact":{"type":"refinement","id":"<id>"},"last_handoff":{"from_skill":"refine","at":"<iso8601>"}}'
```

## Invariants

- Never advance with open refinement questions.
- Coverage minimum: architectural choices, dependencies, risks/unknowns, ruled-out alternatives with rationale.
- Always record answers and findings via MCP — chat history is not authoritative.
