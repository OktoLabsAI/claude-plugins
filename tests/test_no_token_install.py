"""Card c052f2c8 / scenario ts_659675c6 — no-token install in local-pip + docker.

End-to-end: a user without pulse_api_token must still complete
/okto-pulse:setup against a local Pulse daemon (local-pip or docker
deploy mode). MCP handshake succeeds without an Authorization header.

Status: RED scaffold. Lifts to passing once R1.2 ships
- plugins/okto-pulse/.claude-plugin/plugin.json (with userConfig)
- tools/ci/smoke_install.sh (with deploy-mode parameter)
- a local Pulse fixture reachable at http://127.0.0.1:8101/mcp
"""
from __future__ import annotations

from pathlib import Path

import pytest

from .scenarios import SCENARIOS

_S = SCENARIOS["ts_659675c6"]


@pytest.mark.scenario("ts_659675c6")
@pytest.mark.card("c052f2c8-29e0-44f9-8b9b-62be12f210f2")
@pytest.mark.sprint("97de0400-5ba6-4c16-8945-9e1f78d5bd40")
@pytest.mark.spec("75fe081f-2e7f-4d38-ba73-57d47815c369")
@pytest.mark.xfail(
    reason=(
        "awaiting R1.2 impl: plugin.json userConfig + smoke_install.sh "
        "+ local Pulse fixture"
    ),
    strict=True,
)
def test_no_token_install_works(
    clean_claude_home: Path,
    plugin_json_path: Path,
    smoke_install_script: Path,
    deploy_mode: str,
    mcp_url: str,
) -> None:
    f"""GIVEN: {_S['given']}
    WHEN:  {_S['when']}
    THEN:  {_S['then']}

    Parametrized over deploy_mode in {{"local-pip", "docker"}}.
    """
    # Preconditions — both manifest and harness are R1.2 deliverables.
    assert plugin_json_path.exists(), (
        f"R1.2 deliverable missing: {plugin_json_path}"
    )
    assert smoke_install_script.exists(), (
        f"R1.2 deliverable missing: {smoke_install_script}"
    )

    # The harness will:
    #   1. Boot a local Pulse daemon for {deploy_mode} (R1.2 fixture).
    #   2. Run smoke_install.sh with PULSE_DEPLOY_MODE=deploy_mode and
    #      PULSE_API_TOKEN intentionally unset / empty.
    #   3. Open an MCP HTTP session at mcp_url with NO Authorization header.
    #   4. Assert the MCP `initialize` call succeeds (handshake completes,
    #      protocol_version negotiated, no 401/403).
    #   5. Assert at least one tool is listed in the resulting tools/list
    #      response (proves real tool access, not a stub handshake).
    #   6. Assert no log line mentions a missing token error.
    raise NotImplementedError(
        f"No-token MCP smoke for deploy_mode={deploy_mode} lands in R1.2."
    )
