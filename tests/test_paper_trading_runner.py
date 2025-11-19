"""
Tests for Paper Trading Runner

Basic tests to ensure paper trading system works correctly.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from services.paper_execution import PaperExecutionEngine
from services.paper_trading_runner import PaperTradingRunner
from services.trading_statistics import TradingStatistics


# ==============================================================================
# PAPER EXECUTION TESTS
# ==============================================================================


@pytest.mark.unit
def test_paper_execution_buy_order():
    """Test paper execution of buy order."""
    engine = PaperExecutionEngine()

    order = {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "size": 0.1,
        "order_type": "MARKET",
    }

    current_price = 50000.0

    result = engine.execute_order(order, current_price)

    assert result["status"] == "FILLED"
    assert result["filled_quantity"] == 0.1
    assert result["fill_price"] > current_price  # Slippage for buy
    assert result["fees"] > 0


@pytest.mark.unit
def test_paper_execution_sell_order():
    """Test paper execution of sell order."""
    engine = PaperExecutionEngine()

    # First buy to create position
    buy_order = {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "size": 0.1,
        "order_type": "MARKET",
    }
    engine.execute_order(buy_order, 50000.0)

    # Then sell
    sell_order = {
        "symbol": "BTCUSDT",
        "side": "SELL",
        "size": 0.1,
        "order_type": "MARKET",
    }

    result = engine.execute_order(sell_order, 51000.0)

    assert result["status"] == "FILLED"
    assert result["filled_quantity"] == 0.1
    assert result["fill_price"] < 51000.0  # Slippage for sell


@pytest.mark.unit
def test_paper_execution_position_tracking():
    """Test position tracking in paper execution."""
    engine = PaperExecutionEngine()

    # Buy 0.1 BTC
    order1 = {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "size": 0.1,
        "order_type": "MARKET",
    }
    engine.execute_order(order1, 50000.0)

    position = engine.get_position("BTCUSDT")
    assert position is not None
    assert position["quantity"] == 0.1
    assert position["avg_entry_price"] > 0

    # Buy another 0.1 BTC (average entry should update)
    order2 = {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "size": 0.1,
        "order_type": "MARKET",
    }
    engine.execute_order(order2, 51000.0)

    position = engine.get_position("BTCUSDT")
    assert position["quantity"] == 0.2


@pytest.mark.unit
def test_paper_execution_realized_pnl():
    """Test realized P&L calculation."""
    engine = PaperExecutionEngine()

    # Buy at 50000
    buy = {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "size": 0.1,
        "order_type": "MARKET",
    }
    engine.execute_order(buy, 50000.0)

    # Sell at 55000 (profit)
    sell = {
        "symbol": "BTCUSDT",
        "side": "SELL",
        "size": 0.1,
        "order_type": "MARKET",
    }
    engine.execute_order(sell, 55000.0)

    position = engine.get_position("BTCUSDT")
    assert position["realized_pnl"] > 0  # Should have profit


# ==============================================================================
# TRADING STATISTICS TESTS
# ==============================================================================


@pytest.mark.unit
def test_statistics_initial_state():
    """Test statistics initial state."""
    stats = TradingStatistics(initial_equity=100_000.0)

    result = stats.calculate_statistics()

    assert result["total_trades"] == 0
    assert result["win_rate"] == 0.0
    assert result["total_pnl"] == 0.0
    assert result["initial_equity"] == 100_000.0
    assert result["final_equity"] == 100_000.0


@pytest.mark.unit
def test_statistics_trade_tracking():
    """Test trade tracking in statistics."""
    stats = TradingStatistics(initial_equity=100_000.0)

    timestamp = datetime.now(timezone.utc)

    # Add winning trade
    stats.add_trade_close("BTCUSDT", 1000.0, timestamp)

    # Add losing trade
    stats.add_trade_close("ETHUSDT", -500.0, timestamp)

    result = stats.calculate_statistics()

    assert result["total_trades"] == 2
    assert result["winning_trades"] == 1
    assert result["losing_trades"] == 1
    assert result["win_rate"] == 0.5
    assert result["total_pnl"] == 500.0
    assert result["final_equity"] == 100_500.0


@pytest.mark.unit
def test_statistics_max_drawdown():
    """Test max drawdown calculation."""
    stats = TradingStatistics(initial_equity=100_000.0)

    timestamp = datetime.now(timezone.utc)

    # Series of trades causing drawdown
    stats.add_trade_close("BTCUSDT", 5000.0, timestamp)  # Peak: 105000
    stats.add_trade_close("ETHUSDT", -10000.0, timestamp)  # Drawdown
    stats.add_trade_close("SOLUSDT", 3000.0, timestamp)  # Recovery

    result = stats.calculate_statistics()

    assert result["max_drawdown_pct"] > 0
    assert result["peak_equity"] == 105_000.0


# ==============================================================================
# PAPER TRADING RUNNER TESTS
# ==============================================================================


@pytest.mark.unit
def test_runner_initialization():
    """Test runner initialization."""
    runner = PaperTradingRunner(
        strategy_name="test_strategy",
        risk_profile="balanced",
        initial_equity=100_000.0,
    )

    assert runner.strategy_name == "test_strategy"
    assert runner.risk_profile == "balanced"
    assert runner.initial_equity == 100_000.0
    assert runner.risk_config is not None


@pytest.mark.unit
def test_runner_signal_generation():
    """Test signal generation from market data."""
    runner = PaperTradingRunner()

    # Strong upward momentum (should generate BUY)
    market_data_up = {
        "symbol": "BTCUSDT",
        "price": 50000.0,
        "volume": 500.0,
        "pct_change": 3.5,  # >3% = signal
        "timestamp": datetime.now(timezone.utc),
    }

    signal = runner._generate_signal(market_data_up)

    assert signal is not None
    assert signal["side"] == "BUY"
    assert signal["symbol"] == "BTCUSDT"

    # Strong downward momentum (should generate SELL)
    market_data_down = {
        "symbol": "BTCUSDT",
        "price": 50000.0,
        "volume": 500.0,
        "pct_change": -3.5,
        "timestamp": datetime.now(timezone.utc),
    }

    signal = runner._generate_signal(market_data_down)

    assert signal is not None
    assert signal["side"] == "SELL"

    # Weak movement (no signal)
    market_data_weak = {
        "symbol": "BTCUSDT",
        "price": 50000.0,
        "volume": 500.0,
        "pct_change": 1.0,  # <3% = no signal
        "timestamp": datetime.now(timezone.utc),
    }

    signal = runner._generate_signal(market_data_weak)

    assert signal is None


@pytest.mark.unit
def test_runner_complete_run():
    """Test complete paper trading run with mock data."""
    runner = PaperTradingRunner(
        strategy_name="momentum_v1",
        risk_profile="balanced",
        initial_equity=100_000.0,
    )

    # Create mock market data (7 days)
    mock_data = []
    base_time = datetime.now(timezone.utc)

    for hour in range(24 * 7):  # 7 days of hourly data
        timestamp = base_time + timedelta(hours=hour)

        # Simulate price movement
        import random

        random.seed(hour)  # Deterministic
        pct_change = random.uniform(-5.0, 5.0)

        event = {
            "timestamp": timestamp,
            "symbol": "BTCUSDT",
            "price": 50000.0 + (hour * 10),  # Trending up
            "volume": random.uniform(100, 1000),
            "pct_change": pct_change,
        }

        mock_data.append(event)

    # Run with mock data
    result = runner.run(market_data_events=mock_data)

    # Verify result structure
    assert "strategy" in result
    assert "statistics" in result
    assert "equity_curve" in result
    assert "trades" in result

    # Should have some trades
    stats = result["statistics"]
    assert "total_trades" in stats
    assert "final_equity" in stats


# ==============================================================================
# RISK PROFILE TESTS
# ==============================================================================


@pytest.mark.unit
def test_risk_profiles_different():
    """Test that risk profiles have different limits."""
    conservative = PaperTradingRunner(risk_profile="conservative")
    balanced = PaperTradingRunner(risk_profile="balanced")
    aggressive = PaperTradingRunner(risk_profile="aggressive")

    # Position size limits should differ
    assert (
        conservative.risk_config["MAX_POSITION_PCT"]
        < balanced.risk_config["MAX_POSITION_PCT"]
        < aggressive.risk_config["MAX_POSITION_PCT"]
    )

    # Drawdown limits should differ
    assert (
        conservative.risk_config["MAX_DAILY_DRAWDOWN_PCT"]
        < balanced.risk_config["MAX_DAILY_DRAWDOWN_PCT"]
        < aggressive.risk_config["MAX_DAILY_DRAWDOWN_PCT"]
    )


# ==============================================================================
# SCENARIO ORCHESTRATOR TESTS
# ==============================================================================


@pytest.mark.unit
def test_scenario_orchestrator_load_config(tmp_path):
    """Test scenario config loading."""
    from services.scenario_orchestrator import ScenarioOrchestrator

    # Create test config
    config_file = tmp_path / "test_scenarios.yaml"
    config_file.write_text("""
