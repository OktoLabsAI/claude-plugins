---
description: Sprint stage skill - suggests sprints, lets user pick, creates sprint and assigns tasks, writes flow state.
when_to_use: Called by okto-pulse:flow when current_stage is sprint.
disable-model-invocation: false
user-invocable: true
allowed-tools: Bash, Read, Write, AskUserQuestion
---

# okto-pulse:sprint

Sprint stage handler. Generates and creates sprints from the current spec.

## Steps

1. **Suggest sprints**: call `okto_pulse_suggest_sprints` with the current spec id.

2. **Present options to user** via `AskUserQuestion` — list suggested sprint names and let user pick or approve all.

3. **Create sprints**: call `okto_pulse_create_sprint` for each approved sprint.

4. **Assign tasks**: call `okto_pulse_assign_tasks_to_sprint` for each sprint.

5. **Evaluate sprint**: call `okto_pulse_submit_sprint_evaluation`. Target score >= 80.

6. **Advance**: call `okto_pulse_move_sprint` with status `in_progress`.

7. **Write flow state**:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/atomic_write.py" \
     "${CLAUDE_PLUGIN_DATA}/flow-state.json" \
     '{"current_stage":"card","current_artifact":{"type":"sprint","id":"<id>"},"last_handoff":{"from_skill":"sprint","to_subagent":"implementer","at":"<iso8601>"}}'
   ```
