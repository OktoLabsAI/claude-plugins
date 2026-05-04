"""Card 9447d51a / scenario ts_6592e960 — PreCompact hook consolidates KG.

Integration: when Claude Code fires the PreCompact event, the
consolidate-on-compact.sh hook must run kg_begin_consolidation +
kg_commit_consolidation, with kg_abort_consolidation as the rollback
path on commit failure.

Status: RED scaffold. Lifts to passing once R2.2 ships
- plugins/okto-pulse/scripts/consolidate-on-compact.sh
"""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.scenario("ts_6592e960")
@pytest.mark.card("9447d51a-185e-40b1-a583-b6f897d66156")
@pytest.mark.sprint("2c353ca4-c66d-4f9e-9d4f-9c4683c66f5b")
@pytest.mark.spec("46dbff78-5997-442e-a6c3-c6fb6cb735e3")
@pytest.mark.xfail(
    reason=(
        "awaiting R2.2 impl: scripts/consolidate-on-compact.sh + a Pulse "
        "fixture exposing kg_begin/commit/abort_consolidation"
    ),
    strict=True,
)
def test_precompact_persists_unconsolidated_kg_edges(
    consolidate_on_compact_script: Path,
) -> None:
    """Scenario ts_6592e960 — PreCompact hook consolidates KG.

    GIVEN: An active Claude session has created at least one un-consolidated
        KG edge (e.g. via okto_pulse_kg_add_edge_candidate during the session).
    WHEN:  Claude Code triggers context compaction (PreCompact event).
    THEN:  consolidate-on-compact.sh fires; kg_begin_consolidation +
        kg_commit_consolidation succeed; the previously-uncommitted edge is
        queryable via okto_pulse_kg_query_natural after the hook completes;
        on commit failure, kg_abort_consolidation is called and the edge
        remains in the candidate state.
    """
    assert consolidate_on_compact_script.exists(), (
        f"R2.2 deliverable missing: {consolidate_on_compact_script}"
    )

    # The R2.2 harness will:
    #   1. Boot a local Pulse fixture and register a candidate edge via
    #      okto_pulse_kg_add_edge_candidate.
    #   2. Pipe a Claude Code PreCompact event payload (matcher=PreCompact)
    #      into the hook via stdin.
    #   3. Assert the hook exits 0.
    #   4. Query okto_pulse_kg_query_natural and assert the edge is present
    #      (i.e. consolidated).
    #   5. Repeat the test forcing kg_commit_consolidation to fail and
    #      assert kg_abort_consolidation was called (no half-state left).
    raise NotImplementedError(
        "PreCompact hook + Pulse fixture harness lands in R2.2 (impl card ca61ca5c)."
    )