scenarios:
  - name: "Test Scenario"
    strategy: "momentum_v1"
    risk_profile: "balanced"
    period:
      days: 7
""")

    orchestrator = ScenarioOrchestrator(
        config_path=config_file,
        output_dir=tmp_path / "output"
    )

    assert orchestrator.config is not None
    assert "scenarios" in orchestrator.config
    assert len(orchestrator.config["scenarios"]) == 1
    assert orchestrator.config["scenarios"][0]["name"] == "Test Scenario"


@pytest.mark.unit
def test_scenario_orchestrator_missing_config():
    """Test error when config file doesn't exist."""
    from services.scenario_orchestrator import ScenarioOrchestrator
    from pathlib import Path

    with pytest.raises(FileNotFoundError):
        ScenarioOrchestrator(
            config_path=Path("/nonexistent/config.yaml"),
            output_dir=Path("/tmp/output")
        )


@pytest.mark.unit
def test_scenario_orchestrator_invalid_config(tmp_path):
    """Test error when config is invalid."""
    from services.scenario_orchestrator import ScenarioOrchestrator

    # Create invalid config (missing 'scenarios' key)
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text("""
some_key: "some_value"
""")

    with pytest.raises(ValueError, match="scenarios"):
        ScenarioOrchestrator(
            config_path=config_file,
            output_dir=tmp_path / "output"
        )


