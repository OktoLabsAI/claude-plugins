"""Card b53480c6 / scenario ts_5ced4e76 — setup one-prompt-then-green.

End-to-end: /okto-pulse:setup must ask the deploy-mode question exactly
once and then run autonomously to a green /okto-pulse:doctor result
without any further confirmation prompts beyond the userConfig values it
cannot infer.

Status: RED scaffold. Lifts to passing once R2.2 ships
- plugins/okto-pulse/skills/setup/SKILL.md (orchestrator skill)
- plugins/okto-pulse/bin/bootstrap-{local-pip,docker,remote}.sh (helpers)
- plugins/okto-pulse/skills/doctor/SKILL.md
- plugins/okto-pulse/bin/doctor.sh
"""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.scenario("ts_5ced4e76")
@pytest.mark.card("b53480c6-826f-4e8d-ba52-a0d7d8d79961")
@pytest.mark.sprint("2c353ca4-c66d-4f9e-9d4f-9c4683c66f5b")
@pytest.mark.spec("46dbff78-5997-442e-a6c3-c6fb6cb735e3")
@pytest.mark.xfail(
    reason=(
        "awaiting R2.2 impl: setup skill + bootstrap helpers + doctor skill"
    ),
    strict=True,
)
def test_setup_completes_with_one_prompt_and_ends_green(
    setup_skill_path: Path,
    doctor_skill_path: Path,
    bootstrap_local_pip_script: Path,
    bootstrap_docker_script: Path,
    bootstrap_remote_script: Path,
) -> None:
    """Scenario ts_5ced4e76 — setup one-prompt-then-green.

    GIVEN: A clean Claude Code environment with okto-pulse plugin enabled,
        no userConfig set, no Pulse running.
    WHEN:  User invokes /okto-pulse:setup and answers the deploy-mode
        question once (any of local-pip, docker, remote with valid inputs).
    THEN:  No further prompts beyond mode question and userConfig values;
        helper script runs to completion; common tail persists userConfig
        and runs /okto-pulse:doctor; doctor reports 100% green; active
        board picker completes.
    """
    # Preconditions — every artifact below is an R2.2 deliverable.
    assert setup_skill_path.exists(), (
        f"R2.2 deliverable missing: {setup_skill_path}"
    )
    assert doctor_skill_path.exists(), (
        f"R2.2 deliverable missing: {doctor_skill_path}"
    )
    for helper in (
        bootstrap_local_pip_script,
        bootstrap_docker_script,
        bootstrap_remote_script,
    ):
        assert helper.exists(), f"R2.2 deliverable missing: {helper}"

    # The R2.2 / R2.3 harness will:
    #   1. Spawn an isolated CLAUDE_HOME, install plugin via marketplace.
    #   2. Programmatically dispatch /okto-pulse:setup with one mode answer
    #      (parametrize over local-pip / docker / remote).
    #   3. Assert the AskUserQuestion fired exactly once for the mode.
    #   4. Assert helper script ran to exit 0 with `{"ok":true}` last NDJSON line.
    #   5. Run /okto-pulse:doctor and assert 100% green output.
    #   6. Assert active-board.json exists with a chosen board id.
    raise NotImplementedError(
        "End-to-end /okto-pulse:setup harness lands in R2.2 / R2.3 (impl card 75184926)."
    )
