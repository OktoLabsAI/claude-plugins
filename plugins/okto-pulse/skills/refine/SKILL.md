---
description: Refinement stage skill - runs deep investigation protocol, creates refinement artifact, writes flow state.
when_to_use: Called by okto-pulse:flow when current_stage is refinement.
disable-model-invocation: false
user-invocable: true
allowed-tools: Bash, Read, Write, AskUserQuestion
---

# okto-pulse:refine

Refinement stage handler. Runs deep investigation and populates the refinement artifact.

## Steps

1. **Load context** — call `okto_pulse_get_refinement_context` or `okto_pulse_get_ideation_context` for the current artifact.

2. **Create refinement** if none exists: call `okto_pulse_create_refinement` linked to the ideation.

3. **Deep investigation protocol** (mandatory):
   - Call `okto_pulse_list_refinement_qa` for open questions.
   - For each open question: surface to user, call `okto_pulse_answer_refinement_question`.
   - Add findings via `okto_pulse_add_refinement_knowledge`.
   - Target: zero open questions before advancing.

4. **Advance**: call `okto_pulse_move_refinement` with status `validated`.

5. **Write flow state**:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/atomic_write.py" \
     "${CLAUDE_PLUGIN_DATA}/flow-state.json" \
     '{"current_stage":"spec","current_artifact":{"type":"refinement","id":"<id>"},"last_handoff":{"from_skill":"refine","to_subagent":"spec-writer","at":"<iso8601>"}}'
   ```
