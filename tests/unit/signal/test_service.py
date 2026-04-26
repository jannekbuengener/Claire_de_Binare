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
from core.contracts.external_adapter_contracts import (
    StrategyAdapterResponse,
    StrategySignalCandidate,
)


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

    invalid_breakout = SignalConfig(
        strategy_id="primary_breakout_v1", trade_side_mode="short_only"
    )
    with pytest.raises(
        ValueError,
        match="SIGNAL_TRADE_SIDE_MODE muss fuer primary_breakout_v1 long_only sein",
    ):
        invalid_breakout.validate()


@pytest.mark.unit
def test_primary_breakout_v1_rejects_non_canonical_strategy_adapter(monkeypatch):
    test_config = SignalConfig(
        strategy_id="primary_breakout_v1",
        threshold_pct=3.0,
        lookback_minutes=15,
        min_volume=100000.0,
        trade_side_mode="long_only",
    )
    monkeypatch.setenv("SIGNAL_ADAPTER_ID", "does_not_exist")

    with patch("service.config", test_config):
        with pytest.raises(SystemExit) as excinfo:
            SignalEngine()
    assert excinfo.value.code == 1


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


@pytest.mark.unit
def test_primary_breakout_v1_generates_buy_signal_on_breakout():
    test_config = SignalConfig(
        strategy_id="primary_breakout_v1",
        symbol="BTCUSDT",
        min_volume=100000.0,
        entry_lookback_minutes=3,
        exit_lookback_minutes=2,
        breakout_buffer=0.0,
        min_minutes_between_entries=60,
        trade_side_mode="long_only",
    )

    with patch("service.config", test_config):
        engine = SignalEngine()
        base_ts = 1700000000
        seed = [
            {"price": 100.0, "high": 100.0, "low": 99.0},
            {"price": 101.0, "high": 101.0, "low": 100.0},
            {"price": 102.0, "high": 102.0, "low": 101.0},
        ]
        for idx, row in enumerate(seed):
            payload = {
                "symbol": "BTCUSDT",
                "timestamp": base_ts + idx * 60,
                "price": row["price"],
                "close": row["price"],
                "high": row["high"],
                "low": row["low"],
                "volume": 200000.0,
                "regime_id": "TREND",
                "market_state_fresh": True,
                "regime_fresh": True,
            }
            assert engine.process_market_data(payload) is None

        breakout = engine.process_market_data(
            {
                "symbol": "BTCUSDT",
                "timestamp": base_ts + 180,
                "price": 103.0,
                "close": 103.0,
                "high": 103.0,
                "low": 102.0,
                "volume": 200000.0,
                "regime_id": "TREND",
                "market_state_fresh": True,
                "regime_fresh": True,
            }
        )

        assert breakout is not None
        assert breakout.side == "BUY"
        assert breakout.strategy_id == "primary_breakout_v1"
        assert breakout.reason == "breakout_entry"


@pytest.mark.unit
def test_primary_breakout_v1_respects_entry_cooldown():
    test_config = SignalConfig(
        strategy_id="primary_breakout_v1",
        symbol="BTCUSDT",
        min_volume=100000.0,
        entry_lookback_minutes=3,
        exit_lookback_minutes=2,
        breakout_buffer=0.0,
        min_minutes_between_entries=60,
        trade_side_mode="long_only",
    )

    with patch("service.config", test_config):
        engine = SignalEngine()
        base_ts = 1700000000
        for idx, price in enumerate([100.0, 101.0, 102.0, 103.0]):
            payload = {
                "symbol": "BTCUSDT",
                "timestamp": base_ts + idx * 60,
                "price": price,
                "close": price,
                "high": price,
                "low": price - 1.0,
                "volume": 200000.0,
                "regime_id": "TREND",
                "market_state_fresh": True,
                "regime_fresh": True,
            }
            signal = engine.process_market_data(payload)
            if idx < 3:
                assert signal is None
            else:
                assert signal is not None
                assert signal.side == "BUY"

        cooldown_blocked = engine.process_market_data(
            {
                "symbol": "BTCUSDT",
                "timestamp": base_ts + 240,
                "price": 104.0,
                "close": 104.0,
                "high": 104.0,
                "low": 103.0,
                "volume": 200000.0,
                "regime_id": "TREND",
                "market_state_fresh": True,
                "regime_fresh": True,
            }
        )
        assert cooldown_blocked is None


