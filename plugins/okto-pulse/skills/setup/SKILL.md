---
description: One-shot bootstrap of okto-pulse - choose deploy mode, run autonomously to a green doctor and a chosen active board.
when_to_use: First-run setup of the okto-pulse plugin. Manual-invoke only.
disable-model-invocation: true
user-invocable: true
allowed-tools: Bash, Read, Write, AskUserQuestion
---

# okto-pulse:setup

End-to-end bootstrap. Asks the deploy-mode question once, then runs to
completion without further confirmation prompts. On finish you have:

- Pulse reachable at the chosen MCP URL
- `userConfig` populated (`pulse_deploy_mode`, `pulse_mcp_url`,
  `pulse_api_token` - sensitive, `pulse_board_id`)
- `${CLAUDE_PLUGIN_DATA}/active-board.json` written atomically
- `/okto-pulse:doctor` reports 100% green

## Steps

1. **Ask the deploy-mode question** with `AskUserQuestion`:
   - `local-pip` - run Pulse locally via the pip package (needs Python 3.12).
   - `docker` - run Pulse via the bundled `docker-compose.yml`.
   - `remote` - point at an existing Pulse instance (needs URL + token).

2. **Collect mode-specific values**:
   - `local-pip`: base MCP URL (default `http://127.0.0.1:8101/mcp`) and `PULSE_API_TOKEN` (required for auth).
   - `docker`: base MCP URL (default `http://127.0.0.1:8101/mcp`) and `PULSE_API_TOKEN` (required for auth).
   - `remote`: `PULSE_MCP_URL` (base URL, must match `^https?://[^/]+/mcp(/.*)?$`)
     and `PULSE_API_TOKEN` (required for auth).

3. **Run the matching helper** via `Bash`:
   - `local-pip`: `${CLAUDE_PLUGIN_ROOT}/bin/bootstrap-local-pip.sh`
   - `docker`:    `${CLAUDE_PLUGIN_ROOT}/bin/bootstrap-docker.sh`
   - `remote`:    `${CLAUDE_PLUGIN_ROOT}/bin/bootstrap-remote.sh`

   Each helper emits NDJSON progress events plus a final
   `{"ok":true,"mode":"<mode>",...}` line. On non-zero exit, parse the
   final NDJSON line's `error.message` and abort.

4. **Persist `userConfig`** (via the Claude Code plugin runtime):
   - `pulse_deploy_mode`: the chosen mode.
   - `pulse_mcp_url`: construct as `${BASE_URL}?api_key=${PULSE_API_TOKEN}` (full URL with auth param).
   - `pulse_api_token` (sensitive, keychain-backed): stored separately for use by doctor/bootstrap scripts.
   - `pulse_board_id`: set after board picker in step 6.

5. **Run `/okto-pulse:doctor`**. Abort if any check is `fail` (red).

6. **Active-board picker**: call `okto_pulse_list_my_boards`, prompt
   the user to choose, then write
   `${CLAUDE_PLUGIN_DATA}/active-board.json` atomically using the
   shipped helper:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/atomic_write.py" \
     "${CLAUDE_PLUGIN_DATA}/active-board.json" \
     '{"board_id":"<uuid>","board_name":"<name>","set_at":"<iso8601>","set_by":"setup"}'
   ```

## Safety

- This skill is **manual-invocation only** (`disable-model-invocation: true`)
  per FR1 / TR `tr_28ef09f0` so an agent cannot trigger first-run setup
  on a user without consent.
- No retries on top-level failure: if a helper exits non-zero, surface
  the message and let the user decide whether to re-run.
- Never overwrite an existing `active-board.json` without the user
  picking again.
