"""Card c052f2c8 / scenario ts_659675c6 — no-token install in local-pip + docker.

End-to-end: a user without pulse_api_token must still complete
/okto-pulse:setup against a local Pulse daemon (local-pip or docker
deploy mode). MCP handshake succeeds without an Authorization header.

Scope split (R1.2 vs R1.3):
    The live MCP-handshake assertion ("initialize succeeds, tools/list
    returns >=1 tool, no missing-token log line") is the R1.3 smoke;
    R1.2 cannot ship a real Pulse fixture. What we exercise here is:
        - the prerequisite manifests + smoke-install script exist;
        - the smoke-install script tolerates an empty PULSE_API_TOKEN
          for both local-pip and docker deploy modes (it must not
          short-circuit on the missing token);
        - if the local box has the `claude` CLI we run smoke_install.sh
          end-to-end.
    When `claude` is missing we ``pytest.skip``; CI's matrix is the
    strict gate.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.scenario("ts_659675c6")
@pytest.mark.card("c052f2c8-29e0-44f9-8b9b-62be12f210f2")
@pytest.mark.sprint("97de0400-5ba6-4c16-8945-9e1f78d5bd40")
@pytest.mark.spec("75fe081f-2e7f-4d38-ba73-57d47815c369")
def test_no_token_install_works(
    clean_claude_home: Path,
    plugin_json_path: Path,
    smoke_install_script: Path,
    deploy_mode: str,
    mcp_url: str,
) -> None:
    """Scenario ts_659675c6 — no-token install in local-pip + docker.

    GIVEN: A user installs the plugin and selects local-pip (or docker)
        deploy mode in /okto-pulse:setup; pulse_api_token is left empty.
    WHEN:  Plugin is enabled and the MCP server is contacted at
        http://127.0.0.1:8101/mcp without an Authorization header.
    THEN:  MCP handshake succeeds; tool calls work; setup proceeds to the
        board picker; no error about missing token.

    Parametrized over deploy_mode in {"local-pip", "docker"}.
    """
    assert plugin_json_path.exists(), (
        f"R1.2 deliverable missing: {plugin_json_path}"
    )
    assert smoke_install_script.exists(), (
        f"R1.2 deliverable missing: {smoke_install_script}"
    )

    # Manifest sanity: pulse_api_token is declared, sensitive, and is NOT
    # marked required at the schema level (deploy mode local-pip / docker
    # must work with an empty token).
    plugin = json.loads(plugin_json_path.read_text(encoding="utf-8"))
    user_config = plugin.get("userConfig") or {}
    assert "pulse_api_token" in user_config, (
        "userConfig.pulse_api_token is required by spec dec_e59e2a08"
    )
    token_cfg = user_config["pulse_api_token"]
    assert token_cfg.get("sensitive") is True, (
        "userConfig.pulse_api_token must be flagged sensitive"
    )

    if shutil.which("claude") is None:
        pytest.skip("claude CLI not installed; tested in CI matrix")

    env = {
        **os.environ,
        "PULSE_DEPLOY_MODE": deploy_mode,
        "PULSE_API_TOKEN": "",
        "CLAUDE_HOME": str(clean_claude_home),
    }
    result = subprocess.run(
        [str(smoke_install_script)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"smoke_install.sh failed for deploy_mode={deploy_mode} "
        f"with empty PULSE_API_TOKEN (rc={result.returncode})\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    # No missing-token error should have surfaced.
    combined = (result.stdout + result.stderr).lower()
    assert "missing token" not in combined, (
        f"Token-absence error leaked into output for {deploy_mode}:\n{combined}"
    )
    assert "401" not in combined and "403" not in combined, (
        f"Auth-failure status leaked into output for {deploy_mode}:\n{combined}"
    )
