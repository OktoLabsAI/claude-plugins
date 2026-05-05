#!/usr/bin/env python3
"""Resolve the per-project Pulse state directory for a given cwd.

The active-board.json and flow-state.json files used by the okto-pulse
plugin used to be GLOBAL under ${CLAUDE_PLUGIN_DATA}/. Switching cwd
across projects silently inherited the previous project's board and
SDLC state. v0.2.4 isolates state per project under
``${CLAUDE_PLUGIN_DATA}/projects/<key>/``.

Project key derivation
----------------------
Project root = ``git rev-parse --show-toplevel`` if cwd is in a repo,
else the absolute cwd. Canonicalize the same way Claude Code does for
``~/.claude/projects/``: replace ``/`` with ``-`` and prefix with ``-``.
Example: ``/Users/maheidem/Documents/dev/OktoLabsAI`` →
``-Users-maheidem-Documents-dev-OktoLabsAI``.

Migration
---------
On first read for a given project key, if
``$STATE_DIR/active-board.json`` is missing AND the legacy
``${CLAUDE_PLUGIN_DATA}/active-board.json`` exists, copy the legacy
file into the per-project dir. Same for flow-state.json. Legacy files
are kept in place for one release; deletion is scheduled for v0.3.0.

CLI
---
::

    STATE_DIR=$(python3 resolve_project_state.py --cwd "$PWD")

Prints the resolved per-project state directory on stdout (one line, no
trailing whitespace). Always exits 0 unless arguments are malformed.
All non-essential output is silenced — the caller pipes stdout into a
shell variable.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import sys


_LEGACY_FILES = ("active-board.json", "flow-state.json")
_DEFAULT_DATA = pathlib.Path.home() / ".claude" / "plugins" / "data" / "okto-pulse-oktolabs-plugins"


def _resolve_data_dir() -> pathlib.Path:
    """Mirror the ``CLAUDE_PLUGIN_DATA`` fallback used by ``bin/doctor.sh``."""
    raw = os.environ.get("CLAUDE_PLUGIN_DATA", "")
    if raw and "okto-pulse" in raw:
        return pathlib.Path(raw)
    return _DEFAULT_DATA


def _project_root(cwd: pathlib.Path) -> pathlib.Path:
    try:
        out = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return cwd.resolve()
    if out.returncode == 0:
        toplevel = out.stdout.strip()
        if toplevel:
            return pathlib.Path(toplevel).resolve()
    return cwd.resolve()


def _project_key(root: pathlib.Path) -> str:
    abspath = str(root)
    if not abspath.startswith("/"):
        abspath = "/" + abspath
    return "-" + abspath.replace("/", "-").lstrip("-")


def _migrate_legacy(data_dir: pathlib.Path, state_dir: pathlib.Path) -> None:
    for name in _LEGACY_FILES:
        per_project = state_dir / name
        legacy = data_dir / name
        if per_project.exists():
            continue
        if not legacy.exists():
            continue
        try:
            shutil.copy2(str(legacy), str(per_project))
        except OSError:
            # Migration is best-effort. The skill will write fresh state if needed.
            pass


def resolve(cwd: pathlib.Path | None = None) -> pathlib.Path:
    cwd = (cwd or pathlib.Path.cwd()).resolve()
    data_dir = _resolve_data_dir()
    root = _project_root(cwd)
    key = _project_key(root)
    state_dir = data_dir / "projects" / key
    state_dir.mkdir(parents=True, exist_ok=True)
    _migrate_legacy(data_dir, state_dir)
    return state_dir


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", default=os.getcwd(), help="Working directory to resolve from.")
    args = parser.parse_args(argv[1:])
    try:
        state_dir = resolve(pathlib.Path(args.cwd))
    except Exception as exc:  # noqa: BLE001
        print(f"resolve_project_state.py: {exc}", file=sys.stderr)
        return 1
    sys.stdout.write(str(state_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
