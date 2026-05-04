"""Card ae5f23bb / scenario ts_d3c447de — fresh marketplace install.

End-to-end: a clean Claude Code home + /plugin marketplace add +
/plugin install must land okto-pulse in /plugin list with the manifest
version and the marketplace as source.

Status: RED scaffold. Lifts to passing once R1.2 ships
- .claude-plugin/marketplace.json
- plugins/okto-pulse/.claude-plugin/plugin.json
- tools/ci/smoke_install.sh
"""
from __future__ import annotations

from pathlib import Path

import pytest

from .scenarios import SCENARIOS

_S = SCENARIOS["ts_d3c447de"]


@pytest.mark.scenario("ts_d3c447de")
@pytest.mark.card("ae5f23bb-a3a5-4967-987a-cc3e392e7189")
@pytest.mark.sprint("97de0400-5ba6-4c16-8945-9e1f78d5bd40")
@pytest.mark.spec("75fe081f-2e7f-4d38-ba73-57d47815c369")
@pytest.mark.xfail(
    reason=(
        "awaiting R1.2 impl: marketplace.json + plugin.json + smoke_install.sh"
    ),
    strict=True,
)
def test_fresh_install_via_marketplace_shows_plugin(
    clean_claude_home: Path,
    marketplace_json_path: Path,
    plugin_json_path: Path,
    smoke_install_script: Path,
) -> None:
    f"""GIVEN: {_S['given']}
    WHEN:  {_S['when']}
    THEN:  {_S['then']}
    """
    # Preconditions — these resources are R1.2 deliverables.
    assert marketplace_json_path.exists(), (
        f"R1.2 deliverable missing: {marketplace_json_path}"
    )
    assert plugin_json_path.exists(), (
        f"R1.2 deliverable missing: {plugin_json_path}"
    )
    assert smoke_install_script.exists(), (
        f"R1.2 deliverable missing: {smoke_install_script}"
    )

    # The harness will:
    #   1. Use clean_claude_home as an isolated Claude Code home.
    #   2. Run `/plugin marketplace add oktolabsai/claude-plugins`.
    #   3. Run `/plugin install okto-pulse@oktolabs-plugins`.
    #   4. Capture `/plugin list` and assert an okto-pulse row exists,
    #      with the version from plugin_json_path and source pointing
    #      back to the marketplace.
    raise NotImplementedError(
        "Smoke-install harness lands in R1.2 (impl card builds tools/ci/smoke_install.sh)."
    )
