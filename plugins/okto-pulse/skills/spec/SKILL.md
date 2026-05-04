---
description: Spec stage skill - derives spec from refinement, runs detail saturation check, writes flow state.
when_to_use: Called by okto-pulse:flow when current_stage is spec.
disable-model-invocation: false
user-invocable: true
allowed-tools: Bash, Read, Write, AskUserQuestion
---

# okto-pulse:spec

Spec stage handler. Derives and validates a spec from the current refinement.

## Steps

1. **Derive spec**: call `okto_pulse_derive_spec_from_refinement` with the current refinement id.

2. **Detail saturation check** — call `okto_pulse_list_spec_qa` for open questions.
   - Answer each via `okto_pulse_answer_spec_question`.
   - Add business rules via `okto_pulse_add_business_rule`.
   - Add decisions via `okto_pulse_add_decision`.

3. **Evaluate spec**: call `okto_pulse_submit_spec_evaluation`. Target score >= 80.
   - If score < 80: loop back to step 2.

4. **Validate spec**: call `okto_pulse_submit_spec_validation` when score >= 80.

5. **Advance**: call `okto_pulse_move_spec` with status `validated`.

6. **Write flow state**:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/atomic_write.py" \
     "${CLAUDE_PLUGIN_DATA}/flow-state.json" \
     '{"current_stage":"sprint","current_artifact":{"type":"spec","id":"<id>"},"last_handoff":{"from_skill":"spec","to_subagent":"sprint-planner","at":"<iso8601>"}}'
   ```
