---
name: qa-engineer-loop
description: Per-card test/qa procedure - authors test scenarios and submits task validation for one okto-pulse test or qa card. Loaded by the okto-pulse:qa-engineer agent in card MODE.
when_to_use: Loaded only by the okto-pulse:qa-engineer agent when MODE=card. Not user-invocable.
disable-model-invocation: true
user-invocable: false
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_task_context, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_card, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_add_test_scenario, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_link_task_to_scenario, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_submit_task_validation, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_update_test_scenario_status, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_move_card
---

# okto-pulse:qa-engineer-loop

Per-card test-scenario authoring + task-validation procedure for ONE `test`/`qa`-type card. Loaded by the `okto-pulse:qa-engineer` agent when invoked in card-stage `MODE=card`.

## Inputs

Provided by the parent agent prompt:

- `BOARD_ID`
- `SPRINT_ID`
- `CARD_ID`
- `PLUGIN_ROOT`

## Hard constraints

- NEVER call `AskUserQuestion`. Zero-confirmation.
- NEVER spawn further subagents.
- Validation MUST include runtime evidence — assertions alone are not sufficient.

## Workflow

### 1. Load card context

- `okto_pulse_get_task_context` with `card_id=CARD_ID`.
- `okto_pulse_get_card` to confirm card type and status.

If status is not `in_progress`, return `status=FAIL`, `blockers=["card not in_progress"]`.

### 2. Author test scenarios

For each acceptance criterion or linked artifact lacking coverage:

- Compose the scenario as a clear Given/When/Then plus expected runtime evidence (logs, stdout, file diff, HTTP response).
- Call `okto_pulse_add_test_scenario` with the scenario payload.

### 3. Run scenarios and capture runtime evidence

- Execute the test commands from each scenario via `Bash`.
- Capture stdout/stderr, exit codes, and any artifact paths produced.
- For pass scenarios: `okto_pulse_update_test_scenario_status` to `passed`.
- For fail scenarios: `okto_pulse_update_test_scenario_status` to `failed` with the failure reason.

### 4. Link scenarios to the card

For each scenario authored or executed: `okto_pulse_link_task_to_scenario`.

### 5. Submit task validation

- Call `okto_pulse_submit_task_validation` with:
  - `card_id=CARD_ID`
  - `evidence`: structured runtime evidence (stdout snippets, file paths, exit codes)
  - `scenarios_passed` / `scenarios_failed` lists
  - `verdict`: `pass` if all required scenarios pass, otherwise `fail`
- The validation tool will reject submissions lacking runtime evidence — populate it.

### 6. Move the card

- All required scenarios passed → `okto_pulse_move_card` to `done`.
- Any required scenario failed → `okto_pulse_move_card` to `blocked` with the failure reason.

### 7. Return summary

```
{
  "status": "PASS" | "FAIL",
  "card_id": "<CARD_ID>",
  "moved_to": "done" | "blocked",
  "scenarios_added": <int>,
  "scenarios_passed": ["<id>", ...],
  "scenarios_failed": ["<id>", ...],
  "evidence_summary": "<one paragraph>",
  "validation_pass": true | false,
  "blockers": ["<one-line>", ...]
}
```

## Invariants

- Validation requires runtime evidence — never submit `pass` without it.
- Card-level only — for the validation STAGE (post-sprint), use the `okto-pulse:validate` skill instead.
