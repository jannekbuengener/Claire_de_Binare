"""Contract tests for the docs-only Batch-B readiness lock (#4069)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = REPO_ROOT / "docs/contracts/batch_b_funnel_manifest.v1.json"

pytestmark = [pytest.mark.unit, pytest.mark.contract]

EXPECTED_IDS = {
    "hh_hl_continuation_v1",
    "rsi_momentum_v1",
    "high_vol_avoidance_v1",
    "range_bound_reversion_v1",
    "mtf_1m_entry_5m_trend_v1",
}


@pytest.fixture
def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_manifest_locks_exactly_five_unique_candidates(manifest: dict) -> None:
    ids = [row["strategy_id"] for row in manifest["candidates"]]
    assert len(ids) == 5
    assert len(set(ids)) == 5
    assert set(ids) == EXPECTED_IDS


def test_lock_is_docs_only_and_fail_closed(manifest: dict) -> None:
    assert manifest["lock_status"] == "BATCH_B_LOCKED"
    assert manifest["execution_authorized"] is False
    assert manifest["campaign_authorized"] is False
    assert manifest["implementation_authorized"] is True
    assert manifest["implementation_scope"] == ["hh_hl_continuation_v1"]
    assert manifest["implementation_go_comment_id"] == "5196985942"
    assert (
        manifest["implementation_go_main_sha"]
        == "279b7100df899276a92386ee83161734811e9e7c"
    )
    assert manifest["ranking_ready"] is False
    assert manifest["lr_status"] == "NO-GO"
    assert manifest["next_gate"] == (
        "BATCH_B_REMAINING_CANDIDATE_IMPLEMENTATION_OR_STAGE_A_GO"
    )


def test_stage_a_plan_arithmetic_is_consistent(manifest: dict) -> None:
    plan = manifest["stage_a_plan"]
    assert plan["status"] == "planned_not_authorized"
    assert plan["candidate_count"] == len(manifest["candidates"])
    assert plan["planned_scenario_runs"] == (
        plan["candidate_count"] * plan["window_count"] * plan["scenario_count"]
    )
    assert plan["planned_scenario_runs"] == 390


def test_development_selection_reuses_locked_monthly_window_set(manifest: dict) -> None:
    selection = manifest["development_selection"]
    assert selection["window_count"] == 39
    assert selection["overlap_class"] == "monthly"
    assert selection["purpose"] == "development"
    assert (
        selection["selection_sha256"]
        == "3e9ed68736b51fecb299d228c856be80a597cb1dc72fcba595453b856b58bd52"
    )


def test_unimplemented_candidates_still_require_spec(manifest: dict) -> None:
    by_id = {row["strategy_id"]: row for row in manifest["candidates"]}
    hh = by_id["hh_hl_continuation_v1"]
    assert hh["implementation_status"] == "implemented"
    assert hh["runner_module"] == (
        "services.validation.hh_hl_continuation_backtest_runner"
    )
    assert hh["parameter_source"].endswith("arvp_hh_hl_continuation_v1_spec_4372.md")
    for strategy_id in EXPECTED_IDS - {"hh_hl_continuation_v1"}:
        candidate = by_id[strategy_id]
        assert candidate["implementation_status"] == "spec_required"
        assert candidate["runner_module"] is None
        assert candidate["hypothesis_boundary"]
        assert candidate["dedupe_boundary"]
        assert candidate["lookahead_guard"]


def test_mean_reversion_lane_excludes_bollinger_near_duplicate(
    manifest: dict,
) -> None:
    resolutions = {
        row["strategy_id"]: row["decision"]
        for row in manifest["dedupe_resolutions"]
    }
    assert resolutions["bollinger_mean_reversion_v1"] == "EXCLUDED_NEAR_DUPLICATE"
    assert "range_bound_reversion_v1" in EXPECTED_IDS


def test_mtf_lane_is_single_and_closed_bar_only(manifest: dict) -> None:
    by_id = {row["strategy_id"]: row for row in manifest["candidates"]}
    mtf = by_id["mtf_1m_entry_5m_trend_v1"]
    assert "fully closed 5m aggregates" in mtf["lookahead_guard"]
    assert "htf_bias_ltf_trigger_v1" not in EXPECTED_IDS


def test_filter_lane_makes_no_alpha_entry_claim(manifest: dict) -> None:
    by_id = {row["strategy_id"]: row for row in manifest["candidates"]}
    high_vol = by_id["high_vol_avoidance_v1"]
    assert high_vol["family"] == "volatility_filter"
    assert "does not generate an alpha entry" in high_vol["hypothesis_boundary"]


def test_batch_a_and_3990_candidates_are_disjoint(manifest: dict) -> None:
    locked = EXPECTED_IDS
    hard = manifest["hard_exclusions"]
    assert locked.isdisjoint(hard["batch_a_strategy_ids"])
    assert locked.isdisjoint(hard["campaign_3990_strategy_ids"])
