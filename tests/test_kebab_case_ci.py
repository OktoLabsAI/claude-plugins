"""Card 3a62aad0 / scenario ts_e53d04fb — kebab-case violation fails CI.

Integration: when a PR adds a non-kebab path under plugins/<plugin>/skills,
the kebab-case enforcer must fail the build with the offending path.

Status: RED scaffold. Lifts to passing once R1.2 ships
- tools/ci/kebab_case_check.py
"""
from __future__ import annotations

from pathlib import Path

import pytest

from .scenarios import SCENARIOS

_S = SCENARIOS["ts_e53d04fb"]


@pytest.mark.scenario("ts_e53d04fb")
@pytest.mark.card("3a62aad0-45b3-4faa-8c99-9250d863e80a")
@pytest.mark.sprint("97de0400-5ba6-4c16-8945-9e1f78d5bd40")
@pytest.mark.spec("75fe081f-2e7f-4d38-ba73-57d47815c369")
@pytest.mark.xfail(
    reason="awaiting R1.2 impl: tools/ci/kebab_case_check.py",
    strict=True,
)
def test_kebab_case_violation_fails_ci(
    tmp_path: Path,
    kebab_case_check_script: Path,
) -> None:
    f"""GIVEN: {_S['given']}
    WHEN:  {_S['when']}
    THEN:  {_S['then']}
    """
    # Build the offending fixture: a PascalCase skill directory
    # plugins/okto-pulse/skills/StressTest/SKILL.md
    bad = tmp_path / "plugins" / "okto-pulse" / "skills" / "StressTest" / "SKILL.md"
    bad.parent.mkdir(parents=True)
    bad.write_text("# stub\n", encoding="utf-8")

    # Precondition — enforcer is an R1.2 deliverable.
    assert kebab_case_check_script.exists(), (
        f"R1.2 deliverable missing: {kebab_case_check_script}"
    )

    # The harness will:
    #   1. subprocess.run([sys.executable, str(kebab_case_check_script),
    #      "--root", str(tmp_path)], capture_output=True, check=False)
    #   2. assert the returncode is non-zero
    #   3. assert "skills/StressTest" is reported in stdout/stderr
    #   4. assert the script does NOT short-circuit the rest of the check
    #      pipeline (FR[10]: every PR runs all 7 checks even if one fails).
    raise NotImplementedError(
        "Subprocess invocation of the enforcer lands in R1.2."
    )
