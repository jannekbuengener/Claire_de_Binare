"""Unit tests for CandleAggregator - last_tick_ts_ms and last_tick_source tracking."""

import pytest
from services.candles.models import CandleAggregator


@pytest.mark.unit
def test_last_tick_ts_ms_updated_on_trade():
    """last_tick_ts_ms should be updated when a trade is processed."""
    aggregator = CandleAggregator(interval_seconds=60)

    trade = {
        "ts_ms": 1700000000000,
        "symbol": "BTCUSDT",
        "price": "50000.0",
        "trade_qty": "0.1",
    }

    aggregator.process_trade(trade)

    assert aggregator.last_tick_ts_ms.get("BTCUSDT") == 1700000000000


@pytest.mark.unit
def test_last_tick_ts_ms_monotonic_guard():
    """last_tick_ts_ms should only update if new timestamp is greater (monotonic)."""
    aggregator = CandleAggregator(interval_seconds=60)

    # First trade
    trade1 = {
        "ts_ms": 1700000002000,
        "symbol": "BTCUSDT",
        "price": "50000.0",
        "trade_qty": "0.1",
    }
    aggregator.process_trade(trade1)
    assert aggregator.last_tick_ts_ms.get("BTCUSDT") == 1700000002000

    # Out-of-order trade (older timestamp) - should NOT update
    trade2 = {
        "ts_ms": 1700000001000,  # Older than trade1
        "symbol": "BTCUSDT",
        "price": "50001.0",
        "trade_qty": "0.2",
    }
    aggregator.process_trade(trade2)
    assert (
        aggregator.last_tick_ts_ms.get("BTCUSDT") == 1700000002000
    )  # Still older value

    # Newer trade - should update
    trade3 = {
        "ts_ms": 1700000003000,
        "symbol": "BTCUSDT",
        "price": "50002.0",
        "trade_qty": "0.3",
    }
    aggregator.process_trade(trade3)
    assert aggregator.last_tick_ts_ms.get("BTCUSDT") == 1700000003000


@pytest.mark.unit
def test_last_tick_ts_ms_per_symbol():
    """last_tick_ts_ms should be tracked independently per symbol."""
    aggregator = CandleAggregator(interval_seconds=60)

    trade_btc = {
        "ts_ms": 1700000001000,
        "symbol": "BTCUSDT",
        "price": "50000.0",
        "trade_qty": "0.1",
    }
    trade_eth = {
        "ts_ms": 1700000002000,
        "symbol": "ETHUSDT",
        "price": "3000.0",
        "trade_qty": "1.0",
    }

    aggregator.process_trade(trade_btc)
    aggregator.process_trade(trade_eth)

    assert aggregator.last_tick_ts_ms.get("BTCUSDT") == 1700000001000
    assert aggregator.last_tick_ts_ms.get("ETHUSDT") == 1700000002000


@pytest.mark.unit
def test_last_tick_ts_ms_not_set_on_invalid_trade():
    """last_tick_ts_ms should not be set for invalid trades (missing fields)."""
    aggregator = CandleAggregator(interval_seconds=60)

    # Missing ts_ms
    invalid_trade = {
        "symbol": "BTCUSDT",
        "price": "50000.0",
        "trade_qty": "0.1",
    }

    aggregator.process_trade(invalid_trade)

    assert aggregator.last_tick_ts_ms.get("BTCUSDT") is None


@pytest.mark.unit
def test_last_tick_source_tracked_on_trade():
    """last_tick_source should track the source field of each trade."""
    aggregator = CandleAggregator(interval_seconds=60)

    trade = {
        "ts_ms": 1700000000000,
        "symbol": "BTCUSDT",
        "price": "50000.0",
        "trade_qty": "0.1",
        "source": "stimulus_fixture",
    }

    aggregator.process_trade(trade)

    assert aggregator.last_tick_source.get("BTCUSDT") == "stimulus_fixture"


@pytest.mark.unit
def test_last_tick_source_default_empty_on_missing_source():
    """last_tick_source should default to empty string when source is missing."""
    aggregator = CandleAggregator(interval_seconds=60)

    trade = {
        "ts_ms": 1700000000000,
        "symbol": "BTCUSDT",
        "price": "50000.0",
        "trade_qty": "0.1",
    }

    aggregator.process_trade(trade)

    assert aggregator.last_tick_source.get("BTCUSDT") == ""


@pytest.mark.unit
def test_last_tick_source_monotonic_guard():
    """last_tick_source should only update when ts_ms is newer (same guard as ts)."""
    aggregator = CandleAggregator(interval_seconds=60)

    trade1 = {
        "ts_ms": 1700000002000,
        "symbol": "BTCUSDT",
        "price": "50000.0",
        "trade_qty": "0.1",
        "source": "live_exchange",
    }
    aggregator.process_trade(trade1)
    assert aggregator.last_tick_source.get("BTCUSDT") == "live_exchange"

    # Out-of-order trade (older) — source should NOT update
    trade2 = {
        "ts_ms": 1700000001000,
        "symbol": "BTCUSDT",
        "price": "50001.0",
        "trade_qty": "0.2",
        "source": "other",
    }
    aggregator.process_trade(trade2)
    assert aggregator.last_tick_source.get("BTCUSDT") == "live_exchange"

    # Newer trade — source SHOULD update
    trade3 = {
        "ts_ms": 1700000003000,
        "symbol": "BTCUSDT",
        "price": "50002.0",
        "trade_qty": "0.3",
        "source": "stimulus_fixture",
    }
    aggregator.process_trade(trade3)
    assert aggregator.last_tick_source.get("BTCUSDT") == "stimulus_fixture"
