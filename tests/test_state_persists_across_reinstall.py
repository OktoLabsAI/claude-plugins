"""Card 61101f5b / scenario ts_a700a626 — state survives uninstall+reinstall.

End-to-end: ``${CLAUDE_PLUGIN_DATA}/active-board.json`` lives outside the
plugin install (cache) tree, so a plugin uninstall+reinstall must NOT
delete it. This is the contract that lets users keep their active-board
selection across plugin updates.

Layout (verified empirically on claude CLI 2.1.126, macOS):
    Cache (gone on uninstall): ``~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/``
    Data  (kept on uninstall): ``~/.claude/plugins/data/<plugin>@<marketplace>/``

The fixture ``clean_claude_home`` sets ``HOME=tmp_path`` (not the
returned path), so we anchor at ``$HOME/.claude/plugins/data/...`` to
match where the CLI actually writes.

When ``claude`` is missing we ``pytest.skip``; CI's matrix is the gate.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


PLUGIN_FQID = "okto-pulse@oktolabs-plugins"

SENTINEL = {
    "board_id": "550e8400-e29b-41d4-a716-446655440000",
    "board_name": "sentinel",
    "set_at": "2026-05-04T03:00:00Z",
    "set_by": "setup",
}


@pytest.mark.scenario("ts_a700a626")
@pytest.mark.card("61101f5b-3da6-44a3-bb73-79c0a4170d97")
@pytest.mark.sprint("6eaa093b-2ca1-4adc-aabf-1d7bc0e9025f")
@pytest.mark.spec("75fe081f-2e7f-4d38-ba73-57d47815c369")
def test_active_board_survives_reinstall(
    clean_claude_home: Path,
    smoke_install_script: Path,
) -> None:
    """Scenario ts_a700a626 — ``active-board.json`` survives reinstall.

    GIVEN: okto-pulse is installed and a sentinel ``active-board.json`` has
        been written via ``tools.state.atomic_write.atomic_write_json`` to
        ``${CLAUDE_PLUGIN_DATA}/active-board.json``.
    WHEN:  The user uninstalls okto-pulse and reinstalls it.
    THEN:  The sentinel file still exists at the same path with the same
        contents — the data dir is not in the cache dir.
    """
    if shutil.which("claude") is None:
        pytest.skip("claude CLI not installed; tested in CI matrix")

    # ``smoke_install.sh`` adds the marketplace and installs okto-pulse.
    env = {
        **os.environ,
        "PULSE_DEPLOY_MODE": "local-pip",
        "PULSE_API_TOKEN": "",
        "CLAUDE_HOME": str(clean_claude_home),
    }
    install = subprocess.run(
        [str(smoke_install_script)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert install.returncode == 0, (
        f"smoke_install.sh failed (rc={install.returncode})\n"
        f"stdout:\n{install.stdout}\nstderr:\n{install.stderr}"
    )

    # Anchor on the real $HOME (the fixture sets HOME=tmp_path; the CLI
    # then writes to $HOME/.claude/...). Don't trust CLAUDE_HOME — claude
    # 2.1.126 ignores it for the plugins tree.
    home = Path(os.environ["HOME"])
    data_dir = home / ".claude" / "plugins" / "data" / PLUGIN_FQID
    data_dir.mkdir(parents=True, exist_ok=True)
    sentinel_path = data_dir / "active-board.json"

    # Use the same atomic helper the runtime uses for state files.
    from tools.state.atomic_write import atomic_write_json

    atomic_write_json(sentinel_path, SENTINEL)
    assert sentinel_path.exists(), (
        f"Failed to seed sentinel at {sentinel_path}"
    )

    # WHEN: uninstall.
    uninstall = subprocess.run(
        ["claude", "plugin", "uninstall", PLUGIN_FQID],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert uninstall.returncode == 0, (
        f"plugin uninstall failed (rc={uninstall.returncode})\n"
        f"stdout:\n{uninstall.stdout}\nstderr:\n{uninstall.stderr}"
    )

    # Sentinel must survive the uninstall (data dir is outside cache).
    assert sentinel_path.exists(), (
        f"After uninstall, sentinel went missing at {sentinel_path}; the "
        f"plugin data dir was deleted by uninstall — that's the bug this "
        f"test exists to prevent."
    )

    # Reinstall.
    reinstall = subprocess.run(
        ["claude", "plugin", "install", PLUGIN_FQID],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert reinstall.returncode == 0, (
        f"plugin reinstall failed (rc={reinstall.returncode})\n"
        f"stdout:\n{reinstall.stdout}\nstderr:\n{reinstall.stderr}"
    )

    # THEN: same path, same content (parse JSON to compare values, not
    # bytes — atomic_write_json formats with sort_keys+indent+\n).
    assert sentinel_path.exists(), (
        f"After reinstall, sentinel went missing at {sentinel_path}; the "
        f"plugin data dir was clobbered by reinstall."
    )
    parsed = json.loads(sentinel_path.read_text(encoding="utf-8"))
    assert parsed == SENTINEL, (
        f"After reinstall, sentinel contents drifted.\n"
        f"expected: {SENTINEL!r}\n"
        f"got:      {parsed!r}"
    )
