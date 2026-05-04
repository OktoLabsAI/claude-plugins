#!/usr/bin/env python3
"""Plugin-local atomic JSON writer.

Mirrors ``tools/state/atomic_write.atomic_write_json`` so that the
shipped plugin can persist state files (active-board.json,
deploy-mode.json, ...) without depending on the repo-level helper
package after install.

Usage:
    python3 atomic_write.py <path> '<json-payload>'

The payload must be valid JSON. The file is written via tempfile +
``os.replace`` on the same directory so that a crash leaves the target
either at the prior contents or the new contents - never partial.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile


def atomic_write_text(path: pathlib.Path, content: str) -> None:
    path = pathlib.Path(path)
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    if not content.endswith("\n"):
        content = content + "\n"
    tmp_name: str | None = None
    try:
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(parent),
            delete=False,
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
        tmp_name = tmp.name
        try:
            tmp.write(content)
            tmp.flush()
            os.fsync(tmp.fileno())
        finally:
            tmp.close()
        os.replace(tmp_name, str(path))
        tmp_name = None
    finally:
        if tmp_name is not None:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass


def atomic_write_json(path: pathlib.Path, payload) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True)
    atomic_write_text(path, text)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "usage: atomic_write.py <path> <json-payload>",
            file=sys.stderr,
        )
        return 2
    target = pathlib.Path(argv[1])
    try:
        payload = json.loads(argv[2])
    except json.JSONDecodeError as exc:
        print(f"invalid JSON payload: {exc}", file=sys.stderr)
        return 2
    atomic_write_json(target, payload)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
