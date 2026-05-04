"""Card fb59f749 / scenario ts_585c69fd — SessionStart hook dual path.

    SessionStart hook completes in <=5s when Pulse is reachable; when
    Pulse is unreachable or times out, it emits a system-reminder
    suggesting /okto-pulse:doctor and the session continues without a
    block.

We exercise ``ensure-pulse-up.sh`` via the ``MCP_CURL`` indirection seam
(reused from R2.2). Two parametrized cases:

    * healthy — mock returns valid kg_health + unseen_summary JSON
      instantly; assert wall clock << 5s and stdout names the active
      board.
    * dead    — mock sleeps long enough that the curl-style wall-clock
      budget fires; assert exit 0, stdout contains the fallback
      "Pulse unreachable at" + "/okto-pulse:doctor".
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
import time
from pathlib import Path

import pytest


def _write_healthy_mock(bin_dir: Path) -> Path:
    """Mock that returns valid JSON-RPC payloads with no delay."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    mock = bin_dir / "mock_curl.sh"
    mock.write_text(
        "#!/usr/bin/env bash\n"
        "set -uo pipefail\n"
        "BODY=\"\"\n"
        "while [ $# -gt 0 ]; do\n"
        "    case \"$1\" in\n"
        "        -d) BODY=\"$2\"; shift 2 ;;\n"
        "        --data) BODY=\"$2\"; shift 2 ;;\n"
        "        *) shift ;;\n"
        "    esac\n"
        "done\n"
        "METHOD=$(printf '%s' \"$BODY\" | grep -Eo '\"name\"[[:space:]]*:[[:space:]]*\"[^\"]+\"' | head -1 | sed -E 's/.*\"name\"[[:space:]]*:[[:space:]]*\"([^\"]+)\".*/\\1/')\n"
        "case \"$METHOD\" in\n"
        "    okto_pulse_kg_health)\n"
        "        printf '%s' '{\"jsonrpc\":\"2.0\",\"id\":1,\"result\":{\"status\":\"ok\"}}'\n"
        "        ;;\n"
        "    okto_pulse_get_unseen_summary)\n"
        "        printf '%s' '{\"jsonrpc\":\"2.0\",\"id\":1,\"result\":{\"unseen_count\":7}}'\n"
        "        ;;\n"
        "    *)\n"
        "        printf '%s' '{\"jsonrpc\":\"2.0\",\"id\":1,\"result\":{\"ok\":true}}'\n"
        "        ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    mock.chmod(mock.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return mock


def _write_dead_mock(bin_dir: Path) -> Path:
    """Mock that hangs longer than the hooks.json timeout would allow.

    The shell script doesn't enforce its own wall-clock cap when MCP_CURL
    is a non-curl mock (curl's -m flag is silently ignored). So we
    simulate "Pulse unreachable" by sleeping a few seconds and then
    returning a JSON-RPC error envelope. The script's error-detection
    branch (grep '"error":') hits and prints the doctor fallback.
    """
    bin_dir.mkdir(parents=True, exist_ok=True)
    mock = bin_dir / "mock_curl.sh"
    mock.write_text(
        "#!/usr/bin/env bash\n"
        "set -uo pipefail\n"
        "sleep 5\n"
        "printf '%s' '{\"jsonrpc\":\"2.0\",\"id\":1,\"error\":{\"code\":-32000,\"message\":\"timeout\"}}'\n",
        encoding="utf-8",
    )
    mock.chmod(mock.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return mock


def _setup_active_board(tmp_path: Path, board_name: str) -> Path:
    data_dir = tmp_path / "claude-plugin-data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "active-board.json").write_text(
        json.dumps(
            {
                "board_id": "11111111-2222-3333-4444-555555555555",
                "board_name": board_name,
                "set_at": "2026-05-04T00:00:00Z",
                "set_by": "setup",
            }
        ),
        encoding="utf-8",
    )
    (data_dir / "deploy-mode.json").write_text(
        json.dumps({"mode": "local-pip"}),
        encoding="utf-8",
    )
    return data_dir


@pytest.mark.scenario("ts_585c69fd")
@pytest.mark.card("fb59f749-ded2-44bd-b8a9-5cdb6d1c7961")
@pytest.mark.sprint("f337e95f-0d5b-4615-a353-725167306330")
@pytest.mark.spec("46dbff78-5997-442e-a6c3-c6fb6cb735e3")
def test_session_start_hook_healthy_path(
    ensure_pulse_up_script: Path,
    tmp_path: Path,
) -> None:
    """Healthy path: hook returns fast, stdout mentions the active board."""
    assert ensure_pulse_up_script.exists()
    board_name = "Test Sprint Board"
    data_dir = _setup_active_board(tmp_path, board_name)
    mock = _write_healthy_mock(tmp_path / "bin")

    started = time.time()
    result = subprocess.run(
        [str(ensure_pulse_up_script)],
        env={
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
            "HOME": str(tmp_path),
            "MCP_CURL": str(mock),
            "CLAUDE_PLUGIN_DATA": str(data_dir),
            "PULSE_MCP_URL": "http://127.0.0.1:8101/mcp",
        },
        input='{"event":"SessionStart"}',
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    elapsed = time.time() - started

    assert result.returncode == 0, (
        f"hook must exit 0; got {result.returncode}\nstderr:\n{result.stderr}"
    )
    assert elapsed < 5.0, (
        f"healthy path must finish in <5s wall clock; took {elapsed:.2f}s"
    )
    stdout = result.stdout.strip()
    assert stdout, "expected a non-empty system-reminder line on stdout"
    assert "<system-reminder>" in stdout, f"expected system-reminder marker; got {stdout!r}"
    assert board_name in stdout, (
        f"expected board name {board_name!r} in stdout; got {stdout!r}"
    )


@pytest.mark.scenario("ts_585c69fd")
@pytest.mark.card("fb59f749-ded2-44bd-b8a9-5cdb6d1c7961")
@pytest.mark.sprint("f337e95f-0d5b-4615-a353-725167306330")
@pytest.mark.spec("46dbff78-5997-442e-a6c3-c6fb6cb735e3")
def test_session_start_hook_dead_path(
    ensure_pulse_up_script: Path,
    tmp_path: Path,
) -> None:
    """Dead path: when Pulse is unreachable, fallback line is emitted, exit 0."""
    assert ensure_pulse_up_script.exists()
    data_dir = _setup_active_board(tmp_path, "Doesn't matter")
    mock = _write_dead_mock(tmp_path / "bin")
    mcp_url = "http://127.0.0.1:8101/mcp"

    started = time.time()
    result = subprocess.run(
        [str(ensure_pulse_up_script)],
        env={
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
            "HOME": str(tmp_path),
            "MCP_CURL": str(mock),
            "CLAUDE_PLUGIN_DATA": str(data_dir),
            "PULSE_MCP_URL": mcp_url,
        },
        input='{"event":"SessionStart"}',
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    elapsed = time.time() - started

    assert result.returncode == 0, (
        f"hook must always exit 0 (don't block session); got {result.returncode}"
    )
    # The mock sleeps 5s then returns an error envelope; the script
    # detects the error and emits the fallback. So wall clock is bounded
    # by sleep + script overhead, and bounded above by the subprocess
    # timeout we passed.
    assert elapsed >= 5.0, (
        f"dead-path mock should have slept ~5s before erroring; only {elapsed:.2f}s"
    )
    assert elapsed < 10.0, (
        f"dead-path budget exceeded; took {elapsed:.2f}s"
    )
    stdout = result.stdout
    assert "Pulse unreachable at" in stdout, (
        f"expected fallback line; got {stdout!r}"
    )
    assert mcp_url in stdout, f"fallback should name the MCP url; got {stdout!r}"
    assert "/okto-pulse:doctor" in stdout, (
        f"expected /okto-pulse:doctor suggestion; got {stdout!r}"
    )
