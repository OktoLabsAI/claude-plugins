#!/usr/bin/env python3
"""Build the GitHub-pinned marketplace.json for a tagged release.

`marketplace.json` on `main` ships every plugin entry with a relative
`source: "./plugins/<name>"`. For a tagged release we want clones of
the marketplace to install from a fixed ref instead. This tool reads
`.claude-plugin/marketplace.json`, deep-copies it, rewrites every
plugin entry's `source` from a string into a github-pinned dict:

    {"source":"github","repo":"oktolabsai/claude-plugins",
     "ref":"<tag>","path":"plugins/<plugin>"}

and writes the result via the atomic-write helper so a partial write
cannot land in `dist/`.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

# Make ``tools.state`` importable when this script is invoked directly
# (eg via the test harness that calls ``python tools/release/...``).
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.state.atomic_write import atomic_write_json  # noqa: E402


REPO_SLUG = "oktolabsai/claude-plugins"


def _rewrite_source(entry: dict, tag: str) -> dict:
    src = entry.get("source")
    if not isinstance(src, str):
        return entry
    # Strip leading "./" then expect "plugins/<name>".
    rel = src[2:] if src.startswith("./") else src
    rel = rel.rstrip("/")
    entry["source"] = {
        "source": "github",
        "repo": REPO_SLUG,
        "ref": tag,
        "path": rel,
    }
    return entry


def build(marketplace_json_path: Path, tag: str) -> dict:
    data = json.loads(marketplace_json_path.read_text(encoding="utf-8"))
    out = copy.deepcopy(data)
    plugins = out.get("plugins") or []
    for entry in plugins:
        _rewrite_source(entry, tag)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tag",
        required=True,
        help="Release tag, eg v0.1.14.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output path for the GitHub-pinned marketplace.json.",
    )
    parser.add_argument(
        "--marketplace-json",
        default=str(REPO_ROOT / ".claude-plugin" / "marketplace.json"),
        help="Source marketplace.json (default: repo root).",
    )
    args = parser.parse_args(argv)

    src_path = Path(args.marketplace_json)
    if not src_path.is_file():
        print(
            f"ERROR: marketplace.json not found at {src_path}",
            file=sys.stderr,
        )
        return 1

    out = build(src_path, args.tag)
    output_path = Path(args.output)
    atomic_write_json(output_path, out)
    print(f"wrote {output_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
