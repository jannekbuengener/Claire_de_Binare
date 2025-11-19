"""
Paper Trading Runner

Orchestriert komplette Paper-Trading Runs:
- Lädt Events aus Event-Store oder historische Daten
- Spielt Events durch Pipeline (MarketData → Signal → Risk → Execution)
- Nutzt Paper Execution (keine echten Orders)
- Trackt Statistics & P&L
- Generiert Reports

CLI Usage:
    claire run-paper --from 2025-02-10 --to 2025-02-11 --strategy momentum_v1
    claire run-paper --days 30 --profile conservative
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.paper_execution import PaperExecutionEngine
from services.trading_statistics import ReportGenerator, TradingStatistics

logger = logging.getLogger(__name__)


# ==============================================================================
# CONFIGURATION
# ==============================================================================

# Risk profiles
RISK_PROFILES = {
    "conservative": {
        "MAX_POSITION_PCT": 0.05,  # 5%
        "MAX_DAILY_DRAWDOWN_PCT": 0.03,  # 3%
        "MAX_EXPOSURE_PCT": 0.20,  # 20%
        "STOP_LOSS_PCT": 0.015,  # 1.5%
    },
    "balanced": {
        "MAX_POSITION_PCT": 0.10,  # 10%
        "MAX_DAILY_DRAWDOWN_PCT": 0.05,  # 5%
        "MAX_EXPOSURE_PCT": 0.30,  # 30%
        "STOP_LOSS_PCT": 0.02,  # 2%
    },
    "aggressive": {
        "MAX_POSITION_PCT": 0.15,  # 15%
        "MAX_DAILY_DRAWDOWN_PCT": 0.08,  # 8%
        "MAX_EXPOSURE_PCT": 0.50,  # 50%
        "STOP_LOSS_PCT": 0.03,  # 3%
    },
}

# Default config
DEFAULT_INITIAL_EQUITY = 100_000.0
DEFAULT_OUTPUT_DIR = Path("backtest_results")


# ==============================================================================
# PAPER TRADING RUNNER
# ==============================================================================


class PaperTradingRunner:
    """
    Runs paper trading simulation.

    Pipeline:
    1. Load market data events
    2. Generate signals (via strategy)
    3. Validate with risk engine
    4. Execute with paper execution
    5. Track statistics
    6. Generate reports
    """

    def __init__(
        self,
        strategy_name: str = "momentum_v1",
        risk_profile: str = "balanced",
        initial_equity: float = DEFAULT_INITIAL_EQUITY,
        output_dir: Path = DEFAULT_OUTPUT_DIR,
    ):
        """
        Initialize paper trading runner.

        Args:
            strategy_name: Strategy to use
            risk_profile: Risk profile (conservative/balanced/aggressive)
            initial_equity: Starting equity
            output_dir: Output directory for reports
        """
        self.strategy_name = strategy_name
        self.risk_profile = risk_profile
        self.initial_equity = initial_equity
        self.output_dir = Path(output_dir)

        # Load risk config
        self.risk_config = self._load_risk_config(risk_profile)

        # Initialize components
        self.execution_engine = PaperExecutionEngine()
        self.statistics = TradingStatistics(initial_equity=initial_equity)

        # State tracking
        self.risk_state = {
            "equity": initial_equity,
            "daily_pnl": 0.0,
            "total_exposure_pct": 0.0,
            "open_positions": 0,
        }

        logger.info(
            f"📄 Paper Trading Runner initialized "
            f"(strategy={strategy_name}, profile={risk_profile})"
        )

    def _load_risk_config(self, profile: str) -> Dict:
        """Load risk configuration for profile."""
        if profile not in RISK_PROFILES:
            logger.warning(
                f"Unknown risk profile '{profile}', using 'balanced'"
            )
            profile = "balanced"

        config = RISK_PROFILES[profile].copy()
        config["ACCOUNT_EQUITY"] = self.initial_equity

        return config

    def run(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        days: Optional[int] = None,
        market_data_events: Optional[List[Dict]] = None,
    ) -> Dict:
        """
        Run paper trading simulation.

        Args:
            from_date: Start date
            to_date: End date
            days: Number of days to run (alternative to from/to)
            market_data_events: Pre-loaded market data (for testing)

        Returns:
            Dict with run results and statistics
        """
        logger.info("🚀 Starting paper trading run...")

        # Load market data
        if market_data_events is None:
            # Determine date range (only needed when loading data)
            if days:
                to_date = datetime.now(timezone.utc)
                from_date = to_date - timedelta(days=days)

            if not from_date or not to_date:
                raise ValueError("Must specify either from/to dates or days")

            logger.info(f"📅 Period: {from_date.date()} → {to_date.date()}")
            market_data_events = self._load_market_data(from_date, to_date)
        else:
            # Use mock/provided data - infer dates from data if available
            if market_data_events and len(market_data_events) > 0:
                first_ts = market_data_events[0].get("timestamp")
                last_ts = market_data_events[-1].get("timestamp")
                if first_ts and last_ts:
                    from_date = first_ts if isinstance(first_ts, datetime) else datetime.now(timezone.utc)
                    to_date = last_ts if isinstance(last_ts, datetime) else datetime.now(timezone.utc)
                else:
                    from_date = to_date = datetime.now(timezone.utc)
            else:
                from_date = to_date = datetime.now(timezone.utc)

        if not market_data_events:
            logger.warning("No market data found for period")
            return self._empty_result()

        logger.info(f"📊 Loaded {len(market_data_events)} market data events")

        # Process events
        for event in market_data_events:
            self._process_market_data(event)

        # Calculate statistics
        stats = self.statistics.calculate_statistics()

        logger.info("✅ Paper trading run complete")

        # Generate report
        run_result = {
            "strategy": self.strategy_name,
            "risk_profile": self.risk_profile,
            "period": {"from": from_date.isoformat(), "to": to_date.isoformat()},
            "statistics": stats,
            "equity_curve": self.statistics.get_equity_curve(),
            "trades": self.statistics.get_trades(),
        }

        # Save reports
        self._save_reports(run_result)

        return run_result

    def _load_market_data(
        self, from_date: datetime, to_date: datetime
    ) -> List[Dict]:
        """
        Load market data events from Event Store.

        Args:
            from_date: Start date
            to_date: End date

        Returns:
            List of market data events
        """
        # TODO: Load from Event Store
        # For now, return mock data for testing

        logger.warning(
            "Using MOCK market data (Event Store integration pending)"
        )

        # Mock market data (1 hour intervals)
        events = []
        current_time = from_date
        base_price = 50000.0

        while current_time <= to_date:
            # Simulate price movement
            import random

            random.seed(int(current_time.timestamp()))  # Deterministic
            price_change = random.uniform(-0.02, 0.02)  # ±2%
            price = base_price * (1 + price_change)

            event = {
                "timestamp": current_time,
                "symbol": "BTCUSDT",
                "price": price,
                "volume": random.uniform(100, 1000),
                "pct_change": price_change * 100,
            }

            events.append(event)

            base_price = price
            current_time += timedelta(hours=1)

        return events

    def _process_market_data(self, market_data: Dict) -> None:
        """
        Process single market data event through pipeline.

        Pipeline:
        1. Market Data → Signal Generation
        2. Signal → Risk Validation
        3. Approved Signal → Paper Execution
        4. Update Statistics

        Args:
            market_data: Market data event
        """
        symbol = market_data["symbol"]
        price = market_data["price"]
        timestamp = market_data["timestamp"]

        # Step 1: Generate signal (simple momentum strategy)
        signal = self._generate_signal(market_data)

        if not signal:
            return  # No signal

        # Step 2: Risk validation
        risk_decision = self._validate_risk(signal)

        if not risk_decision["approved"]:
            logger.debug(
                f"❌ Signal rejected: {risk_decision['reason']}"
            )
            return

        # Step 3: Execute (paper mode)
        order = {
            "symbol": symbol,
            "side": signal["side"],
            "size": risk_decision["approved_size"],
            "order_type": "MARKET",
            "event_id": str(uuid4()),
        }

        fill = self.execution_engine.execute_order(order, price, timestamp)

        # Step 4: Update statistics
        self._update_statistics(fill, timestamp)

    def _generate_signal(self, market_data: Dict) -> Optional[Dict]:
        """
        Generate trading signal from market data.

        Simple momentum strategy:
        - BUY if price change > +3%
        - SELL if price change < -3%

        Args:
            market_data: Market data event

        Returns:
            Signal dict or None
        """
        pct_change = market_data.get("pct_change", 0.0)

        if pct_change > 3.0:
            # Strong upward momentum
            return {
                "symbol": market_data["symbol"],
                "side": "BUY",
                "confidence": min(pct_change / 10.0, 1.0),
                "reason": f"Strong momentum (+{pct_change:.2f}%)",
                "price": market_data["price"],
            }
        elif pct_change < -3.0:
            # Strong downward momentum (short signal)
            return {
                "symbol": market_data["symbol"],
                "side": "SELL",
                "confidence": min(abs(pct_change) / 10.0, 1.0),
                "reason": f"Strong momentum ({pct_change:.2f}%)",
                "price": market_data["price"],
            }

        return None  # No signal

    def _validate_risk(self, signal: Dict) -> Dict:
        """
        Validate signal against risk limits.

        Args:
            signal: Trading signal

        Returns:
            Risk decision dict
        """
        # Import risk engine
        from services import risk_engine

        # Evaluate signal
        decision = risk_engine.evaluate_signal(
            signal, self.risk_state, self.risk_config
        )

        return {
            "approved": decision.approved,
            "approved_size": decision.position_size if decision.approved else 0.0,
            "reason": decision.reason,
        }

    def _update_statistics(self, fill: Dict, timestamp: datetime) -> None:
        """
        Update statistics after fill.

        Args:
            fill: Fill result from execution
            timestamp: Fill timestamp
        """
        # Add fill
        self.statistics.add_fill(fill)

        # Check if position closed (simplified)
        # In real system, would track positions properly
        symbol = fill["symbol"]
        position = self.execution_engine.get_position(symbol)

        if position and position["quantity"] == 0:
            # Position closed
            realized_pnl = position["realized_pnl"]
            self.statistics.add_trade_close(symbol, realized_pnl, timestamp)

            logger.info(
                f"📊 Trade closed: {symbol} P&L=${realized_pnl:+,.2f}"
            )

        # Update risk state
        self.risk_state["equity"] = self.statistics.current_equity
        self.risk_state["daily_pnl"] = (
            self.statistics.current_equity - self.initial_equity
        )

        # Update exposure
        positions = self.execution_engine.get_all_positions()
        total_notional = sum(
            pos["quantity"] * pos["avg_entry_price"]
            for pos in positions.values()
            if pos["quantity"] > 0
        )
        self.risk_state["total_exposure_pct"] = (
            total_notional / self.statistics.current_equity
            if self.statistics.current_equity > 0
            else 0.0
        )
        self.risk_state["open_positions"] = len(
            [p for p in positions.values() if p["quantity"] > 0]
        )

    def _save_reports(self, run_result: Dict) -> None:
        """
        Save reports to disk.

        Args:
            run_result: Run result dict
        """
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Generate timestamp for filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        scenario_name = f"{self.strategy_name}_{self.risk_profile}"

        # Save JSON report
        json_path = (
            self.output_dir
            / f"{scenario_name}_{timestamp}_report.json"
        )
        ReportGenerator.save_json_report(
            stats=run_result["statistics"],
            equity_curve=run_result["equity_curve"],
            trades=run_result["trades"],
            output_path=json_path,
            metadata={
                "strategy": self.strategy_name,
                "risk_profile": self.risk_profile,
                "period": run_result["period"],
            },
        )

        # Save equity curve CSV
        csv_path = (
            self.output_dir
            / f"{scenario_name}_{timestamp}_equity.csv"
        )
        ReportGenerator.save_equity_curve_csv(
            run_result["equity_curve"], csv_path
        )

        # Save trades CSV
        trades_path = (
            self.output_dir
            / f"{scenario_name}_{timestamp}_trades.csv"
        )
        ReportGenerator.save_trades_csv(run_result["trades"], trades_path)

        # Generate text summary
        summary = ReportGenerator.generate_text_summary(
            run_result["statistics"], scenario_name
        )
        logger.info(f"\n{summary}")

        # Save text summary
        text_path = (
            self.output_dir
            / f"{scenario_name}_{timestamp}_summary.txt"
        )
        with open(text_path, "w") as f:
            f.write(summary)

        logger.info(f"📁 Reports saved to {self.output_dir}")

    def _empty_result(self) -> Dict:
        """Return empty result (no data)."""
        return {
            "strategy": self.strategy_name,
            "risk_profile": self.risk_profile,
            "period": {},
            "statistics": self.statistics.calculate_statistics(),
            "equity_curve": [],
            "trades": [],
        }


# ==============================================================================
# CLI HELPER FUNCTIONS
# ==============================================================================


def run_single_paper_trade(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    days: Optional[int] = None,
    strategy: str = "momentum_v1",
    profile: str = "balanced",
) -> Dict:
    """
    Run single paper trading simulation.

    Args:
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        days: Number of days (alternative to from/to)
        strategy: Strategy name
        profile: Risk profile

    Returns:
        Run results dict
    """
    # Parse dates
    from_dt = None
    to_dt = None

    if from_date:
        from_dt = datetime.fromisoformat(from_date).replace(tzinfo=timezone.utc)
    if to_date:
        to_dt = datetime.fromisoformat(to_date).replace(tzinfo=timezone.utc)

    # Create runner
    runner = PaperTradingRunner(
        strategy_name=strategy, risk_profile=profile
    )

    # Run
    result = runner.run(from_date=from_dt, to_date=to_dt, days=days)

    return result


# ==============================================================================
# EXAMPLE USAGE
# ==============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Example: Run 7 days of paper trading
    result = run_single_paper_trade(days=7, strategy="momentum_v1", profile="balanced")

    logger.info(f"\nRun complete! Check {DEFAULT_OUTPUT_DIR} for reports.")
