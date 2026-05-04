#!/usr/bin/env bash
# Bootstrap okto-pulse in local-pip deploy mode.
#
# Card c12b1506. Implements FR/TR/BR for /okto-pulse:setup local-pip path.
# - Probe Python 3.12 (exit 10 on miss).
# - Ensure okto-pulse pip installed at OKTO_PULSE_PIN_VERSION (exit 20 on
#   pip failure).
# - Run `okto-pulse init --agents` (idempotent).
# - Spawn `okto-pulse serve --accept-terms` in the background unless
#   OKTO_PULSE_FORCE_NO_SERVE=1 (test seam).
# - Poll http://127.0.0.1:8100/readyz up to OKTO_PULSE_READYZ_TIMEOUT_SECONDS
#   (exit 30 on timeout).
# - Final NDJSON stdout line: {"ok":true,"mode":"local-pip",...}.
# - SIGINT / SIGTERM during run -> exit 2 with cancelled NDJSON.
#
# macOS bash 3.2 baseline: no `${var,,}`, no associative arrays, no
# `timeout` binary. Stick to POSIX-y constructs.
set -euo pipefail

OKTO_PULSE_PIN_VERSION="${OKTO_PULSE_PIN_VERSION:-0.1.14}"
PULSE_API_TOKEN="${PULSE_API_TOKEN:-}"
OKTO_PULSE_READYZ_TIMEOUT_SECONDS="${OKTO_PULSE_READYZ_TIMEOUT_SECONDS:-15}"
OKTO_PULSE_FORCE_NO_SERVE="${OKTO_PULSE_FORCE_NO_SERVE:-0}"
PULSE_LOCAL_READYZ_URL="${PULSE_LOCAL_READYZ_URL:-http://127.0.0.1:8100/readyz}"

DATA_DIR="${CLAUDE_PLUGIN_DATA:-${HOME}/.claude/plugins/data/okto-pulse}"
mkdir -p "${DATA_DIR}"
SERVE_LOG="${DATA_DIR}/serve.log"

# Tracks the spawned `okto-pulse serve` PID so the SIGINT trap can clean it up.
SERVE_PID=""

iso8601() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

emit_event() {
    # NDJSON progress on stdout. $1 = phase name.
    printf '{"event":"%s","ts":"%s"}\n' "$1" "$(iso8601)"
}

emit_final_ok() {
    # $1 = pid, $2 = resolved version
    printf '{"ok":true,"mode":"local-pip","url":"http://127.0.0.1:8101/mcp","pid":%s,"version":"%s"}\n' "$1" "$2"
}

emit_final_err() {
    # $1 = reason, $2 = message
    printf '{"ok":false,"error":{"reason":"%s","message":"%s"}}\n' "$1" "$2"
}

emit_cancel() {
    if [ -n "${SERVE_PID}" ]; then
        kill "${SERVE_PID}" 2>/dev/null || true
    fi
    emit_final_err "cancelled" "user cancelled bootstrap"
    exit 2
}

trap 'emit_cancel' INT TERM

# ---- 1) Python 3.12 probe ---------------------------------------------------
emit_event "python_check"
PYBIN=""
if command -v python3.12 >/dev/null 2>&1; then
    PYBIN="python3.12"
elif command -v python3 >/dev/null 2>&1; then
    if python3 -c 'import sys; sys.exit(0 if sys.version_info[:2]==(3,12) else 1)' 2>/dev/null; then
        PYBIN="python3"
    fi
fi
if [ -z "${PYBIN}" ]; then
    printf '[bootstrap-local-pip] python 3.12 not found on PATH\n' >&2
    emit_final_err "python_3_12_missing" "Python 3.12 not detected"
    exit 10
fi
printf '[bootstrap-local-pip] using %s\n' "${PYBIN}" >&2

