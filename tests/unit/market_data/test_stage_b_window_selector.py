"""Tests for Batch-A Stage-B window selector (#4032)."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from tools.market_data.development_window_selector import (
    LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS,
    load_window_bank_manifest,
)
from tools.market_data.stage_b_window_selector import (
    EXPECTED_MONTHLY_OOS,
    EXPECTED_MONTHLY_VALIDATION,
    EXPECTED_STAGE_B_TOTAL,
    EXPECTED_STRESS,
    StageBSelectionError,
    compute_stage_b_selection_sha256,
    select_batch_a_stage_b_windows,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = (
    REPO_ROOT
    / "artifacts/market_data/window_bank/binance/spot/BTCUSDT/1m/"
    "window_bank_manifest.json"
)


def _synthetic_stage_b_manifest() -> dict:
    windows: list[dict] = []
    for idx in range(EXPECTED_MONTHLY_VALIDATION):
        windows.append(
            {
                "window_id": f"binance_1m_month_val_{idx:02d}",
                "purpose": "validation",
                "overlap_class": "monthly",
                "start_ts_ms": idx * 1000,
                "end_ts_ms": idx * 1000 + 500,
            }
        )
    for idx in range(6):
        windows.append(
            {
                "window_id": f"binance_1m_quarter_val_{idx}",
                "purpose": "validation",
                "overlap_class": "quarterly",
                "start_ts_ms": idx * 2000,
                "end_ts_ms": idx * 2000 + 500,
            }
        )
    for idx in range(2):
        windows.append(
            {
                "window_id": f"binance_1m_year_val_{idx}",
                "purpose": "validation",
                "overlap_class": "yearly",
                "start_ts_ms": idx * 3000,
                "end_ts_ms": idx * 3000 + 500,
            }
        )
    for idx in range(EXPECTED_MONTHLY_OOS):
        windows.append(
            {
                "window_id": f"binance_1m_month_oos_{idx:02d}",
                "purpose": "out_of_sample",
                "overlap_class": "monthly",
                "start_ts_ms": idx * 4000,
                "end_ts_ms": idx * 4000 + 500,
            }
        )
    for idx in range(7):
        windows.append(
            {
                "window_id": f"binance_1m_quarter_oos_{idx}",
                "purpose": "out_of_sample",
                "overlap_class": "quarterly",
                "start_ts_ms": idx * 5000,
                "end_ts_ms": idx * 5000 + 500,
            }
        )
    for idx in range(EXPECTED_STRESS):
        windows.append(
            {
                "window_id": f"binance_1m_stress_{idx}",
                "purpose": "stress",
                "overlap_class": "stress",
                "start_ts_ms": idx * 6000,
                "end_ts_ms": idx * 6000 + 500,
            }
        )
    for wid in LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS:
        windows.append(
            {
                "window_id": wid,
                "purpose": "development",
                "overlap_class": "monthly",
                "start_ts_ms": 1,
                "end_ts_ms": 2,
            }
        )
    return {"venue": "binance", "windows": windows}


@pytest.fixture
def live_manifest() -> dict | None:
    if not MANIFEST_PATH.exists():
        return None
    return load_window_bank_manifest(MANIFEST_PATH)


def test_synthetic_manifest_selects_62_with_monthly_splits() -> None:
    result = select_batch_a_stage_b_windows(_synthetic_stage_b_manifest())
    assert result.window_count == EXPECTED_STAGE_B_TOTAL
    assert result.monthly_validation_count == EXPECTED_MONTHLY_VALIDATION
    assert result.monthly_out_of_sample_count == EXPECTED_MONTHLY_OOS
    assert result.stress_count == EXPECTED_STRESS
    assert result.quarterly_count == 13
    assert result.yearly_count == 2


def test_selection_hash_reproducible_on_reordered_input() -> None:
    manifest = _synthetic_stage_b_manifest()
    shuffled = copy.deepcopy(manifest)
    shuffled["windows"] = list(reversed(shuffled["windows"]))
    first = select_batch_a_stage_b_windows(manifest)
    second = select_batch_a_stage_b_windows(shuffled)
    assert first.window_ids == second.window_ids
    assert first.selection_sha256 == second.selection_sha256


def test_compute_hash_stable_for_locked_selection() -> None:
    manifest = _synthetic_stage_b_manifest()
    result = select_batch_a_stage_b_windows(manifest)
    digest = compute_stage_b_selection_sha256(
        result.window_ids,
        purpose_counts=result.purpose_counts,
        overlap_class_counts=result.overlap_class_counts,
    )
    assert digest == result.selection_sha256


def test_rejects_overlap_with_development_windows() -> None:
    manifest = _synthetic_stage_b_manifest()
    dev_id = LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS[0]
    for window in manifest["windows"]:
        if window["window_id"] == dev_id:
            window["purpose"] = "validation"
            break
    with pytest.raises(StageBSelectionError, match="overlaps development"):
        select_batch_a_stage_b_windows(manifest)


@pytest.mark.skipif(not MANIFEST_PATH.exists(), reason="live manifest unavailable")
def test_live_manifest_counts_62(live_manifest: dict | None) -> None:
    assert live_manifest is not None
    result = select_batch_a_stage_b_windows(live_manifest)
    assert result.window_count == 62
    assert result.monthly_validation_count == 27
    assert result.monthly_out_of_sample_count == 15
    assert result.stress_count == 5
