"""Unit tests for core/replay/regime_stats.py (#4031 A3)."""

from __future__ import annotations

import pytest

from core.replay.canonical_json import canonical_hash
from core.replay.regime_stats import (
    RegimeStatsAggregator,
    build_regime_stats_from_replay,
    normalize_regime_id,
    regime_scorecard_status_from_stats,
)

pytestmark = pytest.mark.unit


def _candle(ts_ms: int, regime_id: int | str) -> dict[str, object]:
    return {
        "ts_ms": ts_ms,
        "open": 100.0,
        "high": 101.0,
        "low": 99.0,
        "close": 100.5,
        "volume": 1.0,
        "regime_id": regime_id,
    }


def _trade(
    *,
    entry_ts_ms: int,
    exit_ts_ms: int,
    r_return: float = 0.01,
) -> dict[str, object]:
    return {
        "entry_ts_ms": entry_ts_ms,
        "exit_ts_ms": exit_ts_ms,
        "entry_price": 100.0,
        "exit_price": 101.0,
        "entry_fee": 0.01,
        "exit_fee": 0.01,
        "r_return": r_return,
    }


class TestNormalizeRegimeId:
    def test_numeric_hvc(self) -> None:
        assert normalize_regime_id(2) == "HIGH_VOL_CHAOTIC"

    def test_string_uppercase(self) -> None:
        assert normalize_regime_id("trend") == "TREND"


class TestRegimeStatsAggregator:
    def test_deterministic_finalize_hash(self) -> None:
        candles = [_candle(i * 60_000, i % 3) for i in range(10)]
        trades = [_trade(entry_ts_ms=120_000, exit_ts_ms=180_000)]
        first = build_regime_stats_from_replay(candles, trades, warmup=2)
        second = build_regime_stats_from_replay(candles, trades, warmup=2)
        assert first == second
        assert first["stats_fingerprint"] == second["stats_fingerprint"]

    def test_no_steps_trace_in_output(self) -> None:
        stats = build_regime_stats_from_replay(
            [_candle(0, 0), _candle(60_000, 1)],
            [],
        )
        assert "steps" not in stats
        assert "trace" not in stats
        assert stats["schema_version"] == "regime_stats.v1"

    def test_hvc_dominance_flag_when_over_90_percent_one_regime(self) -> None:
        candles = [_candle(i * 60_000, 2) for i in range(100)]
        candles[0] = _candle(0, 1)
        stats = build_regime_stats_from_replay(candles, [], warmup=0)
        flags = stats["diversity_flags"]
        assert flags["hvc_candle_share"] == "0.99000000"
        assert flags["single_regime_dominance_flag"] is True
        assert flags["dominant_regime_id"] == "HIGH_VOL_CHAOTIC"
        assert flags["regimes_observed_count"] == 2

    def test_warmup_excluded_from_candle_counts(self) -> None:
        candles = [_candle(i * 60_000, 0) for i in range(5)]
        stats = build_regime_stats_from_replay(candles, [], warmup=3)
        assert stats["coverage"]["candles_total"] == 2

    def test_trade_regime_attribution_via_timestamps(self) -> None:
        candles = [
            _candle(60_000, 0),
            _candle(120_000, 1),
            _candle(180_000, 2),
        ]
        trades = [_trade(entry_ts_ms=60_000, exit_ts_ms=180_000)]
        stats = build_regime_stats_from_replay(candles, trades)
        by_regime = {row["regime_id"]: row for row in stats["per_regime"]}
        assert by_regime["TREND"]["entry_trade_count"] == 1
        assert by_regime["HIGH_VOL_CHAOTIC"]["exit_trade_count"] == 1
        assert stats["diversity_flags"]["regimes_with_trades_count"] == 2

    def test_missing_regime_coverage_flag(self) -> None:
        candles = [{"ts_ms": 0, "regime_id": 0}, {"ts_ms": 60_000}]
        stats = build_regime_stats_from_replay(candles, [])
        assert stats["coverage"]["regime_id_missing_flag"] is True
        assert stats["coverage"]["candles_missing_regime_id"] == 1

    def test_fingerprint_stable_for_same_payload(self) -> None:
        agg = RegimeStatsAggregator()
        agg.update_bar(_candle(0, 0))
        payload = agg.finalize()
        assert payload["stats_fingerprint"] == canonical_hash(
            {
                "schema_version": payload["schema_version"],
                "coverage": payload["coverage"],
                "diversity_flags": payload["diversity_flags"],
                "per_regime": payload["per_regime"],
            }
        )


class TestRegimeScorecardStatusHook:
    def test_ok_when_trades_in_multiple_regimes(self) -> None:
        stats = {
            "diversity_flags": {"regimes_with_trades_count": 2},
        }
        assert regime_scorecard_status_from_stats(stats) == "ok"

    def test_unavailable_when_single_regime_trades(self) -> None:
        stats = {
            "diversity_flags": {"regimes_with_trades_count": 1},
        }
        assert regime_scorecard_status_from_stats(stats) == "unavailable"

    def test_unavailable_when_missing(self) -> None:
        assert regime_scorecard_status_from_stats(None) == "unavailable"
