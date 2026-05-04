#!/usr/bin/env sh
# Run gitleaks on the repo. If gitleaks is not installed locally we
# print a notice to stderr and exit 0 -- CI installs gitleaks and will
# enforce; this is a local-dev convenience.
set -eu

if command -v gitleaks >/dev/null 2>&1; then
    exec gitleaks detect --source . --no-banner --redact -v
else
    printf 'secret_scan: gitleaks not installed; CI will catch this\n' >&2
    exit 0
fi
