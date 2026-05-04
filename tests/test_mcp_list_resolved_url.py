"""Card e1edcc19 / scenario ts_b2b47189 — claude mcp list shows resolved URL.

End-to-end: after the okto-pulse plugin is installed via the marketplace,
``claude mcp list`` must show the okto-pulse MCP server entry with the URL
resolved from the ``${user_config.pulse_mcp_url}`` template.

The ``pulse_mcp_url`` userConfig has a default of
``http://127.0.0.1:8101/mcp`` declared in plugin.json, so the substitution
resolves automatically without the user setting an explicit value.

Scope:
    - Assert the plugin manifest declares ``mcpServers.okto-pulse`` with the
      ``${user_config.pulse_mcp_url}`` URL template (static — runs always).
    - If the local box has the ``claude`` CLI we run smoke_install.sh and
      then assert ``claude mcp list`` mentions both ``okto-pulse`` and the
      resolved URL ``127.0.0.1:8101/mcp``.

When ``claude`` is missing we ``pytest.skip`` the dynamic half; CI's matrix
is the strict gate.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.scenario("ts_b2b47189")
@pytest.mark.card("e1edcc19-564d-4462-84e9-7e7143d9137f")
@pytest.mark.sprint("6eaa093b-2ca1-4adc-aabf-1d7bc0e9025f")
@pytest.mark.spec("75fe081f-2e7f-4d38-ba73-57d47815c369")
def test_claude_mcp_list_shows_resolved_url(
    clean_claude_home: Path,
    plugin_json_path: Path,
    smoke_install_script: Path,
    mcp_url: str,
) -> None:
    """Scenario ts_b2b47189 — ``claude mcp list`` shows the resolved URL.

    GIVEN: The okto-pulse plugin is declared with a templated MCP URL
        ``${user_config.pulse_mcp_url}`` whose default is
        ``http://127.0.0.1:8101/mcp``.
    WHEN:  After ``smoke_install.sh`` adds the marketplace and installs
        the plugin, the user runs ``claude mcp list``.
    THEN:  The output names ``okto-pulse`` and the resolved URL
        ``127.0.0.1:8101/mcp`` (template substitution succeeded).
    """
    # Static prerequisite: plugin.json declares the MCP server with the
    # templated URL. This half runs regardless of CLI availability.
    assert plugin_json_path.exists(), (
        f"R1.2 deliverable missing: {plugin_json_path}"
    )
    plugin = json.loads(plugin_json_path.read_text(encoding="utf-8"))
    mcp_servers = plugin.get("mcpServers") or {}
    assert "okto-pulse" in mcp_servers, (
        "plugin.json must declare an 'okto-pulse' MCP server entry"
    )
    okto_entry = mcp_servers["okto-pulse"]
    assert okto_entry.get("type") == "http"
    assert okto_entry.get("url") == "${user_config.pulse_mcp_url}", (
        "MCP URL must be the userConfig template so /plugin enable can "
        "resolve it from the user's pulse_mcp_url choice (default "
        "http://127.0.0.1:8101/mcp)."
    )

    if shutil.which("claude") is None:
        pytest.skip("claude CLI not installed; tested in CI matrix")

    # Dynamic half — run the smoke install, then exercise `claude mcp list`.
    env = {
        **os.environ,
        "PULSE_DEPLOY_MODE": "local-pip",
        "PULSE_API_TOKEN": "",
        "CLAUDE_HOME": str(clean_claude_home),
    }
    install = subprocess.run(
        [str(smoke_install_script)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert install.returncode == 0, (
        f"smoke_install.sh failed (rc={install.returncode})\n"
        f"stdout:\n{install.stdout}\nstderr:\n{install.stderr}"
    )

    # `claude mcp list` does a health check on each server, so allow a few
    # seconds. We only care about substring presence — not the
    # connect/fail status marker (Pulse may or may not be running).
    mcp_list = subprocess.run(
        ["claude", "mcp", "list"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert mcp_list.returncode == 0, (
        f"`claude mcp list` failed (rc={mcp_list.returncode})\n"
        f"stdout:\n{mcp_list.stdout}\nstderr:\n{mcp_list.stderr}"
    )
    combined = mcp_list.stdout + mcp_list.stderr

    assert "okto-pulse" in combined, (
        f"`claude mcp list` did not mention 'okto-pulse'.\n"
        f"output:\n{combined}"
    )
    # Pull the host:path tail out of the canonical URL so the assertion
    # tolerates the prefix being shown as either http:// or https://.
    resolved_tail = "127.0.0.1:8101/mcp"
    assert resolved_tail in combined, (
        f"`claude mcp list` did not show the resolved URL "
        f"'{resolved_tail}'. The userConfig template "
        f"${{user_config.pulse_mcp_url}} did not substitute.\n"
        f"output:\n{combined}"
    )
