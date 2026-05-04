#!/usr/bin/env sh
# Wrap `claude plugin validate plugins/okto-pulse`.
#
# - if claude is not installed: emit a skip notice on stderr and exit 0
#   so local pytest stays green. CI installs the CLI and enforces.
# - if claude IS installed: fail on non-zero exit OR any output line
#   containing "WARN" / "Warning:".
set -eu

if ! command -v claude >/dev/null 2>&1; then
    printf 'validate_plugin: claude CLI not installed; skipping\n' >&2
    exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_DIR"

OUT="$(claude plugin validate plugins/okto-pulse 2>&1)"
RC=$?
printf '%s\n' "$OUT"
if [ "$RC" -ne 0 ]; then
    exit "$RC"
fi
if printf '%s\n' "$OUT" | grep -E '(WARN|Warning:)' >/dev/null 2>&1; then
    printf 'validate_plugin: warnings detected; failing per CI policy\n' >&2
    exit 1
fi
exit 0
