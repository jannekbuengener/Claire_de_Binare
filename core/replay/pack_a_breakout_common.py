"""Shared Pack-A breakout helpers for Donchian and trend-filter variants.

Frozen parameters per docs/evidence/arvp_pack_a_breakout_baseline_spec_3748.md §7.2–7.3.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from core.replay.historical_bridge import ONE_MINUTE_MS, PRIMARY_BREAKOUT_SYMBOL

DONCHIAN_BREAKOUT_STRATEGY_ID = "donchian_breakout_v1"
BREAKOUT_TREND_FILTER_STRATEGY_ID = "breakout_trend_filter_v1"
PACK_A_SYMBOL = PRIMARY_BREAKOUT_SYMBOL

ENTRY_CHANNEL_BARS = 20
EXIT_CHANNEL_BARS = 10
MIN_MINUTES_BETWEEN_ENTRIES = 30
TREND_EMA_PERIOD_5M = 20
FIVE_MINUTE_MS = 5 * ONE_MINUTE_MS

ORDER_SIZE = 1.0
ORDER_BOOK_DEPTH_MULT = 10_000.0


class PackABreakoutError(ValueError):
    """Raised when Pack-A breakout input is invalid."""


@dataclass(frozen=True, slots=True)
class DonchianBreakoutConfig:
    entry_channel_bars: int = ENTRY_CHANNEL_BARS
    exit_channel_bars: int = EXIT_CHANNEL_BARS
    min_minutes_between_entries: int = MIN_MINUTES_BETWEEN_ENTRIES
    trade_side_mode: str = "long_only"

    def validate(self) -> None:
        if self.entry_channel_bars <= 0:
            raise PackABreakoutError("entry_channel_bars must be > 0")
        if self.exit_channel_bars <= 0:
            raise PackABreakoutError("exit_channel_bars must be > 0")
        if self.min_minutes_between_entries < 0:
            raise PackABreakoutError("min_minutes_between_entries must be >= 0")
        if self.trade_side_mode != "long_only":
            raise PackABreakoutError("trade_side_mode must be long_only")


@dataclass(frozen=True, slots=True)
class BreakoutTrendFilterConfig(DonchianBreakoutConfig):
    trend_ema_period_5m: int = TREND_EMA_PERIOD_5M

    def validate(self) -> None:
        super().validate()
        if self.trend_ema_period_5m <= 0:
            raise PackABreakoutError("trend_ema_period_5m must be > 0")


def donchian_warmup_candles(config: DonchianBreakoutConfig | None = None) -> int:
    active = config or DonchianBreakoutConfig()
    active.validate()
    return max(active.entry_channel_bars, active.exit_channel_bars)


def breakout_trend_warmup_candles(
    config: BreakoutTrendFilterConfig | None = None,
) -> int:
    active = config or BreakoutTrendFilterConfig()
    active.validate()
    # Need enough 1m bars to form trend_ema_period completed 5m bars plus Donchian lookback.
    min_5m_bars = active.trend_ema_period_5m
    min_1m_for_5m = min_5m_bars * 5
    return max(donchian_warmup_candles(active), min_1m_for_5m)


def _required_float(row: dict[str, Any], key: str) -> float:
    value = row.get(key)
    if value is None or isinstance(value, bool):
        raise PackABreakoutError(f"missing required field: {key}")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise PackABreakoutError(f"invalid numeric field: {key}") from exc


def _required_int(row: dict[str, Any], key: str) -> int:
    value = row.get(key)
    if value is None or isinstance(value, bool):
        raise PackABreakoutError(f"missing required field: {key}")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise PackABreakoutError(f"invalid integer field: {key}") from exc


def validate_pack_a_candle_series(
    candles: Sequence[dict[str, Any]], *, expected_symbol: str = PACK_A_SYMBOL
) -> None:
    if not candles:
        raise PackABreakoutError("historical candle series must not be empty")

    previous_ts_ms: int | None = None
    for index, row in enumerate(candles):
        symbol = str(row.get("symbol") or "").upper()
        if symbol != expected_symbol:
            raise PackABreakoutError(
                f"unexpected symbol at index {index}: {symbol or '<missing>'}"
            )
        ts_ms = _required_int(row, "ts_ms")
        if previous_ts_ms is not None:
            if ts_ms <= previous_ts_ms:
                raise PackABreakoutError("candles must be strictly increasing by ts_ms")
            if ts_ms - previous_ts_ms != ONE_MINUTE_MS:
                raise PackABreakoutError(
                    "candles must have strict 1m cadence (delta 60000 ms)"
                )
        previous_ts_ms = ts_ms
        _required_float(row, "high")
        _required_float(row, "low")
        _required_float(row, "close")


def compute_donchian_channels(
    highs: Sequence[float],
    lows: Sequence[float],
    *,
    entry_channel_bars: int,
    exit_channel_bars: int,
) -> tuple[list[float | None], list[float | None]]:
    """Upper/lower Donchian channels using prior closed bars only (exclusive of index)."""
    upper: list[float | None] = [None] * len(highs)
    lower: list[float | None] = [None] * len(highs)
    for index in range(len(highs)):
        if index >= entry_channel_bars:
            window = highs[index - entry_channel_bars : index]
            upper[index] = max(window)
        if index >= exit_channel_bars:
            window = lows[index - exit_channel_bars : index]
            lower[index] = min(window)
    return upper, lower


def _ema(values: Sequence[float], period: int) -> list[float | None]:
    if period <= 0:
        raise PackABreakoutError("EMA period must be > 0")
    result: list[float | None] = [None] * len(values)
    if len(values) < period:
        return result
    seed = sum(values[:period]) / period
    result[period - 1] = seed
    multiplier = 2.0 / (period + 1)
    ema_val = seed
    for index in range(period, len(values)):
        ema_val = (values[index] - ema_val) * multiplier + ema_val
        result[index] = ema_val
    return result


def _collect_completed_5m_closes(
    ts_ms_values: Sequence[int], closes: Sequence[float]
) -> list[tuple[int, float]]:
    """Return (end_ts_ms, close) for each completed 5m bar in chronological order."""
    if len(ts_ms_values) != len(closes):
        raise PackABreakoutError("ts_ms and closes length mismatch")

    completed: list[tuple[int, float]] = []
    bucket_start: int | None = None
    bucket_close: float | None = None
    bars_in_bucket = 0

    for ts_ms, close in zip(ts_ms_values, closes, strict=True):
        aligned_start = ts_ms - (ts_ms % FIVE_MINUTE_MS)
        if bucket_start is None or aligned_start != bucket_start:
            if bucket_start is not None and bars_in_bucket == 5 and bucket_close is not None:
                completed.append((ts_ms - ONE_MINUTE_MS, bucket_close))
            bucket_start = aligned_start
            bucket_close = close
            bars_in_bucket = 1
        else:
            bucket_close = close
            bars_in_bucket += 1

    return completed


def build_trend_gate_series(
    ts_ms_values: Sequence[int],
    closes: Sequence[float],
    *,
    trend_ema_period_5m: int,
) -> list[bool | None]:
    """True when last completed 5m close > EMA(trend_ema_period_5m) on 5m series."""
    completed = _collect_completed_5m_closes(ts_ms_values, closes)
    if not completed:
        return [None] * len(closes)

    closes_5m = [value for _, value in completed]
    end_ts_5m = [end_ts for end_ts, _ in completed]
    ema_5m = _ema(closes_5m, trend_ema_period_5m)

    gate: list[bool | None] = [None] * len(closes)
    completed_idx = -1
    for index, ts_ms in enumerate(ts_ms_values):
        while (
            completed_idx + 1 < len(end_ts_5m)
            and end_ts_5m[completed_idx + 1] <= ts_ms
        ):
            completed_idx += 1
        if completed_idx < 0:
            continue
        ema_val = ema_5m[completed_idx]
        close_5m = closes_5m[completed_idx]
        if ema_val is None:
            continue
        gate[index] = close_5m > ema_val
    return gate


def cooldown_allows_entry(
    ts_ms: int,
    last_entry_ts_ms: int | None,
    *,
    min_minutes_between_entries: int,
) -> bool:
    if last_entry_ts_ms is None:
        return True
    return ts_ms - last_entry_ts_ms >= min_minutes_between_entries * ONE_MINUTE_MS
