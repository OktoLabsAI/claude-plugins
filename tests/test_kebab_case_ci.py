"""Card 3a62aad0 / scenario ts_e53d04fb — kebab-case violation fails CI.

Integration: when a PR adds a non-kebab path under plugins/<plugin>/skills,
the kebab-case enforcer must fail the build with the offending path.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.scenario("ts_e53d04fb")
@pytest.mark.card("3a62aad0-45b3-4faa-8c99-9250d863e80a")
@pytest.mark.sprint("97de0400-5ba6-4c16-8945-9e1f78d5bd40")
@pytest.mark.spec("75fe081f-2e7f-4d38-ba73-57d47815c369")
def test_kebab_case_violation_fails_ci(
    tmp_path: Path,
    kebab_case_check_script: Path,
) -> None:
    """Scenario ts_e53d04fb — kebab-case violation fails CI.

    GIVEN: A PR adds a skill directory named skills/StressTest/SKILL.md
        (PascalCase) violating kebab-case.
    WHEN:  CI runs the kebab-case enforcer as part of the 7-check suite.
    THEN:  The kebab-case check fails with the offending path; PR cannot
        be merged; the other 6 checks may still run but the overall gate
        is failed.
    """
    # Build the offending fixture: a PascalCase skill directory
    # plugins/okto-pulse/skills/StressTest/SKILL.md
    bad = tmp_path / "plugins" / "okto-pulse" / "skills" / "StressTest" / "SKILL.md"
    bad.parent.mkdir(parents=True)
    bad.write_text("# stub\n", encoding="utf-8")

    assert kebab_case_check_script.exists(), (
        f"R1.2 deliverable missing: {kebab_case_check_script}"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(kebab_case_check_script),
            "--root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0, (
        "kebab_case_check should have failed for skills/StressTest. "
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    combined = result.stdout + result.stderr
    assert "StressTest" in combined, (
        f"Expected the offending path 'StressTest' in output. "
        f"Got:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
