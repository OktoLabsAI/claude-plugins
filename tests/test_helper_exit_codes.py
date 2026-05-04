"""Card b3e132a6 / scenario ts_d8e85551 - helper-script exit-code contract.

Every bin/bootstrap-*.sh helper must exit with the documented codes
(0/2/10/20/30) per failure mode, and emit a final NDJSON envelope with
ok=false on every non-zero exit.

We inject failures via env-var overrides:
- DOCKER_HOST=unix:///nonexistent.sock -> daemon unreachable -> 10.
- PIP_INDEX_URL=http://127.0.0.1:1/simple + bumped pin version ->
  pip install fails -> 20.  (We force a bumped pin so the script's
  "already installed >= pin?" branch triggers an install attempt; the
  ambient dev box has okto-pulse 0.1.14 in pyenv but python3.12 is brew
  python and PEP 668 makes any --target-less install fail anyway.)
- OKTO_PULSE_FORCE_NO_SERVE=1 + tiny readyz timeout + closed-port URL ->
  /readyz never returns 200 within the budget -> 30.

SIGINT (Ctrl-C) is exercised separately by sending a real SIGINT to a
spawned helper process and asserting exit 2.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import pytest


def _last_json_line(stdout: str) -> dict:
    lines = [ln for ln in stdout.strip().splitlines() if ln.strip()]
    assert lines, "helper produced no stdout NDJSON"
    return json.loads(lines[-1])


@pytest.mark.scenario("ts_d8e85551")
@pytest.mark.card("b3e132a6-96eb-4ada-9c30-21ba8695aca9")
@pytest.mark.sprint("2c353ca4-c66d-4f9e-9d4f-9c4683c66f5b")
@pytest.mark.spec("46dbff78-5997-442e-a6c3-c6fb6cb735e3")
@pytest.mark.parametrize(
    ("scenario_id", "helper", "env_overrides", "expected_code"),
    [
        # (a) docker daemon stopped -> exit 10 (precondition fail).
        (
            "docker-no-daemon",
            "bootstrap-docker.sh",
            {"DOCKER_HOST": "unix:///nonexistent.sock"},
            10,
        ),
        # (b) pip server unreachable -> exit 20 (runtime fail).
        # Force the install branch by bumping the pin past whatever is installed.
        (
            "pip-unreachable",
            "bootstrap-local-pip.sh",
            {
                "PIP_INDEX_URL": "http://127.0.0.1:1/simple",
                "OKTO_PULSE_PIN_VERSION": "99.99.99",
                "OKTO_PULSE_FORCE_NO_SERVE": "1",
            },
            20,
        ),
        # (c) /readyz never returns 200 -> exit 30 (timeout). Also bump the
        # pin so the install path is bypassed for an ambient install.
        (
            "readyz-timeout",
            "bootstrap-local-pip.sh",
            {
                "OKTO_PULSE_READYZ_TIMEOUT_SECONDS": "1",
                "OKTO_PULSE_FORCE_NO_SERVE": "1",
                "PULSE_LOCAL_READYZ_URL": "http://127.0.0.1:1/readyz",
            },
            30,
        ),
    ],
    ids=lambda v: v if isinstance(v, str) else "params",
)
def test_helper_returns_documented_exit_codes(
    scenario_id: str,
    helper: str,
    env_overrides: dict,
    expected_code: int,
    plugin_root: Path,
) -> None:
    helper_path = plugin_root / "bin" / helper
    assert helper_path.exists(), f"R2.2 deliverable missing: {helper_path}"

    # docker-specific test needs docker on PATH and a fast-failing daemon
    # probe. Skip if docker isn't installed at all.
    if scenario_id == "docker-no-daemon" and shutil.which("docker") is None:
        pytest.skip("docker CLI not installed")

    # readyz-timeout has to traverse pip_check WITHOUT triggering the pip
    # install branch (PEP 668 makes any system-pip install fail with exit 20
    # on this box). Pre-skip when:
    # - python3.12 doesn't already have okto-pulse pip-installed, OR
    # - okto-pulse isn't on PATH at all (init step would 20).
    if scenario_id == "readyz-timeout":
        env_overrides = dict(env_overrides)
        env_overrides.setdefault("OKTO_PULSE_PIN_VERSION", "0.0.1")
        if shutil.which("okto-pulse") is None:
            pytest.skip("okto-pulse not on PATH; pip install path would fire")
        py312 = shutil.which("python3.12")
        if py312 is None:
            pytest.skip("python3.12 not on PATH")
        rc = subprocess.run(
            [py312, "-m", "pip", "show", "okto-pulse"],
            capture_output=True,
            check=False,
        ).returncode
        if rc != 0:
            pytest.skip(
                "python3.12 has no okto-pulse pip package; "
                "the install path would fire (PEP 668 blocked on macOS)"
            )

    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
    }
    env.update(env_overrides)

    result = subprocess.run(
        [str(helper_path)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == expected_code, (
        f"{scenario_id}: expected exit {expected_code}, got {result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    final = _last_json_line(result.stdout)
    assert final.get("ok") is False, f"final NDJSON must have ok=false: {final}"
    assert "error" in final, f"final NDJSON must include 'error': {final}"
    assert "reason" in final["error"], f"error must include 'reason': {final}"


@pytest.mark.scenario("ts_d8e85551")
@pytest.mark.card("b3e132a6-96eb-4ada-9c30-21ba8695aca9")
@pytest.mark.sprint("2c353ca4-c66d-4f9e-9d4f-9c4683c66f5b")
@pytest.mark.spec("46dbff78-5997-442e-a6c3-c6fb6cb735e3")
def test_helper_handles_user_cancellation(
    bootstrap_local_pip_script: Path,
) -> None:
    """Sub-case (d): SIGINT during run -> exit 2 + cancelled NDJSON."""
    assert bootstrap_local_pip_script.exists()
    if shutil.which("okto-pulse") is None:
        pytest.skip("okto-pulse not on PATH; cancel test needs to reach wait_readyz")
    py312 = shutil.which("python3.12")
    if py312 is None:
        pytest.skip("python3.12 not on PATH")
    rc = subprocess.run(
        [py312, "-m", "pip", "show", "okto-pulse"],
        capture_output=True,
        check=False,
    ).returncode
    if rc != 0:
        pytest.skip(
            "python3.12 has no okto-pulse pip package; "
            "SIGINT test cannot reach the wait_readyz polling loop"
        )

    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        # Bypass pip install (use a tiny pin) and skip serve so we land in the
        # /readyz polling loop where SIGINT can fire deterministically.
        "OKTO_PULSE_PIN_VERSION": "0.0.1",
        "OKTO_PULSE_FORCE_NO_SERVE": "1",
        "OKTO_PULSE_READYZ_TIMEOUT_SECONDS": "30",
        "PULSE_LOCAL_READYZ_URL": "http://127.0.0.1:1/readyz",
    }
    proc = subprocess.Popen(
        [str(bootstrap_local_pip_script)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        # Give it a moment to advance past python_check / pip_check / init_agents.
        time.sleep(2.0)
        proc.send_signal(signal.SIGINT)
        stdout, stderr = proc.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        pytest.fail(f"helper did not respond to SIGINT in time\nstdout:\n{stdout}\nstderr:\n{stderr}")

    assert proc.returncode == 2, (
        f"SIGINT must yield exit 2; got {proc.returncode}\n"
        f"stdout:\n{stdout}\nstderr:\n{stderr}"
    )
    final = _last_json_line(stdout)
    assert final.get("ok") is False, f"final NDJSON must have ok=false: {final}"
    assert final.get("error", {}).get("reason") == "cancelled", (
        f"reason must be 'cancelled': {final}"
    )
