"""Card 807e9a5c / scenario ts_0cfbc4e7 — TaskCompleted hook dual path.

    TaskCompleted hook moves the linked Pulse card to the next status
    when the task event includes pulse_card_id metadata; with no such
    metadata the hook is a no-op.

We use the ``MCP_CURL`` indirection seam to record JSON-RPC method
names without a live Pulse. Two cases:

    * with metadata    — payload carries metadata.pulse_card_id; assert
      the mock log contains both okto_pulse_move_card and
      okto_pulse_add_comment, exit 0.
    * without metadata — payload carries no pulse_card_id; assert the
      mock was never invoked (log file absent or empty), exit 0.
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path

import pytest


def _write_mock_curl(bin_dir: Path, log_file: Path) -> Path:
    """Drop a fake curl that logs the JSON-RPC method name to log_file."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    mock = bin_dir / "mock_curl.sh"
    mock.write_text(
        "#!/usr/bin/env bash\n"
        "set -uo pipefail\n"
        "LOG=" + str(log_file) + "\n"
        "BODY=\"\"\n"
        "while [ $# -gt 0 ]; do\n"
        "    case \"$1\" in\n"
        "        -d) BODY=\"$2\"; shift 2 ;;\n"
        "        --data) BODY=\"$2\"; shift 2 ;;\n"
        "        *) shift ;;\n"
        "    esac\n"
        "done\n"
        "METHOD=$(printf '%s' \"$BODY\" | grep -Eo '\"name\"[[:space:]]*:[[:space:]]*\"[^\"]+\"' | head -1 | sed -E 's/.*\"name\"[[:space:]]*:[[:space:]]*\"([^\"]+)\".*/\\1/')\n"
        "echo \"$METHOD\" >> \"$LOG\"\n"
        "printf '%s' '{\"jsonrpc\":\"2.0\",\"id\":1,\"result\":{\"ok\":true}}'\n",
        encoding="utf-8",
    )
    mock.chmod(mock.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return mock


@pytest.mark.scenario("ts_0cfbc4e7")
@pytest.mark.card("807e9a5c-1f13-49d9-b610-ce3ec7f38c8b")
@pytest.mark.sprint("f337e95f-0d5b-4615-a353-725167306330")
@pytest.mark.spec("46dbff78-5997-442e-a6c3-c6fb6cb735e3")
def test_task_completed_with_metadata_calls_move_and_comment(
    task_completed_card_sync_script: Path,
    tmp_path: Path,
) -> None:
    """With pulse_card_id present, the hook fires move_card + add_comment."""
    assert task_completed_card_sync_script.exists()
    log = tmp_path / "calls.log"
    mock = _write_mock_curl(tmp_path / "bin", log)

    payload = json.dumps(
        {
            "event": "TaskCompleted",
            "metadata": {
                "pulse_card_id": "11111111-2222-3333-4444-555555555555",
                "pulse_board_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            },
            "task_summary": "validation done",
        }
    )

    result = subprocess.run(
        [str(task_completed_card_sync_script)],
        env={
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
            "HOME": str(tmp_path),
            "MCP_CURL": str(mock),
            "PULSE_MCP_URL": "http://127.0.0.1:8101/mcp",
        },
        input=payload,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )

    assert result.returncode == 0, (
        f"hook must exit 0; got {result.returncode}\nstderr:\n{result.stderr}"
    )
    assert log.exists(), "MCP_CURL mock should have been invoked"
    calls = [c for c in log.read_text(encoding="utf-8").splitlines() if c.strip()]
    assert "okto_pulse_move_card" in calls, (
        f"expected okto_pulse_move_card in MCP calls; got {calls}"
    )
    assert "okto_pulse_add_comment" in calls, (
        f"expected okto_pulse_add_comment in MCP calls; got {calls}"
    )


@pytest.mark.scenario("ts_0cfbc4e7")
@pytest.mark.card("807e9a5c-1f13-49d9-b610-ce3ec7f38c8b")
@pytest.mark.sprint("f337e95f-0d5b-4615-a353-725167306330")
@pytest.mark.spec("46dbff78-5997-442e-a6c3-c6fb6cb735e3")
def test_task_completed_without_metadata_is_noop(
    task_completed_card_sync_script: Path,
    tmp_path: Path,
) -> None:
    """Without pulse_card_id, the hook makes zero MCP calls."""
    assert task_completed_card_sync_script.exists()
    log = tmp_path / "calls.log"
    mock = _write_mock_curl(tmp_path / "bin", log)

    payload = json.dumps(
        {
            "event": "TaskCompleted",
            "task_summary": "some text",
        }
    )

    result = subprocess.run(
        [str(task_completed_card_sync_script)],
        env={
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
            "HOME": str(tmp_path),
            "MCP_CURL": str(mock),
            "PULSE_MCP_URL": "http://127.0.0.1:8101/mcp",
        },
        input=payload,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )

    assert result.returncode == 0, (
        f"hook must exit 0; got {result.returncode}\nstderr:\n{result.stderr}"
    )
    # Without pulse_card_id, the script must not have invoked MCP_CURL at all.
    if log.exists():
        contents = log.read_text(encoding="utf-8").strip()
        assert contents == "", (
            f"expected zero MCP calls without pulse_card_id; log contains: {contents!r}"
        )
