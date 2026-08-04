"""CDB-051 gap / duplicate / out-of-order / Replay-vs-Runtime integrity rules."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.replay.dataset_integrity_rules import (
    REASON_CADENCE_VIOLATION,
    REASON_DUPLICATE_CONFLICTING,
    REASON_DUPLICATE_IDENTICAL,
    REASON_EMPTY,
    REASON_GAP,
    REASON_INCOMPLETE_WINDOW,
    REASON_OUT_OF_ORDER,
    REPLAY_VS_RUNTIME_CONTRACT,
    REPLAY_VS_RUNTIME_CONTRACT_VERSION,
    ROOT_CAUSE_PRIORITY,
    IntegrityError,
    assert_replay_integrity,
    classify_candle_integrity,
    normalize_with_evidence,
    primary_reason_code,
)
from core.replay.dataset_provider import (
    DatasetLoadError,
    DatasetSpec,
    FileBackedDatasetProvider,
    enforce_replay_integrity,
    warmup_start_ms,
)
from services.candles.models import CandleAggregator
from services.validation.strategy_replay_runner import (
    ARVPReplayConfig,
    ReplayRunnerError,
    _load_dataset_result,
)

pytestmark = pytest.mark.unit

_BASE = 1_700_000_000_000


def _row(i: int, **extra: object) -> dict:
    payload = {
        "ts_ms": _BASE + i * 60_000,
        "open": 100.0 + i,
        "high": 101.0 + i,
        "low": 99.0 + i,
        "close": 100.5 + i,
        "volume": 1.0,
    }
    payload.update(extra)
    return payload


def test_cdb051_clean_series_ok_for_replay() -> None:
    candles = [_row(i) for i in range(3)]
    assessment = assert_replay_integrity(
        candles, start_ts_ms=_BASE, end_ts_ms=_BASE + 120_000
    )
    assert assessment.ok_for_replay is True
    assert assessment.reason_codes == ()
    assert assessment.primary_reason_code is None


def test_cdb051_gap_positive_and_negative() -> None:
    clean = [_row(i) for i in range(3)]
    assert (
        REASON_GAP
        not in classify_candle_integrity(
            clean, start_ts_ms=_BASE, end_ts_ms=_BASE + 120_000
        ).reason_codes
    )

    gapped = [_row(0), _row(2)]
    bad = classify_candle_integrity(
        gapped, start_ts_ms=_BASE, end_ts_ms=_BASE + 120_000
    )
    assert REASON_GAP in bad.reason_codes
    with pytest.raises(IntegrityError, match="GAP") as exc:
        assert_replay_integrity(gapped, start_ts_ms=_BASE, end_ts_ms=_BASE + 120_000)
    assert exc.value.code == REASON_GAP


def test_cdb051_duplicate_identical_and_conflicting() -> None:
    identical = [_row(0), _row(0), _row(1)]
    assessment = classify_candle_integrity(identical)
    assert REASON_DUPLICATE_IDENTICAL in assessment.reason_codes

    conflicting = [_row(0), _row(0, close=999.0), _row(1)]
    assessment2 = classify_candle_integrity(conflicting)
    assert REASON_DUPLICATE_CONFLICTING in assessment2.reason_codes


def test_cdb051_out_of_order_positive_and_negative() -> None:
    clean = [_row(i) for i in range(3)]
    assert REASON_OUT_OF_ORDER not in classify_candle_integrity(clean).reason_codes

    ooo = [_row(0), _row(2), _row(1)]
    assessment = classify_candle_integrity(ooo)
    assert REASON_OUT_OF_ORDER in assessment.reason_codes
    with pytest.raises(IntegrityError, match="OUT_OF_ORDER") as exc:
        assert_replay_integrity(ooo)
    assert exc.value.code == REASON_OUT_OF_ORDER


def test_cdb051_cadence_violation() -> None:
    bad = [_row(0), {"ts_ms": _BASE + 90_000, "close": 1.0, "high": 1.0, "low": 1.0}]
    assessment = classify_candle_integrity(bad)
    assert REASON_CADENCE_VIOLATION in assessment.reason_codes


def test_cdb051_empty_series() -> None:
    with pytest.raises(IntegrityError) as exc:
        assert_replay_integrity([])
    assert exc.value.code == REASON_EMPTY


def test_cdb051_priority_ooo_over_gap() -> None:
    # OOO + implied missing middle when window-bound.
    ooo_gap = [_row(0), _row(2), _row(1)]
    assessment = classify_candle_integrity(
        ooo_gap, start_ts_ms=_BASE, end_ts_ms=_BASE + 120_000
    )
    assert REASON_OUT_OF_ORDER in assessment.reason_codes
    assert assessment.primary_reason_code == REASON_OUT_OF_ORDER
    assert primary_reason_code(assessment.reason_codes) == REASON_OUT_OF_ORDER
    assert ROOT_CAUSE_PRIORITY.index(REASON_OUT_OF_ORDER) < ROOT_CAUSE_PRIORITY.index(
        REASON_GAP
    )


def test_cdb051_normalization_evidence_is_deterministic() -> None:
    ooo = [_row(2), _row(0), _row(1)]
    ordered_a, evidence_a = normalize_with_evidence(ooo)
    ordered_b, evidence_b = normalize_with_evidence(ooo)
    assert ordered_a == ordered_b
    assert evidence_a == evidence_b
    assert evidence_a.order_changed is True
    assert "sort_by_ts_ms" in evidence_a.normalization_applied
    assert REASON_OUT_OF_ORDER in evidence_a.reason_codes


def test_cdb051_replay_vs_runtime_contract_versioned() -> None:
    assert (
        REPLAY_VS_RUNTIME_CONTRACT["schema_version"]
        == REPLAY_VS_RUNTIME_CONTRACT_VERSION
    )
    assert REPLAY_VS_RUNTIME_CONTRACT["parity_claim"] == "asymmetric"
    assert REPLAY_VS_RUNTIME_CONTRACT["replay"]["out_of_order"] == "fail_closed"
    assert (
        REPLAY_VS_RUNTIME_CONTRACT["runtime_candles"]["out_of_order"]
        == "late_tick_may_update_current_window_ohlc"
    )


def test_cdb051_spec_window_binding_detects_mid_gap(tmp_path: Path) -> None:
    """After CDB-049 edges pass, Spec-bound integrity detects a mid-window gap."""
    # Contiguous edges with one missing middle live candle.
    candles = [_row(i) for i in range(5)]
    del candles[2]  # remove middle; remaining edges wrong for exact-window
    # Build a series with correct first/last but gap in middle.
    candles = [_row(0), _row(1), _row(3), _row(4)]
    path = tmp_path / "candles.json"
    path.write_text(json.dumps(candles), encoding="utf-8")
    spec = DatasetSpec(
        symbol="BTCUSDT",
        timeframe="1m",
        start_ts_ms=_BASE + 60_000,
        end_ts_ms=_BASE + 4 * 60_000,
        warmup_candles=1,
        source="file",
        file_path=str(path),
    )
    with pytest.raises(DatasetLoadError) as exc:
        FileBackedDatasetProvider().load(spec)
    # Series-local cadence fires first; Spec-bound gap also valid if cadence skipped.
    assert exc.value.code in {REASON_CADENCE_VIOLATION, REASON_GAP}


def test_cdb051_provider_propagates_duplicate_code(tmp_path: Path) -> None:
    candles = [_row(i) for i in range(5)]
    candles[2] = _row(1)  # duplicate of index 1
    path = tmp_path / "candles.json"
    path.write_text(json.dumps(candles), encoding="utf-8")
    # Discover sentinel avoids exact-window / incomplete-window binding.
    spec = DatasetSpec(
        symbol="BTCUSDT",
        timeframe="1m",
        start_ts_ms=0,
        end_ts_ms=0,
        warmup_candles=1,
        source="file",
        file_path=str(path),
    )
    with pytest.raises(DatasetLoadError) as exc:
        FileBackedDatasetProvider().load(spec)
    assert exc.value.code in {REASON_DUPLICATE_IDENTICAL, REASON_DUPLICATE_CONFLICTING}


def test_cdb051_runner_preserves_integrity_code(tmp_path: Path) -> None:
    candles = [_row(i) for i in range(5)]
    candles[3]["ts_ms"] = candles[2]["ts_ms"]
    path = tmp_path / "candles.jsonl"
    path.write_text("\n".join(json.dumps(c) for c in candles) + "\n", encoding="utf-8")
    config = ARVPReplayConfig(
        dataset_source="file",
        input_candles_file=str(path),
        output_directory=str(tmp_path / "out"),
        entry_lookback_minutes=1,
        exit_lookback_minutes=1,
    )
    with pytest.raises(ReplayRunnerError) as exc:
        _load_dataset_result(config, warmup_count=1)
    assert exc.value.code in {REASON_DUPLICATE_IDENTICAL, REASON_DUPLICATE_CONFLICTING}


def test_cdb051_executable_runtime_asymmetry_ooo() -> None:
    """Same OOO ticks: runtime may update OHLC; replay fail-closed.

    Independent paths — no shared helper result compared to itself.
    """
    # Replay path rejects unsorted series.
    ooo = [_row(0), _row(2), _row(1)]
    with pytest.raises(IntegrityError) as replay_exc:
        assert_replay_integrity(ooo)
    assert replay_exc.value.code == REASON_OUT_OF_ORDER

    # Runtime aggregator: late/OOO tick still updates current window OHLC.
    agg = CandleAggregator(interval_seconds=60)
    # Open window with early tick.
    t0 = _BASE
    closed = agg.process_trade(
        {
            "ts_ms": t0 + 10_000,
            "symbol": "BTCUSDT",
            "price": "100.0",
            "trade_qty": "1.0",
        }
    )
    assert closed == []
    # Late tick with earlier ts_ms still mutates OHLC (documented asymmetry).
    closed2 = agg.process_trade(
        {
            "ts_ms": t0 + 5_000,
            "symbol": "BTCUSDT",
            "price": "90.0",
            "trade_qty": "1.0",
        }
    )
    assert closed2 == []
    window = agg.windows["BTCUSDT"]
    assert float(window.low) == 90.0
    assert REPLAY_VS_RUNTIME_CONTRACT["parity_claim"] == "asymmetric"


def test_cdb051_enforce_replay_integrity_public_api() -> None:
    clean = [_row(i) for i in range(3)]
    spec = DatasetSpec(
        symbol="BTCUSDT",
        timeframe="1m",
        start_ts_ms=_BASE,
        end_ts_ms=_BASE + 120_000,
        warmup_candles=0,
        source="file",
        file_path="x.json",
    )
    assert warmup_start_ms(spec) == _BASE
    enforce_replay_integrity(clean, "unit", spec=spec)
