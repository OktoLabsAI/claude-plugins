"""Atomic file-write helpers for Pulse plugin state.

Implements the contract from R1 KB technical-requirements
``tr_0bca8958`` / ``tr_2dbe4461`` / ``tr_a9c5f04f`` and business-rule
``br_a427fe32``: state-file writes must be atomic so that a crash
(power loss, SIGKILL, OOM-kill) leaves the target either at its prior
contents or at the new contents -- never partial, never empty.

The implementation relies on the POSIX guarantee that ``rename(2)`` on
the same filesystem is atomic. Concretely we:

1. Open a uniquely-named tempfile in the **same directory** as the
   target so that ``os.replace`` stays on the same filesystem.
2. Write the payload, ensuring a trailing ``\\n``.
3. ``flush()`` the Python buffer, then ``os.fsync(fd)`` to push the data
   to disk before the rename so that a post-rename crash cannot reveal
   an empty file.
4. ``os.replace(tmp, target)`` to swap atomically.
5. On any failure, unlink the tempfile to avoid leaking ``.foo.<x>.tmp``
   detritus next to the real file.
"""
from __future__ import annotations

import json
import os
import pathlib
import tempfile


def atomic_write_text(path: pathlib.Path, content: str) -> None:
    """Write ``content`` to ``path`` atomically.

    UTF-8 encoding, trailing newline guaranteed.
    """
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
        tmp_name = None  # ownership handed off to the rename.
    finally:
        if tmp_name is not None:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass


def atomic_write_json(path: pathlib.Path, payload: dict) -> None:
    """Write ``payload`` as pretty JSON to ``path`` atomically."""
    text = json.dumps(payload, indent=2, sort_keys=True)
    atomic_write_text(path, text)
