"""Card 9447d51a / scenario ts_6592e960 - PreCompact hook consolidates KG.

Integration: when Claude Code fires the PreCompact event, the
consolidate-on-compact.sh hook must run kg_begin_consolidation +
kg_commit_consolidation, with kg_abort_consolidation as the rollback
path on commit failure.

Strategy: the hook script invokes the MCP via the ``MCP_CURL`` shell
indirection (default ``curl``). We swap it for a tiny mock that records
each invocation so the test can assert the begin -> commit (or
begin -> abort) call order without a live Pulse.
"""
from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest


def _write_mock_curl(
    bin_dir: Path,
    log_file: Path,
    fail_on: list[str] | None = None,
) -> Path:
    """Drop a fake curl that logs the JSON-RPC method name to log_file.

    fail_on is a list of method names that should make the mock return a
    JSON-RPC error envelope (so the script's is_error helper trips).
    """
    fail_on = fail_on or []
    bin_dir.mkdir(parents=True, exist_ok=True)
    mock = bin_dir / "mock_curl.sh"
    fail_set = " ".join(fail_on)
    mock.write_text(
        "#!/usr/bin/env bash\n"
        "set -uo pipefail\n"
        "LOG=" + str(log_file) + "\n"
        "FAIL_SET=\"" + fail_set + "\"\n"
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
        "for f in $FAIL_SET; do\n"
        "    if [ \"$METHOD\" = \"$f\" ]; then\n"
        "        printf '%s' '{\"jsonrpc\":\"2.0\",\"id\":1,\"error\":{\"code\":-32000,\"message\":\"injected\"}}'\n"
        "        exit 0\n"
        "    fi\n"
        "done\n"
        "printf '%s' '{\"jsonrpc\":\"2.0\",\"id\":1,\"result\":{\"ok\":true}}'\n",
        encoding="utf-8",
    )
    mock.chmod(mock.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return mock


@pytest.mark.scenario("ts_6592e960")
@pytest.mark.card("9447d51a-185e-40b1-a583-b6f897d66156")
@pytest.mark.sprint("2c353ca4-c66d-4f9e-9d4f-9c4683c66f5b")
@pytest.mark.spec("46dbff78-5997-442e-a6c3-c6fb6cb735e3")
def test_precompact_calls_begin_then_commit(
    consolidate_on_compact_script: Path,
    tmp_path: Path,
) -> None:
    """Happy path: kg_begin_consolidation then kg_commit_consolidation."""
    assert consolidate_on_compact_script.exists()
    log = tmp_path / "calls.log"
    mock = _write_mock_curl(tmp_path / "bin", log)
    result = subprocess.run(
        [str(consolidate_on_compact_script)],
        env={
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "MCP_CURL": str(mock),
            "PULSE_MCP_URL": "http://127.0.0.1:8101/mcp",
        },
        input='{"event":"PreCompact"}',
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, (
        f"hook must always exit 0 (don't block compact); got rc={result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    calls = [c for c in log.read_text(encoding="utf-8").splitlines() if c.strip()]
    assert calls == [
        "okto_pulse_kg_begin_consolidation",
        "okto_pulse_kg_commit_consolidation",
    ], f"unexpected MCP call sequence: {calls}"


@pytest.mark.scenario("ts_6592e960")
@pytest.mark.card("9447d51a-185e-40b1-a583-b6f897d66156")
@pytest.mark.sprint("2c353ca4-c66d-4f9e-9d4f-9c4683c66f5b")
@pytest.mark.spec("46dbff78-5997-442e-a6c3-c6fb6cb735e3")
def test_precompact_aborts_on_commit_failure(
    consolidate_on_compact_script: Path,
    tmp_path: Path,
) -> None:
    """Failure path: when kg_commit_consolidation errors, kg_abort_consolidation must fire."""
    assert consolidate_on_compact_script.exists()
    log = tmp_path / "calls.log"
    mock = _write_mock_curl(
        tmp_path / "bin",
        log,
        fail_on=["okto_pulse_kg_commit_consolidation"],
    )
    result = subprocess.run(
        [str(consolidate_on_compact_script)],
        env={
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "MCP_CURL": str(mock),
            "PULSE_MCP_URL": "http://127.0.0.1:8101/mcp",
        },
        input='{"event":"PreCompact"}',
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0
    calls = [c for c in log.read_text(encoding="utf-8").splitlines() if c.strip()]
    assert calls == [
        "okto_pulse_kg_begin_consolidation",
        "okto_pulse_kg_commit_consolidation",
        "okto_pulse_kg_abort_consolidation",
    ], f"expected begin -> commit (fail) -> abort; got {calls}"