@pytest.mark.unit
def test_primary_breakout_v1_emits_sell_even_when_entry_is_blocked():
    test_config = SignalConfig(
        strategy_id="primary_breakout_v1",
        symbol="BTCUSDT",
        min_volume=100000.0,
        entry_lookback_minutes=3,
        exit_lookback_minutes=2,
        breakout_buffer=0.0,
        min_minutes_between_entries=60,
        trade_side_mode="long_only",
    )

    with patch("service.config", test_config):
        engine = SignalEngine()
        base_ts = 1700000000
        for idx, price in enumerate([100.0, 101.0, 102.0, 103.0]):
            signal = engine.process_market_data(
                {
                    "symbol": "BTCUSDT",
                    "timestamp": base_ts + idx * 60,
                    "price": price,
                    "close": price,
                    "high": price,
                    "low": price - 1.0,
                    "volume": 200000.0,
                    "regime_id": "TREND",
                    "market_state_fresh": True,
                    "regime_fresh": True,
                }
            )
            if idx == 3:
                assert signal is not None
                assert signal.side == "BUY"

        exit_signal = engine.process_market_data(
            {
                "symbol": "BTCUSDT",
                "timestamp": base_ts + 240,
                "price": 90.0,
                "close": 90.0,
                "high": 91.0,
                "low": 90.0,
                "volume": 200000.0,
                "regime_id": "RANGE",
                "market_state_fresh": False,
                "regime_fresh": False,
                "risk_blocked": True,
            }
        )

        assert exit_signal is not None
        assert exit_signal.side == "SELL"
        assert exit_signal.reason == "channel_exit"


@pytest.mark.unit
def test_signal_engine_uses_registry_selected_adapter():
    test_config = SignalConfig(
        strategy_id="test_strategy",
        bot_id="test_bot",
        threshold_pct=3.0,
        min_volume=100000.0,
    )
    adapter = MagicMock()
    adapter.adapter_id = "momentum_builtin"
    adapter.evaluate.return_value = StrategyAdapterResponse(
        signals=(
            StrategySignalCandidate(
                strategy_id="test_strategy",
                symbol="BTCUSDT",
                side="BUY",
                reason="Momentum: +3.5000% > 3.0%",
                price=50000.0,
                pct_change=3.5,
                metadata={"adapter_id": "momentum_builtin"},
            ),
        )
    )

    with patch("service.config", test_config), patch(
        "service.build_strategy_adapter", return_value=adapter
    ):
        engine = SignalEngine()
        signal = engine.process_market_data(
            {
                "symbol": "BTCUSDT",
                "price": 50000.0,
                "timestamp": 1609459200,
                "pct_change": 3.5,
                "volume": 200000.0,
            }
        )

    assert signal is not None
    adapter.evaluate.assert_called_once()
    assert signal.strategy_id == "test_strategy"
    assert signal.metadata["adapter"] == {"adapter_id": "momentum_builtin"}


@pytest.mark.unit
def test_signal_engine_fails_closed_on_unknown_adapter_id(monkeypatch):
    test_config = SignalConfig(
        strategy_id="test_strategy",
        threshold_pct=3.0,
        lookback_minutes=15,
        min_volume=100000.0,
    )
    monkeypatch.setenv("SIGNAL_ADAPTER_ID", "does_not_exist")

    with patch("service.config", test_config):
        with pytest.raises(KeyError, match="Unknown strategy adapter id"):
            SignalEngine()


@pytest.mark.unit
def test_lookback_time_vs_trade_count():
    """
    Regression: Hohe Trade-Frequenz innerhalb von Sekunden darf Lookback-Fenster (Minuten) nicht füllen.
    """
    test_config = SignalConfig(
        strategy_id="primary_breakout_v1",
        symbol="BTCUSDT",
        min_volume=100.0,
        entry_lookback_minutes=3,
        exit_lookback_minutes=2,
        breakout_buffer=0.0,
        min_minutes_between_entries=60,
        trade_side_mode="long_only",
    )

    with patch("service.config", test_config):
        engine = SignalEngine()
        symbol = "BTCUSDT"

        # Sende 10 Trades innerhalb von 10 Sekunden (alle > Vorheriger High)
        # Aber alle innerhalb derselben Minute.
        for i in range(10):
            payload = {
                "symbol": symbol,
                "timestamp": 1700000000 + i,  # +1s Schritte
                "price": 100.0 + i,
                "high": 100.0 + i,
                "low": 99.0 + i,
                "volume": 200000.0,
                "regime_id": "TREND",
                "market_state_fresh": True,
                "regime_fresh": True,
            }
            signal = engine.process_market_data(payload)
            # Erwartung: Kein Signal, da Lookback 3 Min erfordert, wir aber erst 10s Historie haben.
            # Im alten (fehlerhaften) Code waere len(highs) >= 3 erfuellt gewesen.
            assert signal is None, f"Signal fälschlicherweise bei Trade {i} generiert (Trade-Count Drift)"


