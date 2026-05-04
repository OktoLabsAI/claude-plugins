"""R3.3 — planning subagents declare disallowedTools: Write, Edit.

Verifies that all planning agents (all except implementer) have
disallowedTools: ["Write", "Edit"] in their YAML frontmatter.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO_ROOT / "plugins" / "okto-pulse" / "agents"

PLANNING_AGENTS = [
    "ideation-analyst.md",
    "refinement-investigator.md",
    "spec-writer.md",
    "architect.md",
    "qa-engineer.md",
    "kg-curator.md",
    "sprint-planner.md",
]


@pytest.mark.scenario("ts_aef8ef97")
@pytest.mark.card("55d4f75a-15ae-4371-b1d7-22a5d98c2285")
@pytest.mark.sprint("d6b1dfca-e9c9-46ed-adbc-142b850d34ba")
@pytest.mark.spec("938c5dfb-22fd-44a1-9352-af1aeae2677f")
@pytest.mark.parametrize("agent_file", PLANNING_AGENTS)
def test_planning_agent_has_disallowed_tools(agent_file: str):
    """Planning agents must declare disallowedTools: Write and Edit."""
    path = AGENTS_DIR / agent_file
    assert path.exists(), f"Missing planning agent: {path}"
    content = path.read_text()
    assert "Write" in content and "Edit" in content, (
        f"{agent_file} must declare disallowedTools containing Write and Edit"
    )
    assert "disallowedTools" in content, (
        f"{agent_file} must have disallowedTools frontmatter key"
    )


@pytest.mark.scenario("ts_7095586e")
@pytest.mark.card("915066be-e376-4ba1-a44f-9aaa0167cd8e")
@pytest.mark.sprint("9518d4bd-8bcd-4cb8-b5ed-2ac3ffbdeb42")
@pytest.mark.spec("938c5dfb-22fd-44a1-9352-af1aeae2677f")
def test_implementer_does_not_have_disallowed_write():
    """Implementer agent must NOT restrict Write/Edit tools."""
    implementer = AGENTS_DIR / "implementer.md"
    assert implementer.exists(), f"Missing: {implementer}"
    content = implementer.read_text()
    assert "disallowedTools" not in content or "Write" not in content.split("disallowedTools")[-1].split("\n")[0], (
        "implementer.md must not disallow Write or Edit"
    )
