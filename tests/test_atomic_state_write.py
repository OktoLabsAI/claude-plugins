"""Card 21395632 / scenario ts_2bc10969 — atomic write under SIGKILL.

The state-file atomic-write helper must satisfy:
    target file == (old payload) OR (new payload), never partial,
    never empty, even when the writing process is SIGKILLed at an
    arbitrary moment.

We exercise this by spawning a Python child that calls
``tools.state.atomic_write.atomic_write_json`` to overwrite a file
preloaded with ``{"board_id":"old"}`` with ``{"board_id":"new"}``.
After spawn, we sleep a random number of microseconds and then send
``SIGKILL`` to the child. After joining, we read the file and assert
it parses as JSON AND equals one of the two valid states.

Why this exercises the contract:
    - If SIGKILL hits BEFORE ``os.replace`` runs, the target file
      retains the prior contents (the temp file may be partial, but
      the test only checks the target).
    - If SIGKILL hits AFTER ``os.replace``, the target holds the new
      contents (POSIX rename is atomic on the same filesystem).
    - There is no third state, by definition.

Twenty random kill timings exercise both ends of the window.
"""
from __future__ import annotations

import json
import os
import random
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest


OLD_PAYLOAD = {"board_id": "old"}
NEW_PAYLOAD = {"board_id": "new"}


def _spawn_writer(target: Path) -> subprocess.Popen:
    """Spawn a child that writes NEW_PAYLOAD to ``target`` atomically.

    The child loops and sleeps before+after the write so the parent has
    a real chance of killing it mid-flight regardless of how fast
    atomic_write_json actually returns.
    """
    code = textwrap.dedent(
        f"""
        import json, os, sys, time
        sys.path.insert(0, {str(Path(__file__).resolve().parent.parent)!r})
        from tools.state.atomic_write import atomic_write_json
        target = {str(target)!r}
        payload = {NEW_PAYLOAD!r}
        # Tight loop so we are very likely to be in some phase of the
        # write when the parent fires SIGKILL.
        for _ in range(10000):
            atomic_write_json(target, payload)
        """
    ).strip()
    return subprocess.Popen(
        [sys.executable, "-c", code],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


@pytest.mark.scenario("ts_2bc10969")
@pytest.mark.card("21395632-fdde-4282-8139-1d64f118bbb3")
@pytest.mark.sprint("e18856b2-4d19-4f7b-91a0-2a9a9559d5f5")
@pytest.mark.spec("75fe081f-2e7f-4d38-ba73-57d47815c369")
def test_atomic_write_survives_sigkill(tmp_path: Path) -> None:
    """Scenario ts_2bc10969 — atomic write under SIGKILL.

    GIVEN: target file holds {"board_id":"old"} via the helper
    WHEN:  a child process writes {"board_id":"new"} via the helper
        and we SIGKILL it at random times
    THEN:  target is either old or new; never partial; never empty
    """
    from tools.state.atomic_write import atomic_write_json

    target = tmp_path / "active-board.json"
    rng = random.Random(0xC0FFEE)

    valid_states = (
        json.dumps(OLD_PAYLOAD, indent=2, sort_keys=True) + "\n",
        json.dumps(NEW_PAYLOAD, indent=2, sort_keys=True) + "\n",
    )

    for trial in range(20):
        # GIVEN: target preloaded with OLD via the same helper.
        atomic_write_json(target, OLD_PAYLOAD)
        assert target.read_text(encoding="utf-8") == valid_states[0]

        # WHEN: spawn the writer + SIGKILL after a random delay.
        proc = _spawn_writer(target)
        try:
            delay_us = rng.randint(0, 5000)  # 0–5 ms
            time.sleep(delay_us / 1_000_000.0)
            os.kill(proc.pid, signal.SIGKILL)
        finally:
            proc.wait(timeout=5.0)

        # THEN: target parses as JSON and equals one of the two states.
        contents = target.read_text(encoding="utf-8")
        assert contents, (
            f"Trial {trial}: target file was empty after SIGKILL; "
            f"atomicity contract violated."
        )
        try:
            parsed = json.loads(contents)
        except json.JSONDecodeError as exc:
            raise AssertionError(
                f"Trial {trial}: target file was not valid JSON after "
                f"SIGKILL ({exc}). Contents:\n{contents!r}"
            )
        assert parsed in (OLD_PAYLOAD, NEW_PAYLOAD), (
            f"Trial {trial}: target file held a payload that was "
            f"neither old nor new: {parsed!r}"
        )
        assert contents in valid_states, (
            f"Trial {trial}: byte-for-byte mismatch with a valid state. "
            f"Got:\n{contents!r}"
        )
