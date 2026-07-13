"""Tests for Batch-A Stage-A survivor scorer (#4032)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.arvp_vacation.batch_a_gate_common import compute_gate_contract_sha256
from tools.arvp_vacation.batch_a_stage_a_survivor_scorer import (
    STATUS_INSUFFICIENT,
    STATUS_REJECTED,
    STATUS_SURVIVOR,
    load_stage_a_gate_contract,
    score_stage_a_candidate,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = (
    REPO_ROOT / "docs/contracts/batch_a_stage_a_gate_contract.v1.json"
)
CANDIDATE = "momentum_capture_v1"


def _record(
    *,
    window_id: str,
    scenario: str,
    net_pnl: float,
    closed_trades: int = 12,
    profit_factor: float = 1.2,
    max_drawdown_r: float = 0.2,
    expectancy_r: float = 0.1,
) -> dict:
    return {
        "schema_version": "arvp_strategy_metrics.v1",
        "campaign_id": "test-campaign",
        "job_id": f"job-{window_id}-{scenario}",
        "strategy_id": CANDIDATE,
        "window_id": window_id,
        "window_class": "monthly",
        "purpose": "development",
        "scenario": scenario,
        "rankable": closed_trades > 0,
        "closed_trades_total": closed_trades,
        "net_pnl_quote": net_pnl,
        "profit_factor": profit_factor,
        "max_drawdown_r": max_drawdown_r,
        "fee_adjusted_expectancy_r": expectancy_r,
        "data_quality_flags": [],
    }


def _paired_windows(
    count: int,
    *,
    baseline_net: float = 10.0,
    pessimistic_net: float = 5.0,
) -> list[dict]:
    records: list[dict] = []
    for idx in range(count):
        window_id = f"binance_1m_month_2022_{idx + 1:02d}"
        records.append(
            _record(
                window_id=window_id,
                scenario="baseline",
                net_pnl=baseline_net,
            )
        )
        records.append(
            _record(
                window_id=window_id,
                scenario="pessimistic_execution",
                net_pnl=pessimistic_net,
            )
        )
    return records


@pytest.fixture
def gate_contract() -> dict:
    return load_stage_a_gate_contract(CONTRACT_PATH)


def test_gate_contract_sha256_is_stable(gate_contract: dict) -> None:
    first = compute_gate_contract_sha256(gate_contract)
    second = compute_gate_contract_sha256(json.loads(CONTRACT_PATH.read_text()))
    assert first == second
    assert len(first) == 64


def test_survivor_when_paired_gates_pass(gate_contract: dict) -> None:
    records = _paired_windows(20, baseline_net=12.0, pessimistic_net=6.0)
    result = score_stage_a_candidate(
        candidate_id=CANDIDATE,
        records=records,
        development_window_ids=tuple(
            sorted({row["window_id"] for row in records})
        ),
        gate_contract=gate_contract,
    )
    assert result.status == STATUS_SURVIVOR
    assert result.gate_results["coverage"]["paired_evaluable_share"] >= 0.5
    assert result.gate_results["gates"]["G-E02"]["passed"] is True


def test_missing_pessimistic_pair_fails_closed(gate_contract: dict) -> None:
    records = _paired_windows(10, baseline_net=12.0, pessimistic_net=6.0)
    drop_window = records[0]["window_id"]
    records = [
        row
        for row in records
        if not (
            row["window_id"] == drop_window
            and row["scenario"] == "pessimistic_execution"
        )
    ]
    window_ids = tuple(sorted({row["window_id"] for row in records}))
    result = score_stage_a_candidate(
        candidate_id=CANDIDATE,
        records=records,
        development_window_ids=window_ids,
        gate_contract=gate_contract,
    )
    assert result.status in {STATUS_REJECTED, STATUS_INSUFFICIENT}
    assert result.gate_results["coverage"]["missing_pair_count"] >= 1


def test_missing_pessimistic_scenario_rejects_even_with_strong_baseline(
    gate_contract: dict,
) -> None:
    records = [
        _record(
            window_id=f"binance_1m_month_2021_{idx:02d}",
            scenario="baseline",
            net_pnl=50.0,
        )
        for idx in range(1, 21)
    ]
    window_ids = tuple(f"binance_1m_month_2021_{idx:02d}" for idx in range(1, 21))
    result = score_stage_a_candidate(
        candidate_id=CANDIDATE,
        records=records,
        development_window_ids=window_ids,
        gate_contract=gate_contract,
    )
    assert result.status == STATUS_INSUFFICIENT
    assert result.gate_results["coverage"]["paired_evaluable_share"] < 0.5


def test_separate_rankable_coverage_reported(gate_contract: dict) -> None:
    records = _paired_windows(15)
    records.append(
        _record(
            window_id="binance_1m_month_2099_01",
            scenario="baseline",
            net_pnl=1.0,
            closed_trades=0,
        )
    )
    records.append(
        _record(
            window_id="binance_1m_month_2099_01",
            scenario="pessimistic_execution",
            net_pnl=1.0,
            closed_trades=12,
        )
    )
    window_ids = tuple(sorted({row["window_id"] for row in records}))
    result = score_stage_a_candidate(
        candidate_id=CANDIDATE,
        records=records,
        development_window_ids=window_ids,
        gate_contract=gate_contract,
    )
    coverage = result.coverage
    assert "baseline_rankable_share" in coverage
    assert "pessimistic_rankable_share" in coverage
    assert coverage["baseline_rankable_share"] != coverage["pessimistic_rankable_share"]


def test_negative_pessimistic_median_rejects(gate_contract: dict) -> None:
    records = _paired_windows(20, baseline_net=20.0, pessimistic_net=-1.0)
    window_ids = tuple(sorted({row["window_id"] for row in records}))
    result = score_stage_a_candidate(
        candidate_id=CANDIDATE,
        records=records,
        development_window_ids=window_ids,
        gate_contract=gate_contract,
    )
    assert result.status == STATUS_REJECTED
    assert result.gate_results["gates"]["G-E02"]["passed"] is False
