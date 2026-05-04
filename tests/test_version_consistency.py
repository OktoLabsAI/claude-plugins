"""Card 98365a30 / scenario ts_d6d14d62 — version-consistency check.

Unit: the version-consistency CI script must parse plugin.json's
compatible-pulse-range and reject a pip version that falls outside it
(e.g. range ">=0.1.14, <0.2" must reject pip 0.2.0).

Status: RED scaffold. Lifts to passing once R1.2 ships
- tools/ci/version_consistency_check.py
- plugins/okto-pulse/.claude-plugin/plugin.json (with compatible-pulse-range)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from .scenarios import SCENARIOS

_S = SCENARIOS["ts_d6d14d62"]

# Constants pinned by the spec — keep here so the test is the source of
# truth the impl must match.
PLUGIN_VERSION_UNDER_TEST = "0.1.14"
COMPATIBLE_RANGE_UNDER_TEST = ">=0.1.14, <0.2"
NEXT_MAJOR_PIP_VERSION = "0.2.0"


@pytest.mark.scenario("ts_d6d14d62")
@pytest.mark.card("98365a30-fb54-4a58-b3c8-95364759565f")
@pytest.mark.sprint("97de0400-5ba6-4c16-8945-9e1f78d5bd40")
@pytest.mark.spec("75fe081f-2e7f-4d38-ba73-57d47815c369")
@pytest.mark.xfail(
    reason="awaiting R1.2 impl: tools/ci/version_consistency_check.py",
    strict=True,
)
def test_compatible_pulse_range_excludes_next_major(
    tmp_path: Path,
    version_consistency_check_script: Path,
) -> None:
    f"""GIVEN: {_S['given']}
    WHEN:  {_S['when']}
    THEN:  {_S['then']}
    """
    # Precondition — script is an R1.2 deliverable.
    assert version_consistency_check_script.exists(), (
        f"R1.2 deliverable missing: {version_consistency_check_script}"
    )

    # Build a fixture plugin.json under tmp_path so the test never depends
    # on R1.2's real manifest copy.
    plugin_json = tmp_path / "plugin.json"
    plugin_json.write_text(
        '{\n'
        f'  "version": "{PLUGIN_VERSION_UNDER_TEST}",\n'
        f'  "compatible-pulse-range": "{COMPATIBLE_RANGE_UNDER_TEST}"\n'
        '}\n',
        encoding="utf-8",
    )

    # The harness will:
    #   1. subprocess.run([sys.executable, str(version_consistency_check_script),
    #      "--plugin-json", str(plugin_json),
    #      "--installed-pulse-version", NEXT_MAJOR_PIP_VERSION],
    #      capture_output=True, check=False)
    #   2. assert returncode != 0
    #   3. assert "0.2.0" appears in the output AND that "outside" /
    #      "incompatible" appears (whichever wording R1.2 chooses, lock it).
    raise NotImplementedError(
        "Subprocess invocation of the version check lands in R1.2."
    )
