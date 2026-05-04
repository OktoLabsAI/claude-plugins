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

3. **Write selection** atomically:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/atomic_write.py" \
     "${CLAUDE_PLUGIN_DATA}/active-board.json" \
     '{"board_id":"<uuid>","board_name":"<name>","set_at":"<iso8601>","set_by":"board-skill"}'
   ```

4. **Confirm** the new active board is set.
