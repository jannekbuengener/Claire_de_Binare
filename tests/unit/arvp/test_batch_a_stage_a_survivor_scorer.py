"""Tests for Batch-A Stage-A survivor scorer (#4032 / A1)."""

from __future__ import annotations

import pytest

from tools.arvp_vacation.batch_a_stage_a_survivor_scorer import (
    STATUS_INSUFFICIENT,
    STATUS_REJECTED,
    STATUS_SURVIVOR,
    score_stage_a_candidate,
)
from tools.market_data.development_window_selector import (
    LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]

CANDIDATE = "donchian_breakout_v1"
BASELINE = "baseline"
PESSIMISTIC = "pessimistic_execution"


def _record(
    window_id: str,
    scenario_id: str,
    *,
    net_pnl: float = 100.0,
    closed_trades: int = 5,
    profit_factor: float | str = 1.2,
    max_drawdown_r: float = 0.1,
) -> dict:
    return {
        "candidate_id": CANDIDATE,
        "strategy_id": CANDIDATE,
        "window_id": window_id,
        "scenario_id": scenario_id,
        "net_pnl_quote": net_pnl,
        "closed_trades_total": closed_trades,
        "profit_factor": profit_factor,
        "max_drawdown_r": max_drawdown_r,
        "dataset_quality_verdict": "PASS",
        "job_status": "completed",
    }


def _paired_survivor_records() -> list[dict]:
    records: list[dict] = []
    for window_id in LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS:
        records.append(_record(window_id, BASELINE, net_pnl=120.0, closed_trades=3))
        records.append(
            _record(window_id, PESSIMISTIC, net_pnl=80.0, closed_trades=3)
        )
    return records


def test_survivor_when_all_paired_windows_pass() -> None:
    result = score_stage_a_candidate(
        candidate_id=CANDIDATE,
        records=_paired_survivor_records(),
    )
    assert result.status == STATUS_SURVIVOR
    assert result.coverage["paired_evaluable_share"] >= 0.5


def test_rejected_when_baseline_median_not_positive() -> None:
    records = _paired_survivor_records()
    for record in records:
        if record["scenario_id"] == BASELINE:
            record["net_pnl_quote"] = -10.0
    result = score_stage_a_candidate(candidate_id=CANDIDATE, records=records)
    assert result.status == STATUS_REJECTED


def test_insufficient_when_missing_pessimistic_pairs() -> None:
    records = [
        _record(window_id, BASELINE)
        for window_id in LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS[:10]
    ]
    result = score_stage_a_candidate(candidate_id=CANDIDATE, records=records)
    assert result.status == STATUS_INSUFFICIENT
    assert result.coverage["missing_pair_count"] == 39


def test_anti_auto_pass_requires_positive_pessimistic_median() -> None:
    records = _paired_survivor_records()
    for record in records:
        if record["scenario_id"] == PESSIMISTIC:
            record["net_pnl_quote"] = -1.0
    result = score_stage_a_candidate(candidate_id=CANDIDATE, records=records)
    assert result.status == STATUS_REJECTED
    assert result.gate_results["gates"]["G-E08"]["passed"] is False


def test_profit_factor_infinity_token_passes_when_net_positive() -> None:
    records = _paired_survivor_records()
    for record in records:
        if record["scenario_id"] == BASELINE:
            record["profit_factor"] = "infinity"
    result = score_stage_a_candidate(candidate_id=CANDIDATE, records=records)
    assert result.gate_results["gates"]["G-E04"]["passed"] is True
    assert result.gate_results["gates"]["G-E04"]["observed"] == "infinity"
