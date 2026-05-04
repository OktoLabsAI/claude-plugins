"""Card a88e40f6 / scenario ts_588ed4f7 — marketplace auto-update is off by default.

The marketplace must NOT auto-refresh from its source. A freshly-added
marketplace stays at whatever it was at ``add`` time until the user
explicitly runs ``/plugin marketplace update``.

Two halves:
    Static (always runs): ``.claude-plugin/marketplace.json`` does not
        declare ``autoUpdate`` (or, if present, declares it false).
    Dynamic (skipped without claude CLI): after ``claude plugin
        marketplace add``, the persisted state and ``marketplace list``
        output contain no ``auto-update on`` signal.

The static half MUST run even when the CLI is unavailable, so we run it
unconditionally and only ``return`` early before the dynamic half.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.scenario("ts_588ed4f7")
@pytest.mark.card("a88e40f6-1d70-454c-99e3-32d3c4ed9a0a")
@pytest.mark.sprint("6eaa093b-2ca1-4adc-aabf-1d7bc0e9025f")
@pytest.mark.spec("75fe081f-2e7f-4d38-ba73-57d47815c369")
def test_marketplace_autoupdate_default_off(
    clean_claude_home: Path,
    marketplace_json_path: Path,
    repo_root: Path,
) -> None:
    """Scenario ts_588ed4f7 — marketplace auto-update is off by default.

    GIVEN: ``.claude-plugin/marketplace.json`` ships with no auto-update
        toggle, and ``claude plugin marketplace add`` is the only thing
        the user has run.
    WHEN:  We inspect the marketplace manifest and the CLI's persisted
        state after a fresh ``add``.
    THEN:  No auto-update is declared at the manifest level and no
        auto-update is enabled in the CLI's marketplace state — a
        refresh requires explicit ``/plugin marketplace update``.
    """
    # --- Static half: marketplace.json must not opt into auto-update. ---
    assert marketplace_json_path.exists(), (
        f"R1.2 deliverable missing: {marketplace_json_path}"
    )
    market = json.loads(marketplace_json_path.read_text(encoding="utf-8"))

    # ``autoUpdate`` may either be absent or explicitly false. Anything
    # else is a regression.
    if "autoUpdate" in market:
        assert market["autoUpdate"] is False, (
            f"marketplace.json#autoUpdate must be false (or absent); got "
            f"{market['autoUpdate']!r}. Auto-update by default would "
            f"let a malicious upstream silently push code to every "
            f"install."
        )
    # No per-plugin override either.
    for entry in market.get("plugins", []):
        if "autoUpdate" in entry:
            assert entry["autoUpdate"] is False, (
                f"marketplace.json plugins[] entry "
                f"{entry.get('name')!r} declares autoUpdate="
                f"{entry['autoUpdate']!r}; must be false or absent."
            )

    # --- Dynamic half: requires the claude CLI. ---
    if shutil.which("claude") is None:
        # Static half is the strict gate when the CLI is missing.
        return

    env = {
        **os.environ,
        "CLAUDE_HOME": str(clean_claude_home),
    }
    add = subprocess.run(
        [
            "claude",
            "plugin",
            "marketplace",
            "add",
            str(repo_root),
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert add.returncode == 0, (
        f"`claude plugin marketplace add` failed (rc={add.returncode})\n"
        f"stdout:\n{add.stdout}\nstderr:\n{add.stderr}"
    )

    # Inspect persisted CLI state. The fixture sets HOME=tmp_path; the
    # CLI ignores CLAUDE_HOME and writes under $HOME/.claude.
    home = Path(os.environ["HOME"])
    known = home / ".claude" / "plugins" / "known_marketplaces.json"
    if known.exists():
        known_payload = json.loads(known.read_text(encoding="utf-8"))
        # Whatever shape the CLI uses, no key or nested key may be a
        # truthy 'autoUpdate' / 'auto_update' signal.
        flat = json.dumps(known_payload).lower()
        assert '"autoupdate":true' not in flat, (
            f"known_marketplaces.json declares autoUpdate=true:\n"
            f"{known.read_text(encoding='utf-8')}"
        )
        assert '"auto_update":true' not in flat, (
            f"known_marketplaces.json declares auto_update=true:\n"
            f"{known.read_text(encoding='utf-8')}"
        )

    # `marketplace list` text output must not mention auto-update being
    # on. We accept any phrasing the CLI might use as long as no
    # 'auto-update: on' / 'auto-update enabled' appears.
    listing = subprocess.run(
        ["claude", "plugin", "marketplace", "list"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert listing.returncode == 0, (
        f"`claude plugin marketplace list` failed "
        f"(rc={listing.returncode})\n"
        f"stdout:\n{listing.stdout}\nstderr:\n{listing.stderr}"
    )
    combined = (listing.stdout + listing.stderr).lower()
    forbidden = (
        "auto-update: on",
        "auto update: on",
        "auto-update enabled",
        "auto update enabled",
        "auto-updating: yes",
    )
    for needle in forbidden:
        assert needle not in combined, (
            f"`marketplace list` output contains '{needle}', meaning "
            f"auto-update is on for a freshly-added marketplace. "
            f"Output:\n{combined}"
        )
