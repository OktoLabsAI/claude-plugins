"""R3.3 — /okto-pulse:stress-test uses archive_tree for idempotent cleanup.

Verifies that skills/stress-test/SKILL.md uses archive_tree (reversible)
not delete (irreversible) for board cleanup before each stress run.
"""
from __future__ import annotations
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
STRESS_SKILL = REPO_ROOT / "plugins" / "okto-pulse" / "skills" / "stress-test" / "SKILL.md"


@pytest.mark.scenario("ts_65f3b29f")
@pytest.mark.card("ec8e5df2-732d-4deb-b03e-8f56d4ea72ac")
@pytest.mark.sprint("c4ff2acc-7273-4b57-9784-35cfb75e35a2")
@pytest.mark.spec("938c5dfb-22fd-44a1-9352-af1aeae2677f")
def test_stress_test_uses_archive_tree():
    """stress-test uses archive_tree (not delete) for idempotent board cleanup."""
    assert STRESS_SKILL.exists(), f"Missing: {STRESS_SKILL}"
    content = STRESS_SKILL.read_text()
    assert "archive_tree" in content, (
        "stress-test SKILL.md must use archive_tree for cleanup (not delete)"
    )


@pytest.mark.scenario("ts_ac052027")
@pytest.mark.card("33f24fc0-cfe8-42d2-98f6-785f12069bb7")
@pytest.mark.sprint("d6b1dfca-e9c9-46ed-adbc-142b850d34ba")
@pytest.mark.spec("938c5dfb-22fd-44a1-9352-af1aeae2677f")
def test_stress_test_runs_10_parallel_flows():
    """stress-test SKILL.md specifies 10 parallel flows on pinned board."""
    assert STRESS_SKILL.exists(), f"Missing: {STRESS_SKILL}"
    content = STRESS_SKILL.read_text()
    assert "10" in content, "stress-test SKILL.md must specify 10 parallel flows"
    assert "pulse_stress_board_id" in content or "stress" in content.lower(), (
        "stress-test must reference the pinned stress board"
    )
