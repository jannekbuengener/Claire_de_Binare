"""Tests for Binance window-bank dataset adapter (#4031 slice 2a)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.replay.binance_window_bank_adapter import (
    BinanceWindowBankAdapterError,
    load_binance_window_dataset,
    load_dataset_spec,
    load_window_candles_jsonl,
    resolve_window_bank_paths,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_WINDOW_ID = "binance_1m_month_2021_01"
FIXTURE_BANK_ROOT = REPO_ROOT / "tests/fixtures/market_data/binance_window_bank"
FIXTURE_ROOT = FIXTURE_BANK_ROOT / FIXTURE_WINDOW_ID


def test_load_fixture_window_read_only() -> None:
    before_spec = (FIXTURE_ROOT / "dataset_spec.json").read_text(encoding="utf-8")
    before_candles = (FIXTURE_ROOT / "candles.jsonl").read_text(encoding="utf-8")

    dataset = load_binance_window_dataset(
        FIXTURE_WINDOW_ID,
        warmup_candles=10,
        repo_root=REPO_ROOT,
        window_bank_root=FIXTURE_BANK_ROOT,
    )

    assert len(dataset.candles) == 300
    assert dataset.candles[0]["ts_ms"] < dataset.candles[1]["ts_ms"]
    for key in ("ts_ms", "high", "low", "close"):
        assert key in dataset.candles[0]
    assert dataset.spec.get("purpose") == "development"

    after_spec = (FIXTURE_ROOT / "dataset_spec.json").read_text(encoding="utf-8")
    after_candles = (FIXTURE_ROOT / "candles.jsonl").read_text(encoding="utf-8")
    assert before_spec == after_spec
    assert before_candles == after_candles


def test_resolve_paths_under_repo_relative_fixture_layout() -> None:
    ref = resolve_window_bank_paths(
        FIXTURE_WINDOW_ID,
        repo_root=REPO_ROOT,
        window_bank_root=FIXTURE_BANK_ROOT,
    )
    assert FIXTURE_WINDOW_ID in ref.candles_path
    assert ref.candles_path.startswith("tests/fixtures/")


def test_rmr_and_momentum_warmup_load_via_adapter() -> None:
    dataset = load_binance_window_dataset(
        FIXTURE_WINDOW_ID,
        warmup_candles=240,
        repo_root=REPO_ROOT,
        window_bank_root=FIXTURE_BANK_ROOT,
    )
    assert dataset.dataset_result.warmup_count == 240
    assert "regime_id" in dataset.candles[0]


def test_missing_dataset_spec_fields_fail_closed(tmp_path: Path) -> None:
    bad_spec = tmp_path / "dataset_spec.json"
    bad_spec.write_text(json.dumps({"window_id": "x"}), encoding="utf-8")
    with pytest.raises(BinanceWindowBankAdapterError, match="missing required"):
        load_dataset_spec(bad_spec)


def test_cadence_validation_on_fixture() -> None:
    candles = load_window_candles_jsonl(FIXTURE_ROOT / "candles.jsonl")
    assert len(candles) == 300
