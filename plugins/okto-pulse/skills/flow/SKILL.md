---
description: SDLC state-machine router - reads flow-state.json and dispatches to the appropriate stage skill.
when_to_use: Invoke to continue or start an SDLC flow. Automatically routes to the correct stage based on current flow state.
disable-model-invocation: false
user-invocable: true
allowed-tools: Bash, Read, Write, AskUserQuestion
---

# okto-pulse:flow

State machine router for the Pulse SDLC flow. Reads flow-state.json, determines current stage, and dispatches to the matching stage skill.

## Stages

`draft → ideation → refinement → spec → sprint → card → validation → release`

## Steps

1. **Read flow state** via `Read`:
   ```
   Read "${CLAUDE_PLUGIN_DATA}/flow-state.json"
   ```
   If file does not exist, treat `current_stage` as `draft` and `current_artifact` as null.

2. **Count open Q&A** (tiebreaker when stage is ambiguous):
   - Call `okto_pulse_list_ideation_qa` with the current artifact id (if present) to get open question count.
   - If `open_count > 0` and stage is ambiguous, stay at current stage rather than advancing.

3. **Dispatch to stage skill**:
   | current_stage | Dispatch to |
   |---|---|
   | draft (no state) | `claude run skill okto-pulse:ideate` |
   | ideation | `claude run skill okto-pulse:ideate` |
   | refinement | `claude run skill okto-pulse:refine` |
   | spec | `claude run skill okto-pulse:spec` |
   | sprint | `claude run skill okto-pulse:sprint` |
   | card | `claude run skill okto-pulse:task` |
   | validation | `claude run skill okto-pulse:validate` |

   ```bash
   claude run skill okto-pulse:<stage>
   ```

4. **Write updated flow-state.json** atomically after each stage transition:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/atomic_write.py" \
     "${CLAUDE_PLUGIN_DATA}/flow-state.json" \
     '{"current_stage":"<new_stage>","current_artifact":{"type":"<type>","id":"<id>"},"last_handoff":{"from_skill":"flow","to_subagent":"<stage>","at":"<iso8601>"}}'
   ```

## Safety

- Never skip KG consolidation at stage transitions.
- If `current_stage` is not in the valid enum, ask the user to reset flow state.
- Always check `flow-state.json` before acting — never assume stage from conversation context.
