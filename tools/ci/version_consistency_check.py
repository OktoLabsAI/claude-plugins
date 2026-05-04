#!/usr/bin/env python3
"""Verify plugin.json version <-> compatible-pulse-range <-> installed pulse.

Per business rule ``br_967ba381`` plugin.json must mirror the okto-pulse
pip release 1:1. We enforce two invariants here:

1. ``--installed-pulse-version`` satisfies ``compatible-pulse-range``
   (``packaging.specifiers.SpecifierSet``).
2. ``--installed-pulse-version`` equals plugin.json's ``version``
   exactly. (1:1 mirror.)

``compatible-pulse-range`` lives in the OktoLabs sibling metadata file
``.claude-plugin/oktolabs-meta.json`` because the upstream Claude
validator (CLI 2.1.126) rejects unknown top-level keys on plugin.json.
For unit-test fixtures that pin the field directly inside plugin.json
(see ``tests/test_version_consistency.py``) we fall back to reading
the field from plugin.json itself.

Failure mode prints the line:
    ERROR: pulse version <installed> is outside compatible range <range>
which the leaf scenario ``ts_d6d14d62`` greps for.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from packaging.specifiers import SpecifierSet
from packaging.version import Version, InvalidVersion


DEFAULT_PLUGIN_JSON = Path("plugins/okto-pulse/.claude-plugin/plugin.json")


def _resolve_compatible_range(plugin_json_path: Path, manifest: dict) -> str | None:
    # Preferred: sibling meta file alongside plugin.json.
    sibling = plugin_json_path.parent / "oktolabs-meta.json"
    if sibling.is_file():
        try:
            meta = json.loads(sibling.read_text(encoding="utf-8"))
            value = meta.get("compatible-pulse-range")
            if value:
                return value
        except json.JSONDecodeError:
            pass
    # Fallback: inlined in plugin.json (unit-test fixture path).
    return manifest.get("compatible-pulse-range")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--plugin-json",
        default=str(DEFAULT_PLUGIN_JSON),
        help="Path to plugin.json.",
    )
    parser.add_argument(
        "--installed-pulse-version",
        required=True,
        help="The okto-pulse pip version we're testing against (semver).",
    )
    args = parser.parse_args(argv)

    plugin_json_path = Path(args.plugin_json)
    if not plugin_json_path.is_file():
        print(
            f"ERROR: plugin.json not found at {plugin_json_path}",
            file=sys.stderr,
        )
        return 1

    try:
        manifest = json.loads(plugin_json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: plugin.json is not valid JSON: {exc}", file=sys.stderr)
        return 1

    plugin_version = manifest.get("version")
    range_str = _resolve_compatible_range(plugin_json_path, manifest)
    if not plugin_version or not range_str:
        print(
            "ERROR: plugin.json must define 'version' and either an "
            "inline 'compatible-pulse-range' or a sibling "
            "oktolabs-meta.json with 'compatible-pulse-range'.",
            file=sys.stderr,
        )
        return 1

    installed = args.installed_pulse_version

    try:
        installed_v = Version(installed)
    except InvalidVersion as exc:
        print(
            f"ERROR: --installed-pulse-version {installed!r} is not a "
            f"valid semver: {exc}",
            file=sys.stderr,
        )
        return 1

    try:
        spec = SpecifierSet(range_str)
    except Exception as exc:  # pragma: no cover - defensive
        print(
            f"ERROR: compatible-pulse-range {range_str!r} is not a "
            f"valid SpecifierSet: {exc}",
            file=sys.stderr,
        )
        return 1

    if installed_v not in spec:
        # Single line containing both the literal installed version and
        # the word ``outside`` so leaf scenario ts_d6d14d62 can grep.
        print(
            f"ERROR: pulse version {installed} is outside compatible "
            f"range {range_str}",
            file=sys.stderr,
        )
        return 1

    if Version(plugin_version) != installed_v:
        print(
            f"ERROR: pulse version {installed} is outside compatible "
            f"range {range_str}: plugin.json#version is "
            f"{plugin_version} but installed pulse pip is {installed} "
            f"(1:1 mirror required, br_967ba381).",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
