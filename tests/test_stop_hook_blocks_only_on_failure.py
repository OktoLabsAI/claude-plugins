"""Card 7825b6ba / scenario ts_1d631873 - stop hook blocks only on failure.

The Stop hook stop-validation-gate.sh:
- (a) Active board has a validation_pending card with status=failed:
      stdout JSON contains decision=block + the offending card id; exit 0.
- (b) Active board has only clean validation_pending cards (or none):
      no stdout decision; exit 0.

We mock the MCP via the MCP_CURL indirection seam.
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path

import pytest


def _write_mock_curl(
    bin_dir: Path,
    list_response: str,
    validation_responses: dict[str, str],
) -> Path:
    """Mock curl that returns canned JSON-RPC payloads.

    list_response is the raw JSON-RPC body returned for
    okto_pulse_list_cards_by_status. validation_responses is a map
    {card_id: validation_json_body}.
    """
    bin_dir.mkdir(parents=True, exist_ok=True)
    mock = bin_dir / "mock_curl.sh"
    # Write the validation_responses as a directory of files for lookup.
    val_dir = bin_dir / "validations"
    val_dir.mkdir(exist_ok=True)
    for cid, body in validation_responses.items():
        (val_dir / cid).write_text(body, encoding="utf-8")
    list_file = bin_dir / "list_response.json"
    list_file.write_text(list_response, encoding="utf-8")

    mock.write_text(
        "#!/usr/bin/env bash\n"
        "set -uo pipefail\n"
        "VAL_DIR=" + str(val_dir) + "\n"
        "LIST_FILE=" + str(list_file) + "\n"
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
        "    okto_pulse_list_cards_by_status)\n"
        "        cat \"$LIST_FILE\"\n"
        "        ;;\n"
        "    okto_pulse_get_task_validation)\n"
        "        CARD_ID=$(printf '%s' \"$BODY\" | grep -Eo '\"card_id\"[[:space:]]*:[[:space:]]*\"[^\"]+\"' | head -1 | sed -E 's/.*\"card_id\"[[:space:]]*:[[:space:]]*\"([^\"]+)\".*/\\1/')\n"
        "        if [ -f \"$VAL_DIR/$CARD_ID\" ]; then\n"
        "            cat \"$VAL_DIR/$CARD_ID\"\n"
        "        else\n"
        "            printf '%s' '{\"jsonrpc\":\"2.0\",\"id\":1,\"result\":{\"status\":\"unknown\"}}'\n"
        "        fi\n"
        "        ;;\n"
        "    *)\n"
        "        printf '%s' '{\"jsonrpc\":\"2.0\",\"id\":1,\"result\":{\"ok\":true}}'\n"
        "        ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    mock.chmod(mock.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return mock


def _setup_active_board(tmp_path: Path) -> Path:
    """Write a fake active-board.json and return CLAUDE_PLUGIN_DATA dir."""
    data_dir = tmp_path / "claude-plugin-data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "active-board.json").write_text(
        json.dumps(
            {
                "board_id": "11111111-2222-3333-4444-555555555555",
                "board_name": "Test Board",
                "set_at": "2026-05-04T00:00:00Z",
                "set_by": "setup",
            }
        ),
        encoding="utf-8",
    )
    return data_dir


@pytest.mark.scenario("ts_1d631873")
@pytest.mark.card("7825b6ba")
@pytest.mark.sprint("f337e95f")
@pytest.mark.spec("46dbff78-5997-442e-a6c3-c6fb6cb735e3")
def test_stop_hook_blocks_when_validation_failed(
    stop_validation_gate_script: Path,
    tmp_path: Path,
) -> None:
    """Sub-case (a): one card has status=failed -> decision=block."""
    assert stop_validation_gate_script.exists()

    data_dir = _setup_active_board(tmp_path)
    failing_card = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    list_resp = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "cards": [
                    {"card_id": failing_card, "status": "validation_pending"},
                    {
                        "card_id": "ffffffff-1111-2222-3333-444444444444",
                        "status": "validation_pending",
                    },
                ]
            },
        }
    )
    validations = {
        failing_card: json.dumps(
            {"jsonrpc": "2.0", "id": 1, "result": {"status": "failed"}}
        ),
        "ffffffff-1111-2222-3333-444444444444": json.dumps(
            {"jsonrpc": "2.0", "id": 1, "result": {"status": "passed"}}
        ),
    }
    mock = _write_mock_curl(tmp_path / "bin", list_resp, validations)

    result = subprocess.run(
        [str(stop_validation_gate_script)],
        env={
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
            "HOME": os.environ.get("HOME", "/tmp"),
            "MCP_CURL": str(mock),
            "CLAUDE_PLUGIN_DATA": str(data_dir),
            "PULSE_MCP_URL": "http://127.0.0.1:8101/mcp",
        },
        input='{"event":"Stop"}',
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, f"hook must exit 0; got {result.returncode}\n{result.stderr}"
    lines = [ln for ln in result.stdout.strip().splitlines() if ln.strip()]
    assert lines, "expected a decision JSON on stdout"
    decision = json.loads(lines[-1])
    assert decision.get("decision") == "block", f"expected block decision: {decision}"
    assert failing_card in decision.get("reason", ""), (
        f"reason must mention failing card id: {decision}"
    )


@pytest.mark.scenario("ts_1d631873")
@pytest.mark.card("7825b6ba")
@pytest.mark.sprint("f337e95f")
@pytest.mark.spec("46dbff78-5997-442e-a6c3-c6fb6cb735e3")
def test_stop_hook_silent_when_no_validation_failed(
    stop_validation_gate_script: Path,
    tmp_path: Path,
) -> None:
    """Sub-case (b): all validation_pending cards clean -> no block, silent stdout."""
    assert stop_validation_gate_script.exists()
    data_dir = _setup_active_board(tmp_path)
    list_resp = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "cards": [
                    {
                        "card_id": "11111111-aaaa-bbbb-cccc-dddddddddddd",
                        "status": "validation_pending",
                    },
                ]
            },
        }
    )
    validations = {
        "11111111-aaaa-bbbb-cccc-dddddddddddd": json.dumps(
            {"jsonrpc": "2.0", "id": 1, "result": {"status": "passed"}}
        ),
    }
    mock = _write_mock_curl(tmp_path / "bin", list_resp, validations)

    result = subprocess.run(
        [str(stop_validation_gate_script)],
        env={
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
            "HOME": os.environ.get("HOME", "/tmp"),
            "MCP_CURL": str(mock),
            "CLAUDE_PLUGIN_DATA": str(data_dir),
            "PULSE_MCP_URL": "http://127.0.0.1:8101/mcp",
        },
        input='{"event":"Stop"}',
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "", (
        f"expected silent stdout when no failures; got: {result.stdout!r}"
    )
