---
name: ideate
description: Use this skill when okto-pulse:flow routes to current_stage=ideation or draft, when starting a new ideation directly, or when the okto-pulse:ideation-analyst agent loads it. Drives the ambiguity-killer Q&A loop on a Pulse ideation artifact, evaluates readiness, and advances to refinement.
disable-model-invocation: false
user-invocable: true
allowed-tools: Bash, Read, Write, AskUserQuestion, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_create_ideation, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_ideation, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_list_ideation_qa, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_ask_ideation_question, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_answer_ideation_question, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_add_ideation_knowledge, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_evaluate_ideation, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_move_ideation
---

# okto-pulse:ideate

Procedural skill for the Pulse ideation stage. Drives the ambiguity-killer Q&A protocol on the ideation artifact, evaluates readiness, and advances the flow to refinement.

This skill is loaded by the `okto-pulse:ideation-analyst` agent (when invoked by the flow router) and runs the substantive work inline. It also runs inline when invoked directly via `/okto-pulse:ideate`.

## Inputs

Read from flow state and the parent prompt:

- `$STATE_DIR/active-board.json` → `board_id`
- `$STATE_DIR/flow-state.json` → optional `current_artifact.id` if continuing an existing ideation

`$STATE_DIR` is the per-project state directory (`${CLAUDE_PLUGIN_DATA}/projects/<key>/`) returned by `resolve_project_state.py`. Each project keeps its own active board + flow state.

## Workflow

### 0. Resolve per-project state

```bash
STATE_DIR=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/resolve_project_state.py" --cwd "$PWD")
```

Use `$STATE_DIR/active-board.json` and `$STATE_DIR/flow-state.json` everywhere below.

### 1. Verify board

Read `$STATE_DIR/active-board.json`. If absent or missing `board_id`, abort with: "No active board. Run `/okto-pulse:setup` first."

### 2. Create or load ideation

- If flow state has no `current_artifact` (or it's not an ideation): use `AskUserQuestion` to ask the user for the ideation **title** and **one-paragraph summary**, then call `okto_pulse_create_ideation`.
- Otherwise: call `okto_pulse_get_ideation` with the existing `id`.

### 3. Ambiguity-killer Q&A loop

Repeat until `okto_pulse_list_ideation_qa` reports zero open questions:

1. Call `okto_pulse_list_ideation_qa` to inventory open questions.
2. For every gap covering at minimum **scope boundaries**, **success criteria**, **key constraints**, and **target users**, open a new question via `okto_pulse_ask_ideation_question` if not already asked.
3. For each open question, surface it to the user via `AskUserQuestion`. Record the response with `okto_pulse_answer_ideation_question`.
4. As clarifications crystallize into reusable knowledge (assumptions, validated facts, out-of-scope items), persist them via `okto_pulse_add_ideation_knowledge`.

### 4. Readiness gate

> **Status state machine.** Ideation status flows `draft → evaluating → approved → done`
> (also `review`, `cancelled`). `evaluate_ideation` only succeeds when status is `evaluating`
> — calling it on `draft`/`review`/`approved` returns
> `Evaluation can only be performed in 'evaluating' status` (Family 1, 8 historical errors).
>
> **Preflight.** Call `okto_pulse_get_ideation`. If `status != "evaluating"`, call
> `okto_pulse_move_ideation` to transition into `evaluating` first (typical chain from
> `draft` is `draft → evaluating`). THEN call `okto_pulse_evaluate_ideation`.

- Run the preflight above, then call `okto_pulse_evaluate_ideation`. If score < 70, identify the weakest dimensions from the evaluation breakdown and loop back to Step 3 to address them. Do not advance below threshold.

### 5. Advance to refinement

- Call `okto_pulse_move_ideation` with status `validated` (or whichever target the API accepts after `approved`). If the move tool rejects the target, call `okto_pulse_get_ideation` first and pick the next legal status from the state machine.

### 6. Atomic flow-state write

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/atomic_write.py" \
  "$STATE_DIR/flow-state.json" \
  '{"current_stage":"refinement","current_artifact":{"type":"ideation","id":"<id>"},"last_handoff":{"from_skill":"ideate","at":"<iso8601>"}}'
```

## Invariants

- Never advance below evaluation score 70.
- Always record answers via MCP — chat history is not authoritative.
- Coverage minimum: scope, success criteria, constraints, target users.
- The skill writes flow-state once at the end. Never mid-loop.
