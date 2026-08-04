"""CDB-050 DQ verdict binding to content identity."""

from __future__ import annotations

import pytest

from tools.market_data.historical_common import (
    HistoricalProbeError,
    NormalizedCandle,
    assert_dq_content_binding,
    build_quality_report,
    content_fingerprint_for_normalized,
)

pytestmark = pytest.mark.unit

_BASE = 1_700_000_000_000


def _candles(n: int = 3) -> list[NormalizedCandle]:
    out: list[NormalizedCandle] = []
    for i in range(n):
        out.append(
            NormalizedCandle(
                ts_ms=_BASE + i * 60_000,
                open="100.0",
                high="101.0",
                low="99.0",
                close="100.5",
                volume="1.0",
                quote_volume=None,
                trade_count=None,
                symbol="BTCUSDT",
                venue="binance",
                timeframe="1m",
                source_type="test",
                source_file_sha256="d" * 64,
            )
        )
    return out


def test_cdb050_dq_verdict_binds_content_fingerprint() -> None:
    candles = _candles()
    report = build_quality_report(
        candles,
        start_ts_ms=_BASE,
        end_ts_ms=_BASE + 120_000,
        step_ms=60_000,
        source_hash="e" * 64,
    )
    expected = content_fingerprint_for_normalized(candles)
    assert report["content_fingerprint"] == expected
    assert report["content_binding_schema"] == "cdb.dq_content_binding.v1"
    assert_dq_content_binding(report, content_fingerprint=expected)


def test_cdb050_changed_content_makes_verdict_stale() -> None:
    candles = _candles()
    report = build_quality_report(
        candles,
        start_ts_ms=_BASE,
        end_ts_ms=_BASE + 120_000,
        step_ms=60_000,
        source_hash="e" * 64,
    )
    altered = _candles()
    altered[0] = NormalizedCandle(
        ts_ms=altered[0].ts_ms,
        open="999.0",
        high=altered[0].high,
        low=altered[0].low,
        close=altered[0].close,
        volume=altered[0].volume,
        quote_volume=None,
        trade_count=None,
        symbol="BTCUSDT",
        venue="binance",
        timeframe="1m",
        source_type="test",
        source_file_sha256="d" * 64,
    )
    new_fp = content_fingerprint_for_normalized(altered)
    with pytest.raises(HistoricalProbeError, match="stale or mismatched"):
        assert_dq_content_binding(report, content_fingerprint=new_fp)


def test_cdb050_request_hash_alone_insufficient_mismatch_param() -> None:
    candles = _candles()
    with pytest.raises(HistoricalProbeError, match="does not match"):
        build_quality_report(
            candles,
            start_ts_ms=_BASE,
            end_ts_ms=_BASE + 120_000,
            step_ms=60_000,
            source_hash="e" * 64,
            content_fingerprint="0" * 64,
        )


def test_cdb050_missing_binding_blocks() -> None:
    with pytest.raises(HistoricalProbeError, match="missing content_fingerprint"):
        assert_dq_content_binding(
            {"verdict": "STRICT_COMPLETE"}, content_fingerprint="a" * 64
        )
