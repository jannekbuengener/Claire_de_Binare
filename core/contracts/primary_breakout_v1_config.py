"""Canonical config surface for the first-party primary_breakout_v1 strategy.

This module is intentionally narrow:
- no adapter implementation
- no service wiring
- no dynamic parameter bags
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Final, Literal, Mapping


PRIMARY_BREAKOUT_V1_STRATEGY_ID: Final = "primary_breakout_v1"
PRIMARY_BREAKOUT_V1_SYMBOL: Final = "BTCUSDT"
PRIMARY_BREAKOUT_V1_TRADE_SIDE_MODE: Final = "long_only"

PrimaryBreakoutV1StrategyId = Literal["primary_breakout_v1"]
PrimaryBreakoutV1Symbol = Literal["BTCUSDT"]
PrimaryBreakoutV1TradeSideMode = Literal["long_only"]

_ALLOWED_CONFIG_KEYS = frozenset(
    {
        "strategy_id",
        "symbol",
        "entry_lookback_minutes",
        "exit_lookback_minutes",
        "breakout_buffer",
        "min_minutes_between_entries",
        "trade_side_mode",
    }
)


def _require_exact_value(name: str, actual: object, expected: object) -> None:
    if actual != expected:
        raise ValueError(f"{name} must be {expected!r}, got {actual!r}")


def _require_positive_int(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer, got {value!r}")
    if value <= 0:
        raise ValueError(f"{name} must be > 0, got {value!r}")


def _require_non_negative_number(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number, got {value!r}")
    if value < 0:
        raise ValueError(f"{name} must be >= 0, got {value!r}")


@dataclass(frozen=True, slots=True)
class PrimaryBreakoutV1Config:
    """Small, canonical config surface for primary_breakout_v1."""

    strategy_id: PrimaryBreakoutV1StrategyId = PRIMARY_BREAKOUT_V1_STRATEGY_ID
    symbol: PrimaryBreakoutV1Symbol = PRIMARY_BREAKOUT_V1_SYMBOL
    entry_lookback_minutes: int = 240
    exit_lookback_minutes: int = 120
    breakout_buffer: float = 0.0005
    min_minutes_between_entries: int = 60
    trade_side_mode: PrimaryBreakoutV1TradeSideMode = (
        PRIMARY_BREAKOUT_V1_TRADE_SIDE_MODE
    )

    def __post_init__(self) -> None:
        _require_exact_value(
            "strategy_id", self.strategy_id, PRIMARY_BREAKOUT_V1_STRATEGY_ID
        )
        _require_exact_value("symbol", self.symbol, PRIMARY_BREAKOUT_V1_SYMBOL)
        _require_positive_int(
            "entry_lookback_minutes", self.entry_lookback_minutes
        )
        _require_positive_int("exit_lookback_minutes", self.exit_lookback_minutes)
        _require_non_negative_number("breakout_buffer", self.breakout_buffer)
        _require_positive_int(
            "min_minutes_between_entries", self.min_minutes_between_entries
        )
        _require_exact_value(
            "trade_side_mode",
            self.trade_side_mode,
            PRIMARY_BREAKOUT_V1_TRADE_SIDE_MODE,
        )

    @classmethod
    def from_mapping(
        cls, values: Mapping[str, Any] | None = None
    ) -> "PrimaryBreakoutV1Config":
        """Build a canonical config from a strict mapping."""

        if values is None:
            return cls()

        unknown_keys = sorted(set(values) - _ALLOWED_CONFIG_KEYS)
        if unknown_keys:
            unknown = ", ".join(unknown_keys)
            raise ValueError(f"Unknown primary_breakout_v1 config field(s): {unknown}")

        return cls(**dict(values))

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict for schema validation or serialization."""

        return asdict(self)


PRIMARY_BREAKOUT_V1_DEFAULT_CONFIG = PrimaryBreakoutV1Config()

