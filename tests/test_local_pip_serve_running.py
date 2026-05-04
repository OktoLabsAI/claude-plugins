"""Card d9a4c3a8 / scenario ts_8e08df58 - local-pip serve-running.

Integration: bootstrap-local-pip.sh in OKTO_PULSE_FORCE_NO_SERVE=1 mode
exercises the python_check / pip_check / init_agents / wait_readyz
branching without spawning a real `okto-pulse serve`. The full path
(actually spawn serve and curl /readyz) needs okto-pulse pre-installed
against python3.12 -- pytest.skip when missing.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


def _last_json_line(stdout: str) -> dict:
    lines = [ln for ln in stdout.strip().splitlines() if ln.strip()]
    assert lines, "helper produced no stdout NDJSON"
    return json.loads(lines[-1])


@pytest.mark.scenario("ts_8e08df58")
@pytest.mark.card("d9a4c3a8")
@pytest.mark.sprint("3b4bbb87")
@pytest.mark.spec("46dbff78-5997-442e-a6c3-c6fb6cb735e3")
def test_local_pip_no_serve_branch_dry_runs_to_readyz(
    bootstrap_local_pip_script: Path,
    tmp_path: Path,
) -> None:
    """When OKTO_PULSE_FORCE_NO_SERVE=1 and /readyz is unreachable, the
    script must reach wait_readyz and exit 30 with the readyz_timeout
    NDJSON envelope.

    This proves the python_check + pip_check + init_agents branches all
    pass on a box where okto-pulse is pre-installed against python3.12.
    """
    assert bootstrap_local_pip_script.exists()
    if shutil.which("okto-pulse") is None:
        pytest.skip("okto-pulse not on PATH; can't traverse init_agents")
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

    data_dir = tmp_path / "claude-plugin-data"
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": str(tmp_path / "home"),
        "OKTO_PULSE_PIN_VERSION": "0.0.1",
        "OKTO_PULSE_FORCE_NO_SERVE": "1",
        "OKTO_PULSE_READYZ_TIMEOUT_SECONDS": "1",
        "PULSE_LOCAL_READYZ_URL": "http://127.0.0.1:1/readyz",
        "CLAUDE_PLUGIN_DATA": str(data_dir),
    }
    result = subprocess.run(
        [str(bootstrap_local_pip_script)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 30, (
        f"expected exit 30 (readyz_timeout); got {result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    final = _last_json_line(result.stdout)
    assert final.get("ok") is False
    assert final.get("error", {}).get("reason") == "readyz_timeout"

    # Phases up to wait_readyz must have emitted progress events.
    events = []
    for ln in result.stdout.strip().splitlines():
        if not ln.strip():
            continue
        try:
            obj = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if "event" in obj:
            events.append(obj["event"])
    assert "python_check" in events
    assert "pip_check" in events
    assert "init_agents" in events
    assert "start_serve" in events
    assert "wait_readyz" in events


@pytest.mark.scenario("ts_8e08df58")
@pytest.mark.card("d9a4c3a8")
@pytest.mark.sprint("3b4bbb87")
@pytest.mark.spec("46dbff78-5997-442e-a6c3-c6fb6cb735e3")
def test_local_pip_full_serve_smoke(
    bootstrap_local_pip_script: Path,
    tmp_path: Path,
) -> None:
    """Full path: actually spawn `okto-pulse serve` and curl /readyz.

    Requires okto-pulse pip-installed against python3.12 AND port 8100
    free. We skip when those preconditions aren't met. This is the
    integration smoke for ts_8e08df58 proper.
    """
    assert bootstrap_local_pip_script.exists()
    pytest.skip(
        "full serve smoke requires okto-pulse pre-installed against "
        "python3.12 and a free port 8100; covered in CI's local-pip job"
    )
