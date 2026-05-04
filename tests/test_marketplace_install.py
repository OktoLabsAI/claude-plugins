"""Card ae5f23bb / scenario ts_d3c447de — fresh marketplace install.

End-to-end: a clean Claude Code home + /plugin marketplace add +
/plugin install must land okto-pulse in /plugin list with the manifest
version and the marketplace as source.

R1.2 lift: the deliverables are present, so we now assert the
prerequisites (manifests parse, version mirror is intact) and -- if
the local box has the `claude` CLI -- we delegate the actual
marketplace+install dance to ``tools/ci/smoke_install.sh``.

When `claude` is missing we ``pytest.skip``: CI's matrix
(ubuntu-latest + macos-latest) is the strict gate (per TR
``tr_c59d0fd0`` / BR ``br_86ef48d7``).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.scenario("ts_d3c447de")
@pytest.mark.card("ae5f23bb-a3a5-4967-987a-cc3e392e7189")
@pytest.mark.sprint("97de0400-5ba6-4c16-8945-9e1f78d5bd40")
@pytest.mark.spec("75fe081f-2e7f-4d38-ba73-57d47815c369")
def test_fresh_install_via_marketplace_shows_plugin(
    clean_claude_home: Path,
    marketplace_json_path: Path,
    plugin_json_path: Path,
    smoke_install_script: Path,
) -> None:
    """Scenario ts_d3c447de — fresh install via marketplace shows plugin.

    GIVEN: A clean Claude Code installation with no oktolabs-plugins
        marketplace registered and no okto-pulse plugin installed.
    WHEN:  User runs /plugin marketplace add oktolabsai/claude-plugins
        followed by /plugin install okto-pulse@oktolabs-plugins.
    THEN:  The /plugin list output includes an entry for okto-pulse with
        the version from plugin.json and source pointing to the marketplace.
    """
    # Preconditions — R1.2 deliverables.
    assert marketplace_json_path.exists(), (
        f"R1.2 deliverable missing: {marketplace_json_path}"
    )
    assert plugin_json_path.exists(), (
        f"R1.2 deliverable missing: {plugin_json_path}"
    )
    assert smoke_install_script.exists(), (
        f"R1.2 deliverable missing: {smoke_install_script}"
    )

    marketplace = json.loads(marketplace_json_path.read_text(encoding="utf-8"))
    plugin = json.loads(plugin_json_path.read_text(encoding="utf-8"))

    # 1:1 version mirror (BR br_967ba381) -- plugin.json#version must
    # equal the marketplace entry version.
    assert marketplace["plugins"][0]["name"] == "okto-pulse"
    assert marketplace["plugins"][0]["version"] == plugin["version"]

    # If the claude CLI is available, delegate to the real smoke
    # script. This keeps developer machines that DO have it green and
    # ensures CI exercises the live path.
    if shutil.which("claude") is None:
        pytest.skip("claude CLI not installed; tested in CI matrix")

    env = {
        **os.environ,
        "PULSE_DEPLOY_MODE": "local-pip",
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
        f"smoke_install.sh failed (rc={result.returncode})\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
