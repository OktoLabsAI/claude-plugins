---
description: Validation stage skill - submits task validations, routes pass to next stage or fail back to task.
when_to_use: Called by okto-pulse:flow when current_stage is validation.
disable-model-invocation: false
user-invocable: true
allowed-tools: Bash, Read, Write, AskUserQuestion
---

# okto-pulse:validate

Validation stage handler. Runs task validations and routes accordingly.

## Steps

1. **List cards to validate**: call `okto_pulse_list_task_validations` for the current sprint.

2. **Submit validation**: call `okto_pulse_submit_task_validation` for each completed card.
   - Validation must include: runtime evidence (not just assertions), linked test scenarios, and traceability.

3. **Route results**:
   - All pass: advance to next stage (write flow state with `release` or next sprint).
   - Any fail: call `okto_pulse_move_card` back to `in_progress`, write flow state with `card`.

4. **KG consolidation** (mandatory at stage exit): call `okto_pulse_kg_begin_consolidation`, then `okto_pulse_kg_commit_consolidation`.

5. **Write flow state** on success:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/atomic_write.py" \
     "${CLAUDE_PLUGIN_DATA}/flow-state.json" \
     '{"current_stage":"release","current_artifact":{"type":"sprint","id":"<id>"},"last_handoff":{"from_skill":"validate","to_subagent":"kg-curator","at":"<iso8601>"}}'
   ```
