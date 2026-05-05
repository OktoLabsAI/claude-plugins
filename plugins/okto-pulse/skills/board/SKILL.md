---
description: Board picker - list available boards and switch the active board.
when_to_use: When you need to switch context to a different Pulse board, or when the active board is not set.
disable-model-invocation: false
user-invocable: true
allowed-tools: Bash, Read, Write, AskUserQuestion
---

# okto-pulse:board

Lists and switches the active Pulse board.

## Steps

1. **List boards**: call `okto_pulse_list_my_boards` to get all available boards.

2. **Present list** to user via `AskUserQuestion`.

   > **`AskUserQuestion` 4-option limit.** The tool accepts at most 4 options per call.
   > With **>4 boards**, batch the choices: present the first 3 boards plus a 4th option
   > titled `"Show next batch"`, recurse on selection. Without batching, the call returns
   > `too_big maximum: 4` (Family 3 historical error).

3. **Write selection** atomically into the per-project state dir:
   ```bash
   STATE_DIR=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/resolve_project_state.py" --cwd "$PWD")
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/atomic_write.py" \
     "$STATE_DIR/active-board.json" \
     '{"board_id":"<uuid>","board_name":"<name>","set_at":"<iso8601>","set_by":"board-skill"}'
   ```

   `resolve_project_state.py` returns the per-project state directory
   (`${CLAUDE_PLUGIN_DATA}/projects/<key>/`). Each project keeps its
   own active board — switching projects no longer steals state.

4. **Confirm** the new active board is set.
