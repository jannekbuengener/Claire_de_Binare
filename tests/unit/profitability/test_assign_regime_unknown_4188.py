"""Profitability offline assign helpers share fail-closed UNKNOWN semantics (#4188)."""

from __future__ import annotations

import pytest

from scripts.profitability import assign_regime_calibrate_3032_expansion as cal_3032
from scripts.profitability import assign_regime_to_mexc_3091 as mexc_3091
from scripts.profitability import generate_calibration_variants_3032 as variants_3032
from tools.market_data.assign_regime_offline import REGIME_BLOCK_WARMUP


def _candle(i: int, *, close: float = 100.0) -> dict:
    return {
        "ts_ms": 1_700_000_000_000 + i * 60_000,
        "open": close,
        "high": close + 0.1,
        "low": close - 0.1,
        "close": close,
        "volume": 1.0,
        "trade_count": 1,
    }


@pytest.mark.unit
def test_mexc_3091_warmup_not_trend() -> None:
    rows = [_candle(i) for i in range(8)]
    out = mexc_3091.build_derived_candles(rows)
    assert all(r["regime_id"] is None for r in out)
    assert all(r["regime_block_reason"] == REGIME_BLOCK_WARMUP for r in out)
    assert all(r["regime_id"] != 0 for r in out)


@pytest.mark.unit
def test_calibrate_3032_expansion_warmup_not_trend() -> None:
    rows = [_candle(i) for i in range(8)]
    out, dist = cal_3032.build_derived_candles(rows, atr_threshold=52.59)
    assert None in dist
    assert all(r["regime_id"] is None for r in out)
    assert 0 not in dist or dist.get(0, 0) == 0


@pytest.mark.unit
def test_calibration_variants_warmup_not_trend() -> None:
    rows = [_candle(i) for i in range(8)]
    out, dist = variants_3032.build_derived_candles(rows, atr_threshold=2.0)
    assert None in dist
    assert all(r["regime_id"] is None for r in out)


@pytest.mark.unit
def test_known_trend_preserved_after_confirmation() -> None:
    rows = []
    for i in range(80):
        close = 100.0 + i * 0.5
        rows.append(
            {
                "ts_ms": 1_700_000_000_000 + i * 60_000,
                "open": close,
                "high": close + 0.05,
                "low": close - 0.05,
                "close": close,
                "volume": 1.0,
                "trade_count": 1,
            }
        )
    # High ATR threshold so HIGH_VOL does not dominate; ADX should prefer TREND.
    out, dist = cal_3032.build_derived_candles(rows, atr_threshold=10_000.0)
    assert any(r["regime_id"] == 0 for r in out)
    assert dist.get(0, 0) > 0
