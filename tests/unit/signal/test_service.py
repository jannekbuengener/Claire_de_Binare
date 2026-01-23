"""
Unit-Tests für Signal Engine Service.

Governance: CDB_AGENT_POLICY.md, CDB_RL_SAFETY_POLICY.md
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add services to path for imports (avoid collision with built-in signal module)
services_path = Path(__file__).parent.parent.parent.parent / "services" / "signal"
if str(services_path) not in sys.path:
    sys.path.insert(0, str(services_path))

# Import from signal service package
from service import SignalEngine
from config import SignalConfig
from models import MarketData, Signal


@pytest.mark.unit
def test_service_initialization(mock_redis):
    """
    Test: Signal Engine kann initialisiert werden.
    """
    # Mock config directly instead of ENV vars (config is already loaded at import time)
    test_config = SignalConfig(
        strategy_id="test_strategy",
        threshold_pct=3.0,
        lookback_minutes=15,
        min_volume=100000.0,
    )

    with patch("service.config", test_config):
        engine = SignalEngine()

        assert engine is not None
        assert engine.config.strategy_id == "test_strategy"
        assert engine.config.threshold_pct == 3.0
        assert engine.config.lookback_minutes == 15
        assert engine.price_buffer is not None
        assert engine.running is False


@pytest.mark.unit
def test_config_validation():
    """
    Test: Config wird korrekt validiert.
    """
    # Valid config
    valid_config = SignalConfig(
        threshold_pct=3.0, lookback_minutes=15, strategy_id="test_strategy"
    )
    assert valid_config.validate() is True

    # Invalid: threshold_pct <= 0
    invalid_config_1 = SignalConfig(
        threshold_pct=0.0, lookback_minutes=15, strategy_id="test_strategy"
    )
    with pytest.raises(ValueError, match="SIGNAL_THRESHOLD_PCT muss > 0 sein"):
        invalid_config_1.validate()

    # Invalid: lookback_minutes <= 0
    invalid_config_2 = SignalConfig(
        threshold_pct=3.0, lookback_minutes=0, strategy_id="test_strategy"
    )
    with pytest.raises(ValueError, match="SIGNAL_LOOKBACK_MIN muss > 0 sein"):
        invalid_config_2.validate()

    # Invalid: empty strategy_id
    invalid_config_3 = SignalConfig(
        threshold_pct=3.0, lookback_minutes=15, strategy_id=""
    )
    with pytest.raises(ValueError, match="SIGNAL_STRATEGY_ID muss gesetzt sein"):
        invalid_config_3.validate()


@pytest.mark.unit
def test_signal_generation():
    """
    Test: Signals werden korrekt generiert.

    Prüft, dass Momentum-Strategie Signals mit korrektem Format erzeugt.
    """
    # Mock config directly
    test_config = SignalConfig(
        strategy_id="test_strategy",
        bot_id="test_bot",
        threshold_pct=3.0,
        min_volume=100000.0,
    )

    with patch("service.config", test_config):
        engine = SignalEngine()

        # Test 1: Signal wird generiert bei pct_change >= threshold
        market_data = {
            "symbol": "BTCUSDT",
            "price": 50000.0,
            "timestamp": 1609459200,
            "pct_change": 3.5,  # Above threshold
            "volume": 200000.0,  # Above min_volume
        }

        signal = engine.process_market_data(market_data)

        assert signal is not None
        assert signal.symbol == "BTCUSDT"
        assert signal.side == "BUY"
        assert signal.price == 50000.0
        assert signal.pct_change == 3.5
        assert signal.strategy_id == "test_strategy"
        assert signal.bot_id == "test_bot"
        assert "Momentum" in signal.reason

        # Test 2: Kein Signal bei pct_change < threshold
        market_data_low = {
            "symbol": "ETHUSDT",
            "price": 3000.0,
            "timestamp": 1609459200,
            "pct_change": 1.5,  # Below threshold
            "volume": 200000.0,
        }

        signal_low = engine.process_market_data(market_data_low)
        assert signal_low is None

        # Test 3: Kein Signal bei volume < min_volume
        market_data_low_vol = {
            "symbol": "ADAUSDT",
            "price": 1.5,
            "timestamp": 1609459200,
            "pct_change": 4.0,  # Above threshold
            "volume": 50000.0,  # Below min_volume
        }

        signal_low_vol = engine.process_market_data(market_data_low_vol)
        assert signal_low_vol is None


@pytest.mark.unit
def test_raw_trade_data_pct_change_calculation():
    """
    Test: Raw trade data without pct_change field gets it calculated via PriceBuffer.

    Issue #345: cdb_ws sends raw trades (no pct_change), cdb_signal must calculate it.
    """
    test_config = SignalConfig(
        strategy_id="test_strategy",
        bot_id="test_bot",
        threshold_pct=2.0,
        min_volume=100000.0,
    )

    with patch("service.config", test_config):
        engine = SignalEngine()

        # First trade: cold start (pct_change will be 0.0)
        raw_trade_1 = {
            "symbol": "BTCUSDT",
            "price": 50000.0,
            "timestamp": 1609459200,
            # NO pct_change field (raw trade data from cdb_ws)
            "volume": 200000.0,
        }

        signal_1 = engine.process_market_data(raw_trade_1)
        # No signal on cold start (pct_change = 0.0 < threshold 2.0%)
        assert signal_1 is None

        # Second trade: +3% movement (should generate signal)
        # Formula: (51500 - 50000) / 50000 * 100 = 3.0%
        raw_trade_2 = {
            "symbol": "BTCUSDT",
            "price": 51500.0,
            "timestamp": 1609459260,
            # NO pct_change field
            "volume": 200000.0,
        }

        signal_2 = engine.process_market_data(raw_trade_2)

        # Signal should be generated (3.0% > 2.0% threshold)
        assert signal_2 is not None
        assert signal_2.symbol == "BTCUSDT"
        assert signal_2.side == "BUY"
        assert signal_2.price == 51500.0
        assert signal_2.pct_change == pytest.approx(3.0, rel=1e-9)
        assert "Momentum: +3.0000%" in signal_2.reason

        # Third trade: -1% movement (should not generate signal)
        # Formula: (51000 - 51500) / 51500 * 100 = -0.97%
        raw_trade_3 = {
            "symbol": "BTCUSDT",
            "price": 51000.0,
            "timestamp": 1609459320,
            "volume": 200000.0,
        }

        signal_3 = engine.process_market_data(raw_trade_3)
        # No signal (-0.97% < 2.0% threshold)
        assert signal_3 is None


@pytest.mark.unit
def test_backward_compatibility_with_pct_change():
    """
    Test: Market data WITH pct_change field is used directly (no recalculation).

    Backward compatibility: Existing enriched market_data events should still work.
    """
    test_config = SignalConfig(
        strategy_id="test_strategy", threshold_pct=2.0, min_volume=100000.0
    )

    with patch("service.config", test_config):
        engine = SignalEngine()

        # Market data WITH pct_change (e.g., from aggregator or enriched source)
        enriched_data = {
            "symbol": "ETHUSDT",
            "price": 3000.0,
            "timestamp": 1609459200,
            "pct_change": 2.5,  # Explicitly provided
            "volume": 200000.0,
        }

        signal = engine.process_market_data(enriched_data)

        # Signal should use provided pct_change value
        assert signal is not None
        assert signal.pct_change == 2.5
        assert "Momentum: +2.5000%" in signal.reason
