"""Historical input bridge for deterministic primary_breakout_v1 backtests.

This module intentionally stays narrow:
- one symbol (`BTCUSDT`)
- one timeframe (strict 1m cadence)
- one adapter-facing output (`StrategyAdapterRequest`)
- fail-closed validation for malformed historical input
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.contracts.external_adapter_contracts import StrategyAdapterRequest

PRIMARY_BREAKOUT_STRATEGY_ID = "primary_breakout_v1"
PRIMARY_BREAKOUT_SYMBOL = "BTCUSDT"
ONE_MINUTE_MS = 60_000

VALID_PRICE_POLICIES = frozenset({"close", "high", "hlc3", "ohlc4"})


class HistoricalBridgeError(ValueError):
    """Raised when historical input is not bridge-safe."""


def _apply_price_policy(row: Mapping[str, Any], policy: str) -> float:
    """Compute the effective close_now price for a candle row under a given policy.

    Policies:
    - ``close`` — settled candle close (current default, deterministic)
    - ``high`` — candle high (optimistic intrabar proxy)
    - ``hlc3`` — typical price (high + low + close) / 3 (conservative proxy)
    - ``ohlc4`` — average price (open + high + low + close) / 4 (conservative proxy)
    """
    close = _required_number(row, "close")
    if policy == "close":
        return close
    high = _required_number(row, "high")
    if policy == "high":
        return high
    low = _required_number(row, "low")
    if policy == "hlc3":
        return (high + low + close) / 3.0
    # ohlc4
    open_val = _required_number(row, "open")
    return (open_val + high + low + close) / 4.0


@dataclass(frozen=True, slots=True)
class PrimaryBreakoutBridgeConfig:
    """Canonical v1 breakout runtime config used by the historical bridge."""

    entry_lookback_minutes: int = 240
    exit_lookback_minutes: int = 120
    breakout_buffer: float = 0.0005
    min_minutes_between_entries: int = 60
    trade_side_mode: str = "long_only"
    price_policy: str = "close"

    def validate(self) -> None:
        if self.entry_lookback_minutes <= 0:
            raise HistoricalBridgeError("entry_lookback_minutes must be > 0")
        if self.exit_lookback_minutes <= 0:
            raise HistoricalBridgeError("exit_lookback_minutes must be > 0")
        if self.breakout_buffer < 0:
            raise HistoricalBridgeError("breakout_buffer must be >= 0")
        if self.min_minutes_between_entries < 0:
            raise HistoricalBridgeError("min_minutes_between_entries must be >= 0")
        if self.trade_side_mode != "long_only":
            raise HistoricalBridgeError("trade_side_mode must be long_only")
        if self.price_policy not in VALID_PRICE_POLICIES:
            raise HistoricalBridgeError(
                f"price_policy must be one of {sorted(VALID_PRICE_POLICIES)}, "
                f"got {self.price_policy!r}"
            )


def _required_number(row: Mapping[str, Any], key: str) -> float:
    value = row.get(key)
    if value is None or isinstance(value, bool):
        raise HistoricalBridgeError(f"missing required field: {key}")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise HistoricalBridgeError(f"invalid numeric field: {key}") from exc


def _required_int(row: Mapping[str, Any], key: str) -> int:
    value = row.get(key)
    if value is None or isinstance(value, bool):
        raise HistoricalBridgeError(f"missing required field: {key}")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise HistoricalBridgeError(f"invalid integer field: {key}") from exc


def _optional_bool(row: Mapping[str, Any], key: str, *, default: bool) -> bool:
    value = row.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
    raise HistoricalBridgeError(f"invalid boolean field: {key}")


def _optional_int(row: Mapping[str, Any], key: str) -> int | None:
    value = row.get(key)
    if value is None:
        return None
    if isinstance(value, bool):
        raise HistoricalBridgeError(f"invalid integer field: {key}")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise HistoricalBridgeError(f"invalid integer field: {key}") from exc


def _validate_candle_series(
    candles: Sequence[Mapping[str, Any]], *, expected_symbol: str
) -> None:
    if not candles:
        raise HistoricalBridgeError("historical candle series must not be empty")

    previous_ts_ms: int | None = None
    for index, row in enumerate(candles):
        symbol = str(row.get("symbol") or "").upper()
        if symbol != expected_symbol:
            raise HistoricalBridgeError(
                f"unexpected symbol at index {index}: {symbol or '<missing>'}"
            )

        ts_ms = _required_int(row, "ts_ms")
        if previous_ts_ms is not None:
            if ts_ms <= previous_ts_ms:
                raise HistoricalBridgeError(
                    "candles must be strictly increasing by ts_ms"
                )
            if ts_ms - previous_ts_ms != ONE_MINUTE_MS:
                raise HistoricalBridgeError(
                    "candles must have strict 1m cadence (delta 60000 ms)"
                )
        previous_ts_ms = ts_ms

        _required_number(row, "high")
        _required_number(row, "low")
        _required_number(row, "close")
        _required_int(row, "regime_id")


def build_primary_breakout_historical_bridge(
    candles: Sequence[Mapping[str, Any]],
    *,
    config: PrimaryBreakoutBridgeConfig | None = None,
) -> tuple[StrategyAdapterRequest, ...]:
    """Build deterministic adapter-ready requests for primary_breakout_v1.

    The bridge emits one request per candle after warm-up:
    - warm-up window = max(entry_lookback_minutes, exit_lookback_minutes)
    - `highest_high` and `lowest_low` are computed from history *before* current bar
    """

    active_config = config or PrimaryBreakoutBridgeConfig()
    active_config.validate()
    _validate_candle_series(candles, expected_symbol=PRIMARY_BREAKOUT_SYMBOL)

    max_lookback = max(
        active_config.entry_lookback_minutes, active_config.exit_lookback_minutes
    )
    if len(candles) <= max_lookback:
        raise HistoricalBridgeError(
            "insufficient candles for configured lookback warm-up window"
        )

    runtime_context = {
        "strategy_id": PRIMARY_BREAKOUT_STRATEGY_ID,
        "entry_lookback_minutes": active_config.entry_lookback_minutes,
        "exit_lookback_minutes": active_config.exit_lookback_minutes,
        "breakout_buffer": active_config.breakout_buffer,
        "min_minutes_between_entries": active_config.min_minutes_between_entries,
        "trade_side_mode": active_config.trade_side_mode,
    }
    requests: list[StrategyAdapterRequest] = []
    for index in range(max_lookback, len(candles)):
        row = candles[index]
        close_now = _apply_price_policy(row, active_config.price_policy)
        ts_ms = _required_int(row, "ts_ms")
        data_gap_active = _optional_bool(row, "data_gap_active", default=False)

        entry_window = candles[index - active_config.entry_lookback_minutes : index]
        exit_window = candles[index - active_config.exit_lookback_minutes : index]
        highest_high = max(_required_number(item, "high") for item in entry_window)
        lowest_low = min(_required_number(item, "low") for item in exit_window)

        market_state = {
            "regime_id": _required_int(row, "regime_id"),
            "market_state_fresh": _optional_bool(
                row, "market_state_fresh", default=True
            ),
            "regime_fresh": _optional_bool(row, "regime_fresh", default=True),
            "entry_cooldown_active": _optional_bool(
                row, "entry_cooldown_active", default=False
            ),
            "shutdown_active": _optional_bool(row, "shutdown_active", default=False),
            "kill_switch_active": _optional_bool(
                row, "kill_switch_active", default=False
            ),
            "risk_blocked": _optional_bool(row, "risk_blocked", default=False),
            "allocation_blocked": _optional_bool(
                row, "allocation_blocked", default=False
            ),
            "core_blocked": _optional_bool(row, "core_blocked", default=False),
        }
        if data_gap_active:
            market_state["data_gap_active"] = True
        else:
            market_state["close_now"] = close_now
            market_state["highest_high"] = highest_high
            market_state["lowest_low"] = lowest_low
        last_entry_ts_ms = _optional_int(row, "last_entry_ts_ms")
        if last_entry_ts_ms is not None:
            market_state["last_entry_ts_ms"] = last_entry_ts_ms

        market_event = {
            "symbol": PRIMARY_BREAKOUT_SYMBOL,
            "ts_ms": ts_ms,
            "market_state": market_state,
        }
        market_snapshot = {
            "symbol": PRIMARY_BREAKOUT_SYMBOL,
            "timestamp": ts_ms,
        }
        if data_gap_active:
            market_snapshot["volume"] = (
                _required_number(row, "volume")
                if row.get("volume") is not None
                else 0.0
            )
        else:
            market_event["price"] = close_now
            market_event["close"] = close_now
            market_snapshot["price"] = close_now
            market_snapshot["close"] = close_now
            market_snapshot["high"] = _required_number(row, "high")
            market_snapshot["low"] = _required_number(row, "low")
            market_snapshot["volume"] = (
                _required_number(row, "volume")
                if row.get("volume") is not None
                else 0.0
            )
        requests.append(
            StrategyAdapterRequest(
                symbol=PRIMARY_BREAKOUT_SYMBOL,
                market_event=market_event,
                market_snapshot=market_snapshot,
                runtime_context=runtime_context,
            )
        )

    return tuple(requests)
