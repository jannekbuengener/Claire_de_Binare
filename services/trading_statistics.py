"""
Trading Statistics & Reporting

Berechnet Metriken für Paper-Trading Runs:
- Trade-Statistiken (Anzahl, Win-Rate)
- P&L Tracking (Realized, Unrealized, Total)
- Drawdown Analyse (Max Drawdown, Current Drawdown)
- Equity Curve (Zeitverlauf)
- Sharpe Ratio, Sortino Ratio (optional)

Output: Strukturierte Reports (JSON/CSV/Text)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import csv

logger = logging.getLogger(__name__)


# ==============================================================================
# STATISTICS CALCULATOR
# ==============================================================================


class TradingStatistics:
    """
    Berechnet Trading-Metriken aus Fills und Equity-Curve.

    Metriken:
    - Total Trades
    - Win Rate
    - Profit Factor
    - Total P&L
    - Max Drawdown
    - Sharpe Ratio (optional)
    """

    def __init__(self, initial_equity: float = 100000.0):
        """
        Initialize statistics calculator.

        Args:
            initial_equity: Starting equity
        """
        self.initial_equity = initial_equity
        self.current_equity = initial_equity

        # Trade tracking
        self.trades: List[Dict] = []
        self.fills: List[Dict] = []

        # Equity curve
        self.equity_curve: List[Dict] = []

        # Drawdown tracking
        self.peak_equity = initial_equity
        self.max_drawdown = 0.0

    def add_fill(self, fill: Dict) -> None:
        """
        Add order fill to statistics.

        Args:
            fill: Fill dict from PaperExecutionEngine
        """
        self.fills.append(fill)

        # Update equity (deduct fees)
        if "fees" in fill:
            self.current_equity -= fill["fees"]

    def add_trade_close(
        self, symbol: str, realized_pnl: float, timestamp: datetime
    ) -> None:
        """
        Record closed trade.

        Args:
            symbol: Trading symbol
            realized_pnl: Realized P&L for this trade
            timestamp: Close timestamp
        """
        trade = {
            "symbol": symbol,
            "pnl": realized_pnl,
            "timestamp": timestamp,
            "win": realized_pnl > 0,
        }

        self.trades.append(trade)

        # Update equity
        self.current_equity += realized_pnl

        # Update equity curve
        self._update_equity_curve(timestamp)

        # Update drawdown
        self._update_drawdown()

    def _update_equity_curve(self, timestamp: datetime) -> None:
        """Update equity curve with current equity."""
        self.equity_curve.append(
            {"timestamp": timestamp, "equity": self.current_equity}
        )

    def _update_drawdown(self) -> None:
        """Update peak and max drawdown."""
        if self.current_equity > self.peak_equity:
            self.peak_equity = self.current_equity

        current_drawdown = (self.peak_equity - self.current_equity) / self.peak_equity

        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown

    def calculate_statistics(self) -> Dict:
        """
        Calculate all trading statistics.

        Returns:
            Dict with all metrics
        """
        total_trades = len(self.trades)

        if total_trades == 0:
            return self._empty_statistics()

        # Win rate
        winning_trades = [t for t in self.trades if t["win"]]
        win_rate = len(winning_trades) / total_trades

        # P&L stats
        total_pnl = sum(t["pnl"] for t in self.trades)
        winning_pnl = sum(t["pnl"] for t in winning_trades)
        losing_trades = [t for t in self.trades if not t["win"]]
        losing_pnl = abs(sum(t["pnl"] for t in losing_trades))

        # Profit factor
        profit_factor = winning_pnl / losing_pnl if losing_pnl > 0 else float("inf")

        # Average trade
        avg_win = winning_pnl / len(winning_trades) if winning_trades else 0
        avg_loss = -losing_pnl / len(losing_trades) if losing_trades else 0

        # Return
        total_return = (
            (self.current_equity - self.initial_equity) / self.initial_equity
        )

        return {
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_pnl": total_pnl,
            "total_return_pct": total_return * 100,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "max_drawdown_pct": self.max_drawdown * 100,
            "initial_equity": self.initial_equity,
            "final_equity": self.current_equity,
            "peak_equity": self.peak_equity,
        }

    def _empty_statistics(self) -> Dict:
        """Return empty statistics (no trades)."""
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_pnl": 0.0,
            "total_return_pct": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "max_drawdown_pct": 0.0,
            "initial_equity": self.initial_equity,
            "final_equity": self.current_equity,
            "peak_equity": self.peak_equity,
        }

    def get_equity_curve(self) -> List[Dict]:
        """
        Get equity curve data.

        Returns:
            List of {timestamp, equity} dicts
        """
        return self.equity_curve.copy()

    def get_trades(self) -> List[Dict]:
        """
        Get all trades.

        Returns:
            List of trade dicts
        """
        return self.trades.copy()


# ==============================================================================
# REPORT GENERATOR
# ==============================================================================


class ReportGenerator:
    """
    Generates reports from trading statistics.

    Formats:
    - Text summary (console)
    - JSON (structured data)
    - CSV (equity curve, trades)
    """

    @staticmethod
    def generate_text_summary(stats: Dict, scenario_name: str = "Paper Run") -> str:
        """
        Generate text summary for console output.

        Args:
            stats: Statistics dict from TradingStatistics
            scenario_name: Name of scenario/run

        Returns:
            str: Formatted text summary
        """
        lines = []
        lines.append("=" * 70)
        lines.append(f"PAPER TRADING RESULTS: {scenario_name}")
        lines.append("=" * 70)
        lines.append("")

        # Equity
        lines.append("📊 EQUITY:")
        lines.append(f"  Initial: ${stats['initial_equity']:,.2f}")
        lines.append(f"  Final:   ${stats['final_equity']:,.2f}")
        lines.append(f"  Peak:    ${stats['peak_equity']:,.2f}")
        lines.append(
            f"  Return:  {stats['total_return_pct']:+.2f}% (${stats['total_pnl']:+,.2f})"
        )
        lines.append("")

        # Trades
        lines.append("📈 TRADES:")
        lines.append(f"  Total:   {stats['total_trades']}")
        lines.append(f"  Winners: {stats['winning_trades']}")
        lines.append(f"  Losers:  {stats['losing_trades']}")
        lines.append(f"  Win Rate: {stats['win_rate']*100:.1f}%")
        lines.append("")

        # Performance
        lines.append("💰 PERFORMANCE:")
        lines.append(f"  Profit Factor: {stats['profit_factor']:.2f}")
        lines.append(f"  Avg Win:  ${stats['avg_win']:,.2f}")
        lines.append(f"  Avg Loss: ${stats['avg_loss']:,.2f}")
        lines.append(f"  Max Drawdown: {stats['max_drawdown_pct']:.2f}%")
        lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)

    @staticmethod
    def save_json_report(
        stats: Dict,
        equity_curve: List[Dict],
        trades: List[Dict],
        output_path: Path,
        metadata: Optional[Dict] = None,
    ) -> None:
        """
        Save complete report as JSON.

        Args:
            stats: Statistics dict
            equity_curve: Equity curve data
            trades: List of trades
            output_path: Output file path
            metadata: Optional metadata (scenario, config, etc.)
        """
        report = {
            "metadata": metadata or {},
            "statistics": stats,
            "equity_curve": [
                {
                    "timestamp": point["timestamp"].isoformat(),
                    "equity": point["equity"],
                }
                for point in equity_curve
            ],
            "trades": [
                {
                    "symbol": trade["symbol"],
                    "pnl": trade["pnl"],
                    "timestamp": trade["timestamp"].isoformat(),
                    "win": trade["win"],
                }
                for trade in trades
            ],
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"📄 JSON report saved: {output_path}")

    @staticmethod
    def save_equity_curve_csv(equity_curve: List[Dict], output_path: Path) -> None:
        """
        Save equity curve as CSV.

        Args:
            equity_curve: Equity curve data
            output_path: Output file path
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "equity"])

            for point in equity_curve:
                writer.writerow([point["timestamp"].isoformat(), point["equity"]])

        logger.info(f"📄 Equity curve CSV saved: {output_path}")

    @staticmethod
    def save_trades_csv(trades: List[Dict], output_path: Path) -> None:
        """
        Save trades as CSV.

        Args:
            trades: List of trades
            output_path: Output file path
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "symbol", "pnl", "win"])

            for trade in trades:
                writer.writerow(
                    [
                        trade["timestamp"].isoformat(),
                        trade["symbol"],
                        trade["pnl"],
                        trade["win"],
                    ]
                )

        logger.info(f"📄 Trades CSV saved: {output_path}")

    @staticmethod
    def compare_scenarios(scenario_results: List[Dict]) -> str:
        """
        Generate comparison report for multiple scenarios.

        Args:
            scenario_results: List of {name, stats} dicts

        Returns:
            str: Comparison table
        """
        if not scenario_results:
            return "No scenarios to compare"

        lines = []
        lines.append("=" * 100)
        lines.append("SCENARIO COMPARISON")
        lines.append("=" * 100)
        lines.append("")

        # Header
        header = f"{'Scenario':<25} {'Return':<12} {'Trades':<8} {'Win Rate':<10} {'Max DD':<10} {'Profit Factor':<15}"
        lines.append(header)
        lines.append("-" * 100)

        # Rows
        for result in scenario_results:
            name = result["name"]
            stats = result["stats"]

            row = f"{name:<25} {stats['total_return_pct']:>10.2f}% {stats['total_trades']:>6} {stats['win_rate']*100:>8.1f}% {stats['max_drawdown_pct']:>8.2f}% {stats['profit_factor']:>13.2f}"
            lines.append(row)

        lines.append("")
        lines.append("=" * 100)

        return "\n".join(lines)


# ==============================================================================
# METRICS CALCULATOR (Advanced)
# ==============================================================================


class AdvancedMetrics:
    """
    Advanced trading metrics (Sharpe, Sortino, Calmar, etc.).

    Optional - only if needed for sophisticated analysis.
    """

    @staticmethod
    def calculate_sharpe_ratio(
        returns: List[float], risk_free_rate: float = 0.0
    ) -> float:
        """
        Calculate Sharpe Ratio.

        Args:
            returns: List of period returns
            risk_free_rate: Risk-free rate (annualized)

        Returns:
            float: Sharpe ratio
        """
        if not returns:
            return 0.0

        import statistics

        mean_return = statistics.mean(returns)
        std_return = statistics.stdev(returns) if len(returns) > 1 else 0.0

        if std_return == 0:
            return 0.0

        return (mean_return - risk_free_rate) / std_return

    @staticmethod
    def calculate_sortino_ratio(
        returns: List[float], risk_free_rate: float = 0.0
    ) -> float:
        """
        Calculate Sortino Ratio (only downside deviation).

        Args:
            returns: List of period returns
            risk_free_rate: Risk-free rate

        Returns:
            float: Sortino ratio
        """
        if not returns:
            return 0.0

        import statistics

        mean_return = statistics.mean(returns)
        downside_returns = [r for r in returns if r < 0]

        if not downside_returns:
            return float("inf")

        downside_std = statistics.stdev(downside_returns)

        if downside_std == 0:
            return 0.0

        return (mean_return - risk_free_rate) / downside_std

    @staticmethod
    def calculate_calmar_ratio(
        total_return: float, max_drawdown: float, years: float = 1.0
    ) -> float:
        """
        Calculate Calmar Ratio (return / max drawdown).

        Args:
            total_return: Total return (decimal)
            max_drawdown: Max drawdown (decimal)
            years: Time period in years

        Returns:
            float: Calmar ratio
        """
        if max_drawdown == 0:
            return float("inf")

        annualized_return = total_return / years

        return annualized_return / max_drawdown
