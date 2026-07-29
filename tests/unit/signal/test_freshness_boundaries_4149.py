"""#4149: Signal market-state freshness boundary contract."""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_services_signal = Path(__file__).resolve().parents[3] / "services" / "signal"
if str(_services_signal) not in sys.path:
    sys.path.insert(0, str(_services_signal))

from config import SignalConfig  # noqa: E402
from models import MarketData  # noqa: E402
from service import SignalEngine  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def _engine(staleness_s: int = 30) -> SignalEngine:
    config = SignalConfig(
        strategy_id="primary_breakout_v1",
        symbol="BTCUSDT",
        entry_lookback_minutes=1,
        exit_lookback_minutes=1,
        breakout_buffer=0.0,
        min_minutes_between_entries=0,
        trade_side_mode="long_only",
        market_state_staleness_s=staleness_s,
        lookback_minutes=15,
    )
    engine = SignalEngine.__new__(SignalEngine)
    engine.config = config
    engine.redis_client = MagicMock()
    engine._high_history = defaultdict(list)
    engine._low_history = defaultdict(list)
    engine._last_entry_ts_ms = {}
    engine._position_open_by_symbol = defaultdict(bool)
    from price_buffer import PriceBuffer

    engine.price_buffer = PriceBuffer(lookback_minutes=15)
    return engine


@pytest.mark.parametrize(
    ("age_s", "expect_fresh"),
    [
        (29, True),
        (30, True),
        (31, False),
    ],
)
def test_signal_market_state_freshness_boundary(age_s: int, expect_fresh: bool) -> None:
    engine = _engine(staleness_s=30)
    now_ms = 1_700_000_000_000
    state_ts = now_ms - age_s * 1000
    engine.redis_client.get.return_value = f'{{"ts_ms": {state_ts}, "regime_id": 0}}'

    # Seed one-minute breakout history and lookback horizon.
    for i in range(0, 16):
        ts = now_ms - (15 - i) * 60_000
        price = 100.0 + i * 0.01
        engine._high_history["BTCUSDT"].append((ts, price))
        engine._low_history["BTCUSDT"].append((ts, price - 1.0))
        engine.price_buffer.observe("BTCUSDT", price, ts)

    market = MarketData(
        symbol="BTCUSDT",
        price=101.0,
        timestamp=now_ms,
        close=101.0,
        high=101.0,
        low=100.0,
        volume=1.0,
        pct_change=1.0,
    )
    # Force entry path readiness via prior highs below current close.
    engine._high_history["BTCUSDT"] = [
        (now_ms - 60_000, 100.0),
        (now_ms - 30_000, 100.0),
    ]
    signal = engine._process_primary_breakout_v1(market, {})
    if expect_fresh:
        assert signal is not None
        assert signal.side == "BUY"
    else:
        assert signal is None


def test_missing_market_state_blocks_entry_fail_closed() -> None:
    engine = _engine(staleness_s=30)
    now_ms = 1_700_000_000_000
    engine.redis_client.get.return_value = None
    engine._high_history["BTCUSDT"] = [
        (now_ms - 60_000, 100.0),
        (now_ms - 30_000, 100.0),
    ]
    market = MarketData(
        symbol="BTCUSDT",
        price=101.0,
        timestamp=now_ms,
        close=101.0,
        high=101.0,
        low=100.0,
        volume=1.0,
        pct_change=1.0,
    )
    assert engine._process_primary_breakout_v1(market, {}) is None
