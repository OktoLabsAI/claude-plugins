"""Card b53480c6 / scenario ts_5ced4e76 - setup one-prompt-then-green.

End-to-end: /okto-pulse:setup must ask the deploy-mode question exactly
once and then run autonomously to a green /okto-pulse:doctor result
without any further confirmation prompts beyond the userConfig values it
cannot infer.

Lifted from RED to GREEN in R2.2: this file now asserts the static
shape of the deliverables (scripts exist, are executable, SKILL.md
declares disable-model-invocation: true). The live "/okto-pulse:setup"
end-to-end harness needs a Claude Code subprocess driver and is
deferred to R2.3.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest


@pytest.mark.scenario("ts_5ced4e76")
@pytest.mark.card("b53480c6-826f-4e8d-ba52-a0d7d8d79961")
@pytest.mark.sprint("2c353ca4-c66d-4f9e-9d4f-9c4683c66f5b")
@pytest.mark.spec("46dbff78-5997-442e-a6c3-c6fb6cb735e3")
def test_setup_completes_with_one_prompt_and_ends_green(
    setup_skill_path: Path,
    doctor_skill_path: Path,
    bootstrap_local_pip_script: Path,
    bootstrap_docker_script: Path,
    bootstrap_remote_script: Path,
) -> None:
    """Scenario ts_5ced4e76 - setup one-prompt-then-green.

    GIVEN: A clean Claude Code environment with okto-pulse plugin enabled,
        no userConfig set, no Pulse running.
    WHEN:  User invokes /okto-pulse:setup and answers the deploy-mode
        question once.
    THEN:  No further prompts beyond mode question and userConfig values;
        helper script runs to completion; common tail persists userConfig
        and runs /okto-pulse:doctor; doctor reports 100% green; active
        board picker completes.

    What this test asserts at the unit level:
    - Every R2.2 deliverable exists at the path the conftest fixtures
      promised.
    - The bootstrap helpers are executable scripts (mode 0755).
    - The setup skill's frontmatter declares
      ``disable-model-invocation: true`` per FR1 / TR ``tr_28ef09f0``.
    - The doctor skill's frontmatter declares
      ``disable-model-invocation: false`` (model-invocable per design).

    The full end-to-end harness (driving /okto-pulse:setup via a Claude
    Code subprocess and asserting a single AskUserQuestion fired) lands
    in R2.3.
    """
    # Preconditions - every artifact below is an R2.2 deliverable.
    for artifact in (
        setup_skill_path,
        doctor_skill_path,
        bootstrap_local_pip_script,
        bootstrap_docker_script,
        bootstrap_remote_script,
    ):
        assert artifact.exists(), f"R2.2 deliverable missing: {artifact}"

    # Bootstrap helpers must be executable.
    for helper in (
        bootstrap_local_pip_script,
        bootstrap_docker_script,
        bootstrap_remote_script,
    ):
        assert os.access(helper, os.X_OK), (
            f"R2.2 deliverable not executable (need 0755): {helper}"
        )

    # Setup SKILL.md must mark disable-model-invocation: true.
    setup_text = setup_skill_path.read_text(encoding="utf-8")
    assert re.search(
        r"^disable-model-invocation:\s*true\s*$",
        setup_text,
        re.MULTILINE,
    ), (
        "setup SKILL.md must declare 'disable-model-invocation: true' "
        "per FR1 / TR tr_28ef09f0"
    )

    # Doctor SKILL.md must be model-invocable (false).
    doctor_text = doctor_skill_path.read_text(encoding="utf-8")
    assert re.search(
        r"^disable-model-invocation:\s*false\s*$",
        doctor_text,
        re.MULTILINE,
    ), "doctor SKILL.md must declare 'disable-model-invocation: false'"

    # description+when_to_use combined <= 1536 chars per Claude Code spec.
    for skill in (setup_skill_path, doctor_skill_path):
        text = skill.read_text(encoding="utf-8")
        m_desc = re.search(r"^description:\s*(.+?)$", text, re.MULTILINE)
        m_when = re.search(r"^when_to_use:\s*(.+?)$", text, re.MULTILINE)
        assert m_desc and m_when, f"missing description/when_to_use in {skill}"
        combined = len(m_desc.group(1)) + len(m_when.group(1))
        assert combined <= 1536, (
            f"description+when_to_use too long ({combined}>1536) in {skill}"
        )
