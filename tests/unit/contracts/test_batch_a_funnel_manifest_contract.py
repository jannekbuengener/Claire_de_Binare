"""Contract tests for Batch-A funnel manifest (#4031 slice 2a)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.replay.batch_a_strategy_registry import (
    ALREADY_TESTED_STRATEGY_IDS,
    BATCH_A_STRATEGY_REGISTRY,
    ImplementationStatus,
    assert_batch_a_executable,
    batch_a_strategy_ids,
    executable_batch_a_strategy_ids,
    pending_batch_a_strategy_ids,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = REPO_ROOT / "docs/contracts/batch_a_funnel_manifest.v1.json"
RMR_EVIDENCE = REPO_ROOT / (
    "docs/evidence/profitability_candidate_range_mean_reversion_v1_3157.json"
)
MOMENTUM_EVIDENCE = REPO_ROOT / (
    "docs/evidence/profitability_candidate_momentum_capture_v1_3166.json"
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]


@pytest.fixture
def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_manifest_has_exactly_ten_unique_strategy_ids(manifest: dict) -> None:
    ids = [row["strategy_id"] for row in manifest["candidates"]]
    assert len(ids) == 10
    assert len(set(ids)) == 10


def test_manifest_excludes_already_tested_3990_strategies(manifest: dict) -> None:
    ids = {row["strategy_id"] for row in manifest["candidates"]}
    assert ids.isdisjoint(ALREADY_TESTED_STRATEGY_IDS)


def test_trend_regime_gated_ma_cross_not_in_batch(manifest: dict) -> None:
    ids = {row["strategy_id"] for row in manifest["candidates"]}
    assert "trend_regime_gated_ma_cross_v1" not in ids


def test_atr_expansion_v1_is_in_batch(manifest: dict) -> None:
    ids = {row["strategy_id"] for row in manifest["candidates"]}
    assert "atr_expansion_v1" in ids


def test_rmr_and_momentum_frozen_parameters_match_evidence(manifest: dict) -> None:
    by_id = {row["strategy_id"]: row for row in manifest["candidates"]}
    rmr_evidence = json.loads(RMR_EVIDENCE.read_text(encoding="utf-8"))
    mom_evidence = json.loads(MOMENTUM_EVIDENCE.read_text(encoding="utf-8"))

    rmr_params = by_id["range_mean_reversion_v1"]["frozen_parameters"]
    for key, value in rmr_evidence["parameter_set"].items():
        assert rmr_params[key] == value

    mom_params = by_id["momentum_capture_v1"]["frozen_parameters"]
    for key, value in mom_evidence["parameter_set"].items():
        if key in mom_params:
            assert mom_params[key] == value
    assert mom_params["directional_candle_atr_multiple"] == 1.0
    assert mom_params["max_hold_bars"] == 240


def test_manifest_lr_and_ranking_boundaries(manifest: dict) -> None:
    assert manifest["lr_status"] == "NO-GO"
    assert manifest["ranking_ready"] is False
    assert manifest["evidence_class"] == "historical_cross_venue_research"


def test_registry_matches_manifest_strategy_ids(manifest: dict) -> None:
    manifest_ids = {row["strategy_id"] for row in manifest["candidates"]}
    assert set(batch_a_strategy_ids()) == manifest_ids


def test_all_ten_runners_executable() -> None:
    assert len(executable_batch_a_strategy_ids()) == 10
    assert pending_batch_a_strategy_ids() == frozenset()
    for strategy_id in batch_a_strategy_ids():
        record = assert_batch_a_executable(strategy_id)
        assert record.runner_module is not None


def test_pending_candidates_not_executable() -> None:
    for strategy_id in pending_batch_a_strategy_ids():
        record = BATCH_A_STRATEGY_REGISTRY[strategy_id]
        assert record.implementation_status == ImplementationStatus.IMPLEMENTATION_PENDING
        assert not record.executable
