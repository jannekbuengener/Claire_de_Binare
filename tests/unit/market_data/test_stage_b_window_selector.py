"""Tests for Batch-A Stage-B window selector (#4032)."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from tools.market_data.development_window_selector import (
    LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS,
)
from tools.market_data.stage_b_window_selector import (
    EXPECTED_MONTHLY_OOS,
    EXPECTED_MONTHLY_VALIDATION,
    EXPECTED_OUT_OF_SAMPLE,
    EXPECTED_STAGE_B_TOTAL,
    EXPECTED_STRESS,
    EXPECTED_VALIDATION,
    LOCKED_STAGE_B_SELECTION_SHA256,
    StageBSelectionError,
    compute_stage_b_selection_sha256,
    load_stage_b_manifest,
    select_batch_a_stage_b_windows,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
MAIN_MANIFEST = (
    REPO_ROOT.parent
    / "Claire_de_Binare"
    / "artifacts/market_data/window_bank/binance/spot/BTCUSDT/1m/"
    "window_bank_manifest.json"
)
LOCAL_MANIFEST = (
    REPO_ROOT
    / "artifacts/market_data/window_bank/binance/spot/BTCUSDT/1m/"
    "window_bank_manifest.json"
)


def _manifest_path() -> Path | None:
    if LOCAL_MANIFEST.exists():
        return LOCAL_MANIFEST
    if MAIN_MANIFEST.exists():
        return MAIN_MANIFEST
    return None


@pytest.fixture
def live_manifest() -> dict:
    path = _manifest_path()
    if path is None:
        pytest.skip("Binance window bank manifest not available")
    return load_stage_b_manifest(manifest_path=path, repo_root=path.parents[7])


def _synthetic_stage_b_manifest() -> dict:
    windows: list[dict[str, object]] = []
    for idx in range(EXPECTED_MONTHLY_VALIDATION):
        windows.append(
            {
                "window_id": f"binance_1m_val_month_{idx:02d}",
                "purpose": "validation",
                "overlap_class": "monthly",
            }
        )
    for idx in range(8):
        windows.append(
            {
                "window_id": f"binance_1m_val_q_{idx}",
                "purpose": "validation",
                "overlap_class": "quarterly",
            }
        )
    for idx in range(2):
        windows.append(
            {
                "window_id": f"binance_1m_val_y_{idx}",
                "purpose": "validation",
                "overlap_class": "yearly",
            }
        )
    for idx in range(EXPECTED_MONTHLY_OOS):
        windows.append(
            {
                "window_id": f"binance_1m_oos_month_{idx:02d}",
                "purpose": "out_of_sample",
                "overlap_class": "monthly",
            }
        )
    for idx in range(5):
        windows.append(
            {
                "window_id": f"binance_1m_oos_q_{idx}",
                "purpose": "out_of_sample",
                "overlap_class": "quarterly",
            }
        )
    for idx in range(EXPECTED_STRESS):
        windows.append(
            {
                "window_id": f"binance_1m_stress_{idx}",
                "purpose": "stress",
                "overlap_class": "stress",
            }
        )
    for wid in LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS:
        windows.append(
            {
                "window_id": wid,
                "purpose": "development",
                "overlap_class": "monthly",
            }
        )
    return {"venue": "binance", "windows": windows}


def test_synthetic_selects_62_stage_b_windows() -> None:
    result = select_batch_a_stage_b_windows(_synthetic_stage_b_manifest())
    assert result.window_count == EXPECTED_STAGE_B_TOTAL
    assert result.purpose_counts["validation"] == EXPECTED_VALIDATION
    assert result.purpose_counts["out_of_sample"] == EXPECTED_OUT_OF_SAMPLE
    assert result.purpose_counts["stress"] == EXPECTED_STRESS
    assert result.monthly_validation_count == EXPECTED_MONTHLY_VALIDATION
    assert result.monthly_out_of_sample_count == EXPECTED_MONTHLY_OOS


def test_rejects_development_window_id_in_stage_b_purpose() -> None:
    manifest = _synthetic_stage_b_manifest()
    manifest["windows"].append(
        {
            "window_id": LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS[0],
            "purpose": "validation",
            "overlap_class": "monthly",
        }
    )
    with pytest.raises(StageBSelectionError, match="overlaps development lock"):
        select_batch_a_stage_b_windows(manifest)


def test_selection_hash_reproducible_on_reordered_input() -> None:
    manifest = _synthetic_stage_b_manifest()
    shuffled = copy.deepcopy(manifest)
    shuffled["windows"] = list(reversed(shuffled["windows"]))
    first = select_batch_a_stage_b_windows(manifest)
    second = select_batch_a_stage_b_windows(shuffled)
    assert first.window_ids == second.window_ids
    assert first.selection_sha256 == second.selection_sha256


def test_compute_hash_stable_for_window_ids() -> None:
    manifest = _synthetic_stage_b_manifest()
    result = select_batch_a_stage_b_windows(manifest)
    forward = compute_stage_b_selection_sha256(
        result.window_ids,
        purpose_counts=result.purpose_counts,
        overlap_class_counts=result.overlap_class_counts,
    )
    reverse = compute_stage_b_selection_sha256(
        reversed(result.window_ids),
        purpose_counts=result.purpose_counts,
        overlap_class_counts=result.overlap_class_counts,
    )
    assert forward == reverse == result.selection_sha256


def test_live_manifest_matches_wp4_lock(live_manifest: dict) -> None:
    result = select_batch_a_stage_b_windows(live_manifest)
    assert result.selection_sha256 == LOCKED_STAGE_B_SELECTION_SHA256
    assert result.window_count == EXPECTED_STAGE_B_TOTAL
