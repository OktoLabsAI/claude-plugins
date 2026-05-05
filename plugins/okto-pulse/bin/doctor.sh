#!/usr/bin/env bash
# Read-only diagnostic for okto-pulse plugin state.
#
# Card 6a776702. Emits one NDJSON line per check on stdout, plus a final
# summary line. Always exits 0 - the orchestrator decides what to do
# with red checks.
#
# Reads ${CLAUDE_PLUGIN_DATA}/deploy-mode.json to know which mode-
# specific checks to run.
# NOTE: deliberately NOT using `set -e` / `pipefail` here. doctor.sh runs
# many "best-effort" probes that may fail (pip show on a missing package,
# docker info on a stopped daemon, curl on an unreachable port). Each
# check encapsulates its own pass/fail decision; we don't want a single
# failed sub-shell to abort the whole diagnostic.
set -u

# If CLAUDE_PLUGIN_DATA is set but points at a different plugin, fall back to the canonical path.
_default_data="${HOME}/.claude/plugins/data/okto-pulse-oktolabs-plugins"
if [ -n "${CLAUDE_PLUGIN_DATA:-}" ] && printf '%s' "${CLAUDE_PLUGIN_DATA:-}" | grep -q 'okto-pulse'; then
    DATA_DIR="${CLAUDE_PLUGIN_DATA}"
else
    DATA_DIR="${_default_data}"
fi
DEPLOY_MODE_FILE="${DATA_DIR}/deploy-mode.json"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/../deploy/docker-compose.yml"

# Per-project state directory: resolve via shipped helper. Falls back to the
# global DATA_DIR if the helper is unavailable so a missing python3 doesn't
# break the diagnostic. The helper handles legacy → per-project migration.
RESOLVE_PY="${SCRIPT_DIR}/../scripts/resolve_project_state.py"
if command -v python3 >/dev/null 2>&1 && [ -f "${RESOLVE_PY}" ]; then
    STATE_DIR=$(python3 "${RESOLVE_PY}" --cwd "${PWD}" 2>/dev/null || true)
fi
if [ -z "${STATE_DIR:-}" ]; then
    STATE_DIR="${DATA_DIR}"
fi
ACTIVE_BOARD_FILE="${STATE_DIR}/active-board.json"

# Detect deploy mode (default local-pip when file missing).
DEPLOY_MODE="local-pip"
if [ -f "${DEPLOY_MODE_FILE}" ]; then
    DETECTED=$(grep -E '"mode"\s*:' "${DEPLOY_MODE_FILE}" 2>/dev/null | head -1 | sed -E 's/.*"mode"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/' || true)
    if [ -n "${DETECTED}" ]; then
        DEPLOY_MODE="${DETECTED}"
    fi
fi

GREEN=0
YELLOW=0
RED=0
RUN=0

emit_check() {
    # $1 = name, $2 = status (ok|warn|fail), $3 = detail
    case "$2" in
        ok)   GREEN=$((GREEN+1)) ;;
        warn) YELLOW=$((YELLOW+1)) ;;
        fail) RED=$((RED+1)) ;;
    esac
    RUN=$((RUN+1))
    # JSON-escape the detail (very minimal: just escape backslashes and quotes).
    DETAIL=$(printf '%s' "$3" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')
    printf '{"check":"%s","status":"%s","detail":"%s"}\n' "$1" "$2" "${DETAIL}"
}

# Determines READYZ URL by deploy mode; defaults to 8101 (docker/remote).
# Both URLs can be overridden via env (handy for tests / CI / non-default
# port mappings).
READYZ_URL="${PULSE_READYZ_URL:-}"
MCP_URL="${PULSE_MCP_URL:-}"
if [ -z "${READYZ_URL}" ] || [ -z "${MCP_URL}" ]; then
    case "${DEPLOY_MODE}" in
        local-pip)
            READYZ_URL="${READYZ_URL:-http://127.0.0.1:8100/readyz}"
            MCP_URL="${MCP_URL:-http://127.0.0.1:8101/mcp}"
            ;;
        docker)
            READYZ_URL="${READYZ_URL:-http://127.0.0.1:8101/readyz}"
            MCP_URL="${MCP_URL:-http://127.0.0.1:8101/mcp}"
            ;;
        remote)
            if [ -n "${PULSE_MCP_URL:-}" ]; then
                MCP_URL="${PULSE_MCP_URL}"
                MCP_BASE=$(printf '%s' "${PULSE_MCP_URL}" | sed -E 's@\?.*$@@')
                READYZ_URL=$(printf '%s' "${MCP_BASE}" | sed -E 's@/mcp(/.*)?$@@')/readyz
            fi
            ;;
    esac
