---
description: Stress-test the Pulse SDLC flow with 10 parallel ideations on a pinned board. Manual-invoke only.
when_to_use: Run before releases to validate no cross-contamination between concurrent flows. Manual only.
disable-model-invocation: true
user-invocable: true
allowed-tools: Bash, Read, Write, AskUserQuestion, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_archive_tree, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_create_ideation, mcp__plugin_okto-pulse_okto-pulse__okto_pulse_get_traceability_report
---

# okto-pulse:stress-test

Runs 10 parallel SDLC flows on the pinned stress-test board to validate isolation and idempotency.

## Prerequisites

- `pulse_stress_board_id` must be set in `userConfig`.

## Steps

1. **Get stress board id** from `userConfig.pulse_stress_board_id`.

2. **Idempotent cleanup**: call `okto_pulse_archive_tree` on the stress board root to archive all existing cards before starting. This ensures repeatable runs without leftover state.

3. **Create 10 parallel ideations**: for i in 1..10, call `okto_pulse_create_ideation` with title `stress-test-flow-{i}` on the stress board.

4. **Advance each through full flow**: for each ideation id, run the full ideation → refinement → spec → sprint → card → validation pipeline.

5. **Validate no cross-contamination**: after all flows complete, verify each ideation's artifacts only reference cards from its own flow. Check via `okto_pulse_get_traceability_report`.

6. **Report results** — print a summary of pass/fail per flow.

## Safety

- Only operates on `pulse_stress_board_id` board — never touches other boards.
- All cleanup uses `archive_tree` (reversible) — never `delete`.
- Manual-invocation only (`disable-model-invocation: true`).