# ---- 2) Pip-show + maybe install -------------------------------------------
emit_event "pip_check"
INSTALLED_VERSION=""
if "${PYBIN}" -m pip show okto-pulse >/tmp/.okto_pulse_pipshow.$$ 2>/dev/null; then
    INSTALLED_VERSION=$(awk -F': ' '/^Version: /{print $2}' /tmp/.okto_pulse_pipshow.$$ | tr -d '\r\n ')
fi
rm -f /tmp/.okto_pulse_pipshow.$$ 2>/dev/null || true
printf '[bootstrap-local-pip] pip-installed okto-pulse: %s (pin=%s)\n' "${INSTALLED_VERSION:-<none>}" "${OKTO_PULSE_PIN_VERSION}" >&2

NEED_INSTALL=0
if [ -z "${INSTALLED_VERSION}" ]; then
    NEED_INSTALL=1
else
    # Compare via Python to avoid bash version-sort quirks.
    if ! "${PYBIN}" -c "import sys; from packaging.version import Version; sys.exit(0 if Version('${INSTALLED_VERSION}') >= Version('${OKTO_PULSE_PIN_VERSION}') else 1)" 2>/dev/null; then
        NEED_INSTALL=1
    fi
fi

if [ "${NEED_INSTALL}" = "1" ]; then
    emit_event "pip_install"
    if ! "${PYBIN}" -m pip install -U "okto-pulse==${OKTO_PULSE_PIN_VERSION}" "okto-pulse-core==${OKTO_PULSE_PIN_VERSION}" >&2; then
        emit_final_err "pip_install_failed" "pip install failed for okto-pulse==${OKTO_PULSE_PIN_VERSION}"
        exit 20
    fi
    INSTALLED_VERSION="${OKTO_PULSE_PIN_VERSION}"
fi

# ---- 3) okto-pulse init --agents -------------------------------------------
emit_event "init_agents"
if ! command -v okto-pulse >/dev/null 2>&1; then
    emit_final_err "okto_pulse_missing" "okto-pulse not on PATH after pip install"
    exit 20
fi
if ! okto-pulse init --agents >&2; then
    emit_final_err "init_agents_failed" "okto-pulse init --agents non-zero exit"
    exit 20
fi

# ---- 4) Spawn serve ---------------------------------------------------------
emit_event "start_serve"
if [ "${OKTO_PULSE_FORCE_NO_SERVE}" = "1" ]; then
    SERVE_PID=0
    printf '[bootstrap-local-pip] OKTO_PULSE_FORCE_NO_SERVE=1; skipping serve spawn\n' >&2
else
    nohup okto-pulse serve --accept-terms >>"${SERVE_LOG}" 2>&1 &
    SERVE_PID=$!
    printf '[bootstrap-local-pip] spawned okto-pulse serve pid=%s log=%s\n' "${SERVE_PID}" "${SERVE_LOG}" >&2
fi

# ---- 5) Poll /readyz --------------------------------------------------------
emit_event "wait_readyz"
DEADLINE=$(( $(date +%s) + OKTO_PULSE_READYZ_TIMEOUT_SECONDS ))
READY=0
while [ "$(date +%s)" -lt "${DEADLINE}" ]; do
    HTTP_CODE=$(curl -s -m 2 -o /dev/null -w '%{http_code}' "${PULSE_LOCAL_READYZ_URL}" 2>/dev/null || true)
    if [ "${HTTP_CODE}" = "200" ]; then
        READY=1
        break
    fi
    sleep 0.2 2>/dev/null || sleep 1
done
if [ "${READY}" != "1" ]; then
    if [ -n "${SERVE_PID}" ] && [ "${SERVE_PID}" != "0" ]; then
        kill "${SERVE_PID}" 2>/dev/null || true
    fi
    emit_final_err "readyz_timeout" "/readyz did not return 200 within ${OKTO_PULSE_READYZ_TIMEOUT_SECONDS}s"
    exit 30
fi

# ---- 6) Final ok ------------------------------------------------------------
emit_final_ok "${SERVE_PID:-0}" "${INSTALLED_VERSION}"
exit 0
