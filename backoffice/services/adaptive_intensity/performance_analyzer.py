"""
Performance Analyzer - Analysiert Trade-Performance aus PostgreSQL

Berechnet Metriken über letzte N Trades:
- Winrate
- Profit Factor
- Max Drawdown
- Circuit Breaker Events
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor

try:
    from .models import PerformanceMetrics
except ImportError:
    from models import PerformanceMetrics

logger = logging.getLogger(__name__)


class PerformanceAnalyzer:
    """
    Analysiert Trading-Performance aus PostgreSQL

    Berechnet Performance-Metriken über rollierende Fenster von N Trades.
    """

    def __init__(
        self,
        db_host: str,
        db_port: int,
        db_name: str,
        db_user: str,
        db_password: str,
        lookback_trades: int = 300,
    ):
        """
        Args:
            db_host: PostgreSQL Host
            db_port: PostgreSQL Port
            db_name: Database Name
            db_user: Database User
            db_password: Database Password
            lookback_trades: Anzahl Trades für rollierendes Fenster (default: 300)
        """
        self.db_host = db_host
        self.db_port = db_port
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.lookback_trades = lookback_trades

    def _get_connection(self):
        """Erstellt PostgreSQL Connection"""
        return psycopg2.connect(
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            user=self.db_user,
            password=self.db_password,
        )

    def analyze_recent_performance(self) -> Optional[PerformanceMetrics]:
        """
        Analysiert Performance der letzten N Trades

        Returns:
            PerformanceMetrics oder None wenn nicht genug Daten
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Hole letzte N Trades (mit P&L falls vorhanden)
            cursor.execute(
                """
                SELECT
                    id,
                    symbol,
                    side,
                    size,
                    execution_price,
                    slippage_bps,
                    timestamp,
                    pnl,
                    metadata
                FROM trades
                ORDER BY timestamp DESC
                LIMIT %s
            """,
                (self.lookback_trades,),
            )

            trades = cursor.fetchall()

            if not trades:
                logger.warning("No trades found in database")
                return None

            trade_count = len(trades)

            # Berechne Metriken
            metrics = self._calculate_metrics(trades)

            # Circuit Breaker Events (letzte 7 Tage)
            circuit_breaker_events = self._count_circuit_breaker_events(cursor)

            cursor.close()
            conn.close()

            return PerformanceMetrics(
                timestamp=datetime.now(datetime.UTC),
                trade_count=trade_count,
                lookback_trades=self.lookback_trades,
                winrate=metrics["winrate"],
                profit_factor=metrics["profit_factor"],
                max_drawdown_pct=metrics["max_drawdown_pct"],
                total_pnl=metrics["total_pnl"],
                avg_win=metrics["avg_win"],
                avg_loss=metrics["avg_loss"],
                sharpe_ratio=metrics.get("sharpe_ratio"),
                circuit_breaker_events=circuit_breaker_events,
            )

        except Exception as e:
            logger.error(f"Failed to analyze performance: {e}")
            return None

    def _calculate_metrics(self, trades: list) -> dict:
        """
        Berechnet Performance-Metriken aus Trade-Liste

        Args:
            trades: Liste von Trade-Dicts aus PostgreSQL

        Returns:
            Dict mit berechneten Metriken
        """
        # Filter trades with PnL (nicht alle haben PnL wenn nicht geschlossen)
        trades_with_pnl = [t for t in trades if t.get("pnl") is not None]

        if not trades_with_pnl:
            logger.warning("No trades with P&L found - using placeholder metrics")
            return {
                "winrate": 0.5,
                "profit_factor": 1.0,
                "max_drawdown_pct": 0.0,
                "total_pnl": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
            }

        # Winrate berechnen
        winning_trades = [t for t in trades_with_pnl if t["pnl"] > 0]
        losing_trades = [t for t in trades_with_pnl if t["pnl"] <= 0]

        winrate = len(winning_trades) / len(trades_with_pnl)

        # Profit Factor berechnen
        total_profit = sum(t["pnl"] for t in winning_trades) if winning_trades else 0.0
        total_loss = abs(sum(t["pnl"] for t in losing_trades)) if losing_trades else 0.01

        profit_factor = total_profit / total_loss if total_loss > 0 else 1.0

        # Total P&L
        total_pnl = sum(t["pnl"] for t in trades_with_pnl)

        # Average Win/Loss
        avg_win = total_profit / len(winning_trades) if winning_trades else 0.0
        avg_loss = total_loss / len(losing_trades) if losing_trades else 0.0

        # Max Drawdown berechnen (über kumulative P&L)
        max_drawdown_pct = self._calculate_max_drawdown(trades_with_pnl)

        return {
            "winrate": winrate,
            "profit_factor": profit_factor,
            "max_drawdown_pct": max_drawdown_pct,
            "total_pnl": total_pnl,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
        }

    def _calculate_max_drawdown(self, trades: list) -> float:
        """
        Berechnet maximalen Drawdown über kumulative P&L

        Args:
            trades: Trades sortiert nach timestamp DESC

        Returns:
            Max Drawdown als Prozent (0.0 - 1.0)
        """
        if not trades:
            return 0.0

        # Reverse to chronological order
        trades_chrono = list(reversed(trades))

        # Kumulative P&L
        cumulative_pnl = 0.0
        peak = 0.0
        max_drawdown = 0.0

        for trade in trades_chrono:
            cumulative_pnl += trade["pnl"]

            # Update peak
            if cumulative_pnl > peak:
                peak = cumulative_pnl

            # Berechne Drawdown vom Peak
            if peak > 0:
                drawdown = (peak - cumulative_pnl) / peak
                max_drawdown = max(max_drawdown, drawdown)

        return max_drawdown

    def _count_circuit_breaker_events(self, cursor) -> int:
        """
        Zählt Circuit Breaker Events in letzten 7 Tagen

        Args:
            cursor: PostgreSQL Cursor

        Returns:
            Anzahl Circuit Breaker Events
        """
        try:
            seven_days_ago = datetime.now(datetime.UTC) - timedelta(days=7)

            cursor.execute(
                """
                SELECT COUNT(*) as count
                FROM alerts
                WHERE alert_type = 'CIRCUIT_BREAKER'
                  AND timestamp >= %s
            """,
                (seven_days_ago,),
            )

            result = cursor.fetchone()
            return result["count"] if result else 0

        except Exception as e:
            logger.warning(f"Failed to count circuit breaker events: {e}")
            return 0

    def get_performance_summary(self) -> dict:
        """
        Erstellt Performance-Summary für Logging/Monitoring

        Returns:
            Dict mit Performance-Übersicht
        """
        metrics = self.analyze_recent_performance()

        if not metrics:
            return {"status": "insufficient_data", "trade_count": 0}

        return {
            "status": "ok",
            "trade_count": metrics.trade_count,
            "winrate": f"{metrics.winrate * 100:.1f}%",
            "profit_factor": f"{metrics.profit_factor:.2f}",
            "max_drawdown": f"{metrics.max_drawdown_pct * 100:.1f}%",
            "total_pnl": f"{metrics.total_pnl:.2f}",
            "circuit_breaker_events": metrics.circuit_breaker_events,
            "can_upgrade": metrics.meets_upgrade_criteria(),
            "needs_downgrade": metrics.meets_downgrade_criteria(),
        }