@pytest.mark.unit
def test_scenario_orchestrator_run_single_scenario(tmp_path):
    """Test running a single scenario."""
    from services.scenario_orchestrator import ScenarioOrchestrator

    # Create test config
    config_file = tmp_path / "single_scenario.yaml"
    config_file.write_text("""
default_period:
  days: 7

scenarios:
  - name: "Test Conservative"
    strategy: "momentum_v1"
    risk_profile: "conservative"
""")

    orchestrator = ScenarioOrchestrator(
        config_path=config_file,
        output_dir=tmp_path / "output"
    )

    results = orchestrator.run_all_scenarios()

    assert len(results) == 1
    assert results[0]["scenario_name"] == "Test Conservative"
    assert "statistics" in results[0]
    assert "equity_curve" in results[0]


@pytest.mark.unit
def test_scenario_orchestrator_run_multiple_scenarios(tmp_path):
    """Test running multiple scenarios."""
    from services.scenario_orchestrator import ScenarioOrchestrator

    # Create test config with multiple scenarios
    config_file = tmp_path / "multi_scenario.yaml"
    config_file.write_text("""
default_period:
  days: 7

scenarios:
  - name: "Conservative"
    strategy: "momentum_v1"
    risk_profile: "conservative"

  - name: "Balanced"
    strategy: "momentum_v1"
    risk_profile: "balanced"

  - name: "Aggressive"
    strategy: "momentum_v1"
    risk_profile: "aggressive"
""")

    orchestrator = ScenarioOrchestrator(
        config_path=config_file,
        output_dir=tmp_path / "output"
    )

    results = orchestrator.run_all_scenarios()

    assert len(results) == 3
    assert results[0]["scenario_name"] == "Conservative"
    assert results[1]["scenario_name"] == "Balanced"
    assert results[2]["scenario_name"] == "Aggressive"


@pytest.mark.unit
def test_scenario_orchestrator_custom_risk_params(tmp_path):
    """Test scenario with custom risk parameters."""
    from services.scenario_orchestrator import ScenarioOrchestrator

    config_file = tmp_path / "custom_params.yaml"
    config_file.write_text("""
scenarios:
  - name: "Custom Profile"
    strategy: "momentum_v1"
    risk_params:
      MAX_POSITION_PCT: 0.08
      MAX_DAILY_DRAWDOWN_PCT: 0.04
      MAX_EXPOSURE_PCT: 0.25
    period:
      days: 7
""")

    orchestrator = ScenarioOrchestrator(
        config_path=config_file,
        output_dir=tmp_path / "output"
    )

    results = orchestrator.run_all_scenarios()

    assert len(results) == 1
    assert results[0]["scenario_name"] == "Custom Profile"


