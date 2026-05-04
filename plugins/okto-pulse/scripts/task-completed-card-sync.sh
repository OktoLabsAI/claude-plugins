#!/usr/bin/env bash
# TaskCompleted hook.
#
# Card 8db215b6. Reads stdin JSON event payload. If
# metadata.pulse_card_id is missing -> exit 0 silently with NO MCP
# traffic. If present, calls okto_pulse_move_card to the next status
# (heuristic on metadata.task_summary) and posts a comment via
# okto_pulse_add_comment.
set -uo pipefail

# Read stdin payload (TaskCompleted event JSON).
PAYLOAD=""
if [ ! -t 0 ]; then
    PAYLOAD=$(cat 2>/dev/null || true)
fi

if [ -z "${PAYLOAD}" ]; then
    exit 0
fi

# Pull metadata.pulse_card_id and metadata.task_summary out of the payload.
CARD_ID=$(printf '%s' "${PAYLOAD}" | grep -Eo '"pulse_card_id"\s*:\s*"[^"]+"' | head -1 | sed -E 's/.*"pulse_card_id"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/' || true)

if [ -z "${CARD_ID}" ]; then
    # No card id -> NO MCP traffic. Silent exit.
    exit 0
fi

TASK_SUMMARY=$(printf '%s' "${PAYLOAD}" | grep -Eo '"task_summary"\s*:\s*"[^"]*"' | head -1 | sed -E 's/.*"task_summary"[[:space:]]*:[[:space:]]*"([^"]*)".*/\1/' || true)
TS_LOWER=$(printf '%s' "${TASK_SUMMARY}" | tr '[:upper:]' '[:lower:]')

NEXT_STATUS="in_progress"
case "${TS_LOWER}" in
    *validation*|*review*) NEXT_STATUS="validation" ;;
    *done*|*complete*)     NEXT_STATUS="done" ;;
esac

MCP_URL="${PULSE_MCP_URL:-http://127.0.0.1:8101/mcp}"
MCP_CURL="${MCP_CURL:-curl}"
AUTH_HEADER=""
if [ -n "${PULSE_API_TOKEN:-}" ]; then
    AUTH_HEADER="Authorization: Bearer ${PULSE_API_TOKEN}"
fi

call_mcp() {
    METHOD_NAME="$1"
    ARGS_JSON="${2:-{}}"
    BODY=$(printf '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"%s","arguments":%s}}' "${METHOD_NAME}" "${ARGS_JSON}")
    if [ -n "${AUTH_HEADER}" ]; then
        "${MCP_CURL}" -s -m 5 \
            -H "Content-Type: application/json" \
            -H "Accept: application/json, text/event-stream" \
            -H "${AUTH_HEADER}" \
            -X POST -d "${BODY}" "${MCP_URL}" 2>/dev/null || true
    else
        "${MCP_CURL}" -s -m 5 \
            -H "Content-Type: application/json" \
            -H "Accept: application/json, text/event-stream" \
            -X POST -d "${BODY}" "${MCP_URL}" 2>/dev/null || true
    fi
}

# Escape task_summary for embedding in the comment JSON arg.
ESC_SUMMARY=$(printf '%s' "${TASK_SUMMARY}" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')

call_mcp "okto_pulse_move_card" "{\"card_id\":\"${CARD_ID}\",\"status\":\"${NEXT_STATUS}\"}" >/dev/null 2>&1 || true
call_mcp "okto_pulse_add_comment" "{\"card_id\":\"${CARD_ID}\",\"body\":\"TaskCompleted: ${ESC_SUMMARY}\"}" >/dev/null 2>&1 || true

exit 0