@pytest.mark.unit
def test_lookback_positive_time_trigger():
    """
    Test: Nach ausreichendem Zeitfenster (Minuten) löst Breakout BUY aus.
    """
    test_config = SignalConfig(
        strategy_id="primary_breakout_v1",
        symbol="BTCUSDT",
        min_volume=100.0,
        entry_lookback_minutes=3,
        exit_lookback_minutes=2,
        breakout_buffer=0.0,
        min_minutes_between_entries=60,
        trade_side_mode="long_only",
    )

    with patch("service.config", test_config):
        engine = SignalEngine()
        symbol = "BTCUSDT"
        base_ts = 1700000000

        # Fülle Historie über 4 Minuten (1 Trade pro Minute)
        for i in range(4):
            payload = {
                "symbol": symbol,
                "timestamp": base_ts + (i * 60),  # +1m Schritte
                "price": 100.0 + i,
                "high": 100.0 + i,
                "low": 99.0 + i,
                "volume": 200000.0,
                "regime_id": "TREND",
                "market_state_fresh": True,
                "regime_fresh": True,
            }
            signal = engine.process_market_data(payload)
            if i < 3:
                assert signal is None
            else:
                # Nach 3 Minuten (4. Trade bei T+3m) sollte ein Breakout möglich sein,
                # sofern der Preis das High der letzten 3m (102.0) schlägt.
                # Aber hier ist price=103.0 und max(prior_highs) = max(100, 101, 102) = 102.0.
                assert signal is not None
                assert signal.side == "BUY"


@pytest.mark.unit
def test_lookback_gap_regression():
    """
    Regression: Nach einer langen Datenlücke darf erst dann ein Signal erfolgen,
    wenn das aktuelle Fenster zeitlich wieder gefüllt ist.
    """
    test_config = SignalConfig(
        strategy_id="primary_breakout_v1",
        symbol="BTCUSDT",
        min_volume=100.0,
        entry_lookback_minutes=3,
        exit_lookback_minutes=2,
        breakout_buffer=0.0,
        min_minutes_between_entries=60,
        trade_side_mode="long_only",
    )

    with patch("service.config", test_config):
        engine = SignalEngine()
        symbol = "BTCUSDT"
        t0 = 1700000000

        # 1. Initialer Aufbau (alt, wird später gepruned)
        for i in range(5):
            payload = {
                "symbol": symbol,
                "timestamp": t0 + i,
                "price": 100.0,
                "high": 100.0,
                "low": 99.0,
                "volume": 200000.0,
                "risk_blocked": True,  # Verhindere BUY
            }
            engine.process_market_data(payload)

        # 2. Lange Datenlücke (1 Stunde)
        t_gap = t0 + 3600

        # 3. Neue Trades innerhalb weniger Sekunden
        # Erwartung: Kein BUY, da das Fenster [t_gap - 3m, t_gap] nur Daten von vor 1 Sekunde enthält.
        for i in range(3):
            payload = {
                "symbol": symbol,
                "timestamp": t_gap + i,
                "price": 110.0,  # Deutlicher Breakout gegenüber 100.0
                "high": 110.0,
                "low": 109.0,
                "volume": 200000.0,
                "regime_id": "TREND",
                "market_state_fresh": True,
                "regime_fresh": True,
            }
            signal = engine.process_market_data(payload)
            assert (
                signal is None
            ), f"Signal fälschlicherweise nach Gap bei Trade {i} generiert (Warmup Drift)"

        # 4. Nach 3 Minuten (t_gap + 180s) sollte es wieder gehen
        payload_final = {
            "symbol": symbol,
            "timestamp": t_gap + 180,
            "price": 115.0,
            "high": 115.0,
            "low": 114.0,
            "volume": 200000.0,
            "regime_id": "TREND",
            "market_state_fresh": True,
            "regime_fresh": True,
        }
        signal = engine.process_market_data(payload_final)
        assert signal is not None
        assert signal.side == "BUY"