@pytest.mark.unit
def test_scenario_orchestrator_comparison_report(tmp_path):
    """Test comparison report generation."""
    from services.scenario_orchestrator import ScenarioOrchestrator

    config_file = tmp_path / "comparison.yaml"
    config_file.write_text("""
default_period:
  days: 7

scenarios:
  - name: "Scenario A"
    strategy: "momentum_v1"
    risk_profile: "conservative"

  - name: "Scenario B"
    strategy: "momentum_v1"
    risk_profile: "balanced"
""")

    output_dir = tmp_path / "output"

    orchestrator = ScenarioOrchestrator(
        config_path=config_file,
        output_dir=output_dir
    )

    orchestrator.run_all_scenarios()

    # Check that comparison report was created
    comparison_txt = output_dir / "scenario_comparison.txt"
    comparison_json = output_dir / "scenario_comparison.json"

    assert comparison_txt.exists()
    assert comparison_json.exists()

    # Verify content
    content = comparison_txt.read_text()
    assert "Scenario A" in content
    assert "Scenario B" in content


# ==============================================================================
# ADDITIONAL PAPER TRADING RUNNER TESTS (Coverage Boost)
# ==============================================================================


@pytest.mark.unit
def test_runner_unknown_risk_profile():
    """Test runner with unknown risk profile falls back to balanced."""
    runner = PaperTradingRunner(risk_profile="unknown_profile")

    # Should fall back to balanced
    assert runner.risk_config["MAX_POSITION_PCT"] == 0.10  # balanced value


@pytest.mark.unit
def test_runner_empty_result():
    """Test empty result when no data."""
    runner = PaperTradingRunner()

    result = runner._empty_result()

    assert result["strategy"] == "momentum_v1"
    assert result["statistics"]["total_trades"] == 0
    assert len(result["equity_curve"]) == 0
    assert len(result["trades"]) == 0


@pytest.mark.unit
def test_runner_run_with_days_parameter():
    """Test run with days parameter."""
    runner = PaperTradingRunner()

    # Mock data will be generated for 7 days
    result = runner.run(days=7)

    assert result is not None
    assert "statistics" in result
    assert "period" in result


@pytest.mark.unit
def test_runner_run_with_date_range():
    """Test run with specific date range."""
    runner = PaperTradingRunner()

    from_date = datetime(2025, 11, 1, tzinfo=timezone.utc)
    to_date = datetime(2025, 11, 7, tzinfo=timezone.utc)

    result = runner.run(from_date=from_date, to_date=to_date)

    assert result is not None
    assert "period" in result
    assert "2025-11-01" in result["period"]["from"]
    assert "2025-11-07" in result["period"]["to"]


@pytest.mark.unit
def test_runner_run_without_dates_raises_error():
    """Test that run without dates raises ValueError."""
    runner = PaperTradingRunner()

    with pytest.raises(ValueError, match="from/to dates or days"):
        runner.run()


@pytest.mark.unit
def test_runner_save_reports(tmp_path):
    """Test report generation and saving."""
    from pathlib import Path

    runner = PaperTradingRunner(
        strategy_name="test_strategy",
        risk_profile="balanced",
        output_dir=tmp_path / "reports"
    )

    # Create minimal mock data
    mock_data = [
        {
            "timestamp": datetime.now(timezone.utc),
            "symbol": "BTCUSDT",
            "price": 50000.0,
            "volume": 100.0,
            "pct_change": 0.5,
        }
    ]

    result = runner.run(market_data_events=mock_data)

    # Check that output directory was created
    assert (tmp_path / "reports").exists()


# ==============================================================================
# ADDITIONAL TRADING STATISTICS TESTS (Coverage Boost)
# ==============================================================================


