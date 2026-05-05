#!/usr/bin/env bash
# SessionStart hook (matchers: startup, resume).
#
# Card 1ad51f44. Hard ~5s wall-clock budget (the hooks.json declaration
# carries a `timeout: 5` for the orchestrator; we additionally cap our
# curl probes at 2-3s each so the script self-bounds).
#
# - Reads ${CLAUDE_PLUGIN_DATA}/active-board.json for context.
# - Probes okto_pulse_kg_health + okto_pulse_get_unseen_summary via curl
#   to the MCP HTTP endpoint.
# - On success: prints a single system-reminder line on stdout.
# - On failure/timeout: prints "Pulse unreachable at <url>. Run
#   /okto-pulse:doctor." on stdout.
# - Always exits 0 (FR19 / BR br_2dc40fa8 -- never block the session).
#
# stdin is the JSON event payload; we ignore parse failures (TR tr_8935e055).
set -uo pipefail

# Discard stdin (event payload) - we don't need to parse it for this hook.
if [ ! -t 0 ]; then
    cat >/dev/null 2>&1 || true
fi

DATA_DIR="${CLAUDE_PLUGIN_DATA:-${HOME}/.claude/plugins/data/okto-pulse}"
ACTIVE_BOARD_FILE="${DATA_DIR}/active-board.json"
DEPLOY_MODE_FILE="${DATA_DIR}/deploy-mode.json"

# Determine MCP URL (default local-pip mapping).
MCP_URL="${PULSE_MCP_URL:-http://127.0.0.1:8101/mcp}"

DEPLOY_MODE="local-pip"
if [ -f "${DEPLOY_MODE_FILE}" ]; then
    DETECTED=$(grep -E '"mode"\s*:' "${DEPLOY_MODE_FILE}" 2>/dev/null | head -1 | sed -E 's/.*"mode"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/' || true)
    if [ -n "${DETECTED}" ]; then
        DEPLOY_MODE="${DETECTED}"
    fi
fi

BOARD_NAME="(no active board)"
if [ -f "${ACTIVE_BOARD_FILE}" ]; then
    DETECTED_NAME=$(grep -E '"board_name"\s*:' "${ACTIVE_BOARD_FILE}" 2>/dev/null | head -1 | sed -E 's/.*"board_name"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/' || true)
    if [ -n "${DETECTED_NAME}" ]; then
        BOARD_NAME="${DETECTED_NAME}"
    fi
fi

# Indirection seam: tests can swap MCP_CURL=/path/to/mock to short-circuit
# the network. Default to plain curl.
MCP_CURL="${MCP_CURL:-curl}"
# AUTH NOTE: This legacy SessionStart helper still uses ``Authorization: Bearer``
# for backward compatibility — the live MCP HTTP transport actually requires the
# token as a ``?api_key=...`` query parameter (see hooks/session_start_pulse_ping.py
# and the v0.1.16-v0.1.19 fix history). Bearer was rejected by the server in those
# versions; this script is grandfathered, scheduled for migration in v0.3.0.
AUTH_HEADER=""
if [ -n "${PULSE_API_TOKEN:-}" ]; then
    AUTH_HEADER="Authorization: Bearer ${PULSE_API_TOKEN}"
fi

call_mcp() {
    # $1 = tool name. Prints raw response on stdout.
    METHOD_NAME="$1"
    BODY=$(printf '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"%s","arguments":{}}}' "${METHOD_NAME}")
    if [ -n "${AUTH_HEADER}" ]; then
        "${MCP_CURL}" -s -m 3 \
            -H "Content-Type: application/json" \
            -H "Accept: application/json, text/event-stream" \
            -H "${AUTH_HEADER}" \
            -X POST -d "${BODY}" "${MCP_URL}" 2>/dev/null || true
    else
        "${MCP_CURL}" -s -m 3 \
            -H "Content-Type: application/json" \
            -H "Accept: application/json, text/event-stream" \
            -X POST -d "${BODY}" "${MCP_URL}" 2>/dev/null || true
    fi
}

KG_OUT=$(call_mcp "okto_pulse_kg_health")
if [ -z "${KG_OUT}" ] || printf '%s' "${KG_OUT}" | grep -E '"error"\s*:' >/dev/null; then
    printf 'Pulse unreachable at %s. Run /okto-pulse:doctor.\n' "${MCP_URL}"
    exit 0
fi

UNSEEN_OUT=$(call_mcp "okto_pulse_get_unseen_summary")
UNSEEN_COUNT="?"
if [ -n "${UNSEEN_OUT}" ]; then
    DETECTED_COUNT=$(printf '%s' "${UNSEEN_OUT}" | grep -Eo '"unseen_count"[[:space:]]*:[[:space:]]*[0-9]+' | head -1 | sed -E 's/.*:[[:space:]]*([0-9]+).*/\1/' || true)
    if [ -n "${DETECTED_COUNT}" ]; then
        UNSEEN_COUNT="${DETECTED_COUNT}"
    fi
fi

printf '<system-reminder>okto-pulse: board="%s" mode=%s unseen=%s</system-reminder>\n' "${BOARD_NAME}" "${DEPLOY_MODE}" "${UNSEEN_COUNT}"
exit 0
