"""#4149: Market-state TTL default/boundary documentation contract."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.contract]

_MARKET_SERVICE = (
    Path(__file__).resolve().parents[3] / "services" / "market" / "service.py"
)


def test_market_state_ttl_default_documented_as_120s() -> None:
    text = _MARKET_SERVICE.read_text(encoding="utf-8")
    assert 'os.getenv("MARKET_STATE_TTL_SECONDS", "120")' in text


def test_candle_market_state_ttl_default_documented_as_120s() -> None:
    candles_config = (
        Path(__file__).resolve().parents[3] / "services" / "candles" / "config.py"
    )
    text = candles_config.read_text(encoding="utf-8")
    assert 'os.getenv("CANDLE_MARKET_STATE_TTL_SECONDS", "120")' in text
