---
description: Task/card stage skill - dispatches to specialist subagent per card type, writes flow state.
when_to_use: Called by okto-pulse:flow when current_stage is card.
disable-model-invocation: false
user-invocable: true
allowed-tools: Bash, Read, Write, AskUserQuestion
---

# okto-pulse:task

Task (card) stage handler. Dispatches each card to the appropriate specialist subagent.

## Steps

1. **List in-progress cards**: call `okto_pulse_list_cards_by_status` with status `in_progress`.

2. **Pick next card** — choose the highest-priority unblocked card.

3. **Dispatch by card type**:
   | Card type | Subagent |
   |---|---|
   | implementation | implementer |
   | test / qa | qa-engineer |
   | architecture | architect |
   | knowledge / docs | kg-curator |
   | planning | sprint-planner |

4. **Track completion**: after subagent finishes, call `okto_pulse_move_card` to `done`.

5. **Repeat** until all sprint cards are done.

6. **Write flow state**:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/atomic_write.py" \
     "${CLAUDE_PLUGIN_DATA}/flow-state.json" \
     '{"current_stage":"validation","current_artifact":{"type":"card","id":"<id>"},"last_handoff":{"from_skill":"task","to_subagent":"qa-engineer","at":"<iso8601>"}}'
   ```
