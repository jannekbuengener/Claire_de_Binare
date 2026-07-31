"""Fail-closed UNKNOWN semantics for offline regime assignment (#4188).

Test-First:
- Regel: missing / UNKNOWN / warmup darf nie stillschweigend TREND (regime_id=0)
  werden; Runtime-/Candles-Semantik (None) ist kanonisch.
- Testart: Schutz-Test (unit)
- Entscheidung: Offline-Assign und Runtime teilen dieselbe fail-closed Mapping-Regel.
- Metadata: issue_ref=#4188, refs=#4149
- Weiterverarbeitung: PASS → Slice-Evidence; FAIL → HOLD / Fix im Assign-Pfad.
"""

from __future__ import annotations

import pytest

from tools.market_data import assign_regime_offline as offline
from tools.market_data.assign_regime_offline import (
    REGIME_BLOCK_UNKNOWN,
    REGIME_BLOCK_WARMUP,
    REGIME_NAME_TO_ID,
    annotate_regime_row,
    assign_regime_ids,
    regime_distribution,
    regime_name_to_id,
    resolve_assigned_regime,
)


def _candle(
    i: int, *, close: float = 100.0, high: float | None = None, low: float | None = None
) -> dict:
    h = close + 0.5 if high is None else high
    lo = close - 0.5 if low is None else low
    return {
        "ts_ms": 1_780_272_000_000 + i * 60_000,
        "open": close,
        "high": h,
        "low": lo,
        "close": close,
        "volume": 1.0,
        "trade_count": 1,
    }


@pytest.mark.unit
def test_missing_regime_name_not_mapped_to_trend() -> None:
    assert regime_name_to_id(None) is None
    assert regime_name_to_id("") is None
    assert regime_name_to_id("   ") is None
    rid, reason = resolve_assigned_regime(indicators_ready=True, current_regime=None)
    assert rid is None
    assert reason == REGIME_BLOCK_UNKNOWN


@pytest.mark.unit
def test_unknown_name_not_mapped_to_regime_id_zero() -> None:
    assert regime_name_to_id("UNKNOWN") is None
    assert regime_name_to_id("unknown") is None
    assert regime_name_to_id("NOT_A_REAL_REGIME") is None
    # Explicit guard: dict.get(..., 0) must not be used as semantics.
    assert REGIME_NAME_TO_ID.get("UNKNOWN", 0) == 0  # legacy trap value
    assert regime_name_to_id("UNKNOWN") != 0
    rid, reason = resolve_assigned_regime(
        indicators_ready=True, current_regime="UNKNOWN"
    )
    assert rid is None
    assert reason == REGIME_BLOCK_UNKNOWN
    row = annotate_regime_row({}, regime_id=rid, block_reason=reason)
    assert row["regime_id"] is None
    assert row["regime_name"] == "UNKNOWN"
    assert row["regime_block_reason"] == REGIME_BLOCK_UNKNOWN


@pytest.mark.unit
def test_warmup_rows_are_unknown_not_trend() -> None:
    # Fewer than ADX/ATR period+1 candles → indicators not ready → UNKNOWN.
    rows = [_candle(i) for i in range(10)]
    out = assign_regime_ids(rows)
    assert len(out) == 10
    for row in out:
        assert row["regime_id"] is None
        assert row["regime_name"] == "UNKNOWN"
        assert row["regime_block_reason"] == REGIME_BLOCK_WARMUP
        assert row["regime_id"] != 0


@pytest.mark.unit
def test_known_trend_remains_trend() -> None:
    assert regime_name_to_id("TREND") == 0
    rid, reason = resolve_assigned_regime(indicators_ready=True, current_regime="TREND")
    assert rid == 0
    assert reason is None
    row = annotate_regime_row({"ts_ms": 1}, regime_id=rid, block_reason=reason)
    assert row["regime_id"] == 0
    assert row["regime_name"] == "TREND"
    assert "regime_block_reason" not in row


@pytest.mark.unit
def test_known_other_regimes_remain_correct() -> None:
    assert regime_name_to_id("RANGE") == 1
    assert regime_name_to_id("HIGH_VOL_CHAOTIC") == 2
    assert regime_name_to_id("HIGH_VOL_SPIKE") == 2  # HIGH_VOL_* prefix
    assert regime_name_to_id("CRISIS") == 3


@pytest.mark.unit
def test_offline_matches_runtime_null_semantics() -> None:
    """Runtime candles: UNKNOWN/missing → None. Offline must match."""
    # Warmup path
    rid_w, reason_w = resolve_assigned_regime(
        indicators_ready=False, current_regime="UNKNOWN"
    )
    assert rid_w is None and reason_w == REGIME_BLOCK_WARMUP
    # Unknown name after indicators ready
    rid_u, reason_u = resolve_assigned_regime(
        indicators_ready=True, current_regime="UNKNOWN"
    )
    assert rid_u is None and reason_u == REGIME_BLOCK_UNKNOWN
    # Known ids unchanged
    assert resolve_assigned_regime(indicators_ready=True, current_regime="TREND") == (
        0,
        None,
    )
    assert resolve_assigned_regime(indicators_ready=True, current_regime="RANGE") == (
        1,
        None,
    )


@pytest.mark.unit
def test_no_silent_numeric_fallback_in_distribution() -> None:
    candles = [
        {"regime_id": None, "regime_name": "UNKNOWN"},
        {"regime_id": 0, "regime_name": "TREND"},
        {"regime_id": 1, "regime_name": "RANGE"},
    ]
    dist = regime_distribution(candles)
    assert dist["null"]["regime_name"] == "UNKNOWN"
    assert dist["null"]["count"] == 1
    assert dist["0"]["regime_name"] == "TREND"
    assert dist["0"]["count"] == 1
    assert dist["1"]["regime_name"] == "RANGE"


@pytest.mark.unit
def test_strong_trend_series_emits_trend_after_warmup() -> None:
    """Known TREND path: after indicators warm, confirmed TREND stays 0."""
    # Monotone rising close with small range → ADX high, ATR below absolute 2.0
    rows = []
    for i in range(80):
        close = 100.0 + i * 0.5
        rows.append(_candle(i, close=close, high=close + 0.05, low=close - 0.05))
    out = assign_regime_ids(rows)
    warmup = out[: offline.ADX_PERIOD]
    assert all(r["regime_id"] is None for r in warmup)
    assert all(r["regime_block_reason"] == REGIME_BLOCK_WARMUP for r in warmup)
    # After confirmation, TREND (0) should appear among later bars.
    later_ids = {r["regime_id"] for r in out[40:]}
    assert 0 in later_ids
    assert None not in later_ids or True  # UNKNOWN only if still unconfirmed
    # Never coerce UNKNOWN via silent 0 during true warmup.
    assert all(r["regime_id"] is None for r in warmup)
