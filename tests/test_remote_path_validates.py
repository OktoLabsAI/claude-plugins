"""Card 7b3a8b71 / scenario ts_8c3aa4ed - remote path validates URL/token.

bootstrap-remote.sh must validate the URL shape against
``^https?://[^/]+/mcp(/.*)?$`` BEFORE any network call, then probe
/readyz + okto_pulse_kg_health with the Bearer token. The full
end-to-end "live remote Pulse" assertion (kg_health returns ok,
userConfig persisted) requires a reachable Pulse fixture and is
``pytest.skip``-ped on the dev box.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


@pytest.mark.scenario("ts_8c3aa4ed")
@pytest.mark.card("7b3a8b71-ed98-487d-b393-d37ccafb51ad")
@pytest.mark.sprint("2c353ca4-c66d-4f9e-9d4f-9c4683c66f5b")
@pytest.mark.spec("46dbff78-5997-442e-a6c3-c6fb6cb735e3")
def test_remote_path_validates_url_and_token(
    bootstrap_remote_script: Path,
) -> None:
    """Scenario ts_8c3aa4ed - remote path validates URL/token (happy path).

    Requires a reachable Pulse instance to fully validate. Skipped on the
    dev box; full E2E coverage lives in CI's optional remote-Pulse job
    (see R2.3 plans).
    """
    assert bootstrap_remote_script.exists(), (
        f"R2.2 deliverable missing: {bootstrap_remote_script}"
    )
    pytest.skip(
        "requires a reachable remote Pulse instance; "
        "exit-30 (no-network) and exit-10 (bad-shape) cases covered "
        "by test_remote_path_rejects_malformed_url"
    )


@pytest.mark.scenario("ts_8c3aa4ed")
@pytest.mark.card("7b3a8b71-ed98-487d-b393-d37ccafb51ad")
@pytest.mark.sprint("2c353ca4-c66d-4f9e-9d4f-9c4683c66f5b")
@pytest.mark.spec("46dbff78-5997-442e-a6c3-c6fb6cb735e3")
@pytest.mark.parametrize(
    ("pulse_mcp_url", "expected_exit", "expected_reason"),
    [
        # Empty URL - exit 10, bad_url_shape.
        ("", 10, "bad_url_shape"),
        # Missing /mcp suffix - exit 10, bad_url_shape.
        ("http://no-mcp-suffix", 10, "bad_url_shape"),
        # Too short - exit 10.
        ("https://", 10, "bad_url_shape"),
        # Wrong protocol - exit 10.
        ("ftp://example.com/mcp", 10, "bad_url_shape"),
        # Valid shape but unreachable host -> readyz_unreachable
        # (the URL-shape branch passed - exit 30 confirms shape was OK).
        ("http://127.0.0.1:1/mcp", 30, "readyz_unreachable"),
        # Valid shape with /mcp/v1 suffix - shape OK, network fails -> 30.
        ("http://127.0.0.1:1/mcp/v1", 30, "readyz_unreachable"),
    ],
    ids=["empty", "no-mcp", "short", "ftp", "valid-unreach", "valid-with-path"],
)
def test_remote_path_rejects_malformed_url(
    pulse_mcp_url: str,
    expected_exit: int,
    expected_reason: str,
    bootstrap_remote_script: Path,
) -> None:
    """Sub-case: URL-shape branch (exit 10) and unreachable-host branch (exit 30).

    Per spec FR[6] / BR br_4b32d5a2: URL shape is validated against
    ``https?://[^/]+/mcp(/.*)?$`` BEFORE any network call. Bad shape -> 10.
    Good shape but unreachable -> 30.
    """
    result = subprocess.run(
        [str(bootstrap_remote_script)],
        env={
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "PULSE_MCP_URL": pulse_mcp_url,
            "PULSE_API_TOKEN": "fake-token",
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == expected_exit, (
        f"PULSE_MCP_URL={pulse_mcp_url!r} expected exit {expected_exit}, "
        f"got {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    # Last NDJSON line on stdout must be an error envelope with the right reason.
    lines = [ln for ln in result.stdout.strip().splitlines() if ln.strip()]
    assert lines, f"no stdout NDJSON for url={pulse_mcp_url!r}"
    final = json.loads(lines[-1])
    assert final.get("ok") is False, f"expected ok=false; got {final}"
    assert final.get("error", {}).get("reason") == expected_reason, (
        f"reason mismatch: expected={expected_reason} got={final}"
    )
