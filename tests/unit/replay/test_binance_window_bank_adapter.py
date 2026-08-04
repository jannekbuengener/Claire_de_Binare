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
    # CDB-049: DatasetSpec uses live start (after warmup), not series-first metadata.
    assert dataset.dataset_result.spec.start_ts_ms == dataset.candles[10]["ts_ms"]
    assert dataset.dataset_result.spec.end_ts_ms == dataset.candles[-1]["ts_ms"]
    assert dataset.dataset_result.candles[0]["ts_ms"] == dataset.candles[0]["ts_ms"]
    assert dataset.dataset_result.warmup_count == 10

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
    assert dataset.dataset_result.spec.start_ts_ms == dataset.candles[240]["ts_ms"]
    assert dataset.dataset_result.spec.end_ts_ms == dataset.candles[-1]["ts_ms"]


def test_cdb049_adapter_rejects_end_mismatch(tmp_path: Path) -> None:
    window_id = "bad_end_window"
    root = tmp_path / window_id
    root.mkdir()
    candles = [
        {
            "ts_ms": 1_700_000_000_000 + i * 60_000,
            "high": 1.0,
            "low": 1.0,
            "close": 1.0,
            "regime_id": 0,
        }
        for i in range(5)
    ]
    (root / "candles.jsonl").write_text(
        "\n".join(json.dumps(c) for c in candles) + "\n", encoding="utf-8"
    )
    (root / "dataset_spec.json").write_text(
        json.dumps(
            {
                "window_id": window_id,
                "symbol": "BTCUSDT",
                "timeframe": "1m",
                "start_ts_ms": candles[0]["ts_ms"],
                "end_ts_ms": candles[-1]["ts_ms"] + 60_000,
                "file_path": str(root / "candles.jsonl"),
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(BinanceWindowBankAdapterError, match="end mismatch"):
        load_binance_window_dataset(
            window_id,
            warmup_candles=1,
            repo_root=tmp_path,
            window_bank_root=tmp_path,
        )


def test_missing_dataset_spec_fields_fail_closed(tmp_path: Path) -> None:
    bad_spec = tmp_path / "dataset_spec.json"
    bad_spec.write_text(json.dumps({"window_id": "x"}), encoding="utf-8")
    with pytest.raises(BinanceWindowBankAdapterError, match="missing required"):
        load_dataset_spec(bad_spec)


def test_cadence_validation_on_fixture() -> None:
    candles = load_window_candles_jsonl(FIXTURE_ROOT / "candles.jsonl")
    assert len(candles) == 300
