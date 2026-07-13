"""Tests for Batch-A development window selector (#4031 slice 2a)."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from tools.market_data.development_window_selector import (
    LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS,
    LOCKED_DEVELOPMENT_SELECTION_SHA256,
    DevelopmentSelectionError,
    compute_development_selection_sha256,
    load_window_bank_manifest,
    select_batch_a_development_windows,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = (
    REPO_ROOT
    / "artifacts/market_data/window_bank/binance/spot/BTCUSDT/1m/"
    "window_bank_manifest.json"
)


@pytest.fixture
def live_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        pytest.skip("Local Binance window bank manifest not available")
    return load_window_bank_manifest(MANIFEST_PATH)


def test_selects_exactly_39_development_monthly_windows(live_manifest: dict) -> None:
    result = select_batch_a_development_windows(live_manifest)
    assert result.window_count == 39
    assert len(result.window_ids) == 39
    assert result.purpose == "development"
    assert result.overlap_class == "monthly"


def test_selection_hash_matches_wp1_lock(live_manifest: dict) -> None:
    result = select_batch_a_development_windows(live_manifest)
    assert result.selection_sha256 == LOCKED_DEVELOPMENT_SELECTION_SHA256


def test_selection_hash_reproducible_on_reordered_input(live_manifest: dict) -> None:
    shuffled = copy.deepcopy(live_manifest)
    shuffled["windows"] = list(reversed(shuffled["windows"]))
    first = select_batch_a_development_windows(live_manifest)
    second = select_batch_a_development_windows(shuffled)
    assert first.window_ids == second.window_ids
    assert first.selection_sha256 == second.selection_sha256


def test_compute_hash_stable_for_locked_ids() -> None:
    forward = compute_development_selection_sha256(LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS)
    reverse = compute_development_selection_sha256(
        reversed(LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS)
    )
    assert forward == reverse == LOCKED_DEVELOPMENT_SELECTION_SHA256


def test_rejects_stress_purpose_in_manifest() -> None:
    manifest = {
        "windows": [
            {
                "window_id": wid,
                "start_ts_ms": idx * 1000,
                "end_ts_ms": idx * 1000 + 500,
                "overlap_class": "monthly",
                "purpose": "development",
            }
            for idx, wid in enumerate(LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS)
        ]
    }
    manifest["windows"][0]["purpose"] = "stress"
    with pytest.raises(DevelopmentSelectionError, match="diverges"):
        select_batch_a_development_windows(manifest)


def test_rejects_validation_purpose_windows(live_manifest: dict) -> None:
    mutated = copy.deepcopy(live_manifest)
    for window in mutated["windows"]:
        if window.get("window_id") == LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS[0]:
            window["purpose"] = "validation"
            break
    with pytest.raises(DevelopmentSelectionError, match="diverges"):
        select_batch_a_development_windows(mutated)


def test_quarterly_windows_never_selected(live_manifest: dict) -> None:
    result = select_batch_a_development_windows(live_manifest)
    for window in result.windows:
        assert window["overlap_class"] == "monthly"
        assert window["purpose"] == "development"


def test_rejects_unknown_extra_development_window(live_manifest: dict) -> None:
    mutated = copy.deepcopy(live_manifest)
    mutated["windows"].append(
        {
            "window_id": "binance_1m_month_2099_01",
            "start_ts_ms": 1,
            "end_ts_ms": 2,
            "overlap_class": "monthly",
            "purpose": "development",
        }
    )
    with pytest.raises(DevelopmentSelectionError, match="extra="):
        select_batch_a_development_windows(mutated)


def test_rejects_overlapping_development_windows() -> None:
    manifest = {
        "windows": [
            {
                "window_id": wid,
                "start_ts_ms": 0,
                "end_ts_ms": 10,
                "overlap_class": "monthly",
                "purpose": "development",
            }
            for wid in LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS
        ]
    }
    manifest["windows"][0]["start_ts_ms"] = 0
    manifest["windows"][0]["end_ts_ms"] = 100
    manifest["windows"][1]["start_ts_ms"] = 50
    manifest["windows"][1]["end_ts_ms"] = 150
    with pytest.raises(DevelopmentSelectionError, match="Pairwise overlap"):
        select_batch_a_development_windows(manifest, require_locked_ids=False)