@pytest.mark.unit
def test_statistics_add_fill():
    """Test adding fills to statistics."""
    stats = TradingStatistics(initial_equity=100_000.0)

    fill = {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "filled_quantity": 0.1,
        "fill_price": 50000.0,
        "fees": 5.0,
        "timestamp": datetime.now(timezone.utc),
    }

    stats.add_fill(fill)

    # Verify fill was tracked
    assert len(stats.fills) == 1


@pytest.mark.unit
def test_statistics_get_equity_curve():
    """Test equity curve retrieval."""
    stats = TradingStatistics(initial_equity=100_000.0)

    timestamp = datetime.now(timezone.utc)
    stats.add_trade_close("BTCUSDT", 1000.0, timestamp)

    curve = stats.get_equity_curve()

    assert len(curve) > 0
    assert "timestamp" in curve[0]
    assert "equity" in curve[0]


@pytest.mark.unit
def test_statistics_get_trades():
    """Test trades retrieval."""
    stats = TradingStatistics(initial_equity=100_000.0)

    timestamp = datetime.now(timezone.utc)
    stats.add_trade_close("BTCUSDT", 1000.0, timestamp)
    stats.add_trade_close("ETHUSDT", -500.0, timestamp)

    trades = stats.get_trades()

    assert len(trades) == 2


@pytest.mark.unit
def test_statistics_profit_factor():
    """Test profit factor calculation."""
    stats = TradingStatistics(initial_equity=100_000.0)

    timestamp = datetime.now(timezone.utc)

    # Add profitable trades
    stats.add_trade_close("BTC1", 1000.0, timestamp)
    stats.add_trade_close("BTC2", 500.0, timestamp)

    # Add losing trade
    stats.add_trade_close("ETH1", -300.0, timestamp)

    result = stats.calculate_statistics()

    # Profit factor = total_wins / total_losses = 1500 / 300 = 5.0
    assert result["profit_factor"] > 0
    assert result["total_pnl"] == 1200.0


@pytest.mark.unit
def test_statistics_zero_trades():
    """Test statistics with zero trades."""
    stats = TradingStatistics(initial_equity=100_000.0)

    result = stats.calculate_statistics()

    assert result["total_trades"] == 0
    assert result["win_rate"] == 0.0
    assert result["profit_factor"] == 0.0


@pytest.mark.unit
def test_report_generator_json(tmp_path):
    """Test JSON report generation."""
    from services.trading_statistics import ReportGenerator

    stats = {
        "total_trades": 10,
        "win_rate": 0.6,
        "total_pnl": 5000.0,
    }

    timestamp = datetime.now(timezone.utc)
    equity_curve = [
        {"timestamp": timestamp, "equity": 100_000.0, "pnl": 0.0, "drawdown_pct": 0.0}
    ]

    trades = [
        {"symbol": "BTCUSDT", "pnl": 1000.0, "timestamp": timestamp, "win": True}
    ]

    output_path = tmp_path / "report.json"

    ReportGenerator.save_json_report(
        stats=stats,
        equity_curve=equity_curve,
        trades=trades,
        output_path=output_path,
    )

    assert output_path.exists()

    import json
    with open(output_path) as f:
        data = json.load(f)

    assert "statistics" in data
    assert "equity_curve" in data
    assert "trades" in data


@pytest.mark.unit
def test_report_generator_equity_csv(tmp_path):
    """Test equity curve CSV generation."""
    from services.trading_statistics import ReportGenerator

    timestamp1 = datetime(2025, 11, 1, tzinfo=timezone.utc)
    timestamp2 = datetime(2025, 11, 2, tzinfo=timezone.utc)

    equity_curve = [
        {"timestamp": timestamp1, "equity": 100_000.0, "pnl": 0.0, "drawdown_pct": 0.0},
        {"timestamp": timestamp2, "equity": 101_000.0, "pnl": 1000.0, "drawdown_pct": 0.0},
    ]

    output_path = tmp_path / "equity.csv"

    ReportGenerator.save_equity_curve_csv(equity_curve, output_path)

    assert output_path.exists()

    content = output_path.read_text()
    assert "timestamp,equity" in content
    assert "100000" in content


@pytest.mark.unit
def test_report_generator_trades_csv(tmp_path):
    """Test trades CSV generation."""
    from services.trading_statistics import ReportGenerator

    timestamp = datetime.now(timezone.utc)

    trades = [
        {
            "symbol": "BTCUSDT",
            "pnl": 1000.0,
            "entry_price": 50000.0,
            "timestamp": timestamp,
            "win": True,
        }
    ]

    output_path = tmp_path / "trades.csv"

    ReportGenerator.save_trades_csv(trades, output_path)

    assert output_path.exists()

    content = output_path.read_text()
    assert "BTCUSDT" in content


