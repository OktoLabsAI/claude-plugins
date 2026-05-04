"""R3.3 — persona/okto-pulse-rules.md fragment resolves and is importable.

Verifies that the persona fragment exists as plain markdown with
the expected rule content and no YAML frontmatter.
"""
from __future__ import annotations
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PERSONA_FILE = REPO_ROOT / "plugins" / "okto-pulse" / "persona" / "okto-pulse-rules.md"


@pytest.mark.scenario("ts_86d75260")
@pytest.mark.card("aa4ff485-a35c-48d2-8bc6-c45c35c13f5d")
@pytest.mark.sprint("c4ff2acc-7273-4b57-9784-35cfb75e35a2")
@pytest.mark.spec("938c5dfb-22fd-44a1-9352-af1aeae2677f")
def test_persona_fragment_resolves():
    """@okto-pulse-rules resolves to persona/okto-pulse-rules.md fragment."""
    assert PERSONA_FILE.exists(), f"Missing: {PERSONA_FILE}"
    content = PERSONA_FILE.read_text()
    assert "flow" in content.lower() or "stage" in content.lower() or "mcp" in content.lower(), (
        "persona fragment must mention flow state, stages, or MCP rules"
    )
    assert not content.startswith("---"), (
        "persona/okto-pulse-rules.md must be plain markdown with no YAML frontmatter"
    )
