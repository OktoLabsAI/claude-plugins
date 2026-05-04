"""Card 98365a30 / scenario ts_d6d14d62 — version-consistency check.

Unit: the version-consistency CI script must parse plugin.json's
compatible-pulse-range and reject a pip version that falls outside it
(e.g. range ">=0.1.14, <0.2" must reject pip 0.2.0).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

# Constants pinned by the spec — keep here so the test is the source of
# truth the impl must match.
PLUGIN_VERSION_UNDER_TEST = "0.1.14"
COMPATIBLE_RANGE_UNDER_TEST = ">=0.1.14, <0.2"
NEXT_MAJOR_PIP_VERSION = "0.2.0"


@pytest.mark.scenario("ts_d6d14d62")
@pytest.mark.card("98365a30-fb54-4a58-b3c8-95364759565f")
@pytest.mark.sprint("97de0400-5ba6-4c16-8945-9e1f78d5bd40")
@pytest.mark.spec("75fe081f-2e7f-4d38-ba73-57d47815c369")
def test_compatible_pulse_range_excludes_next_major(
    tmp_path: Path,
    version_consistency_check_script: Path,
) -> None:
    """Scenario ts_d6d14d62 — compatible-pulse-range excludes next major.

    GIVEN: plugin.json#version is 0.1.14 and compatible-pulse-range is
        ">=0.1.14, <0.2"; CI is testing against okto-pulse pip 0.2.0.
    WHEN:  CI version-consistency check parses the range and compares
        against the installed pip version.
    THEN:  Check fails with a message that 0.2.0 is outside the
        compatible range; PR is blocked from merging.
    """
    assert version_consistency_check_script.exists(), (
        f"R1.2 deliverable missing: {version_consistency_check_script}"
    )

    plugin_json = tmp_path / "plugin.json"
    plugin_json.write_text(
        '{\n'
        f'  "version": "{PLUGIN_VERSION_UNDER_TEST}",\n'
        f'  "compatible-pulse-range": "{COMPATIBLE_RANGE_UNDER_TEST}"\n'
        '}\n',
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(version_consistency_check_script),
            "--plugin-json",
            str(plugin_json),
            "--installed-pulse-version",
            NEXT_MAJOR_PIP_VERSION,
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0, (
        f"Expected non-zero exit for pulse 0.2.0 vs range "
        f"'>=0.1.14, <0.2'. stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    combined = (result.stdout + result.stderr).lower()
    assert NEXT_MAJOR_PIP_VERSION in combined, (
        f"Expected installed version {NEXT_MAJOR_PIP_VERSION!r} in "
        f"output; got:\n{combined}"
    )
    assert "outside" in combined, (
        f"Expected the word 'outside' in output; got:\n{combined}"
    )
