---
description: Ideation stage skill - creates or advances an ideation artifact, runs ambiguity-killer questions, writes flow state.
when_to_use: Called by okto-pulse:flow when current_stage is ideation or draft. Can be invoked directly to start a new ideation.
disable-model-invocation: false
user-invocable: true
allowed-tools: Bash, Read, Write, AskUserQuestion
---

# okto-pulse:ideate

Ideation stage handler. Creates a new ideation or advances an existing one.

## Steps

1. **Check active board** — read `${CLAUDE_PLUGIN_DATA}/active-board.json` for `board_id`.

2. **Create or load ideation**:
   - If no `current_artifact` in flow state: call `okto_pulse_create_ideation` with title from user.
   - Otherwise: call `okto_pulse_get_ideation` with existing id.

3. **Ambiguity-killer protocol** (MANDATORY before advancing):
   - Call `okto_pulse_list_ideation_qa` to count open questions.
   - If open_count > 0: surface each open question to the user via `AskUserQuestion` and call `okto_pulse_answer_ideation_question` for each answer.
   - Ask at minimum: scope, success criteria, key constraints, and target users.

4. **Evaluate readiness**: call `okto_pulse_evaluate_ideation`. If score < 70, loop back to step 3.

5. **Advance to refinement**: call `okto_pulse_move_ideation` with status `validated`.

6. **Write flow state**:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/atomic_write.py" \
     "${CLAUDE_PLUGIN_DATA}/flow-state.json" \
     '{"current_stage":"refinement","current_artifact":{"type":"ideation","id":"<id>"},"last_handoff":{"from_skill":"ideate","to_subagent":"refinement-investigator","at":"<iso8601>"}}'
   ```

7. **Dispatch to ideation-analyst subagent** for deeper investigation if needed.