@pytest.mark.unit
def test_report_generator_text_summary():
    """Test text summary generation."""
    from services.trading_statistics import ReportGenerator

    stats = {
        "total_trades": 42,
        "winning_trades": 25,
        "losing_trades": 17,
        "win_rate": 0.595,
        "profit_factor": 1.85,
        "total_pnl": 8432.50,
        "total_return_pct": 8.43,
        "avg_win": 523.45,
        "avg_loss": -287.21,
        "largest_win": 1234.56,
        "largest_loss": -678.90,
        "max_drawdown_pct": -3.21,
        "peak_equity": 108432.50,
        "final_equity": 108432.50,
        "initial_equity": 100000.00,
    }

    summary = ReportGenerator.generate_text_summary(stats, "test_scenario")

    assert "test_scenario" in summary
    assert "42" in summary  # total trades
    assert "59.5" in summary  # win rate
    assert "8,432.50" in summary  # total P&L (formatted with comma)


@pytest.mark.unit
def test_report_generator_compare_scenarios():
    """Test scenario comparison report."""
    from services.trading_statistics import ReportGenerator

    scenario_results = [
        {
            "name": "Conservative",
            "stats": {
                "total_trades": 28,
                "win_rate": 0.64,
                "total_pnl": 5120.0,
                "total_return_pct": 5.12,
                "max_drawdown_pct": -2.1,
                "profit_factor": 2.1,
            }
        },
        {
            "name": "Aggressive",
            "stats": {
                "total_trades": 67,
                "win_rate": 0.52,
                "total_pnl": 12345.0,
                "total_return_pct": 12.35,
                "max_drawdown_pct": -5.8,
                "profit_factor": 1.5,
            }
        },
    ]

    comparison = ReportGenerator.compare_scenarios(scenario_results)

    assert "Conservative" in comparison
    assert "Aggressive" in comparison
    assert "28" in comparison  # Conservative trades
    assert "67" in comparison  # Aggressive trades


# ==============================================================================
# ADDITIONAL PAPER EXECUTION TESTS (Coverage Boost)
# ==============================================================================


@pytest.mark.unit
def test_report_generator_empty_scenarios():
    """Test scenario comparison with empty list."""
    from services.trading_statistics import ReportGenerator

    result = ReportGenerator.compare_scenarios([])

    assert "No scenarios" in result


@pytest.mark.unit
def test_statistics_sharpe_ratio():
    """Test Sharpe ratio calculation."""
    from services.trading_statistics import AdvancedMetrics

    # Positive returns
    returns = [0.01, 0.02, -0.005, 0.015, 0.01]
    sharpe = AdvancedMetrics.calculate_sharpe_ratio(returns, risk_free_rate=0.0)

    assert sharpe > 0

    # Empty returns
    sharpe_empty = AdvancedMetrics.calculate_sharpe_ratio([], risk_free_rate=0.0)
    assert sharpe_empty == 0.0

    # Zero std (all same returns)
    returns_same = [0.01, 0.01, 0.01]
    sharpe_zero_std = AdvancedMetrics.calculate_sharpe_ratio(returns_same)
    assert sharpe_zero_std == 0.0


@pytest.mark.unit
def test_statistics_sortino_ratio():
    """Test Sortino ratio calculation."""
    from services.trading_statistics import AdvancedMetrics

    # Mixed returns
    returns = [0.02, 0.015, -0.01, 0.01, -0.005]
    sortino = AdvancedMetrics.calculate_sortino_ratio(returns, risk_free_rate=0.0)

    assert sortino != 0.0

    # Empty returns
    sortino_empty = AdvancedMetrics.calculate_sortino_ratio([])
    assert sortino_empty == 0.0

    # All positive returns (no downside)
    returns_positive = [0.01, 0.02, 0.015, 0.01]
    sortino_inf = AdvancedMetrics.calculate_sortino_ratio(returns_positive)
    assert sortino_inf == float("inf")

    # Multiple downside values
    returns_multi_down = [0.01, 0.02, -0.01, -0.02, 0.015]
    sortino_multi = AdvancedMetrics.calculate_sortino_ratio(returns_multi_down)
    # Should return valid ratio
    assert sortino_multi != 0.0


