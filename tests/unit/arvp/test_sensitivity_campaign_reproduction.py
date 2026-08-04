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
    assert len(plan["baseline_run_keys"]) == 1
    assert len(plan["sample_run_keys"]) == 5
    assert len(plan["reproduction_items"]) == 6


def test_reproduction_deterministic_selection_fingerprint() -> None:
    """Two plan builds with identical inputs produce identical plans and fingerprints."""
    keys = [f"rk-{i:03d}" for i in range(50)]
    plan_a = build_reproduction_plan(run_keys=keys, policy=DEFAULT_REPRODUCTION_POLICY)
    plan_b = build_reproduction_plan(
        run_keys=list(keys), policy=DEFAULT_REPRODUCTION_POLICY
    )
    assert (
        plan_a["reproduction_plan_fingerprint"]
        == plan_b["reproduction_plan_fingerprint"]
    )
    assert plan_a["baseline_run_keys"] == plan_b["baseline_run_keys"]
    assert plan_a["sample_run_keys"] == plan_b["sample_run_keys"]


def test_reproduction_mismatch_returns_structured_dict() -> None:
    """Mismatch returns status/reason_code — no raise on the compare call."""
    fields = ["gate_reason", "trade_count", "net_pnl"]
    primary = {"gate_reason": "OK", "trade_count": 1, "net_pnl": "0"}
    reproduction = {"gate_reason": "OK", "trade_count": 2, "net_pnl": "0"}
    result = compare_reproduction_results(
        primary=primary,
        reproduction=reproduction,
        compared_fields=fields,
    )
    assert result["status"] == "MISMATCH"
    assert result["reason_code"] == "REPRODUCTION_RESULT_MISMATCH"
    assert (
        result["primary_result_fingerprint"]
        != result["reproduction_result_fingerprint"]
    )
    assert any(
        item["field"] == "trade_count" and item["reason_code"] == "REPRO_MISMATCH"
        for item in result["mismatched_fields"]
    )
    assert result["comparison_fingerprint"]


def test_reproduction_exact_match_returns_pass() -> None:
    fields = ["gate_reason", "trade_count"]
    row = {"gate_reason": "OK", "trade_count": 0}
    result = compare_reproduction_results(
        primary=row, reproduction=dict(row), compared_fields=fields
    )
    assert result["status"] == "PASS"
    assert result["reason_code"] == "REPRODUCTION_RESULT_PASS"
    assert result["mismatched_fields"] == []
    assert (
        result["primary_result_fingerprint"]
        == result["reproduction_result_fingerprint"]
    )


def test_reproduction_volatile_field_forbidden() -> None:
    fields = ["gate_reason", "started_at_utc"]
    row = {"gate_reason": "OK", "started_at_utc": "2026-01-01T00:00:00Z"}
    with pytest.raises(SensitivityReproductionError) as exc:
        compare_reproduction_results(
            primary=row, reproduction=dict(row), compared_fields=fields
        )
    assert "REPRO_COMPARED_FIELD_FORBIDDEN:started_at_utc" in str(exc.value)


def test_reproduction_bindings_mismatch_raises() -> None:
    """Bindings validation raises when primary/reproduction disagree on a bound key."""
    fields = ["gate_reason"]
    primary = {
        "gate_reason": "OK",
        "run_key": "rk-000",
        "manifest_fingerprint": "aaa",
        "run_plan_fingerprint": "bbb",
        "authorization_fingerprint": "ccc",
    }
    reproduction = {
        "gate_reason": "OK",
        "run_key": "rk-999",  # different
        "manifest_fingerprint": "aaa",
        "run_plan_fingerprint": "bbb",
        "authorization_fingerprint": "ccc",
    }
    with pytest.raises(SensitivityReproductionError) as exc:
        compare_reproduction_results(
            primary=primary,
            reproduction=reproduction,
            compared_fields=fields,
            bindings=True,
        )
    assert "REPRO_BINDING_MISMATCH:run_key" in str(exc.value)


def test_reproduction_bindings_match_pass() -> None:
    fields = ["gate_reason"]
    payload = {
        "gate_reason": "OK",
        "run_key": "rk-000",
        "manifest_fingerprint": "aaa",
        "run_plan_fingerprint": "bbb",
        "authorization_fingerprint": "ccc",
    }
    result = compare_reproduction_results(
        primary=payload,
        reproduction=dict(payload),
        compared_fields=fields,
        bindings=True,
    )
    assert result["status"] == "PASS"


def test_reproduction_empty_compared_fields_raises() -> None:
    with pytest.raises(SensitivityReproductionError) as exc:
        compare_reproduction_results(
            primary={},
            reproduction={},
            compared_fields=[],
        )
    assert "REPRO_COMPARED_FIELDS_EMPTY" in str(exc.value)


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
