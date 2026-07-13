"""Tests for Batch-A Stage-B confirmation scorer (#4032 / A2)."""

from __future__ import annotations

import pytest

from tools.arvp_vacation.batch_a_stage_b_confirmation_scorer import (
    STATUS_CONFIRMED,
    STATUS_PARTIAL,
    STATUS_REJECTED,
    score_stage_b_candidate,
)
from tools.market_data.stage_b_window_selector import (
    EXPECTED_MONTHLY_OOS,
    EXPECTED_MONTHLY_VALIDATION,
    EXPECTED_STRESS,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]

CANDIDATE = "donchian_breakout_v1"


def _record(slice_name: str, idx: int, *, net_pnl: float = 50.0) -> dict:
    purpose, overlap = {
        "validation_monthly": ("validation", "monthly"),
        "out_of_sample_monthly": ("out_of_sample", "monthly"),
        "stress": ("stress", "stress"),
        "corroborative_quarterly": ("validation", "quarterly"),
        "corroborative_yearly": ("validation", "yearly"),
    }[slice_name]
    return {
        "candidate_id": CANDIDATE,
        "strategy_id": CANDIDATE,
        "window_id": f"{slice_name}_{idx}",
        "stage_b_slice": slice_name,
        "purpose": purpose,
        "overlap_class": overlap,
        "net_pnl_quote": net_pnl,
        "closed_trades_total": 4,
        "dataset_quality_verdict": "PASS",
    }


def _confirmed_records() -> list[dict]:
    records: list[dict] = []
    for idx in range(EXPECTED_MONTHLY_VALIDATION):
        records.append(_record("validation_monthly", idx, net_pnl=80.0))
    for idx in range(EXPECTED_MONTHLY_OOS):
        records.append(_record("out_of_sample_monthly", idx, net_pnl=60.0))
    for idx in range(EXPECTED_STRESS):
        records.append(_record("stress", idx, net_pnl=40.0))
    for idx in range(3):
        records.append(_record("corroborative_quarterly", idx, net_pnl=-999.0))
    records.append(_record("corroborative_yearly", 0, net_pnl=-999.0))
    return records


def test_confirmed_when_all_primary_slices_pass() -> None:
    result = score_stage_b_candidate(
        candidate_id=CANDIDATE,
        records=_confirmed_records(),
    )
    assert result.status == STATUS_CONFIRMED


def test_corroborative_slices_do_not_affect_primary_median() -> None:
    result = score_stage_b_candidate(
        candidate_id=CANDIDATE,
        records=_confirmed_records(),
    )
    aggregation = result.gate_results["primary_aggregation"]
    assert aggregation["quarterly_yearly_in_primary_median"] is False
    assert aggregation["primary_combined_median_net_pnl_quote"] > 0
    assert aggregation["corroborative_median_net_pnl_quote"] < 0


def test_partial_when_rankable_share_insufficient() -> None:
    records = _confirmed_records()[: EXPECTED_MONTHLY_VALIDATION // 2]
    result = score_stage_b_candidate(candidate_id=CANDIDATE, records=records)
    assert result.status in {STATUS_PARTIAL, STATUS_REJECTED}


def test_rejected_when_primary_slices_negative() -> None:
    records = _confirmed_records()
    for record in records:
        if record["stage_b_slice"] in {
            "validation_monthly",
            "out_of_sample_monthly",
            "stress",
        }:
            record["net_pnl_quote"] = -5.0
    result = score_stage_b_candidate(candidate_id=CANDIDATE, records=records)
    assert result.status in {STATUS_REJECTED, STATUS_PARTIAL}
    assert result.gate_results["gates"]["B-V02"]["passed"] is False