fi

API_KEY_PARAM=""
if [ -n "${PULSE_API_TOKEN:-}" ]; then
    API_KEY_PARAM="?api_key=${PULSE_API_TOKEN}"
fi

# ---- Check 1: Python 3.12 (local-pip only) ----------------------------------
if [ "${DEPLOY_MODE}" = "local-pip" ]; then
    if command -v python3.12 >/dev/null 2>&1 || python3 -c 'import sys; sys.exit(0 if sys.version_info[:2]==(3,12) else 1)' 2>/dev/null; then
        emit_check "python_3_12_detected" "ok" "Python 3.12 found"
    else
        emit_check "python_3_12_detected" "fail" "Python 3.12 not on PATH"
    fi
fi

# ---- Check 2: okto-pulse pip installed (local-pip only) ---------------------
if [ "${DEPLOY_MODE}" = "local-pip" ]; then
    PIP_VER=""
    if command -v python3.12 >/dev/null 2>&1; then
        PIP_VER=$(python3.12 -m pip show okto-pulse 2>/dev/null | awk -F': ' '/^Version: /{print $2}' | tr -d '\r\n ')
    fi
    if [ -z "${PIP_VER}" ] && command -v python3 >/dev/null 2>&1; then
        PIP_VER=$(python3 -m pip show okto-pulse 2>/dev/null | awk -F': ' '/^Version: /{print $2}' | tr -d '\r\n ')
    fi
    if [ -n "${PIP_VER}" ]; then
        emit_check "okto_pulse_pip_installed" "ok" "okto-pulse ${PIP_VER}"
    else
        emit_check "okto_pulse_pip_installed" "fail" "okto-pulse pip not installed"
    fi
fi

# ---- Check 3: docker daemon reachable (docker only) -------------------------
if [ "${DEPLOY_MODE}" = "docker" ]; then
    if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
        emit_check "docker_daemon_reachable" "ok" "docker info ok"
    else
        emit_check "docker_daemon_reachable" "fail" "docker daemon unreachable"
    fi
fi

# ---- Check 4: container okto-pulse running (docker only) --------------------
if [ "${DEPLOY_MODE}" = "docker" ]; then
    if command -v docker >/dev/null 2>&1; then
        STATE=$(docker inspect -f '{{.State.Running}}' okto-pulse 2>/dev/null || true)
        if [ "${STATE}" = "true" ]; then
            emit_check "container_running" "ok" "okto-pulse container running"
        else
            emit_check "container_running" "fail" "okto-pulse container is not running"
        fi
    else
        emit_check "container_running" "fail" "docker missing"
    fi
fi

# ---- Check 5: GHCR image tag matches plugin version (docker only) -----------
if [ "${DEPLOY_MODE}" = "docker" ]; then
    PLUGIN_VERSION=$(grep -E '"version"\s*:' "${SCRIPT_DIR}/../.claude-plugin/plugin.json" 2>/dev/null | head -1 | sed -E 's/.*"version"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/' || true)
    EXPECTED_TAG=":${PLUGIN_VERSION}"
    IMAGE_TAG=$(docker inspect -f '{{.Config.Image}}' okto-pulse 2>/dev/null || true)
    if [ -n "${PLUGIN_VERSION}" ] && [ -n "${IMAGE_TAG}" ] && printf '%s' "${IMAGE_TAG}" | grep -F "${EXPECTED_TAG}" >/dev/null; then
        emit_check "image_tag_matches_plugin" "ok" "image=${IMAGE_TAG}"
    else
        emit_check "image_tag_matches_plugin" "warn" "expected tag ${EXPECTED_TAG}; got ${IMAGE_TAG:-<none>}"
    fi
fi

# ---- Check 6: /readyz returns 200 -------------------------------------------
HTTP_CODE=""
if [ -n "${READYZ_URL}" ]; then
    HTTP_CODE=$(curl -s -m 3 -o /dev/null -w '%{http_code}' "${READYZ_URL}${API_KEY_PARAM}" 2>/dev/null || true)
fi
if [ "${HTTP_CODE}" = "200" ]; then
    emit_check "readyz_200" "ok" "${READYZ_URL} -> 200"
else
    emit_check "readyz_200" "fail" "${READYZ_URL:-<unset>} -> ${HTTP_CODE:-no-response}"
fi

