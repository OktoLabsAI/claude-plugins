#!/usr/bin/env bash
# Bootstrap okto-pulse in remote deploy mode.
#
# Card 303d0e09. Implements FR/TR/BR for /okto-pulse:setup remote path.
# - Validate URL shape against ^https?://[^/]+/mcp(/.*)?$ (exit 10 on miss).
# - Probe the readyz endpoint (URL with /mcp stripped, /readyz appended)
#   with the Bearer token. 401/403 -> exit 20. Anything else (timeout,
#   network) -> exit 30.
# - Probe MCP kg_health via POST. Failure -> exit 20.
# - No install or container actions.
# - Final NDJSON: {"ok":true,"mode":"remote",...}.
set -euo pipefail

PULSE_MCP_URL="${PULSE_MCP_URL:-}"
PULSE_API_TOKEN="${PULSE_API_TOKEN:-}"

iso8601() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
emit_event() { printf '{"event":"%s","ts":"%s"}\n' "$1" "$(iso8601)"; }
emit_final_ok() { printf '{"ok":true,"mode":"remote","url":"%s","validated_at":"%s"}\n' "$1" "$(iso8601)"; }
emit_final_err() { printf '{"ok":false,"error":{"reason":"%s","message":"%s"}}\n' "$1" "$2"; }

emit_cancel() {
    emit_final_err "cancelled" "user cancelled bootstrap"
    exit 2
}
trap 'emit_cancel' INT TERM

# ---- 1) URL shape validation -----------------------------------------------
emit_event "url_check"
if [ -z "${PULSE_MCP_URL}" ]; then
    emit_final_err "bad_url_shape" "PULSE_MCP_URL is empty"
    exit 10
fi
# bash 3.2-compatible regex via [[ =~ ]] (still supported in 3.2).
if ! printf '%s' "${PULSE_MCP_URL}" | grep -E '^https?://[^/]+/mcp(/.*)?$' >/dev/null; then
    emit_final_err "bad_url_shape" "URL must match ^https?://[^/]+/mcp(/.*)?$"
    exit 10
fi

# Derive the readyz URL (strip a trailing /mcp* path, append /readyz).
HOST_BASE=$(printf '%s' "${PULSE_MCP_URL}" | sed -E 's@/mcp(/.*)?$@@')
READYZ_URL="${HOST_BASE}/readyz"

# ---- 2) Probe /readyz -------------------------------------------------------
emit_event "probe_readyz"
API_KEY_PARAM=""
if [ -n "${PULSE_API_TOKEN}" ]; then
    API_KEY_PARAM="?api_key=${PULSE_API_TOKEN}"
fi
HTTP_CODE=$(curl -s -m 5 -o /dev/null -w '%{http_code}' "${READYZ_URL}${API_KEY_PARAM}" 2>/dev/null || true)
case "${HTTP_CODE}" in
    200)
        ;;
    401|403)
        emit_final_err "auth_failed" "/readyz returned ${HTTP_CODE}; Bearer token rejected"
        exit 20
        ;;
    *)
        emit_final_err "readyz_unreachable" "/readyz returned ${HTTP_CODE:-no-response}"
        exit 30
        ;;
esac

# ---- 3) Probe MCP kg_health -------------------------------------------------
emit_event "probe_kg_health"
JSONRPC_BODY='{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"okto_pulse_kg_health","arguments":{}}}'
MCP_URL_WITH_KEY="${PULSE_MCP_URL}${API_KEY_PARAM}"
MCP_OUT=$(curl -s -m 5 -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -X POST -d "${JSONRPC_BODY}" "${MCP_URL_WITH_KEY}" 2>/dev/null || true)
if [ -z "${MCP_OUT}" ]; then
    emit_final_err "mcp_unreachable" "MCP kg_health returned no payload"
    exit 20
fi
# A minimal sanity check: the JSON-RPC reply should mention "result" or
# "ok" somewhere. If it carries an "error" object, treat as failure.
if printf '%s' "${MCP_OUT}" | grep -E '"error"\s*:' >/dev/null; then
    emit_final_err "mcp_error" "MCP kg_health returned an error envelope"
    exit 20
fi

# ---- 4) Final ok ------------------------------------------------------------
emit_final_ok "${PULSE_MCP_URL}"
exit 0
