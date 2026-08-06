"""Unit/contract tests for campaign profile + hh_hl planning-only prep (#4374).

test_id: tc_hh_hl_campaign_prep_001
test_type: Bauteil-Test / Schutz-Test
cdb_area: arvp_campaign
issue_ref: #4374
live_relevant: false
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.arvp_vacation.campaign_executor_providers import (
    HhHlSingleRunReplayProvider,
    PlanningOnlyExecutor,
    resolve_campaign_executor,
)
from tools.arvp_vacation.campaign_profile import (
    HH_HL_PREP_PROFILE_ID,
    LEGACY_4153_PROFILE_ID,
    CampaignProfileError,
    assert_execution_allowed,
    assert_profile_manifest_bind,
    load_profile,
    profile_from_mapping,
)
from tools.arvp_vacation.hh_hl_campaign_analyzer import (
    build_hh_hl_analyzer_profile,
    classify_fixture_completeness,
)
from tools.arvp_vacation.hh_hl_campaign_dataset import (
    HhHlDatasetBindingError,
    build_dataset_binding_receipt,
)
from tools.arvp_vacation.hh_hl_campaign_grid import (
    expand_hh_hl_variants,
    grid_draft_report,
)
from tools.arvp_vacation.hh_hl_campaign_manifest import build_hh_hl_draft_manifest
from tools.arvp_vacation.hh_hl_campaign_plan import dry_plan
from tools.arvp_vacation.hh_hl_campaign_reproduction import (
    HhHlReproductionPlanError,
    build_hh_hl_reproduction_plan,
)
from tools.arvp_vacation.hh_hl_campaign_run_plan import build_hh_hl_run_plan
from tools.arvp_vacation.sensitivity_campaign_executor import RunEnvelope
from tools.arvp_vacation.sensitivity_campaign_grid import (
    EXPECTED_RUN_COUNT,
    EXPECTED_UNIQUE_VARIANTS,
    expand_variants,
)
from tools.arvp_vacation.sensitivity_campaign_run_plan import build_run_plan
from tools.arvp_vacation.sensitivity_experiment_manifest import (
    fingerprint_manifest,
    load_manifest,
    validate_manifest,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LEGACY_MANIFEST = PROJECT_ROOT / "config" / "arvp" / "sensitivity_campaign_4153_v1.json"


def _envelope(**overrides):
    base = {
        "run_key": "rk",
        "campaign_id": "c",
        "manifest_fingerprint": "m" * 64,
        "execution_sha": "a" * 40,
        "window_id": "binance_1m_month_2017_10",
        "strategy_id": "hh_hl_continuation_v1",
        "parameters": {
            "swing_left_bars": 2,
            "swing_right_bars": 2,
            "min_minutes_between_entries": 60,
            "trade_side_mode": "long_only",
        },
        "slot_id": "hh_hl_baseline_001",
        "phase": "BASELINE",
        "label": "spec_frozen_baseline",
        "physical_parameter_set_fingerprint": "p" * 64,
        "effective_config_fingerprint": "e" * 64,
        "dataset_content_fingerprint": "d" * 64,
        "seed": "s",
        "output_dir": "/tmp/out",
        "run_plan_fingerprint": "r" * 64,
        "authorization_fingerprint": "x" * 64,
    }
    base.update(overrides)
    return RunEnvelope(**base)


@pytest.mark.unit
def test_legacy_4153_profile_loads_and_matches_identity():
    profile = load_profile(LEGACY_4153_PROFILE_ID)
    assert profile.issue_number == 4153
    assert profile.strategy_id == "primary_breakout_v1"
    assert profile.evidence_namespace == "artifacts/arvp_sensitivity/4153"
    assert profile.execution_enabled is True


@pytest.mark.unit
def test_hh_hl_profile_is_planning_only():
    profile = load_profile(HH_HL_PREP_PROFILE_ID)
    assert profile.planning_enabled is True
    assert profile.execution_enabled is False
    assert profile.campaign_authorized is False
    assert profile.lr_status == "NO-GO"
    assert profile.strategy_id == "hh_hl_continuation_v1"
    with pytest.raises(CampaignProfileError, match="PLANNING_ONLY_EXECUTE_FORBIDDEN"):
        assert_execution_allowed(profile)


@pytest.mark.unit
def test_unknown_profile_fail_closed(tmp_path: Path):
    payload = load_profile(HH_HL_PREP_PROFILE_ID).as_dict()
    payload["profile_id"] = "not_a_real_profile"
    path = tmp_path / "not_a_real_profile.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CampaignProfileError, match="UNKNOWN_CAMPAIGN_PROFILE"):
        load_profile("not_a_real_profile", profiles_dir=tmp_path)


@pytest.mark.unit
def test_profile_manifest_and_issue_mismatch_fail_closed():
    profile = load_profile(HH_HL_PREP_PROFILE_ID)
    with pytest.raises(CampaignProfileError, match="PROFILE_ISSUE_MISMATCH"):
        assert_profile_manifest_bind(profile, issue_number=4153)
    with pytest.raises(CampaignProfileError, match="PROFILE_STRATEGY_MISMATCH"):
        assert_profile_manifest_bind(profile, strategy_id="primary_breakout_v1")
    with pytest.raises(CampaignProfileError, match="PROFILE_ADAPTER_MISMATCH"):
        assert_profile_manifest_bind(profile, adapter_id="primary_breakout_runner_v1")


@pytest.mark.unit
def test_wrong_strategy_in_profile_payload_fail_closed():
    payload = load_profile(HH_HL_PREP_PROFILE_ID).as_dict()
    payload["strategy_id"] = "primary_breakout_v1"
    with pytest.raises(CampaignProfileError, match="PROFILE_STRATEGY_MISMATCH"):
        profile_from_mapping(payload)


@pytest.mark.unit
def test_hh_hl_grid_baseline_only_deterministic():
    a = expand_hh_hl_variants()
    b = expand_hh_hl_variants()
    assert len(a) == 1
    assert a[0].as_dict() == b[0].as_dict()
    report = grid_draft_report()
    assert report["status"] == "HOLD_CAMPAIGN_GRID_OWNER_RATIFICATION_REQUIRED"
    assert report["executable_manifest_allowed"] is False
    assert "copy_4153_21_slot_grid" in report["forbidden_variants"]


@pytest.mark.unit
def test_hh_hl_run_plan_count_and_byte_identical():
    manifest = build_hh_hl_draft_manifest()
    plan1 = build_hh_hl_run_plan(manifest=manifest, planning_sha="a" * 40)
    plan2 = build_hh_hl_run_plan(manifest=manifest, planning_sha="a" * 40)
    assert plan1.expected_run_count == 39 * 1
    assert plan1.expected_run_count == plan1.window_count * plan1.variant_count
    assert len(set(plan1.run_keys)) == plan1.expected_run_count
    assert plan1.as_dict() == plan2.as_dict()
    assert plan1.campaign_execution_authorized is False
    assert plan1.executable is False
    assert plan1.execution_sha is None


@pytest.mark.unit
def test_dry_plan_write_free_and_no_replays():
    payload = dry_plan(repo_root=PROJECT_ROOT)
    assert payload["writes"] is False
    assert payload["replays"] is False
    assert payload["campaign_execution_authorized"] is False
    assert payload["strategy_id"] == "hh_hl_continuation_v1"
    assert payload["expected_run_count"] == 39
    assert payload["execution_sha"] is None
    assert "PLANNING_ONLY_EXECUTE_FORBIDDEN" in payload["execute_probe"]


@pytest.mark.unit
def test_dataset_missing_and_foreign_windows_block():
    receipt = build_dataset_binding_receipt()
    assert receipt.local_proof_required is True
    with pytest.raises(HhHlDatasetBindingError, match="MISSING_WINDOWS"):
        build_dataset_binding_receipt(window_ids=receipt.ordered_window_ids[:-1])
    with pytest.raises(HhHlDatasetBindingError, match="FOREIGN_WINDOWS"):
        build_dataset_binding_receipt(
            window_ids=list(receipt.ordered_window_ids) + ["binance_1m_month_2099_01"]
        )


@pytest.mark.unit
def test_dataset_content_fingerprint_mismatch_blocks():
    receipt = build_dataset_binding_receipt()
    bad = {wid: "0" * 64 for wid in receipt.ordered_window_ids}
    bad[receipt.ordered_window_ids[0]] = "1" * 63  # invalid length
    with pytest.raises(HhHlDatasetBindingError, match="INVALID_CONTENT_FP"):
        build_dataset_binding_receipt(content_fingerprints_by_window=bad)
    fps = {wid: "a" * 64 for wid in receipt.ordered_window_ids}
    fps["foreign_window"] = "b" * 64
    with pytest.raises(HhHlDatasetBindingError, match="FOREIGN_CONTENT_FPS"):
        build_dataset_binding_receipt(content_fingerprints_by_window=fps)


@pytest.mark.unit
def test_executor_hh_hl_provider_no_pb1_or_scenario_fallback():
    profile = load_profile(HH_HL_PREP_PROFILE_ID)
    executor = resolve_campaign_executor(profile)
    assert isinstance(executor, PlanningOnlyExecutor)
    with pytest.raises(CampaignProfileError, match="PLANNING_ONLY_EXECUTE_FORBIDDEN"):
        executor.execute(_envelope())

    # Force provider object for wiring checks without enabling execution.
    provider = HhHlSingleRunReplayProvider(profile)
    req = provider.build_single_run_request(_envelope())
    assert req["scenario_group_id"] is None
    assert req["adapter_id"] == "batch_b_shadow_runner_v1"
    with pytest.raises(CampaignProfileError, match="HH_HL_ENVELOPE_STRATEGY_MISMATCH"):
        provider.build_single_run_request(_envelope(strategy_id="primary_breakout_v1"))
    with pytest.raises(CampaignProfileError, match="HH_HL_SCENARIO_GROUP_FORBIDDEN"):
        provider.build_single_run_request(
            _envelope(parameters={"scenario_group_id": "x", "swing_left_bars": 2})
        )


@pytest.mark.unit
def test_reproduction_deterministic_and_bindings():
    keys = [f"k{i:02d}" for i in range(10)]
    a = build_hh_hl_reproduction_plan(keys)
    b = build_hh_hl_reproduction_plan(keys)
    assert a == b
    assert a["baseline_keys"]
    assert a["policy"]["comparison_mode"] == "exact_equality"
    with pytest.raises(HhHlReproductionPlanError, match="VOLATILE_FIELD"):
        build_hh_hl_reproduction_plan(
            keys,
            policy={
                **a["policy"],
                "compared_result_fields": ["net_pnl_quote", "pid"],
            },
        )


@pytest.mark.unit
def test_analyzer_fixture_blocks_missing_foreign_and_no_4153_matrix():
    manifest = build_hh_hl_draft_manifest()
    plan = build_hh_hl_run_plan(manifest=manifest, planning_sha="b" * 40)
    profile = build_hh_hl_analyzer_profile(expected_run_keys=plan.run_keys)
    assert profile["matrix_assumptions"]["slots_21"] is False
    assert profile["variant_count"] != 21

    blocked_missing = classify_fixture_completeness(
        expected_run_keys=plan.run_keys,
        present_run_keys=plan.run_keys[1:],
        reproduction_pass=True,
    )
    assert blocked_missing["classification"] == "BLOCKED"

    blocked_foreign = classify_fixture_completeness(
        expected_run_keys=plan.run_keys,
        present_run_keys=list(plan.run_keys) + ["foreign"],
        reproduction_pass=True,
    )
    assert blocked_foreign["classification"] == "BLOCKED"

    blocked_repro = classify_fixture_completeness(
        expected_run_keys=plan.run_keys,
        present_run_keys=plan.run_keys,
        reproduction_pass=False,
    )
    assert blocked_repro["classification"] == "BLOCKED"

    ok = classify_fixture_completeness(
        expected_run_keys=plan.run_keys,
        present_run_keys=plan.run_keys,
        reproduction_pass=True,
    )
    assert ok["classification"] == "INCONCLUSIVE"


@pytest.mark.unit
def test_safety_bans_and_no_4153_identity_in_hh_hl_manifest():
    manifest = build_hh_hl_draft_manifest()
    assert manifest["campaign_execution_authorized"] is False
    assert manifest["lr_status"] == "NO-GO"
    assert "4153" not in manifest["manifest_path"]
    assert "4153" not in manifest["evidence_namespace"]
    assert manifest["stage_b"] is False
    assert manifest["oos"] is False
    assert manifest["stress"] is False
    assert manifest["paper"] is False
    assert manifest["live"] is False
    assert manifest["echtgeld"] is False
    bans = manifest["absolute_bans"]
    for key in (
        "stage_b",
        "oos",
        "stress",
        "paper",
        "live",
        "echtgeld",
        "promotion",
        "orders",
        "exchange_execution",
    ):
        assert bans[key] is False


@pytest.mark.unit
def test_regression_4153_grid_and_manifest_unchanged():
    variants = expand_variants()
    assert len(variants) == EXPECTED_UNIQUE_VARIANTS == 21
    manifest = load_manifest(LEGACY_MANIFEST)
    validate_manifest(manifest)
    fp = fingerprint_manifest(manifest)
    assert fp == manifest["manifest_fingerprint"]
    plan = build_run_plan(manifest, main_sha="c" * 40)
    assert plan.run_count == EXPECTED_RUN_COUNT == 819
    assert len(plan.run_keys) == 819
    assert plan.evidence_namespace == "artifacts/arvp_sensitivity/4153"
    assert plan.strategy_id == "primary_breakout_v1"
