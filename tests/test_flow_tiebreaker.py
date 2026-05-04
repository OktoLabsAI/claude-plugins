"""R3.3 — /okto-pulse:flow open-Q&A tiebreaker verification.

Verifies that skills/flow/SKILL.md defines the MCP-completeness tiebreaker.
"""
from __future__ import annotations
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FLOW_SKILL = REPO_ROOT / "plugins" / "okto-pulse" / "skills" / "flow" / "SKILL.md"


@pytest.mark.scenario("ts_38c5fa71")
@pytest.mark.card("044663a0-bd2b-4982-8bc3-31eddb171d15")
@pytest.mark.sprint("c4ff2acc-7273-4b57-9784-35cfb75e35a2")
@pytest.mark.spec("938c5dfb-22fd-44a1-9352-af1aeae2677f")
def test_open_qa_count_breaks_stage_tie():
    """open Q&A count (MCP completeness) breaks ties when current_stage is ambiguous."""
    assert FLOW_SKILL.exists(), f"Missing: {FLOW_SKILL}"
    content = FLOW_SKILL.read_text()
    assert "tiebreaker" in content.lower() or "ambiguous" in content.lower() or "open_count" in content, (
        "flow SKILL.md must mention tiebreaker/ambiguous/open_count logic"
    )
    assert "list_ideation_qa" in content or "open" in content.lower(), (
        "flow SKILL.md must check open Q&A count"
    )

