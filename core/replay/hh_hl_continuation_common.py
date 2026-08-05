"""Shared config and swing helpers for hh_hl_continuation_v1 (#4372)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Sequence

from core.replay.pack_a_breakout_common import (
    ONE_MINUTE_MS,
    ORDER_BOOK_DEPTH_MULT,
    ORDER_SIZE,
    PACK_A_SYMBOL,
    PackABreakoutError,
    cooldown_allows_entry,
)

HH_HL_CONTINUATION_STRATEGY_ID = "hh_hl_continuation_v1"
HH_HL_CONTINUATION_CONTRACT_VERSION = "cdb.batch_b.hh_hl_continuation_v1.spec.1"
HH_HL_CONTINUATION_SPEC_REF = "docs/evidence/arvp_hh_hl_continuation_v1_spec_4372.md"
BATCH_B_SHADOW_ADAPTER_ID = "batch_b_shadow_runner_v1"

SWING_LEFT_BARS = 2
SWING_RIGHT_BARS = 2
MIN_MINUTES_BETWEEN_ENTRIES = 60


@dataclass(frozen=True, slots=True)
class HhHlContinuationConfig:
    swing_left_bars: int = SWING_LEFT_BARS
    swing_right_bars: int = SWING_RIGHT_BARS
    min_minutes_between_entries: int = MIN_MINUTES_BETWEEN_ENTRIES
    trade_side_mode: str = "long_only"

    def validate(self) -> None:
        if self.swing_left_bars <= 0:
            raise PackABreakoutError("swing_left_bars must be > 0")
        if self.swing_right_bars <= 0:
            raise PackABreakoutError("swing_right_bars must be > 0")
        if self.min_minutes_between_entries < 0:
            raise PackABreakoutError("min_minutes_between_entries must be >= 0")
        if self.trade_side_mode != "long_only":
            raise PackABreakoutError("trade_side_mode must be long_only")


@dataclass(frozen=True, slots=True)
class ConfirmedSwing:
    pivot_index: int
    confirmation_index: int
    price: float
    ts_ms: int


def hh_hl_warmup_candles(config: HhHlContinuationConfig | None = None) -> int:
    cfg = config or HhHlContinuationConfig()
    cfg.validate()
    return int(cfg.swing_left_bars + cfg.swing_right_bars)


def frozen_hh_hl_parameters(
    config: HhHlContinuationConfig | None = None,
) -> dict[str, Any]:
    cfg = config or HhHlContinuationConfig()
    cfg.validate()
    return {
        "swing_left_bars": cfg.swing_left_bars,
        "swing_right_bars": cfg.swing_right_bars,
        "min_minutes_between_entries": cfg.min_minutes_between_entries,
        "trade_side_mode": cfg.trade_side_mode,
    }


def _required_finite_float(row: dict[str, Any], key: str) -> float:
    value = row.get(key)
    if value is None or isinstance(value, bool):
        raise PackABreakoutError(f"missing required field: {key}")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise PackABreakoutError(f"invalid numeric field: {key}") from exc
    if not math.isfinite(number):
        raise PackABreakoutError(f"non-finite numeric field: {key}")
    if number <= 0.0:
        raise PackABreakoutError(f"non-positive price field: {key}")
    return number


def _required_int(row: dict[str, Any], key: str) -> int:
    value = row.get(key)
    if value is None or isinstance(value, bool):
        raise PackABreakoutError(f"missing required field: {key}")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise PackABreakoutError(f"invalid integer field: {key}") from exc


def validate_hh_hl_candle_series(
    candles: Sequence[dict[str, Any]],
    *,
    expected_symbol: str = PACK_A_SYMBOL,
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

        open_px = _required_finite_float(row, "open")
        high_px = _required_finite_float(row, "high")
        low_px = _required_finite_float(row, "low")
        close_px = _required_finite_float(row, "close")
        if high_px < low_px:
            raise PackABreakoutError(f"high < low at index {index}")
        if high_px < open_px or high_px < close_px:
            raise PackABreakoutError(
                f"high does not dominate open/close at index {index}"
            )
        if low_px > open_px or low_px > close_px:
            raise PackABreakoutError(f"low does not floor open/close at index {index}")


def _is_swing_high(
    highs: Sequence[float],
    pivot: int,
    *,
    left: int,
    right: int,
) -> bool:
    pivot_high = highs[pivot]
    for j in range(pivot - left, pivot):
        if highs[j] >= pivot_high:
            return False
    for j in range(pivot + 1, pivot + right + 1):
        if highs[j] >= pivot_high:
            return False
    return True


def _is_swing_low(
    lows: Sequence[float],
    pivot: int,
    *,
    left: int,
    right: int,
) -> bool:
    pivot_low = lows[pivot]
    for j in range(pivot - left, pivot):
        if lows[j] <= pivot_low:
            return False
    for j in range(pivot + 1, pivot + right + 1):
        if lows[j] <= pivot_low:
            return False
    return True


def confirmed_swing_at(
    highs: Sequence[float],
    lows: Sequence[float],
    ts_values: Sequence[int],
    confirmation_index: int,
    *,
    config: HhHlContinuationConfig,
    kind: str,
) -> ConfirmedSwing | None:
    """Return swing confirmed exactly at ``confirmation_index``, else None."""
    left = config.swing_left_bars
    right = config.swing_right_bars
    pivot = confirmation_index - right
    if pivot < left:
        return None
    if confirmation_index >= len(highs):
        return None
    if kind == "high":
        if not _is_swing_high(highs, pivot, left=left, right=right):
            return None
        price = highs[pivot]
    elif kind == "low":
        if not _is_swing_low(lows, pivot, left=left, right=right):
            return None
        price = lows[pivot]
    else:
        raise PackABreakoutError(f"unknown swing kind: {kind}")
    return ConfirmedSwing(
        pivot_index=pivot,
        confirmation_index=confirmation_index,
        price=float(price),
        ts_ms=int(ts_values[pivot]),
    )


def structure_is_hh_hl(
    swing_highs: Sequence[ConfirmedSwing],
    swing_lows: Sequence[ConfirmedSwing],
) -> bool:
    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return False
    return (
        swing_highs[-1].price > swing_highs[-2].price
        and swing_lows[-1].price > swing_lows[-2].price
    )


__all__ = [
    "BATCH_B_SHADOW_ADAPTER_ID",
    "ConfirmedSwing",
    "HH_HL_CONTINUATION_CONTRACT_VERSION",
    "HH_HL_CONTINUATION_SPEC_REF",
    "HH_HL_CONTINUATION_STRATEGY_ID",
    "HhHlContinuationConfig",
    "MIN_MINUTES_BETWEEN_ENTRIES",
    "ORDER_BOOK_DEPTH_MULT",
    "ORDER_SIZE",
    "SWING_LEFT_BARS",
    "SWING_RIGHT_BARS",
    "confirmed_swing_at",
    "cooldown_allows_entry",
    "frozen_hh_hl_parameters",
    "hh_hl_warmup_candles",
    "structure_is_hh_hl",
    "validate_hh_hl_candle_series",
]