# ---- Check 7: KG health via REST API (MCP uses SSE sessions; not curl-able) -
# Derives REST base URL from MCP URL; for local-pip maps port 8101→8100.
MCP_OUT=""
if [ -n "${MCP_URL}" ]; then
    REST_BASE=$(printf '%s' "${MCP_URL}" | sed -E 's@/mcp(/.*)?$@@')
    if [ "${DEPLOY_MODE}" = "local-pip" ]; then
        REST_BASE=$(printf '%s' "${REST_BASE}" | sed -E 's/:8101\b/:8100/')
    fi
    BOARD_ID=""
    if [ -f "${ACTIVE_BOARD_FILE}" ]; then
        BOARD_ID=$(grep -E '"board_id"' "${ACTIVE_BOARD_FILE}" 2>/dev/null | head -1 \
            | sed -E 's/.*"board_id"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/' || true)
    fi
    if [ -z "${BOARD_ID}" ]; then
        emit_check "mcp_kg_health" "warn" "no active board — skipping KG health (run /okto-pulse:setup first)"
    else
        KG_URL="${REST_BASE}/api/v1/kg/health?board_id=${BOARD_ID}"
        if [ -n "${API_KEY_PARAM}" ]; then
            KG_URL="${KG_URL}&api_key=${PULSE_API_TOKEN}"
        fi
        KG_OUT=$(curl -s -m 5 "${KG_URL}" 2>/dev/null || true)
        if [ -n "${KG_OUT}" ] && ! printf '%s' "${KG_OUT}" | grep -E '"detail"' >/dev/null; then
            MCP_OUT="${KG_OUT}"
            emit_check "mcp_kg_health" "ok" "kg_health responded for board ${BOARD_ID}"
        else
            emit_check "mcp_kg_health" "fail" "kg_health did not respond cleanly: ${KG_OUT:-no-response}"
        fi
    fi
else
    emit_check "mcp_kg_health" "fail" "MCP URL undetermined"
fi

# ---- Check 8: pulse_api_token set (all modes) -------------------------------
if [ -n "${PULSE_API_TOKEN:-}" ]; then
    emit_check "pulse_api_token_set" "ok" "token present"
else
    emit_check "pulse_api_token_set" "fail" "PULSE_API_TOKEN missing (required for all modes)"
fi

# ---- Check 9: active-board.json exists --------------------------------------
if [ -f "${ACTIVE_BOARD_FILE}" ]; then
    emit_check "active_board_file_exists" "ok" "${ACTIVE_BOARD_FILE}"
else
    emit_check "active_board_file_exists" "warn" "no active board chosen yet"
fi

# ---- Check 10: active board still exists in Pulse (kg query) ----------------
if [ -f "${ACTIVE_BOARD_FILE}" ] && [ -n "${MCP_URL}" ]; then
    BOARD_ID=$(grep -E '"board_id"' "${ACTIVE_BOARD_FILE}" | head -1 | sed -E 's/.*"board_id"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/' || true)
    if [ -n "${BOARD_ID}" ]; then
        # We don't have a board-exists tool to call directly here without
        # a richer client. Best-effort: assume present unless MCP errored.
        if [ -n "${MCP_OUT:-}" ] && ! printf '%s' "${MCP_OUT}" | grep -E '"error"\s*:' >/dev/null; then
            emit_check "active_board_present_in_pulse" "ok" "board_id=${BOARD_ID}"
        else
            emit_check "active_board_present_in_pulse" "warn" "could not verify (MCP not reachable)"
        fi
    else
        emit_check "active_board_present_in_pulse" "warn" "active-board.json missing board_id"
    fi
else
    emit_check "active_board_present_in_pulse" "warn" "no active board or MCP URL"
fi

# ---- Check 11: claude plugin validate okto-pulse ----------------------------
if command -v claude >/dev/null 2>&1; then
    REPO_ROOT=$(cd "${SCRIPT_DIR}/../../.." && pwd)
    if (cd "${REPO_ROOT}" && claude plugin validate plugins/okto-pulse) >/dev/null 2>&1; then
        emit_check "claude_plugin_validate_clean" "ok" "validate passed"
    else
        emit_check "claude_plugin_validate_clean" "fail" "claude plugin validate failed"
    fi
else
    emit_check "claude_plugin_validate_clean" "warn" "claude CLI not on PATH"
fi

# ---- Final summary ----------------------------------------------------------
printf '{"summary":{"green":%d,"yellow":%d,"red":%d,"checks_run":%d}}\n' "${GREEN}" "${YELLOW}" "${RED}" "${RUN}"
exit 0
