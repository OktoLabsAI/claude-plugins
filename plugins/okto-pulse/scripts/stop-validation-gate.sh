#!/usr/bin/env bash
# Stop hook.
#
# Card 7c92da9e. Lists active-board cards in status=validation_pending
# via okto_pulse_list_cards_by_status. For each, fetches
# okto_pulse_get_task_validation. If any returns status=failed, emit
# `{"decision":"block","reason":"..."}` on stdout (exit 0). If none have
# failing tests, exit 0 silently. Distinguishes "active validation_pending
# with failing tests" (block) from generic session failures (don't
# block) per TR tr_3004a6fc.
set -uo pipefail

if [ ! -t 0 ]; then
    cat >/dev/null 2>&1 || true
fi

DATA_DIR="${CLAUDE_PLUGIN_DATA:-${HOME}/.claude/plugins/data/okto-pulse}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Per-project state: resolve via shipped helper. Fall back to legacy global
# path if python3 / helper is unavailable.
RESOLVE_PY="${SCRIPT_DIR}/resolve_project_state.py"
STATE_DIR=""
if command -v python3 >/dev/null 2>&1 && [ -f "${RESOLVE_PY}" ]; then
    STATE_DIR=$(python3 "${RESOLVE_PY}" --cwd "${PWD}" 2>/dev/null || true)
fi
if [ -z "${STATE_DIR}" ]; then
    STATE_DIR="${DATA_DIR}"
fi
ACTIVE_BOARD_FILE="${STATE_DIR}/active-board.json"

MCP_URL="${PULSE_MCP_URL:-http://127.0.0.1:8101/mcp}"
MCP_CURL="${MCP_CURL:-curl}"
AUTH_HEADER=""
if [ -n "${PULSE_API_TOKEN:-}" ]; then
    AUTH_HEADER="Authorization: Bearer ${PULSE_API_TOKEN}"
fi

BOARD_ID=""
if [ -f "${ACTIVE_BOARD_FILE}" ]; then
    BOARD_ID=$(grep -E '"board_id"\s*:' "${ACTIVE_BOARD_FILE}" 2>/dev/null | head -1 | sed -E 's/.*"board_id"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/' || true)
fi

if [ -z "${BOARD_ID}" ]; then
    # No active board -> nothing to gate on.
    exit 0
fi

call_mcp() {
    # $1 = method, $2 = arguments JSON object string (eg '{"board_id":"..."}')
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

LIST_OUT=$(call_mcp "okto_pulse_list_cards_by_status" "{\"board_id\":\"${BOARD_ID}\",\"status\":\"validation_pending\"}")
if [ -z "${LIST_OUT}" ]; then
    exit 0
fi

# Collect candidate card ids. Quick & dirty: look for "card_id":"<uuid>" or
# "id":"<uuid>" entries in the response.
CARD_IDS=$(printf '%s' "${LIST_OUT}" | grep -Eo '"(card_id|id)"\s*:\s*"[0-9a-fA-F-]{8,}"' | sed -E 's/.*"([0-9a-fA-F-]{8,})".*/\1/' | sort -u || true)

if [ -z "${CARD_IDS}" ]; then
    exit 0
fi

FAILING_CARD=""
for CARD_ID in ${CARD_IDS}; do
    VAL_OUT=$(call_mcp "okto_pulse_get_task_validation" "{\"card_id\":\"${CARD_ID}\"}")
    if [ -z "${VAL_OUT}" ]; then
        continue
    fi
    if printf '%s' "${VAL_OUT}" | grep -E '"status"\s*:\s*"failed"' >/dev/null; then
        FAILING_CARD="${CARD_ID}"
        break
    fi
done

if [ -n "${FAILING_CARD}" ]; then
    printf '{"decision":"block","reason":"validation_pending card %s has failing validation; resolve before stopping"}\n' "${FAILING_CARD}"
fi

exit 0
