#!/usr/bin/env python3
"""Verify every ``${user_config.X}`` reference resolves to a userConfig key.

Greps the manifest's ``mcpServers``, the linked ``hooks`` file, and all
skill ``SKILL.md`` / agent ``*.md`` files for substitutions of the form
``${user_config.<KEY>}``. Asserts every referenced KEY exists in
plugin.json's ``userConfig`` block.

If userConfig is empty AND no references exist, exits 0.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


USER_CONFIG_RE = re.compile(r"\$\{user_config\.([A-Za-z0-9_]+)\}")


def _scan_text(text: str) -> set[str]:
    return set(USER_CONFIG_RE.findall(text))


def _scan_obj(obj: object) -> set[str]:
    """Walk a parsed JSON object and pull every user_config substitution."""
    found: set[str] = set()
    if isinstance(obj, str):
        found |= _scan_text(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            found |= _scan_obj(k)
            found |= _scan_obj(v)
    elif isinstance(obj, list):
        for item in obj:
            found |= _scan_obj(item)
    return found


def collect_references(plugin_json_path: Path) -> tuple[set[str], set[str]]:
    """Return (referenced_keys, declared_keys)."""
    manifest = json.loads(plugin_json_path.read_text(encoding="utf-8"))
    plugin_dir = plugin_json_path.parent.parent  # plugins/<name>/

    declared = set((manifest.get("userConfig") or {}).keys())

    referenced: set[str] = set()
    referenced |= _scan_obj(manifest.get("mcpServers"))

    hooks_rel = manifest.get("hooks")
    if isinstance(hooks_rel, str):
        hooks_path = (plugin_dir / hooks_rel).resolve()
        if hooks_path.is_file():
            try:
                hooks_data = json.loads(hooks_path.read_text(encoding="utf-8"))
                referenced |= _scan_obj(hooks_data)
            except json.JSONDecodeError:
                referenced |= _scan_text(hooks_path.read_text(encoding="utf-8"))

    skills_dir = plugin_dir / "skills"
    if skills_dir.is_dir():
        for skill_md in skills_dir.rglob("SKILL.md"):
            referenced |= _scan_text(skill_md.read_text(encoding="utf-8"))

    agents_dir = plugin_dir / "agents"
    if agents_dir.is_dir():
        for agent_md in agents_dir.rglob("*.md"):
            referenced |= _scan_text(agent_md.read_text(encoding="utf-8"))

    return referenced, declared


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--plugin-json",
        default="plugins/okto-pulse/.claude-plugin/plugin.json",
        help="Path to plugin.json.",
    )
    args = parser.parse_args(argv)
    plugin_json_path = Path(args.plugin_json)
    if not plugin_json_path.is_file():
        print(
            f"ERROR: plugin.json not found at {plugin_json_path}",
            file=sys.stderr,
        )
        return 1

    referenced, declared = collect_references(plugin_json_path)

    if not referenced and not declared:
        return 0

    missing = sorted(referenced - declared)
    if missing:
        for key in missing:
            print(
                f"FAIL: ${{user_config.{key}}} referenced but not declared "
                f"in plugin.json#userConfig",
                file=sys.stderr,
            )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
