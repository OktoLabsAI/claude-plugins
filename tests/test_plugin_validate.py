"""Card 41c50f74 / scenario ts_a0e7dc6c — claude plugin validate clean.

CI must run `claude plugin validate plugins/okto-pulse` on every PR;
the validator must exit 0 with zero warnings against a clean
checkout. This is the official Anthropic check that catches dangling
agents/, skills/, hooks/ paths and bad mcpServers wiring before we
publish.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.scenario("ts_a0e7dc6c")
@pytest.mark.card("41c50f74-9c22-4d9b-9293-a5279ed6598f")
@pytest.mark.sprint("e18856b2-4d19-4f7b-91a0-2a9a9559d5f5")
@pytest.mark.spec("75fe081f-2e7f-4d38-ba73-57d47815c369")
def test_claude_plugin_validate_passes_on_clean_checkout(
    repo_root: Path,
) -> None:
    """Scenario ts_a0e7dc6c — claude plugin validate exits 0 with no warnings.

    GIVEN: A clean checkout with valid plugin.json
    WHEN:  CI runs `claude plugin validate plugins/okto-pulse`
    THEN:  Exit 0, zero warning lines
    """
    if shutil.which("claude") is None:
        pytest.skip(
            "claude CLI not installed; CI matrix runs this on Ubuntu+macOS"
        )
    result = subprocess.run(
        ["claude", "plugin", "validate", "plugins/okto-pulse"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"claude plugin validate failed:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    output = result.stdout + result.stderr
    for line in output.splitlines():
        assert "warn" not in line.lower(), (
            f"validator emitted warning: {line!r}"
        )
