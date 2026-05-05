---
name: spec
description: Use this skill when okto-pulse:flow routes to current_stage=spec, or when the okto-pulse:spec-writer agent loads it. Derives the spec, drives saturation/evaluation to score >= 80, optionally spawns the architect agent when an architecture diagram is missing, then advances to sprint.
disable-model-invocation: false
user-invocable: true
allowed-tools: Bash, Read, Write, AskUserQuestion, Task, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_derive_spec_from_refinement, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_spec_context, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_list_spec_qa, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_ask_spec_question, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_answer_spec_question, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_add_business_rule, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_add_decision, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_add_spec_knowledge, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_submit_spec_evaluation, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_spec_evaluation, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_submit_spec_validation, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_move_spec, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_list_architecture_designs
---

# okto-pulse:spec

Procedural skill for the Pulse spec stage. Derives the spec from the refinement, drives detail saturation (questions, business rules, decisions, knowledge), evaluates to score >= 80, and ensures an architecture diagram is attached before advancing.

Loaded by the `okto-pulse:spec-writer` agent during flow routing or invoked directly.

## Inputs

- Refinement id from flow state (`current_artifact`)
- Active board id

Both come from the per-project state directory (`${CLAUDE_PLUGIN_DATA}/projects/<key>/`)
returned by `resolve_project_state.py`.

## Workflow

### 0. Resolve per-project state

```bash
STATE_DIR=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/resolve_project_state.py" --cwd "$PWD")
```

Read `$STATE_DIR/active-board.json` and `$STATE_DIR/flow-state.json` everywhere below.

### 1. Derive spec

- Call `okto_pulse_derive_spec_from_refinement` with the refinement id. Capture the new `spec_id`.

### 2. Load spec context (slim)

- `okto_pulse_get_spec_context` for the spec, but **slim the payload**:
  pass `include_qa="false"` and `include_superseded="false"`.

  Rationale: the default call returns
  `include_qa=true, include_knowledge=true, include_mockups=true,
  include_architecture=true`. For a v22+ spec like the
  `9936d6f7-...` Symphoy-PreSales-Toolkit spec, that exceeds the 96k
  char token limit and trips Family 3 errors (5 historical cases).

  When the saturation loop in Step 3 needs Q&A inspection, paginate via
  `list_spec_qa` instead — never re-call `get_spec_context` with full
  includes.

### 3. Saturation loop

Repeat until detail coverage is rich AND `okto_pulse_list_spec_qa` shows zero open questions:

1. `okto_pulse_list_spec_qa` to inventory open questions.
2. For each gap, ask new questions via `okto_pulse_ask_spec_question`.
3. Resolve each via investigation + `AskUserQuestion` when human input is required, then `okto_pulse_answer_spec_question`.
4. Add **business rules** via `okto_pulse_add_business_rule`. Coverage targets: invariants, validation rules, authorization, data lifecycle.
5. Add **decisions** via `okto_pulse_add_decision` for every design choice with alternatives. Each decision must include the alternatives considered and the rationale.
6. Add **knowledge** via `okto_pulse_add_spec_knowledge` for context not captured in questions/rules/decisions.

### 4. Evaluate

> **Status state machine.** Spec status flows
> `draft → review → approved → in_progress → done` (also `cancelled`).
> `submit_spec_evaluation` requires status `evaluating` (a sub-state of `review`);
> `submit_spec_validation` requires `approved`. Calling either from the wrong status
> trips Family 1 errors.
>
> **Preflight.** Read the current status from `get_spec_context.spec.status`. If it isn't
> `evaluating`, call `okto_pulse_move_spec` to transition through the legal chain
> (typical: `draft → review → evaluating`). Only when status is `evaluating` should you call
> `okto_pulse_submit_spec_evaluation`. If `move_spec` rejects a hop, call
> `get_spec_context` again to re-read the canonical status before retrying.

- Run the preflight, then `okto_pulse_submit_spec_evaluation`. Read the resulting score and per-dimension breakdown.
- If score < 80: identify weakest dimensions and loop back to Step 3 to address them.

### 5. Architecture branch

- Call `okto_pulse_list_architecture_designs` for this spec.
- If no design is attached, spawn the architect agent via Task:

```
Task →
  subagent_type: "okto-pulse:architect"
  description: "Author and import architecture diagram for spec <SPEC_ID>"
  prompt: |
    BOARD_ID=<board_id>
    SPEC_ID=<spec_id>
    PLUGIN_ROOT=${CLAUDE_PLUGIN_ROOT}
```

Wait for the agent's `===REPORT===` JSON. If `status=FAIL`, surface the blockers via `AskUserQuestion` and retry; do not advance without an attached design.

### 6. Validate spec

> **Preflight.** `submit_spec_validation` requires status `approved`. Read the current
> status (via the slim `get_spec_context` from Step 2 — or re-read it). If status is
> not `approved`, call `okto_pulse_move_spec` to transition through the legal chain
> (typical: `evaluating → approved`). Only then call `okto_pulse_submit_spec_validation`.

- Run the preflight, then `okto_pulse_submit_spec_validation` once score >= 80 and arch is attached.

### 7. Advance

- `okto_pulse_move_spec` with status `validated` (or whichever post-`approved` target the API accepts after validation succeeds).

### 8. Atomic flow-state write

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/atomic_write.py" \
  "$STATE_DIR/flow-state.json" \
  '{"current_stage":"sprint","current_artifact":{"type":"spec","id":"<id>"},"last_handoff":{"from_skill":"spec","at":"<iso8601>"}}'
```

## Invariants

- Never advance below evaluation score 80.
- Never advance without an attached architecture diagram.
- Each decision MUST include alternatives + rationale (not just the chosen option).
- Task is in allowed-tools ONLY for the arch-missing branch (Step 5). Do not spawn other subagents.
