"""Shared Pack-A breakout helpers for Donchian and trend-filter variants.

Frozen parameters per docs/evidence/arvp_pack_a_breakout_baseline_spec_3748.md §7.2–7.5
and Batch-A registry (#4031).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Sequence

from core.replay.historical_bridge import ONE_MINUTE_MS, PRIMARY_BREAKOUT_SYMBOL

DONCHIAN_BREAKOUT_STRATEGY_ID = "donchian_breakout_v1"
BREAKOUT_TREND_FILTER_STRATEGY_ID = "breakout_trend_filter_v1"
BREAKOUT_VOLATILITY_FILTER_STRATEGY_ID = "breakout_volatility_filter_v1"
VOLATILITY_BREAKOUT_STRATEGY_ID = "volatility_breakout_v1"
BOLLINGER_SQUEEZE_BREAKOUT_STRATEGY_ID = "bollinger_squeeze_breakout_v1"
ATR_EXPANSION_STRATEGY_ID = "atr_expansion_v1"
EMA_TREND_FOLLOW_STRATEGY_ID = "ema_trend_follow_v1"
MA_CROSSOVER_STRATEGY_ID = "ma_crossover_v1"
OPENING_RANGE_BREAKOUT_STRATEGY_ID = "opening_range_breakout_v1"
PACK_A_SYMBOL = PRIMARY_BREAKOUT_SYMBOL

ENTRY_CHANNEL_BARS = 20
EXIT_CHANNEL_BARS = 10
MIN_MINUTES_BETWEEN_ENTRIES = 30
TREND_EMA_PERIOD_5M = 20
FIVE_MINUTE_MS = 5 * ONE_MINUTE_MS

ATR_PERIOD = 14
VOL_FLOOR = 0.0003
VOL_CEILING = 0.0030
BREAKOUT_LOOKBACK = 20
EXIT_LOOKBACK = 10
EXPANSION_LAG = 5
EXPANSION_MULTIPLIER = 1.15
BB_PERIOD = 20
BB_STD_DEV = 2.0
SQUEEZE_THRESHOLD = 0.015
SQUEEZE_BARS_MIN = 5
EXPANSION_CEILING = 0.04
ATR_RATIO_THRESHOLD = 0.0025
ATR_RATIO_EXIT = 0.0018
SMA_PERIOD = 20
VOL_BREAKOUT_MIN_MINUTES_BETWEEN_ENTRIES = 30
BOLLINGER_MIN_MINUTES_BETWEEN_ENTRIES = 60
ATR_EXPANSION_MIN_MINUTES_BETWEEN_ENTRIES = 60
FAST_EMA_PERIOD = 20
SLOW_EMA_PERIOD = 50
FAST_SMA_PERIOD = 20
SLOW_SMA_PERIOD = 50
TREND_MIN_MINUTES_BETWEEN_ENTRIES = 60
OR_START_UTC = "00:00"
OR_END_UTC = "01:00"
TRADE_END_UTC = "20:00"
ORB_MIN_MINUTES_BETWEEN_ENTRIES = 1440
ORB_WARMUP_BARS = 60

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
        DonchianBreakoutConfig.validate(self)
        if self.trend_ema_period_5m <= 0:
            raise PackABreakoutError("trend_ema_period_5m must be > 0")


@dataclass(frozen=True, slots=True)
class BreakoutVolatilityFilterConfig(DonchianBreakoutConfig):
    atr_period: int = ATR_PERIOD
    vol_floor: float = VOL_FLOOR
    vol_ceiling: float = VOL_CEILING

    def validate(self) -> None:
        DonchianBreakoutConfig.validate(self)
        if self.atr_period <= 0:
            raise PackABreakoutError("atr_period must be > 0")
        if self.vol_floor < 0:
            raise PackABreakoutError("vol_floor must be >= 0")
        if self.vol_ceiling <= self.vol_floor:
            raise PackABreakoutError("vol_ceiling must be > vol_floor")


@dataclass(frozen=True, slots=True)
class VolatilityBreakoutConfig:
    breakout_lookback: int = BREAKOUT_LOOKBACK
    exit_lookback: int = EXIT_LOOKBACK
    atr_period: int = ATR_PERIOD
    expansion_lag: int = EXPANSION_LAG
    expansion_multiplier: float = EXPANSION_MULTIPLIER
    min_minutes_between_entries: int = VOL_BREAKOUT_MIN_MINUTES_BETWEEN_ENTRIES
    trade_side_mode: str = "long_only"

    def validate(self) -> None:
        if self.breakout_lookback <= 0:
            raise PackABreakoutError("breakout_lookback must be > 0")
        if self.exit_lookback <= 0:
            raise PackABreakoutError("exit_lookback must be > 0")
        if self.atr_period <= 0:
            raise PackABreakoutError("atr_period must be > 0")
        if self.expansion_lag <= 0:
            raise PackABreakoutError("expansion_lag must be > 0")
        if self.expansion_multiplier <= 0:
            raise PackABreakoutError("expansion_multiplier must be > 0")
        if self.min_minutes_between_entries < 0:
            raise PackABreakoutError("min_minutes_between_entries must be >= 0")
        if self.trade_side_mode != "long_only":
            raise PackABreakoutError("trade_side_mode must be long_only")


@dataclass(frozen=True, slots=True)
class BollingerSqueezeConfig:
    bb_period: int = BB_PERIOD
    bb_std_dev: float = BB_STD_DEV
    squeeze_threshold: float = SQUEEZE_THRESHOLD
    squeeze_bars_min: int = SQUEEZE_BARS_MIN
    expansion_ceiling: float = EXPANSION_CEILING
    min_minutes_between_entries: int = BOLLINGER_MIN_MINUTES_BETWEEN_ENTRIES
    trade_side_mode: str = "long_only"

    def validate(self) -> None:
        if self.bb_period <= 0:
            raise PackABreakoutError("bb_period must be > 0")
        if self.bb_std_dev <= 0:
            raise PackABreakoutError("bb_std_dev must be > 0")
        if self.squeeze_threshold <= 0:
            raise PackABreakoutError("squeeze_threshold must be > 0")
        if self.squeeze_bars_min <= 0:
            raise PackABreakoutError("squeeze_bars_min must be > 0")
        if self.expansion_ceiling <= 0:
            raise PackABreakoutError("expansion_ceiling must be > 0")
        if self.min_minutes_between_entries < 0:
            raise PackABreakoutError("min_minutes_between_entries must be >= 0")
        if self.trade_side_mode != "long_only":
            raise PackABreakoutError("trade_side_mode must be long_only")


@dataclass(frozen=True, slots=True)
class AtrExpansionConfig:
    atr_period: int = ATR_PERIOD
    atr_ratio_threshold: float = ATR_RATIO_THRESHOLD
    atr_ratio_exit: float = ATR_RATIO_EXIT
    sma_period: int = SMA_PERIOD
    min_minutes_between_entries: int = ATR_EXPANSION_MIN_MINUTES_BETWEEN_ENTRIES
    trade_side_mode: str = "long_only"

    def validate(self) -> None:
        if self.atr_period <= 0:
            raise PackABreakoutError("atr_period must be > 0")
        if self.atr_ratio_threshold <= 0:
            raise PackABreakoutError("atr_ratio_threshold must be > 0")
        if self.atr_ratio_exit <= 0:
            raise PackABreakoutError("atr_ratio_exit must be > 0")
        if self.sma_period <= 0:
            raise PackABreakoutError("sma_period must be > 0")
        if self.min_minutes_between_entries < 0:
            raise PackABreakoutError("min_minutes_between_entries must be >= 0")
        if self.trade_side_mode != "long_only":
            raise PackABreakoutError("trade_side_mode must be long_only")


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


def breakout_volatility_filter_warmup_candles(
    config: BreakoutVolatilityFilterConfig | None = None,
) -> int:
    active = config or BreakoutVolatilityFilterConfig()
    active.validate()
    return max(active.entry_channel_bars, active.exit_channel_bars) + active.atr_period


def volatility_breakout_warmup_candles(
    config: VolatilityBreakoutConfig | None = None,
) -> int:
    active = config or VolatilityBreakoutConfig()
    active.validate()
    return active.breakout_lookback + active.expansion_lag


def bollinger_squeeze_warmup_candles(
    config: BollingerSqueezeConfig | None = None,
) -> int:
    active = config or BollingerSqueezeConfig()
    active.validate()
    return active.bb_period


def atr_expansion_warmup_candles(config: AtrExpansionConfig | None = None) -> int:
    active = config or AtrExpansionConfig()
    active.validate()
    return max(active.sma_period + active.atr_period, 50)


@dataclass(frozen=True, slots=True)
class EmaTrendFollowConfig:
    fast_ema_period: int = FAST_EMA_PERIOD
    slow_ema_period: int = SLOW_EMA_PERIOD
    min_minutes_between_entries: int = TREND_MIN_MINUTES_BETWEEN_ENTRIES
    trade_side_mode: str = "long_only"

    def validate(self) -> None:
        if self.fast_ema_period <= 0:
            raise PackABreakoutError("fast_ema_period must be > 0")
        if self.slow_ema_period <= 0:
            raise PackABreakoutError("slow_ema_period must be > 0")
        if self.fast_ema_period >= self.slow_ema_period:
            raise PackABreakoutError("fast_ema_period must be < slow_ema_period")
        if self.min_minutes_between_entries < 0:
            raise PackABreakoutError("min_minutes_between_entries must be >= 0")
        if self.trade_side_mode != "long_only":
            raise PackABreakoutError("trade_side_mode must be long_only")


@dataclass(frozen=True, slots=True)
class MaCrossoverConfig:
    fast_sma_period: int = FAST_SMA_PERIOD
    slow_sma_period: int = SLOW_SMA_PERIOD
    min_minutes_between_entries: int = TREND_MIN_MINUTES_BETWEEN_ENTRIES
    trade_side_mode: str = "long_only"

    def validate(self) -> None:
        if self.fast_sma_period <= 0:
            raise PackABreakoutError("fast_sma_period must be > 0")
        if self.slow_sma_period <= 0:
            raise PackABreakoutError("slow_sma_period must be > 0")
        if self.fast_sma_period >= self.slow_sma_period:
            raise PackABreakoutError("fast_sma_period must be < slow_sma_period")
        if self.min_minutes_between_entries < 0:
            raise PackABreakoutError("min_minutes_between_entries must be >= 0")
        if self.trade_side_mode != "long_only":
            raise PackABreakoutError("trade_side_mode must be long_only")


@dataclass(frozen=True, slots=True)
class OpeningRangeBreakoutConfig:
    or_start_utc: str = OR_START_UTC
    or_end_utc: str = OR_END_UTC
    trade_end_utc: str = TRADE_END_UTC
    min_minutes_between_entries: int = ORB_MIN_MINUTES_BETWEEN_ENTRIES
    trade_side_mode: str = "long_only"

    def validate(self) -> None:
        _parse_utc_hhmm(self.or_start_utc, field="or_start_utc")
        or_end = _parse_utc_hhmm(self.or_end_utc, field="or_end_utc")
        trade_end = _parse_utc_hhmm(self.trade_end_utc, field="trade_end_utc")
        or_start = _parse_utc_hhmm(self.or_start_utc, field="or_start_utc")
        if or_end <= or_start:
            raise PackABreakoutError("or_end_utc must be after or_start_utc")
        if trade_end <= or_end:
            raise PackABreakoutError("trade_end_utc must be after or_end_utc")
        if self.min_minutes_between_entries < 0:
            raise PackABreakoutError("min_minutes_between_entries must be >= 0")
        if self.trade_side_mode != "long_only":
            raise PackABreakoutError("trade_side_mode must be long_only")


def ema_trend_follow_warmup_candles(
    config: EmaTrendFollowConfig | None = None,
) -> int:
    active = config or EmaTrendFollowConfig()
    active.validate()
    return active.slow_ema_period


def ma_crossover_warmup_candles(config: MaCrossoverConfig | None = None) -> int:
    active = config or MaCrossoverConfig()
    active.validate()
    return active.slow_sma_period


def opening_range_breakout_warmup_candles(
    config: OpeningRangeBreakoutConfig | None = None,
) -> int:
    active = config or OpeningRangeBreakoutConfig()
    active.validate()
    return ORB_WARMUP_BARS


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


def compute_highest_high(
    highs: Sequence[float],
    lookback: int,
) -> list[float | None]:
    """Highest high over prior ``lookback`` closed bars (exclusive of index)."""
    if lookback <= 0:
        raise PackABreakoutError("lookback must be > 0")
    result: list[float | None] = [None] * len(highs)
    for index in range(len(highs)):
        if index >= lookback:
            result[index] = max(highs[index - lookback : index])
    return result


def compute_lowest_low(
    lows: Sequence[float],
    lookback: int,
) -> list[float | None]:
    """Lowest low over prior ``lookback`` closed bars (exclusive of index)."""
    if lookback <= 0:
        raise PackABreakoutError("lookback must be > 0")
    result: list[float | None] = [None] * len(lows)
    for index in range(len(lows)):
        if index >= lookback:
            result[index] = min(lows[index - lookback : index])
    return result


def compute_atr_series(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    period: int,
) -> list[float | None]:
    """Wilder ATR on closed 1m bars; ``None`` until the first smoothed value."""
    if period <= 0:
        raise PackABreakoutError("period must be > 0")
    if not (len(highs) == len(lows) == len(closes)):
        raise PackABreakoutError("highs, lows, closes length mismatch")
    if len(closes) < 2:
        return [None] * len(closes)

    true_ranges: list[float] = []
    for index in range(1, len(closes)):
        prev_close = closes[index - 1]
        tr = max(
            highs[index] - lows[index],
            abs(highs[index] - prev_close),
            abs(lows[index] - prev_close),
        )
        true_ranges.append(tr)

    atr: list[float | None] = [None] * len(closes)
    if len(true_ranges) < period:
        return atr

    seed = sum(true_ranges[:period]) / period
    atr_index = period
    atr[atr_index] = seed
    smoothed = seed
    for tr in true_ranges[period:]:
        atr_index += 1
        smoothed = (smoothed * (period - 1) + tr) / period
        atr[atr_index] = smoothed
    return atr


def compute_ema_series(
    closes: Sequence[float],
    period: int,
) -> list[float | None]:
    """EMA on closed 1m bars using SMA seed (matches core.indicators.trend.EMA)."""
    return _ema(closes, period)


def compute_sma_series(
    closes: Sequence[float],
    period: int,
) -> list[float | None]:
    """Simple moving average using closed bars inclusive of index."""
    if period <= 0:
        raise PackABreakoutError("period must be > 0")
    result: list[float | None] = [None] * len(closes)
    for index in range(period - 1, len(closes)):
        window = closes[index - period + 1 : index + 1]
        result[index] = sum(window) / period
    return result


def compute_bollinger_series(
    closes: Sequence[float],
    *,
    period: int,
    std_dev: float,
) -> tuple[list[float | None], list[float | None], list[float | None], list[float | None]]:
    """Upper/middle/lower BB and bandwidth using closed bars inclusive of index."""
    if period <= 0:
        raise PackABreakoutError("period must be > 0")
    if std_dev <= 0:
        raise PackABreakoutError("std_dev must be > 0")

    upper: list[float | None] = [None] * len(closes)
    middle: list[float | None] = [None] * len(closes)
    lower: list[float | None] = [None] * len(closes)
    bandwidth: list[float | None] = [None] * len(closes)

    for index in range(period - 1, len(closes)):
        window = closes[index - period + 1 : index + 1]
        sma = sum(window) / period
        variance = sum((value - sma) ** 2 for value in window) / period
        std = math.sqrt(variance)
        upper_band = sma + std_dev * std
        lower_band = sma - std_dev * std
        upper[index] = upper_band
        middle[index] = sma
        lower[index] = lower_band
        bandwidth[index] = (upper_band - lower_band) / sma if sma > 0 else 0.0
    return upper, middle, lower, bandwidth


def vol_ratio_in_band(
    atr_value: float | None,
    close: float,
    *,
    vol_floor: float,
    vol_ceiling: float,
) -> bool:
    if atr_value is None or close <= 0:
        return False
    ratio = atr_value / close
    return vol_floor <= ratio <= vol_ceiling


def atr_expansion_holds(
    atr_series: Sequence[float | None],
    index: int,
    *,
    expansion_lag: int,
    expansion_multiplier: float,
) -> bool:
    current = atr_series[index]
    lag_index = index - expansion_lag
    if current is None or lag_index < 0:
        return False
    lagged = atr_series[lag_index]
    if lagged is None or lagged <= 0:
        return False
    return current > lagged * expansion_multiplier


def squeeze_precedes_breakout(
    bandwidth_series: Sequence[float | None],
    index: int,
    *,
    squeeze_threshold: float,
    squeeze_bars_min: int,
) -> bool:
    if index < squeeze_bars_min:
        return False
    for offset in range(1, squeeze_bars_min + 1):
        prior = bandwidth_series[index - offset]
        if prior is None or prior >= squeeze_threshold:
            return False
    return True


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


def resolve_candle_ts_ms(row: dict[str, Any]) -> int:
    """Return candle timestamp in ms from ``ts_ms`` or ``timestamp_ms``."""
    for key in ("ts_ms", "timestamp_ms"):
        value = row.get(key)
        if value is None or isinstance(value, bool):
            continue
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise PackABreakoutError(f"invalid integer field: {key}") from exc
    raise PackABreakoutError("missing required field: ts_ms or timestamp_ms")


def is_bullish_crossover(
    fast_series: Sequence[float | None],
    slow_series: Sequence[float | None],
    index: int,
) -> bool:
    if index < 1:
        return False
    fast_prev = fast_series[index - 1]
    fast_curr = fast_series[index]
    slow_prev = slow_series[index - 1]
    slow_curr = slow_series[index]
    if None in (fast_prev, fast_curr, slow_prev, slow_curr):
        return False
    return fast_prev <= slow_prev and fast_curr > slow_curr


def is_bearish_crossover(
    fast_series: Sequence[float | None],
    slow_series: Sequence[float | None],
    index: int,
) -> bool:
    if index < 1:
        return False
    fast_prev = fast_series[index - 1]
    fast_curr = fast_series[index]
    slow_prev = slow_series[index - 1]
    slow_curr = slow_series[index]
    if None in (fast_prev, fast_curr, slow_prev, slow_curr):
        return False
    return fast_prev >= slow_prev and fast_curr < slow_curr


def _parse_utc_hhmm(value: str, *, field: str) -> int:
    parts = value.split(":")
    if len(parts) != 2:
        raise PackABreakoutError(f"{field} must be HH:MM")
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError as exc:
        raise PackABreakoutError(f"{field} must be HH:MM") from exc
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise PackABreakoutError(f"{field} must be a valid UTC time")
    return hour * 60 + minute


def utc_minutes_of_day(ts_ms: int) -> int:
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    return dt.hour * 60 + dt.minute


def utc_day_key(ts_ms: int) -> str:
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d")


def orb_session_phase(
    ts_ms: int,
    *,
    or_start_utc: str,
    or_end_utc: str,
    trade_end_utc: str,
) -> str:
    """Return ``opening_range``, ``trading``, or ``closed`` for a UTC timestamp."""
    minute = utc_minutes_of_day(ts_ms)
    or_start = _parse_utc_hhmm(or_start_utc, field="or_start_utc")
    or_end = _parse_utc_hhmm(or_end_utc, field="or_end_utc")
    trade_end = _parse_utc_hhmm(trade_end_utc, field="trade_end_utc")
    if or_start <= minute < or_end:
        return "opening_range"
    if or_end <= minute < trade_end:
        return "trading"
    return "closed"
