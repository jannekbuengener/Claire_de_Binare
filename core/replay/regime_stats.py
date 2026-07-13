"""Compact regime evidence aggregation for ARVP Batch-A campaign jobs (#4031 A3).

Streaming/online aggregation from candle ``regime_id`` fields and closed trades.
Produces schema-versioned ``regime_stats.v1`` artifacts without persisting full
per-candle step traces.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from core.replay.canonical_json import canonical_hash

_SCHEMA_VERSION = "regime_stats.v1"
_UNKNOWN_REGIME = "UNKNOWN"
_HVC_REGIME = "HIGH_VOL_CHAOTIC"
_DOMINANCE_THRESHOLD = Decimal("0.90")
_MONEY_Q = Decimal("0.00000001")
_RATE_Q = Decimal("0.00000001")

_REGIME_ID_TO_NAME: dict[int, str] = {
    0: "TREND",
    1: "RANGE",
    2: "HIGH_VOL_CHAOTIC",
    3: "CRISIS",
}


def normalize_regime_id(raw: object) -> str | None:
    """Map candle/trade regime context to a stable uppercase string id."""
    if isinstance(raw, str) and raw.strip():
        return raw.strip().upper()
    if isinstance(raw, int) and not isinstance(raw, bool):
        return _REGIME_ID_TO_NAME.get(raw, _UNKNOWN_REGIME)
    return None


@dataclass
class _RegimeBucket:
    candle_count: int = 0
    entry_trade_count: int = 0
    exit_trade_count: int = 0
    gross_pnl_r: Decimal = Decimal("0")
    net_pnl_r: Decimal = Decimal("0")
    fees_quote: Decimal = Decimal("0")
    r_returns: list[Decimal] = field(default_factory=list)


class RegimeStatsAggregator:
    """Online regime counter updated per bar and per closed trade."""

    def __init__(self, *, warmup: int = 0) -> None:
        if warmup < 0:
            raise ValueError("warmup must be >= 0")
        self._warmup = warmup
        self._buckets: dict[str, _RegimeBucket] = defaultdict(_RegimeBucket)
        self._ts_to_regime: dict[int, str] = {}
        self._candles_total = 0
        self._candles_with_regime = 0
        self._candles_missing_regime = 0

    def update_bar(self, candle: Mapping[str, Any], *, index: int | None = None) -> None:
        """Count one candle/step toward its regime bucket."""
        if index is not None and index < self._warmup:
            return
        self._candles_total += 1
        regime = normalize_regime_id(candle.get("regime_id"))
        if regime is None:
            self._candles_missing_regime += 1
            return
        self._candles_with_regime += 1
        self._buckets[regime].candle_count += 1
        ts_ms = candle.get("ts_ms")
        if isinstance(ts_ms, int) and not isinstance(ts_ms, bool):
            self._ts_to_regime[ts_ms] = regime

    def record_trade(self, trade: Mapping[str, Any]) -> None:
        """Attribute one closed trade to entry/exit regime buckets when derivable."""
        entry_regime = normalize_regime_id(trade.get("entry_regime_id"))
        exit_regime = normalize_regime_id(trade.get("exit_regime_id"))
        if entry_regime is None:
            entry_regime = self._lookup_regime(trade.get("entry_ts_ms"))
        if exit_regime is None:
            exit_regime = self._lookup_regime(trade.get("exit_ts_ms"))

        if entry_regime is not None:
            self._buckets[entry_regime].entry_trade_count += 1
        if exit_regime is not None:
            bucket = self._buckets[exit_regime]
            bucket.exit_trade_count += 1
            r_return = _as_decimal(trade.get("r_return"))
            if r_return is not None:
                bucket.gross_pnl_r += r_return
                bucket.r_returns.append(r_return)
                entry_fee = _as_decimal(trade.get("entry_fee")) or Decimal("0")
                exit_fee = _as_decimal(trade.get("exit_fee")) or Decimal("0")
                fees = (entry_fee + exit_fee).quantize(_MONEY_Q)
                bucket.fees_quote += fees
                entry_price = _as_decimal(trade.get("entry_price"))
                order_size = _as_decimal(trade.get("order_size")) or Decimal("1")
                if entry_price is not None and entry_price > 0:
                    fee_r = fees / (entry_price * order_size)
                    bucket.net_pnl_r += (r_return - fee_r).quantize(_RATE_Q)

    def finalize(self) -> dict[str, Any]:
        """Return deterministic ``regime_stats.v1`` payload (no step trace)."""
        per_regime = []
        regimes_with_trades: set[str] = set()
        for regime_id in sorted(self._buckets):
            bucket = self._buckets[regime_id]
            if bucket.entry_trade_count or bucket.exit_trade_count:
                regimes_with_trades.add(regime_id)
            expectancy_r: str | None = None
            if bucket.r_returns:
                total = sum(bucket.r_returns, Decimal("0"))
                expectancy_r = str(
                    (total / Decimal(len(bucket.r_returns))).quantize(_RATE_Q)
                )
            segment: dict[str, Any] = {
                "regime_id": regime_id,
                "candle_count": bucket.candle_count,
                "step_count": bucket.candle_count,
                "entry_trade_count": bucket.entry_trade_count,
                "exit_trade_count": bucket.exit_trade_count,
            }
            if bucket.exit_trade_count:
                segment["gross_pnl_r"] = str(bucket.gross_pnl_r.quantize(_RATE_Q))
                segment["net_pnl_r"] = str(bucket.net_pnl_r.quantize(_RATE_Q))
                segment["fees_quote"] = str(bucket.fees_quote.quantize(_MONEY_Q))
                if expectancy_r is not None:
                    segment["expectancy_r"] = expectancy_r
            per_regime.append(segment)

        diversity = _build_diversity_flags(self._buckets, self._candles_with_regime)
        coverage = {
            "candles_total": self._candles_total,
            "candles_with_regime_id": self._candles_with_regime,
            "candles_missing_regime_id": self._candles_missing_regime,
            "regime_id_missing_flag": self._candles_missing_regime > 0,
        }
        payload_without_hash = {
            "schema_version": _SCHEMA_VERSION,
            "coverage": coverage,
            "diversity_flags": diversity,
            "per_regime": per_regime,
        }
        payload = {
            **payload_without_hash,
            "stats_fingerprint": canonical_hash(payload_without_hash),
        }
        _assert_no_trace_keys(payload)
        return payload

    def _lookup_regime(self, ts_ms: object) -> str | None:
        if isinstance(ts_ms, int) and not isinstance(ts_ms, bool):
            return self._ts_to_regime.get(ts_ms)
        return None


def build_regime_stats_from_replay(
    candles: list[Mapping[str, Any]],
    trades: list[Mapping[str, Any]],
    *,
    warmup: int = 0,
) -> dict[str, Any]:
    """Convenience helper: aggregate candles + trades into ``regime_stats.v1``."""
    aggregator = RegimeStatsAggregator(warmup=warmup)
    for index, candle in enumerate(candles):
        aggregator.update_bar(candle, index=index)
    for trade in trades:
        aggregator.record_trade(trade)
    return aggregator.finalize()


def regime_scorecard_status_from_stats(regime_stats: Mapping[str, Any] | None) -> str:
    """Minimal PEP hook: ok when trades span multiple regimes, else unavailable."""
    if not isinstance(regime_stats, Mapping):
        return "unavailable"
    diversity = regime_stats.get("diversity_flags")
    if not isinstance(diversity, Mapping):
        return "unavailable"
    trades_count = diversity.get("regimes_with_trades_count")
    if isinstance(trades_count, int) and trades_count >= 2:
        return "ok"
    return "unavailable"


def _build_diversity_flags(
    buckets: dict[str, _RegimeBucket],
    candles_with_regime: int,
) -> dict[str, Any]:
    regimes_observed = sum(1 for bucket in buckets.values() if bucket.candle_count > 0)
    regimes_with_trades = sum(
        1
        for bucket in buckets.values()
        if bucket.entry_trade_count or bucket.exit_trade_count
    )
    hvc_count = buckets.get(_HVC_REGIME, _RegimeBucket()).candle_count
    hvc_share = (
        Decimal(hvc_count) / Decimal(candles_with_regime)
        if candles_with_regime > 0
        else Decimal("0")
    ).quantize(_RATE_Q)

    dominant_regime: str | None = None
    dominant_share = Decimal("0")
    if candles_with_regime > 0:
        for regime_id, bucket in buckets.items():
            if bucket.candle_count <= 0:
                continue
            share = Decimal(bucket.candle_count) / Decimal(candles_with_regime)
            if share > dominant_share:
                dominant_share = share
                dominant_regime = regime_id

    return {
        "hvc_candle_share": str(hvc_share),
        "regimes_observed_count": regimes_observed,
        "regimes_with_trades_count": regimes_with_trades,
        "single_regime_dominance_flag": dominant_share > _DOMINANCE_THRESHOLD,
        "dominant_regime_id": dominant_regime,
        "dominant_regime_share": str(dominant_share.quantize(_RATE_Q)),
    }


def _as_decimal(value: object) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        try:
            return Decimal(value)
        except (InvalidOperation, ValueError):
            return None
    return None


def _assert_no_trace_keys(payload: Mapping[str, Any]) -> None:
    forbidden = ("steps", "trace", "step_trace")
    for key in forbidden:
        if key in payload:
            raise ValueError(f"regime_stats must not include {key!r}")
