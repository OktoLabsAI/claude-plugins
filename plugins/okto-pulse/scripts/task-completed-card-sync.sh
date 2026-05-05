#!/usr/bin/env bash
# TaskCompleted hook.
#
# Card 8db215b6. Reads stdin JSON event payload. The canonical
# TaskCompleted schema (per code.claude.com/docs/en/hooks) provides:
# task_id, task_subject, optional task_description, teammate_name,
# team_name. Earlier draft incorrectly read pulse_card_id /
# task_summary / metadata.* — none of those exist on the wire.
#
# Card-id discovery: the Pulse card_id is encoded as a "[CARD-xxx]"
# prefix on task_subject by the spawner (set when the okto-pulse:task
# skill or a sibling Task() call composes the subject). If the prefix
# is absent we silent-exit with NO MCP traffic — generic Claude Code
# tasks unrelated to a Pulse card are out of scope for this hook.
#
# Status heuristic: parsed from task_description (free-form summary
# text the agent emits at task completion); falls back to in_progress.
set -uo pipefail

# Read stdin payload (TaskCompleted event JSON).
PAYLOAD=""
if [ ! -t 0 ]; then
    PAYLOAD=$(cat 2>/dev/null || true)
fi

if [ -z "${PAYLOAD}" ]; then
    exit 0
fi

# Pull task_subject and task_description from the canonical schema.
TASK_SUBJECT=$(printf '%s' "${PAYLOAD}" | grep -Eo '"task_subject"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed -E 's/.*"task_subject"[[:space:]]*:[[:space:]]*"([^"]*)".*/\1/' || true)
TASK_DESCRIPTION=$(printf '%s' "${PAYLOAD}" | grep -Eo '"task_description"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed -E 's/.*"task_description"[[:space:]]*:[[:space:]]*"([^"]*)".*/\1/' || true)

# Card id discovery: scan task_subject for a "[CARD-<id>]" prefix.
# Accept hex / kebab / underscore in the id body.
CARD_ID=$(printf '%s' "${TASK_SUBJECT}" | grep -Eo '\[CARD-[A-Za-z0-9_-]+\]' | head -1 | sed -E 's/^\[CARD-([A-Za-z0-9_-]+)\]$/\1/' || true)

if [ -z "${CARD_ID}" ]; then
    # Not a Pulse-card-bound task. Silent exit, NO MCP traffic.
    exit 0
fi

# Status heuristic against the free-form task_description.
TD_LOWER=$(printf '%s' "${TASK_DESCRIPTION}" | tr '[:upper:]' '[:lower:]')
NEXT_STATUS="in_progress"
case "${TD_LOWER}" in
    *validation*|*review*) NEXT_STATUS="validation" ;;
    *done*|*complete*)     NEXT_STATUS="done" ;;
esac

MCP_URL="${PULSE_MCP_URL:-http://127.0.0.1:8101/mcp}"
MCP_CURL="${MCP_CURL:-curl}"
# AUTH NOTE: the live MCP HTTP transport requires the token as a
# ``?api_key=...`` query param (Bearer was rejected in v0.1.16-v0.1.19).
# Compose the URL with the token appended so the call actually authenticates.
API_KEY_PARAM=""
if [ -n "${PULSE_API_TOKEN:-}" ]; then
    sep="?"
    case "${MCP_URL}" in *\?*) sep="&" ;; esac
    API_KEY_PARAM="${sep}api_key=${PULSE_API_TOKEN}"
fi
MCP_URL_AUTHED="${MCP_URL}${API_KEY_PARAM}"

call_mcp() {
    METHOD_NAME="$1"
    ARGS_JSON="${2:-{}}"
    BODY=$(printf '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"%s","arguments":%s}}' "${METHOD_NAME}" "${ARGS_JSON}")
    "${MCP_CURL}" -s -m 5 \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -X POST -d "${BODY}" "${MCP_URL_AUTHED}" 2>/dev/null || true
}

# Escape task_description for embedding in the comment JSON arg.
ESC_DESC=$(printf '%s' "${TASK_DESCRIPTION}" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')

call_mcp "okto_pulse_move_card" "{\"card_id\":\"${CARD_ID}\",\"status\":\"${NEXT_STATUS}\"}" >/dev/null 2>&1 || true
call_mcp "okto_pulse_add_comment" "{\"card_id\":\"${CARD_ID}\",\"body\":\"TaskCompleted: ${ESC_DESC}\"}" >/dev/null 2>&1 || true

exit 0
