"""
Analytics Query Tool - Claire de Binare
Einfache Queries für Trading-Auswertung

Verwendung:
    python query_analytics.py --last-signals 10
    python query_analytics.py --last-trades 20
    python query_analytics.py --portfolio-summary
    python query_analytics.py --daily-pnl
"""

import sys
import os
import argparse
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ModuleNotFoundError:  # pragma: no cover - import-time dependency check
    psycopg2 = None
    RealDictCursor = None

if sys.platform == "win32":
    import codecs

    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")

# datetime and timedelta available if needed for future queries
try:
    from tabulate import tabulate
except ModuleNotFoundError:  # pragma: no cover - import-time dependency check
    tabulate = None


class AnalyticsQuery:
    """Analytics Query Tool"""

    def __init__(self):
        """Initialize database connection"""
        if psycopg2 is None:
            raise RuntimeError(
                "Missing dependency: psycopg2. Install it to use this tool."
            )
        # Use localhost by default (for host machine), cdb_postgres in Docker
        default_host = "localhost" if not os.getenv("DOCKER_ENV") else "cdb_postgres"

        try:
            self.conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", default_host),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                database=os.getenv("POSTGRES_DB", "claire_de_binare"),
                user=os.getenv("POSTGRES_USER", "claire_user"),
                password=os.getenv("POSTGRES_PASSWORD", ""),
            )
        except psycopg2.Error as exc:
            raise RuntimeError(
                "PostgreSQL connection failed. Check POSTGRES_* env vars and DB availability."
            ) from exc

    def _require_tabulate(self) -> bool:
        if tabulate is None:
            print("Missing dependency: tabulate. Install it to print tables.")
            return False
        return True

    def last_signals(self, limit=10):
        """Get last N signals"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT id, symbol, signal_type, price, confidence, timestamp
                FROM signals
                ORDER BY timestamp DESC
                LIMIT %s
            """,
                (limit,),
            )
            rows = cursor.fetchall()

            if rows:
                if not self._require_tabulate():
                    return
                print(f"\n📊 Last {len(rows)} Signals:\n")
                print(tabulate(rows, headers="keys", tablefmt="grid"))
            else:
                print("No signals found.")

    def last_trades(self, limit=20):
        """Get last N trades"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT id, symbol, side, price, size, status, slippage_bps, timestamp
                FROM trades
                ORDER BY timestamp DESC
                LIMIT %s
            """,
                (limit,),
            )
            rows = cursor.fetchall()

            if rows:
                if not self._require_tabulate():
                    return
                print(f"\n💼 Last {len(rows)} Trades:\n")
                print(tabulate(rows, headers="keys", tablefmt="grid"))
            else:
                print("No trades found.")

    def portfolio_summary(self):
        """Get latest portfolio snapshot"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT
                    timestamp,
                    total_equity,
                    available_balance,
                    daily_pnl,
                    total_realized_pnl,
                    total_unrealized_pnl,
                    open_positions,
                    total_exposure_pct
                FROM portfolio_snapshots
                ORDER BY timestamp DESC
                LIMIT 1
            """
            )
            row = cursor.fetchone()

            if row:
                print("\n💰 Portfolio Summary (Latest Snapshot):\n")
                for key, value in row.items():
                    if isinstance(value, float):
                        print(f"  {key:25s}: {value:>15,.2f}")
                    else:
                        print(f"  {key:25s}: {value}")
            else:
                print("No portfolio snapshots found.")

    def daily_pnl(self, days=7):
        """Get daily P&L for last N days"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT
                    DATE(timestamp) as date,
                    COUNT(*) as num_snapshots,
                    AVG(daily_pnl) as avg_daily_pnl,
                    MAX(total_equity) as max_equity,
                    MIN(total_equity) as min_equity
                FROM portfolio_snapshots
                WHERE timestamp >= NOW() - INTERVAL '%s days'
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """,
                (days,),
            )
            rows = cursor.fetchall()

            if rows:
                if not self._require_tabulate():
                    return
                print(f"\n📈 Daily P&L (Last {days} days):\n")
                print(tabulate(rows, headers="keys", tablefmt="grid", floatfmt=".2f"))
            else:
                print(f"No data for the last {days} days.")

    def trade_statistics(self):
        """Get overall trade statistics"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total_trades,
                    COUNT(CASE WHEN side = 'buy' THEN 1 END) as buy_trades,
                    COUNT(CASE WHEN side = 'sell' THEN 1 END) as sell_trades,
                    AVG(slippage_bps) as avg_slippage_bps,
                    SUM(fees) as total_fees,
                    COUNT(DISTINCT symbol) as unique_symbols
                FROM trades
            """
            )
            row = cursor.fetchone()

            if row and row["total_trades"] > 0:
                print("\n📊 Trade Statistics:\n")
                for key, value in row.items():
                    if isinstance(value, float):
                        print(f"  {key:25s}: {value:>15,.2f}")
                    else:
                        print(f"  {key:25s}: {value:>15}")
            else:
                print("No trade statistics available.")

    def open_positions(self):
        """Get currently open positions"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT
                    symbol,
                    side,
                    size,
                    entry_price,
                    current_price,
                    unrealized_pnl,
                    opened_at
                FROM positions
                WHERE side != 'none' AND size > 0
                ORDER BY opened_at DESC
            """
            )
            rows = cursor.fetchall()

            if rows:
                if not self._require_tabulate():
                    return
                print(f"\n📌 Open Positions ({len(rows)}):\n")
                print(tabulate(rows, headers="keys", tablefmt="grid", floatfmt=".2f"))
            else:
                print("No open positions.")

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Claire de Binare - Analytics Query Tool"
    )

    parser.add_argument(
        "--last-signals", type=int, metavar="N", help="Show last N signals"
    )
    parser.add_argument(
        "--last-trades", type=int, metavar="N", help="Show last N trades"
    )
    parser.add_argument(
        "--portfolio-summary",
        action="store_true",
        help="Show latest portfolio snapshot",
    )
    parser.add_argument(
        "--daily-pnl", type=int, metavar="DAYS", help="Show daily P&L for last N days"
    )
    parser.add_argument(
        "--trade-statistics", action="store_true", help="Show overall trade statistics"
    )
    parser.add_argument(
        "--open-positions", action="store_true", help="Show currently open positions"
    )

    args = parser.parse_args()

    # Initialize query tool
    try:
        query = AnalyticsQuery()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    try:
        # Execute requested queries
        if args.last_signals:
            query.last_signals(args.last_signals)

        if args.last_trades:
            query.last_trades(args.last_trades)

        if args.portfolio_summary:
            query.portfolio_summary()

        if args.daily_pnl:
            query.daily_pnl(args.daily_pnl)

        if args.trade_statistics:
            query.trade_statistics()

        if args.open_positions:
            query.open_positions()

        # If no arguments, show usage
        if not any(vars(args).values()):
            parser.print_help()
    except Exception as exc:
        if psycopg2 is not None and isinstance(exc, psycopg2.Error):
            message = getattr(exc, "pgerror", None) or str(exc)
            print(f"ERROR: Database query failed: {message}", file=sys.stderr)
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        query.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
