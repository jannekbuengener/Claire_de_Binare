"""Analyzer contract unit tests (#4153).

test_id: tc_sensitivity_campaign_analyzer_001
test_type: schutz|bauteil
cdb_area: arvp/validation-research
issue_ref: #4153
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import pytest

from tools.arvp_vacation.sensitivity_campaign_analyzer_contract import (
    EXPECTED_OVERLAPS,
    EXPECTED_PHYSICAL_PARAMETER_SETS,
    SensitivityAnalyzerContractError,
    assert_results_bindings,
    classify_overlap_slots,
    effect_partition,
    ranking_weights_for_slots,
)
from tools.arvp_vacation.sensitivity_campaign_grid import EXPECTED_UNIQUE_VARIANTS


def test_overlap_classification_21_19_2() -> None:
    report = classify_overlap_slots()
    assert report["matrix_slots"] == EXPECTED_UNIQUE_VARIANTS == 21
    assert report["physical_parameter_sets"] == EXPECTED_PHYSICAL_PARAMETER_SETS == 19
    assert report["overlaps"] == EXPECTED_OVERLAPS == 2
    assert len(report["slots"]) == 21
    assert len(report["overlap_groups"]) == 2
    assert report["rules"]["no_double_weight_global_ranking"] is True
    assert report["rules"]["report_must_state_21_slots_19_sets_2_overlaps"] is True


def test_overlap_ranking_weights_sum_to_physical_sets() -> None:
    report = classify_overlap_slots()
    weights = ranking_weights_for_slots(report["slots"])
    assert len(weights) == 21
    # Each physical set contributes total weight 1.0.
    assert abs(sum(weights.values()) - 19.0) < 1e-9
    for group in report["overlap_groups"]:
        slot_ids = [s["slot_id"] for s in group["slots"]]
        share = sum(weights[sid] for sid in slot_ids)
        assert abs(share - 1.0) < 1e-9
        assert len(slot_ids) > 1


def test_effect_partition_phases() -> None:
    report = classify_overlap_slots()
    parts = effect_partition(report["slots"])
    assert parts["main_effect_slot_ids"]
    assert parts["interaction_effect_slot_ids"]
    assert set(parts["main_effect_slot_ids"]).isdisjoint(
        parts["interaction_effect_slot_ids"]
    )


def test_stale_results_block() -> None:
    keys = ["rk1", "rk2"]
    rows = [
        {
            "run_key": "rk1",
            "manifest_fingerprint": "a" * 64,
            "run_plan_fingerprint": "b" * 64,
            "authorization_fingerprint": "c" * 64,
        },
        {
            "run_key": "rk2",
            "manifest_fingerprint": "a" * 64,
            "run_plan_fingerprint": "STALE" + "b" * 59,
            "authorization_fingerprint": "c" * 64,
        },
    ]
    with pytest.raises(SensitivityAnalyzerContractError) as exc:
        assert_results_bindings(
            results=rows,
            manifest_fingerprint="a" * 64,
            run_plan_fingerprint="b" * 64,
            authorization_fingerprint="c" * 64,
            expected_run_keys=keys,
        )
    assert "ANALYZER_STALE_OR_FOREIGN_RESULT" in str(exc.value)


def test_results_bindings_happy() -> None:
    keys = ["rk1"]
    rows = [
        {
            "run_key": "rk1",
            "manifest_fingerprint": "a" * 64,
            "run_plan_fingerprint": "b" * 64,
            "authorization_fingerprint": "c" * 64,
        }
    ]
    assert_results_bindings(
        results=rows,
        manifest_fingerprint="a" * 64,
        run_plan_fingerprint="b" * 64,
        authorization_fingerprint="c" * 64,
        expected_run_keys=keys,
    )
