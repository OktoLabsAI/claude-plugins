#!/usr/bin/env python3
"""Enforce kebab-case for skill / agent / command directory names.

Walks ``<root>/plugins/**/skills``, ``<root>/plugins/**/agents``, and
``<root>/plugins/**/commands``. Each immediate child entry (file or
directory) must be kebab-case (``^[a-z0-9]+(-[a-z0-9]+)*$``). The
following are explicitly skipped:

- hidden files / dirs (any name starting with a dot, eg ``.gitkeep``)
- ``__init__.py``
- markdown files at the top level (``*.md``)

The script collects ALL violations before reporting. It does NOT
short-circuit on the first hit -- this preserves the FR[10] property
that every PR runs all 7 checks even when one fails.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SCAN_BUCKETS = ("skills", "agents", "commands")


def _is_skipped(name: str) -> bool:
    if name.startswith("."):
        return True
    if name == "__init__.py":
        return True
    if name.endswith(".md"):
        return True
    return False


def _kebab_ok(name: str) -> bool:
    # For files, strip the extension before testing -- a kebab name with
    # a dotted extension (eg ``my-skill.json``) should still be accepted.
    stem = name.split(".", 1)[0] if "." in name else name
    return bool(KEBAB_RE.fullmatch(stem))


def find_violations(root: Path) -> list[Path]:
    violations: list[Path] = []
    plugins_root = root / "plugins"
    if not plugins_root.is_dir():
        return violations
    for plugin_dir in sorted(plugins_root.iterdir()):
        if not plugin_dir.is_dir():
            continue
        for bucket in SCAN_BUCKETS:
            bucket_dir = plugin_dir / bucket
            if not bucket_dir.is_dir():
                continue
            for child in sorted(bucket_dir.iterdir()):
                if _is_skipped(child.name):
                    continue
                if not _kebab_ok(child.name):
                    violations.append(child)
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Repository root to scan.")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    violations = find_violations(root)
    if violations:
        for v in violations:
            try:
                rel = v.relative_to(root)
            except ValueError:
                rel = v
            print(str(rel))
        print(
            f"kebab_case_check: {len(violations)} violation(s) found",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
