"""Card 7b3a8b71 / scenario ts_8c3aa4ed — remote path validates URL/token.

End-to-end: bootstrap-remote.sh must validate URL shape, probe /readyz
with the Bearer token, and call okto_pulse_kg_health to confirm auth — no
pip install, no docker container.

Status: RED scaffold. Lifts to passing once R2.2 ships
- plugins/okto-pulse/bin/bootstrap-remote.sh
"""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.scenario("ts_8c3aa4ed")
@pytest.mark.card("7b3a8b71-ed98-487d-b393-d37ccafb51ad")
@pytest.mark.sprint("2c353ca4-c66d-4f9e-9d4f-9c4683c66f5b")
@pytest.mark.spec("46dbff78-5997-442e-a6c3-c6fb6cb735e3")
@pytest.mark.xfail(
    reason="awaiting R2.2 impl: plugins/okto-pulse/bin/bootstrap-remote.sh",
    strict=True,
)
def test_remote_path_validates_url_and_token(
    tmp_path: Path,
    bootstrap_remote_script: Path,
) -> None:
    """Scenario ts_8c3aa4ed — remote path validates URL/token.

    GIVEN: A reachable remote Pulse instance at
        http://192.168.31.154:9100/mcp with a valid Bearer token; user has
        selected 'remote' deploy mode and entered URL+token.
    WHEN:  /okto-pulse:setup runs bootstrap-remote.sh to completion.
    THEN:  No pip install, no docker container; URL validated; /readyz
        returns 200 with the Bearer header; okto_pulse_kg_health returns ok;
        userConfig is populated with the URL and token (token sensitive=true →
        keychain); MCP handshake succeeds.
    """
    assert bootstrap_remote_script.exists(), (
        f"R2.2 deliverable missing: {bootstrap_remote_script}"
    )

    # The R2.2 harness will:
    #   1. subprocess.run([str(bootstrap_remote_script)],
    #        env={"PULSE_MCP_URL": "http://192.168.31.154:9100/mcp",
    #             "PULSE_API_TOKEN": "<valid-bearer>"},
    #        capture_output=True, check=False, timeout=10)
    #   2. Assert returncode == 0.
    #   3. Parse the last stdout line as JSON; assert ok=true and mode=remote.
    #   4. Assert no `pip install` / `docker pull` was invoked
    #      (e.g. verify a sentinel that those binaries weren't called via
    #      a wrapping PATH override or strace-style shim).
    raise NotImplementedError(
        "Remote-path harness lands in R2.2 (impl card 303d0e09)."
    )


@pytest.mark.scenario("ts_8c3aa4ed")
@pytest.mark.card("7b3a8b71-ed98-487d-b393-d37ccafb51ad")
@pytest.mark.sprint("2c353ca4-c66d-4f9e-9d4f-9c4683c66f5b")
@pytest.mark.spec("46dbff78-5997-442e-a6c3-c6fb6cb735e3")
@pytest.mark.xfail(
    reason="awaiting R2.2 impl: bootstrap-remote.sh URL-shape validation",
    strict=True,
)
def test_remote_path_rejects_malformed_url(
    bootstrap_remote_script: Path,
) -> None:
    """Sub-case: malformed URL must hit the precondition exit code (10).

    Per spec FR[6] / BR br_4b32d5a2: URL shape is validated against
    `https?://[^/]+/mcp(/.*)?$` BEFORE any network call.
    """
    assert bootstrap_remote_script.exists(), (
        f"R2.2 deliverable missing: {bootstrap_remote_script}"
    )
    raise NotImplementedError(
        "Subprocess invocation with malformed PULSE_MCP_URL → exit 10 lands in R2.2."
    )
