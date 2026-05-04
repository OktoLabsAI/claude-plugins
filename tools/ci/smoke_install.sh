#!/usr/bin/env sh
# Smoke-install the okto-pulse plugin from this repo as a marketplace.
#
# Inputs (env):
#   PULSE_DEPLOY_MODE  - local-pip | docker | remote (default local-pip)
#   PULSE_API_TOKEN    - bearer token; may be empty for local modes
#   CLAUDE_HOME        - isolated Claude Code home for the test (must exist)
#
# Behaviour:
#   - if `claude` is not on PATH: print a skip notice on stderr and exit 0.
#     Local dev convenience so pytest stays green; CI installs the CLI.
#   - else: marketplace add this repo, install okto-pulse, verify
#     `claude plugin list` mentions it.
set -eu

PULSE_DEPLOY_MODE="${PULSE_DEPLOY_MODE:-local-pip}"
PULSE_API_TOKEN="${PULSE_API_TOKEN:-}"

case "$PULSE_DEPLOY_MODE" in
    local-pip|docker|remote) ;;
    *)
        printf 'smoke_install: invalid PULSE_DEPLOY_MODE=%s\n' "$PULSE_DEPLOY_MODE" >&2
        exit 1
        ;;
esac

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

if ! command -v claude >/dev/null 2>&1; then
    printf 'smoke_install: claude CLI not installed; skipping marketplace add+install\n' >&2
    exit 0
fi

if [ -z "${CLAUDE_HOME:-}" ]; then
    printf 'smoke_install: CLAUDE_HOME must be set\n' >&2
    exit 1
fi

export CLAUDE_HOME
export PULSE_DEPLOY_MODE
export PULSE_API_TOKEN

claude plugin marketplace add "$REPO_DIR"
claude plugin install okto-pulse@oktolabs-plugins

# Verify plugin is present AND loaded successfully (not just present in list)
PLUGIN_LIST="$(claude plugin list 2>&1)"
if ! printf '%s' "$PLUGIN_LIST" | grep -q 'okto-pulse'; then
    printf 'smoke_install: okto-pulse not found in plugin list\n' >&2
    printf '%s\n' "$PLUGIN_LIST" >&2
    exit 1
fi
if printf '%s' "$PLUGIN_LIST" | grep -A3 'okto-pulse@oktolabs-plugins' | grep -q 'failed to load'; then
    printf 'smoke_install: okto-pulse failed to load\n' >&2
    printf '%s\n' "$PLUGIN_LIST" >&2
    exit 1
fi
