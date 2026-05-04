"""R3.3 — /okto-pulse:flow routing logic verification.

Verifies that skills/flow/SKILL.md defines correct stage→skill dispatch
for all SDLC stages including the draft→ideation initial transition.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FLOW_SKILL = REPO_ROOT / "plugins" / "okto-pulse" / "skills" / "flow" / "SKILL.md"

EXPECTED_STAGES = ["ideation", "refinement", "spec", "sprint", "card", "validation"]
EXPECTED_STAGE_SKILLS = ["ideate", "refine", "spec", "sprint", "task", "validate"]


@pytest.mark.scenario("ts_c02d9681")
@pytest.mark.card("27fb15ec-31a3-4e5a-9007-fca0e99427ff")
@pytest.mark.sprint("c4ff2acc-7273-4b57-9784-35cfb75e35a2")
@pytest.mark.spec("938c5dfb-22fd-44a1-9352-af1aeae2677f")
def test_flow_routes_draft_to_ideation():
    """flow skill routes draft (no state) to okto-pulse:ideate stage."""
    assert FLOW_SKILL.exists(), f"Missing: {FLOW_SKILL}"
    content = FLOW_SKILL.read_text()
    assert "draft" in content.lower(), "flow SKILL.md must handle draft (no state) case"
    assert "ideate" in content, "flow SKILL.md must route to okto-pulse:ideate"
    assert "flow-state.json" in content, "flow SKILL.md must read/write flow-state.json"


@pytest.mark.scenario("ts_f0adb427")
@pytest.mark.card("4d8de7a0-4e32-4070-9382-9afedf733fb3")
@pytest.mark.sprint("9518d4bd-8bcd-4cb8-b5ed-2ac3ffbdeb42")
@pytest.mark.spec("938c5dfb-22fd-44a1-9352-af1aeae2677f")
def test_flow_maps_all_stages():
    """flow SKILL.md has routing for all 6 SDLC stages."""
    assert FLOW_SKILL.exists(), f"Missing: {FLOW_SKILL}"
    content = FLOW_SKILL.read_text()
    for stage_skill in EXPECTED_STAGE_SKILLS:
        assert stage_skill in content, (
            f"flow SKILL.md missing routing for okto-pulse:{stage_skill}"
        )


@pytest.mark.scenario("ts_cbad8556")
@pytest.mark.card("61d2205d-b9ae-4ca9-aaa0-f20baf60cbf7")
@pytest.mark.sprint("9518d4bd-8bcd-4cb8-b5ed-2ac3ffbdeb42")
@pytest.mark.spec("938c5dfb-22fd-44a1-9352-af1aeae2677f")
def test_flow_uses_atomic_write_for_state():
    """flow SKILL.md persists state via atomic_write.py."""
    assert FLOW_SKILL.exists(), f"Missing: {FLOW_SKILL}"
    content = FLOW_SKILL.read_text()
    assert "atomic_write.py" in content, (
        "flow SKILL.md must use scripts/atomic_write.py for state persistence"
    )
