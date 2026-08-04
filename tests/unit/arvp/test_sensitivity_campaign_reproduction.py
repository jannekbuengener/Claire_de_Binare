"""Reproduction contract unit tests (#4153).

test_id: tc_sensitivity_campaign_reproduction_001
test_type: schutz|bauteil
cdb_area: arvp/validation-research
issue_ref: #4153
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import pytest

from tools.arvp_vacation.sensitivity_campaign_reproduction import (
    SensitivityReproductionError,
    build_reproduction_plan,
    compare_reproduction_results,
)
from tools.arvp_vacation.sensitivity_campaign_run_plan import (
    DEFAULT_REPRODUCTION_POLICY,
)


def test_reproduction_adds_no_new_run_keys() -> None:
    keys = [f"rk-{i:03d}" for i in range(20)]
    plan = build_reproduction_plan(run_keys=keys, policy=DEFAULT_REPRODUCTION_POLICY)
    assert plan["enabled"] is True
    assert plan["adds_run_keys"] is False
    assert plan["max_run_count_unchanged"] is True
    assert plan["unique_run_key_count"] == 20
    for item in plan["reproduction_items"]:
        assert item["creates_new_run_key"] is False
        assert item["run_key"] in keys
    # baseline (1) + sample (5) with 1 attempt each
    assert len(plan["baseline_run_keys"]) == 1
    assert len(plan["sample_run_keys"]) == 5
    assert len(plan["reproduction_items"]) == 6


def test_reproduction_mismatch_blocks() -> None:
    fields = ["gate_reason", "trade_count", "net_pnl"]
    primary = {"gate_reason": "OK", "trade_count": 1, "net_pnl": "0"}
    reproduction = {"gate_reason": "OK", "trade_count": 2, "net_pnl": "0"}
    with pytest.raises(SensitivityReproductionError) as exc:
        compare_reproduction_results(
            primary=primary,
            reproduction=reproduction,
            compared_fields=fields,
        )
    assert "REPRO_MISMATCH:trade_count" in str(exc.value)


def test_reproduction_exact_match_ok() -> None:
    fields = ["gate_reason", "trade_count"]
    row = {"gate_reason": "OK", "trade_count": 0}
    compare_reproduction_results(
        primary=row, reproduction=dict(row), compared_fields=fields
    )


def test_disabled_reproduction_empty() -> None:
    plan = build_reproduction_plan(run_keys=["a"], policy={"enabled": False})
    assert plan["enabled"] is False
    assert plan["reproduction_items"] == []
    assert plan["adds_run_keys"] is False


def test_unsupported_comparison_mode() -> None:
    with pytest.raises(SensitivityReproductionError) as exc:
        build_reproduction_plan(
            run_keys=["a", "b"],
            policy={
                **DEFAULT_REPRODUCTION_POLICY,
                "comparison_mode": "approx",
            },
        )
    assert "REPRO_COMPARISON_MODE_UNSUPPORTED" in str(exc.value)
