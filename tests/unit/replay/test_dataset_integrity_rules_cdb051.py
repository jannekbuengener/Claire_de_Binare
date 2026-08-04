"""CDB-051 gap / duplicate / out-of-order / Replay-vs-Runtime integrity rules."""

from __future__ import annotations

import pytest

from core.replay.dataset_integrity_rules import (
    REASON_CADENCE_VIOLATION,
    REASON_DUPLICATE_CONFLICTING,
    REASON_DUPLICATE_IDENTICAL,
    REASON_GAP,
    REASON_OUT_OF_ORDER,
    REPLAY_VS_RUNTIME_CONTRACT,
    REPLAY_VS_RUNTIME_CONTRACT_VERSION,
    assert_replay_integrity,
    classify_candle_integrity,
    normalize_with_evidence,
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
    with pytest.raises(ValueError, match="GAP"):
        assert_replay_integrity(gapped, start_ts_ms=_BASE, end_ts_ms=_BASE + 120_000)


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
    with pytest.raises(ValueError, match="OUT_OF_ORDER"):
        assert_replay_integrity(ooo)


def test_cdb051_cadence_violation() -> None:
    bad = [_row(0), {"ts_ms": _BASE + 90_000, "close": 1.0, "high": 1.0, "low": 1.0}]
    assessment = classify_candle_integrity(bad)
    assert REASON_CADENCE_VIOLATION in assessment.reason_codes


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
    assert REPLAY_VS_RUNTIME_CONTRACT["replay"]["out_of_order"] == "fail_closed"
    assert (
        REPLAY_VS_RUNTIME_CONTRACT["runtime_candles"]["out_of_order"]
        == "late_tick_may_update_current_window_ohlc"
    )
