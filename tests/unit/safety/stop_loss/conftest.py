"""Shared fixtures for the stop-loss consumer slice (Issue #4186)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from core.safety.stop_loss import (
    PositionSide,
    PositionSnapshot,
    PriceObservation,
    StopLossTriggerConfig,
)

NOW_MS = 1_800_000_000_000


@pytest.fixture
def now_ms() -> int:
    return NOW_MS


@pytest.fixture
def config() -> StopLossTriggerConfig:
    return StopLossTriggerConfig(stop_loss_pct=Decimal("0.02"))


@pytest.fixture
def long_position() -> PositionSnapshot:
    return PositionSnapshot(
        symbol="BTCUSDT",
        side=PositionSide.LONG,
        quantity=Decimal("0.5"),
        entry_price=Decimal("100.00"),
        position_id="pos-long-1",
        opened_at_ms=NOW_MS - 60_000,
    )


@pytest.fixture
def short_position() -> PositionSnapshot:
    return PositionSnapshot(
        symbol="BTCUSDT",
        side=PositionSide.SHORT,
        quantity=Decimal("0.5"),
        entry_price=Decimal("100.00"),
        position_id="pos-short-1",
        opened_at_ms=NOW_MS - 60_000,
    )


def observation(
    price: str,
    *,
    observed_at_ms: int = NOW_MS - 1_000,
    symbol: str = "BTCUSDT",
    source: str = "market_state:BTCUSDT",
) -> PriceObservation:
    """Build a price observation with decimal-string input."""
    return PriceObservation(
        symbol=symbol,
        price=Decimal(price),
        observed_at_ms=observed_at_ms,
        source=source,
    )


@pytest.fixture
def breach_observation() -> PriceObservation:
    """Price below the 2% long stop (98.00)."""
    return observation("97.50")


@pytest.fixture
def safe_observation() -> PriceObservation:
    """Price above the 2% long stop."""
    return observation("99.00")
