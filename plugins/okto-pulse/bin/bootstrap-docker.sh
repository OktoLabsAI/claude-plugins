#!/usr/bin/env bash
# Bootstrap okto-pulse in docker deploy mode.
#
# Card da60159b. Implements FR/TR/BR for /okto-pulse:setup docker path.
# - docker info / daemon reachable (exit 10 on miss).
# - docker pull ghcr image (exit 20 on registry/network failure).
# - docker compose up -d using deploy/docker-compose.yml.
# - Poll http://127.0.0.1:8101/readyz (NOT 8100 -- docker maps 8101).
# - Final NDJSON: {"ok":true,"mode":"docker",...}.
set -euo pipefail

OKTO_PULSE_PIN_VERSION="${OKTO_PULSE_PIN_VERSION:-0.1.14}"
OKTO_PULSE_IMAGE="${OKTO_PULSE_IMAGE:-ghcr.io/oktolabsai/okto-pulse:${OKTO_PULSE_PIN_VERSION}}"
OKTO_PULSE_READYZ_TIMEOUT_SECONDS="${OKTO_PULSE_READYZ_TIMEOUT_SECONDS:-30}"
PULSE_DOCKER_READYZ_URL="${PULSE_DOCKER_READYZ_URL:-http://127.0.0.1:8101/readyz}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/../deploy/docker-compose.yml"

iso8601() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
emit_event() { printf '{"event":"%s","ts":"%s"}\n' "$1" "$(iso8601)"; }
emit_final_ok() { printf '{"ok":true,"mode":"docker","url":"http://127.0.0.1:8101/mcp","image":"%s","container":"okto-pulse"}\n' "$1"; }
emit_final_err() { printf '{"ok":false,"error":{"reason":"%s","message":"%s"}}\n' "$1" "$2"; }

emit_cancel() {
    emit_final_err "cancelled" "user cancelled bootstrap"
    exit 2
}
trap 'emit_cancel' INT TERM

# ---- 1) Docker daemon reachable ---------------------------------------------
emit_event "docker_check"
if ! command -v docker >/dev/null 2>&1; then
    emit_final_err "docker_missing" "docker CLI not on PATH"
    exit 10
fi
if ! docker info >/dev/null 2>&1; then
    emit_final_err "docker_daemon_unreachable" "docker info failed; is the daemon running?"
    exit 10
fi

# ---- 2) docker pull ---------------------------------------------------------
emit_event "docker_pull"
export OKTO_PULSE_IMAGE
if ! docker pull "${OKTO_PULSE_IMAGE}" >&2; then
    emit_final_err "docker_pull_failed" "docker pull ${OKTO_PULSE_IMAGE} failed"
    exit 20
fi

# ---- 3) docker compose up -d ------------------------------------------------
emit_event "docker_up"
if [ ! -f "${COMPOSE_FILE}" ]; then
    emit_final_err "compose_file_missing" "compose file not found at ${COMPOSE_FILE}"
    exit 20
fi
if ! docker compose -f "${COMPOSE_FILE}" up -d >&2; then
    emit_final_err "docker_compose_up_failed" "docker compose up -d failed"
    exit 20
fi

# ---- 4) Poll /readyz --------------------------------------------------------
emit_event "wait_readyz"
DEADLINE=$(( $(date +%s) + OKTO_PULSE_READYZ_TIMEOUT_SECONDS ))
READY=0
while [ "$(date +%s)" -lt "${DEADLINE}" ]; do
    HTTP_CODE=$(curl -s -m 2 -o /dev/null -w '%{http_code}' "${PULSE_DOCKER_READYZ_URL}" 2>/dev/null || true)
    if [ "${HTTP_CODE}" = "200" ]; then
        READY=1
        break
    fi
    sleep 0.5 2>/dev/null || sleep 1
done
if [ "${READY}" != "1" ]; then
    emit_final_err "readyz_timeout" "/readyz did not return 200 within ${OKTO_PULSE_READYZ_TIMEOUT_SECONDS}s"
    exit 30
fi

emit_final_ok "${OKTO_PULSE_IMAGE}"
exit 0
