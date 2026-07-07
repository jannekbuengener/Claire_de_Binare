"""Profitability / training-validation regression contract tests (#3840).

Extends league scorer coverage for PARK/HOLD/BLOCK semantics and evidence gaps.
No new strategy, ML, or ranking-policy changes.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

from services.validation.profitability_league_scorer import (
    build_league_table_report,
    hard_gate_failures,
    score_candidate,
)

from tests.unit.validation.test_profitability_league_scorer import (
    _ranking_ready_pep,
    _sentinel_pep,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def _park_hold_pep() -> dict[str, Any]:
    pep = _ranking_ready_pep()
    pep["candidate_id"] = "cand-park-hold-v1"
    pep["recommendation"] = "PARK"
    pep["net_return"] = -0.02
    return pep


@pytest.mark.unit
def test_missing_evidence_stays_gap_not_promotion_score() -> None:
    pep = _sentinel_pep()
    result = score_candidate(pep)
    assert result.ranking_ready is False
    assert result.total_score == 0.0
    assert result.sentinel_mode is True
    report = build_league_table_report([pep])
    assert report["candidate_rankings"][0]["ranking_ready"] is False
    assert report["table_status"] in {"PARTIAL", "BLOCKED"}


@pytest.mark.unit
def test_park_research_hold_is_visible_but_not_ranking_ready() -> None:
    result = score_candidate(_park_hold_pep())
    assert result.ranking_ready is False
    assert any("PARK" in note or "research hold" in note for note in result.limitations_summary)


@pytest.mark.unit
def test_hold_partial_table_status_when_mixed_candidates() -> None:
    ready = _ranking_ready_pep()
    park = _park_hold_pep()
    report = build_league_table_report([park, ready])
    assert report["table_status"] == "PARTIAL"
    ranking_by_id = {row["candidate_id"]: row for row in report["candidate_rankings"]}
    assert ranking_by_id[ready["candidate_id"]]["ranking_ready"] is True
    assert ranking_by_id[park["candidate_id"]]["ranking_ready"] is False


@pytest.mark.unit
def test_block_table_status_when_all_candidates_unsafe() -> None:
    unsafe_a = _ranking_ready_pep()
    unsafe_a["candidate_id"] = "cand-block-a"
    unsafe_a["recommendation"] = "UNSAFE"
    unsafe_b = copy.deepcopy(unsafe_a)
    unsafe_b["candidate_id"] = "cand-block-b"
    unsafe_b["recommendation"] = "REJECT"
    report = build_league_table_report([unsafe_a, unsafe_b])
    assert report["table_status"] == "BLOCKED"
    assert all(not row["ranking_ready"] for row in report["candidate_rankings"])


@pytest.mark.unit
def test_null_metrics_are_evidence_gaps_not_zero_scores() -> None:
    pep = _ranking_ready_pep()
    pep["profit_factor"] = None
    failures = hard_gate_failures(pep)
    assert failures == ()
    result = score_candidate(pep)
    assert result.ranking_ready is True
    economics = next(d for d in result.dimension_scores if d.dimension == "NET_ECONOMICS")
    assert economics.score > 0.0


@pytest.mark.unit
def test_deterministic_scoring_is_stable_across_repeated_runs() -> None:
    pep = _ranking_ready_pep()
    first = score_candidate(pep)
    second = score_candidate(copy.deepcopy(pep))
    assert first.total_score == second.total_score
    assert first.ranking_ready == second.ranking_ready
    assert [d.score for d in first.dimension_scores] == [
        d.score for d in second.dimension_scores
    ]


@pytest.mark.unit
def test_no_promotion_on_missing_paper_reference_gate() -> None:
    pep = _ranking_ready_pep()
    pep["replay_vs_paper_status"] = "missing_reference"
    failures = hard_gate_failures(pep)
    assert any("missing_reference" in note for note in failures)
    result = score_candidate(pep)
    assert result.ranking_ready is False
