#!/usr/bin/env bash
# PreCompact hook.
#
# Card ca61ca5c. Calls okto_pulse_kg_begin_consolidation then
# okto_pulse_kg_commit_consolidation. On any error in either, calls
# okto_pulse_kg_abort_consolidation.
#
# Always exits 0 - never block compaction (BR br_2dc40fa8).
set -uo pipefail

if [ ! -t 0 ]; then
    cat >/dev/null 2>&1 || true
fi

MCP_URL="${PULSE_MCP_URL:-http://127.0.0.1:8101/mcp}"
MCP_CURL="${MCP_CURL:-curl}"
AUTH_HEADER=""
if [ -n "${PULSE_API_TOKEN:-}" ]; then
    AUTH_HEADER="Authorization: Bearer ${PULSE_API_TOKEN}"
fi

call_mcp() {
    METHOD_NAME="$1"
    BODY=$(printf '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"%s","arguments":{}}}' "${METHOD_NAME}")
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

is_error() {
    # $1 = response payload. Returns 0 if error, 1 if ok.
    if [ -z "$1" ]; then return 0; fi
    if printf '%s' "$1" | grep -E '"error"\s*:' >/dev/null; then return 0; fi
    return 1
}

BEGIN_OUT=$(call_mcp "okto_pulse_kg_begin_consolidation")
if is_error "${BEGIN_OUT}"; then
    printf '[consolidate-on-compact] kg_begin_consolidation failed; aborting.\n' >&2
    call_mcp "okto_pulse_kg_abort_consolidation" >/dev/null 2>&1 || true
    exit 0
fi

COMMIT_OUT=$(call_mcp "okto_pulse_kg_commit_consolidation")
if is_error "${COMMIT_OUT}"; then
    printf '[consolidate-on-compact] kg_commit_consolidation failed; calling abort.\n' >&2
    call_mcp "okto_pulse_kg_abort_consolidation" >/dev/null 2>&1 || true
    exit 0
fi

exit 0
