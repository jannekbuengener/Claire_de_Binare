"""Tests for Batch-A Stage-B confirmation scorer (#4032)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.arvp_vacation.batch_a_stage_b_confirmation_scorer import (
    STATUS_CONFIRMED,
    STATUS_PARTIAL,
    STATUS_REJECTED,
    load_stage_b_confirmation_contract,
    score_stage_b_candidate,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = (
    REPO_ROOT / "docs/contracts/batch_a_stage_b_confirmation_contract.v1.json"
)
CANDIDATE = "momentum_capture_v1"


def _record(
    *,
    window_id: str,
    purpose: str,
    overlap_class: str,
    net_pnl: float,
    closed_trades: int = 12,
) -> dict:
    slice_name = {
        ("validation", "monthly"): "validation_monthly",
        ("out_of_sample", "monthly"): "out_of_sample_monthly",
        ("stress", "stress"): "stress",
        ("validation", "quarterly"): "corroborative_quarterly",
        ("out_of_sample", "quarterly"): "corroborative_quarterly",
        ("validation", "yearly"): "corroborative_yearly",
    }[(purpose, overlap_class)]
    return {
        "strategy_id": CANDIDATE,
        "window_id": window_id,
        "purpose": purpose,
        "window_class": overlap_class,
        "stage_b_slice": slice_name,
        "scenario": "baseline",
        "rankable": closed_trades > 0,
        "closed_trades_total": closed_trades,
        "net_pnl_quote": net_pnl,
        "profit_factor": 1.2,
    }


def _strong_primary_records() -> list[dict]:
    records: list[dict] = []
    for idx in range(27):
        records.append(
            _record(
                window_id=f"val_m_{idx}",
                purpose="validation",
                overlap_class="monthly",
                net_pnl=8.0,
            )
        )
    for idx in range(15):
        records.append(
            _record(
                window_id=f"oos_m_{idx}",
                purpose="out_of_sample",
                overlap_class="monthly",
                net_pnl=6.0,
            )
        )
    for idx in range(5):
        records.append(
            _record(
                window_id=f"stress_{idx}",
                purpose="stress",
                overlap_class="stress",
                net_pnl=4.0,
            )
        )
    return records


@pytest.fixture
def gate_contract() -> dict:
    return load_stage_b_confirmation_contract(CONTRACT_PATH)


def test_confirmed_when_primary_slices_pass(gate_contract: dict) -> None:
    result = score_stage_b_candidate(
        candidate_id=CANDIDATE,
        records=_strong_primary_records(),
        gate_contract=gate_contract,
    )
    assert result.status == STATUS_CONFIRMED


def test_quarterly_not_in_primary_median(gate_contract: dict) -> None:
    records = _strong_primary_records()
    # Strong negative quarterly corroborative windows must not flip primary median positive.
    for idx in range(6):
        records.append(
            _record(
                window_id=f"val_q_{idx}",
                purpose="validation",
                overlap_class="quarterly",
                net_pnl=-1000.0,
            )
        )
    result = score_stage_b_candidate(
        candidate_id=CANDIDATE,
        records=records,
        gate_contract=gate_contract,
    )
    primary = result.gate_results["primary_aggregation"]
    assert primary["quarterly_yearly_in_primary_median"] is False
    assert primary["primary_combined_median_net_pnl_quote"] > 0
    assert primary["corroborative_median_net_pnl_quote"] < 0
    assert result.status in {STATUS_CONFIRMED, STATUS_PARTIAL}


def test_negative_primary_monthly_rejects(gate_contract: dict) -> None:
    records = _strong_primary_records()
    for row in records:
        if row["stage_b_slice"] == "validation_monthly":
            row["net_pnl_quote"] = -5.0
    result = score_stage_b_candidate(
        candidate_id=CANDIDATE,
        records=records,
        gate_contract=gate_contract,
    )
    assert result.status in {STATUS_REJECTED, STATUS_PARTIAL}
    assert result.gate_results["gates"]["B-V02"]["passed"] is False


def test_validation_and_oos_evaluated_separately(gate_contract: dict) -> None:
    records = _strong_primary_records()
    for row in records:
        if row["stage_b_slice"] == "out_of_sample_monthly":
            row["net_pnl_quote"] = -10.0
    result = score_stage_b_candidate(
        candidate_id=CANDIDATE,
        records=records,
        gate_contract=gate_contract,
    )
    assert result.gate_results["gates"]["B-V02"]["passed"] is True
    assert result.gate_results["gates"]["B-O02"]["passed"] is False
    assert result.status in {STATUS_REJECTED, STATUS_PARTIAL}
