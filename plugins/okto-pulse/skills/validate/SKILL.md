---
name: validate
description: Use this skill when okto-pulse:flow routes to current_stage=validation, or when the okto-pulse:qa-engineer agent loads it in MODE=validation. Submits task validations for sprint cards with runtime evidence, routes any failures back to card stage, then chains into KG consolidation.
disable-model-invocation: false
user-invocable: true
allowed-tools: Bash, Read, Write, Skill, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_list_cards_by_status, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_card, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_task_context, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_list_task_validations, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_submit_task_validation, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_move_card, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_move_sprint
---

# okto-pulse:validate

Procedural skill for the Pulse validation stage. Inspects every card in the validating sprint, ensures each has a runtime-evidenced task validation, routes any failures back to the card stage, and chains into KG consolidation on success.

Loaded by the `okto-pulse:qa-engineer` agent (in `MODE=validation`) during flow routing, or invoked directly.

## Inputs

- Sprint id from flow state (`current_artifact`) under the per-project `$STATE_DIR`.

## Workflow

### 0. Resolve per-project state

```bash
STATE_DIR=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/resolve_project_state.py" --cwd "$PWD")
```

### 1. List cards in the sprint

- `okto_pulse_list_cards_by_status` for status `done` (cards expected to validate) AND for status `in_progress` (cards still open).
- If any cards are still `in_progress`, route immediately to fail-handling (Step 4) without submitting validations.

### 2. Inspect existing validations

- For each `done` card, call `okto_pulse_list_task_validations`. Identify cards lacking a validation OR whose latest validation has no runtime evidence.

### 3. Submit missing validations

For each card needing validation:

- `okto_pulse_get_task_context` to load card + linked artifacts.
- Re-execute the linked test scenarios to capture runtime evidence (stdout, exit codes, file paths).
- `okto_pulse_submit_task_validation` with structured runtime evidence, scenario pass/fail, and verdict.

If a validation fails (verdict=fail, missing evidence, or scenario failure surfaces): collect into `failed_cards`.

### 4. Route results

- **All cards pass** → continue to Step 5.
- **Any card failed** → for each failed card: `okto_pulse_move_card` to `in_progress`. Atomic flow-state write rolling back to `card` stage:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/atomic_write.py" \
  "$STATE_DIR/flow-state.json" \
  '{"current_stage":"card","current_artifact":{"type":"sprint","id":"<sprint_id>"},"last_handoff":{"from_skill":"validate","at":"<iso8601>","reason":"validation failures: <count>"}}'
```

  Stop here. Do NOT chain into consolidation on a failed run.

### 5. Close the sprint

- `okto_pulse_move_sprint` with status `done`.

### 6. Chain into KG consolidation

- Load the `okto-pulse:consolidate` skill via the Skill tool. It will run the KG begin → commit → health flow on the validated sprint.

### 7. Atomic flow-state write (success path)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/atomic_write.py" \
  "$STATE_DIR/flow-state.json" \
  '{"current_stage":"release","current_artifact":{"type":"sprint","id":"<sprint_id>"},"last_handoff":{"from_skill":"validate","at":"<iso8601>"}}'
```

## Invariants

- Validation MUST include runtime evidence. Assertions alone are insufficient.
- Failed validations route back to the card stage; never to release.
- KG consolidation runs ONLY on the success path, via the Skill tool to `okto-pulse:consolidate`.
- Never call `okto_pulse_kg_*` directly — chain into consolidate.