@pytest.mark.unit
def test_statistics_calmar_ratio():
    """Test Calmar ratio calculation."""
    from services.trading_statistics import AdvancedMetrics

    # Normal case
    calmar = AdvancedMetrics.calculate_calmar_ratio(
        total_return=0.20,  # 20% return
        max_drawdown=0.05,  # 5% drawdown
        years=1.0
    )

    assert calmar == 0.20 / 0.05  # 4.0

    # Zero drawdown (infinite Calmar)
    calmar_inf = AdvancedMetrics.calculate_calmar_ratio(
        total_return=0.15,
        max_drawdown=0.0,
        years=1.0
    )

    assert calmar_inf == float("inf")

    # Multi-year
    calmar_multi = AdvancedMetrics.calculate_calmar_ratio(
        total_return=0.40,  # 40% over 2 years
        max_drawdown=0.10,  # 10% drawdown
        years=2.0
    )

    assert calmar_multi == (0.40 / 2.0) / 0.10  # 2.0


@pytest.mark.unit
def test_paper_execution_get_all_positions():
    """Test getting all positions."""
    engine = PaperExecutionEngine()

    # Create multiple positions
    engine.execute_order(
        {"symbol": "BTCUSDT", "side": "BUY", "size": 0.1, "order_type": "MARKET"},
        50000.0
    )

    engine.execute_order(
        {"symbol": "ETHUSDT", "side": "BUY", "size": 1.0, "order_type": "MARKET"},
        3000.0
    )

    all_positions = engine.get_all_positions()

    assert len(all_positions) == 2
    assert "BTCUSDT" in all_positions
    assert "ETHUSDT" in all_positions


@pytest.mark.unit
def test_paper_execution_nonexistent_position():
    """Test getting nonexistent position."""
    engine = PaperExecutionEngine()

    position = engine.get_position("NONEXISTENT")

    assert position is None


@pytest.mark.unit
def test_paper_execution_partial_close():
    """Test partial position close."""
    engine = PaperExecutionEngine()

    # Buy 1.0
    engine.execute_order(
        {"symbol": "BTCUSDT", "side": "BUY", "size": 1.0, "order_type": "MARKET"},
        50000.0
    )

    # Sell 0.5 (partial close)
    engine.execute_order(
        {"symbol": "BTCUSDT", "side": "SELL", "size": 0.5, "order_type": "MARKET"},
        51000.0
    )

    position = engine.get_position("BTCUSDT")

    assert position["quantity"] == 0.5  # Half remaining
    assert position["realized_pnl"] > 0  # Should have some profit


@pytest.mark.unit
def test_paper_execution_with_timestamp():
    """Test execution with specific timestamp."""
    engine = PaperExecutionEngine()

    timestamp = datetime(2025, 11, 19, 12, 0, 0, tzinfo=timezone.utc)

    result = engine.execute_order(
        {"symbol": "BTCUSDT", "side": "BUY", "size": 0.1, "order_type": "MARKET"},
        50000.0,
        timestamp=timestamp
    )

    assert result["timestamp"] == timestamp


@pytest.mark.unit
def test_paper_execution_slippage_calculation():
    """Test slippage calculation for buy and sell."""
    engine = PaperExecutionEngine(slippage_pct=0.001)  # 0.1%

    # BUY: should pay MORE (worse price)
    buy_result = engine.execute_order(
        {"symbol": "BTCUSDT", "side": "BUY", "size": 0.1, "order_type": "MARKET"},
        50000.0
    )

    # Expected: 50000 * (1 + 0.001) = 50050
    assert buy_result["fill_price"] > 50000.0
    assert abs(buy_result["fill_price"] - 50050.0) < 1.0

    # SELL: should receive LESS (worse price)
    sell_result = engine.execute_order(
        {"symbol": "BTCUSDT", "side": "SELL", "size": 0.1, "order_type": "MARKET"},
        50000.0
    )

    # Expected: 50000 * (1 - 0.001) = 49950
    assert sell_result["fill_price"] < 50000.0
    assert abs(sell_result["fill_price"] - 49950.0) < 1.0
