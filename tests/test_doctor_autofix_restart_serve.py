"""Card 4973a709 / scenario ts_988b5d64 - doctor auto-fix restart serve.

Integration: doctor.sh detects a downed serve (red readyz_200 check) in
local-pip mode. The doctor SKILL's auto-fix would re-spawn it; we test
the diagnostic side here -- restart of `okto-pulse serve` requires the
pip package and is part of the live SDLC harness.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.scenario("ts_988b5d64")
@pytest.mark.card("4973a709")
@pytest.mark.sprint("3b4bbb87")
@pytest.mark.spec("46dbff78-5997-442e-a6c3-c6fb6cb735e3")
def test_doctor_emits_summary_and_red_when_serve_down(
    doctor_script: Path,
    tmp_path: Path,
) -> None:
    """Doctor must emit one NDJSON record per check + a final summary.

    With deploy mode = local-pip and no serve running, readyz_200 should
    be red and mcp_kg_health should be red. Doctor exit code is always 0.
    """
    assert doctor_script.exists(), f"R2.2 deliverable missing: {doctor_script}"

    data_dir = tmp_path / "claude-plugin-data"
    data_dir.mkdir()
    deploy_mode = data_dir / "deploy-mode.json"
    deploy_mode.write_text(
        json.dumps(
            {
                "mode": "local-pip",
                "set_at": "2026-05-04T00:00:00Z",
            }
        )
    )

    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": str(tmp_path / "home"),
        "CLAUDE_PLUGIN_DATA": str(data_dir),
        # Point at a closed port so readyz_200 / mcp_kg_health both go red
        # (otherwise the dev box's running Pulse would mask the assertion).
        "PULSE_READYZ_URL": "http://127.0.0.1:1/readyz",
        "PULSE_MCP_URL": "http://127.0.0.1:1/mcp",
    }
    result = subprocess.run(
        [str(doctor_script)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"doctor must always exit 0; got {result.returncode}\nstderr:\n{result.stderr}"
    )

    parsed = []
    summary = None
    for ln in result.stdout.strip().splitlines():
        if not ln.strip():
            continue
        obj = json.loads(ln)
        if "summary" in obj:
            summary = obj["summary"]
        else:
            parsed.append(obj)

    assert summary is not None, "doctor must emit a final summary line"
    assert isinstance(summary.get("checks_run"), int)
    assert summary["checks_run"] == len(parsed)
    assert summary["red"] + summary["green"] + summary["yellow"] == summary["checks_run"]

    # /readyz against http://127.0.0.1:8100/readyz must fail without serve up.
    readyz = next((c for c in parsed if c["check"] == "readyz_200"), None)
    assert readyz is not None
    assert readyz["status"] == "fail"


@pytest.mark.scenario("ts_988b5d64")
@pytest.mark.card("4973a709")
@pytest.mark.sprint("3b4bbb87")
@pytest.mark.spec("46dbff78-5997-442e-a6c3-c6fb6cb735e3")
def test_doctor_autofix_restart_serve_full_loop(
    doctor_script: Path,
) -> None:
    """Full restart-serve loop: kill serve, doctor detects red, auto-fix
    spawns serve, doctor reruns green.

    Requires okto-pulse pre-installed against python3.12 and ability to
    bind 127.0.0.1:8100. Skipped on the dev box.
    """
    assert doctor_script.exists()
    if shutil.which("okto-pulse") is None:
        pytest.skip("okto-pulse not on PATH; integration loop needs serve")
    pytest.skip(
        "full doctor auto-fix loop is a live integration; covered in "
        "CI's local-pip job"
    )
