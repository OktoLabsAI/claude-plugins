#!/usr/bin/env python3
"""Lint .claude-plugin/marketplace.json + repo-level docs.

Asserts:
- ``name == "oktolabs-plugins"``
- ``owner.name`` and ``owner.email`` exist; the email host is NOT
  ``example.com`` (per ``tr_64b8594b``)
- ``version`` exists
- ``metadata.pluginRoot == "./plugins"``
- ``plugins`` is a non-empty list and every entry has all required
  fields with ``category == "workflow"``
- top-level ``CHANGELOG.md`` and ``CONTRIBUTING.md`` exist non-empty
  (per ``br_993c1faa``)

All failures are collected and reported; exit 1 if any fail.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REQUIRED_PLUGIN_FIELDS = (
    "name",
    "description",
    "category",
    "tags",
    "version",
    "author",
    "homepage",
    "source",
)


def lint(marketplace_json_path: Path) -> list[str]:
    failures: list[str] = []
    if not marketplace_json_path.is_file():
        return [f"marketplace.json not found at {marketplace_json_path}"]

    try:
        data = json.loads(marketplace_json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"marketplace.json is not valid JSON: {exc}"]

    if data.get("name") != "oktolabs-plugins":
        failures.append(
            f"name must be 'oktolabs-plugins' (got {data.get('name')!r})"
        )

    owner = data.get("owner") or {}
    if not owner.get("name"):
        failures.append("owner.name is required")
    email = owner.get("email") or ""
    if not email:
        failures.append("owner.email is required")
    elif "example.com" in email.lower():
        failures.append(
            f"owner.email must not use example.com (got {email!r}) -- tr_64b8594b"
        )

    if not data.get("version"):
        failures.append("version is required")

    metadata = data.get("metadata") or {}
    if metadata.get("pluginRoot") != "./plugins":
        failures.append(
            f"metadata.pluginRoot must be './plugins' "
            f"(got {metadata.get('pluginRoot')!r})"
        )

    plugins = data.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        failures.append("plugins[] must be a non-empty list")
    else:
        for i, entry in enumerate(plugins):
            if not isinstance(entry, dict):
                failures.append(f"plugins[{i}] must be an object")
                continue
            for field in REQUIRED_PLUGIN_FIELDS:
                if field not in entry:
                    failures.append(
                        f"plugins[{i}] missing required field: {field!r}"
                    )
            if entry.get("category") != "workflow":
                failures.append(
                    f"plugins[{i}].category must be 'workflow' "
                    f"(got {entry.get('category')!r})"
                )
            author = entry.get("author") or {}
            if not isinstance(author, dict) or not author.get("name"):
                failures.append(f"plugins[{i}].author.name is required")
            tags = entry.get("tags")
            if not isinstance(tags, list):
                failures.append(f"plugins[{i}].tags must be a list")

    repo_root = marketplace_json_path.parent.parent
    for required_doc in ("CHANGELOG.md", "CONTRIBUTING.md"):
        doc_path = repo_root / required_doc
        if not doc_path.is_file():
            failures.append(
                f"{required_doc} is required at the repo root (br_993c1faa)"
            )
        elif doc_path.stat().st_size == 0:
            failures.append(
                f"{required_doc} must not be empty (br_993c1faa)"
            )

    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--marketplace-json",
        default=".claude-plugin/marketplace.json",
        help="Path to marketplace.json.",
    )
    args = parser.parse_args(argv)
    failures = lint(Path(args.marketplace_json))
    if failures:
        for f in failures:
            print(f"FAIL: {f}", file=sys.stderr)
        print(
            f"marketplace_lint: {len(failures)} failure(s)",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
