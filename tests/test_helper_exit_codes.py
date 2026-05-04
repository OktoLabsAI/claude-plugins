"""Card b3e132a6 / scenario ts_d8e85551 — helper-script exit-code contract.

Integration: every bin/bootstrap-*.sh helper must exit with the documented
codes (0/2/10/20/30) per failure mode, and emit a final NDJSON envelope
with ok=false on every non-zero exit.

Status: RED scaffold. Lifts to passing once R2.2 ships
- plugins/okto-pulse/bin/bootstrap-local-pip.sh
- plugins/okto-pulse/bin/bootstrap-docker.sh
- plugins/okto-pulse/bin/bootstrap-remote.sh
"""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.scenario("ts_d8e85551")
@pytest.mark.card("b3e132a6-96eb-4ada-9c30-21ba8695aca9")
@pytest.mark.sprint("2c353ca4-c66d-4f9e-9d4f-9c4683c66f5b")
@pytest.mark.spec("46dbff78-5997-442e-a6c3-c6fb6cb735e3")
@pytest.mark.xfail(
    reason="awaiting R2.2 impl: bin/bootstrap-{local-pip,docker,remote}.sh",
    strict=True,
)
@pytest.mark.parametrize(
    ("scenario_id", "helper", "env_overrides", "expected_code"),
    [
        # (a) docker daemon stopped → exit 10 (precondition fail).
        ("docker-no-daemon", "bootstrap-docker.sh", {"DOCKER_HOST": "unix:///nonexistent.sock"}, 10),
        # (b) pip server unreachable → exit 20 (runtime fail).
        ("pip-unreachable", "bootstrap-local-pip.sh", {"PIP_INDEX_URL": "http://127.0.0.1:1/simple"}, 20),
        # (c) /readyz never returns 200 → exit 30 (timeout).
        ("readyz-timeout", "bootstrap-local-pip.sh", {"OKTO_PULSE_READYZ_TIMEOUT_SECONDS": "1", "OKTO_PULSE_FORCE_NO_SERVE": "1"}, 30),
    ],
    ids=lambda v: v if isinstance(v, str) else "params",
)
def test_helper_returns_documented_exit_codes(
    scenario_id: str,
    helper: str,
    env_overrides: dict[str, str],
    expected_code: int,
    plugin_root: Path,
    bootstrap_local_pip_script: Path,
    bootstrap_docker_script: Path,
    bootstrap_remote_script: Path,
) -> None:
    """Scenario ts_d8e85551 — exit-code contract.

    GIVEN: Failure injections per parametrize id.
    WHEN:  Each helper runs under the failure injection.
    THEN:  Exit code matches docker-no-daemon→10, pip-unreachable→20,
        readyz-timeout→30; final NDJSON line has ok=false and an error.message.
    """
    # Each helper is an R2.2 deliverable.
    helper_path = plugin_root / "bin" / helper
    assert helper_path.exists(), f"R2.2 deliverable missing: {helper_path}"

    # The R2.2 harness will:
    #   1. subprocess.run([str(helper_path)], env={**os.environ, **env_overrides},
    #        capture_output=True, text=True, timeout=20, check=False).
    #   2. Assert result.returncode == expected_code.
    #   3. Parse stdout's last non-empty line as JSON, assert {"ok": false}
    #      and that "error" exists with a non-empty message.
    raise NotImplementedError(
        f"Failure-injection harness for {scenario_id} lands in R2.2 (cards c12b1506 / da60159b / 303d0e09)."
    )


@pytest.mark.scenario("ts_d8e85551")
@pytest.mark.card("b3e132a6-96eb-4ada-9c30-21ba8695aca9")
@pytest.mark.sprint("2c353ca4-c66d-4f9e-9d4f-9c4683c66f5b")
@pytest.mark.spec("46dbff78-5997-442e-a6c3-c6fb6cb735e3")
@pytest.mark.xfail(
    reason="awaiting R2.2 impl: helpers must trap SIGINT and exit 2",
    strict=True,
)
def test_helper_handles_user_cancellation(
    bootstrap_local_pip_script: Path,
) -> None:
    """Scenario ts_d8e85551 sub-case (d) — user cancellation = exit 2.

    GIVEN: Any helper running.
    WHEN:  User sends SIGINT (Ctrl-C) at any point.
    THEN:  Helper exits 2 with `{"ok": false, "error":{"reason":"cancelled"}}`.
    """
    assert bootstrap_local_pip_script.exists(), (
        f"R2.2 deliverable missing: {bootstrap_local_pip_script}"
    )
    # The R2.2 harness will spawn the helper with subprocess.Popen, send
    # SIGINT after a short delay, wait for exit, assert returncode == 2.
    raise NotImplementedError(
        "SIGINT cancellation harness lands in R2.2 (impl card c12b1506)."
    )
