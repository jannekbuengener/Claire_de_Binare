#!/usr/bin/env python3
"""
One-Time Positions Reconciliation Script

Reconstructs positions table from historical orders/order_results.
Makes positions table the source-of-truth before risk bootstrap runs.

Usage:
    python infrastructure/scripts/reconcile_positions.py

Safety:
    - Idempotent: Can be run multiple times
    - Read-only on orders/order_results tables
    - Writes only to positions table
    - Generates reconciliation report
    - No manual trades created

Context:
    Shadow Mode started 2026-01-17 14:15:00 with empty positions table.
    Paper trading accumulated BUY orders without position tracking.
    This script reconstructs the missing position state.
"""

import os
import sys
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List

import psycopg2
from psycopg2.extras import RealDictCursor

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Shadow Mode start timestamp (when risk service started)
SHADOW_MODE_START = "2026-01-17 14:15:00"


class PositionReconciler:
    """Reconciles positions table from historical orders"""

    def __init__(self):
        self.postgres_host = os.getenv("POSTGRES_HOST", "cdb_postgres")
        self.postgres_port = int(os.getenv("POSTGRES_PORT", "5432"))
        self.postgres_db = os.getenv("POSTGRES_DB", "claire_de_binare")
        self.postgres_user = os.getenv("POSTGRES_USER", "claire_user")
        self.postgres_password = os.getenv("POSTGRES_PASSWORD", "")
        self.conn = None

    def connect(self):
        """Connect to PostgreSQL"""
        try:
            self.conn = psycopg2.connect(
                host=self.postgres_host,
                port=self.postgres_port,
                database=self.postgres_db,
                user=self.postgres_user,
                password=self.postgres_password,
            )
            logger.info(
                f"✅ Connected to PostgreSQL at {self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )
        except Exception as e:
            logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
            raise

    def get_filled_orders(self) -> List[Dict]:
        """
        Get all filled orders since Shadow Mode start.

        Returns:
            List of orders with: symbol, side, filled_size, avg_fill_price, created_at
        """
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)

        # Query filled orders (status='filled', filled_size > 0)
        cursor.execute(
            """
            SELECT
                symbol,
                side,
                filled_size,
                avg_fill_price,
                created_at
            FROM orders
            WHERE status = 'filled'
              AND filled_size > 0
              AND created_at >= %s
            ORDER BY created_at ASC
            """,
            (SHADOW_MODE_START,)
        )

        orders = cursor.fetchall()
        logger.info(f"📊 Found {len(orders)} filled orders since {SHADOW_MODE_START}")
        cursor.close()
        return orders

    def calculate_net_positions(self, orders: List[Dict]) -> Dict[str, Dict]:
        """
        Calculate net position per symbol from order history.

        Args:
            orders: List of filled orders

        Returns:
            Dict mapping symbol -> {
                'net_qty': Decimal,
                'side': 'long' | 'short' | 'none',
                'weighted_entry_price': Decimal,
                'buy_fills': int,
                'sell_fills': int,
                'first_fill': datetime,
                'last_fill': datetime
            }
        """
        positions = {}

        for order in orders:
            symbol = order["symbol"]
            side = order["side"].lower()
            qty = Decimal(str(order["filled_size"]))
            price = Decimal(str(order["avg_fill_price"]))

            if symbol not in positions:
                positions[symbol] = {
                    "buy_qty": Decimal("0"),
                    "buy_notional": Decimal("0"),  # For weighted avg calculation
                    "sell_qty": Decimal("0"),
                    "sell_notional": Decimal("0"),
                    "buy_fills": 0,
                    "sell_fills": 0,
                    "first_fill": order["created_at"],
                    "last_fill": order["created_at"],
                }

            pos = positions[symbol]
            pos["last_fill"] = order["created_at"]

            if side == "buy":
                pos["buy_qty"] += qty
                pos["buy_notional"] += qty * price
                pos["buy_fills"] += 1
            elif side == "sell":
                pos["sell_qty"] += qty
                pos["sell_notional"] += qty * price
                pos["sell_fills"] += 1

        # Calculate net positions and weighted avg entry price
        result = {}
        for symbol, data in positions.items():
            net_qty = data["buy_qty"] - data["sell_qty"]

            if net_qty == 0:
                # Flat position - no need to track
                continue

            # Determine side
            if net_qty > 0:
                side = "long"
                # Weighted avg entry price from BUY fills
                weighted_entry_price = data["buy_notional"] / data["buy_qty"] if data["buy_qty"] > 0 else Decimal("0")
            else:
                side = "short"
                # Weighted avg entry price from SELL fills
                weighted_entry_price = data["sell_notional"] / data["sell_qty"] if data["sell_qty"] > 0 else Decimal("0")

            result[symbol] = {
                "net_qty": abs(net_qty),
                "side": side,
                "weighted_entry_price": weighted_entry_price,
                "buy_fills": data["buy_fills"],
                "sell_fills": data["sell_fills"],
                "first_fill": data["first_fill"],
                "last_fill": data["last_fill"],
            }

            logger.info(
                f"  {symbol}: {side.upper()} {net_qty:.8f} @ {weighted_entry_price:.2f} "
                f"({data['buy_fills']} BUY, {data['sell_fills']} SELL)"
            )

        return result

    def check_existing_positions(self) -> List[Dict]:
        """Check if positions table already has data"""
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT symbol, side, size FROM positions WHERE closed_at IS NULL")
        existing = cursor.fetchall()
        cursor.close()
        return existing

    def write_positions(self, positions: Dict[str, Dict]) -> int:
        """
        Write calculated positions to positions table.

        Args:
            positions: Dict mapping symbol -> position data

        Returns:
            Number of positions written
        """
        if not positions:
            logger.warning("⚠️ No open positions to write")
            return 0

        cursor = self.conn.cursor()
        written = 0

        for symbol, pos in positions.items():
            try:
                # Check if position already exists
                cursor.execute(
                    "SELECT id FROM positions WHERE symbol = %s AND closed_at IS NULL",
                    (symbol,)
                )
                existing = cursor.fetchone()

                if existing:
                    logger.warning(f"⚠️ Position for {symbol} already exists (id={existing[0]}) - skipping")
                    continue

                # Insert new position
                cursor.execute(
                    """
                    INSERT INTO positions
                    (symbol, side, size, entry_price, current_price, opened_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        symbol,
                        pos["side"],
                        pos["net_qty"],
                        pos["weighted_entry_price"],
                        pos["weighted_entry_price"],  # Use entry price as initial current_price
                        pos["first_fill"],
                        pos["last_fill"],
                    )
                )
                position_id = cursor.fetchone()[0]
                self.conn.commit()

                logger.info(
                    f"✅ Position written: ID={position_id}, {symbol} {pos['side'].upper()} "
                    f"{pos['net_qty']:.8f} @ {pos['weighted_entry_price']:.2f}"
                )
                written += 1

            except Exception as e:
                logger.error(f"❌ Failed to write position for {symbol}: {e}")
                self.conn.rollback()
                raise

        cursor.close()
        return written

    def generate_report(self, positions: Dict[str, Dict]) -> str:
        """Generate reconciliation report"""
        total_exposure = sum(
            pos["net_qty"] * pos["weighted_entry_price"]
            for pos in positions.values()
        )

        report = [
            "=" * 80,
            "POSITIONS RECONCILIATION REPORT",
            "=" * 80,
            f"Timestamp: {datetime.utcnow().isoformat()}",
            f"Shadow Mode Start: {SHADOW_MODE_START}",
            f"",
            f"Summary:",
            f"  Total Positions: {len(positions)}",
            f"  Total Exposure: ${total_exposure:,.2f} USD",
            f"",
            "Positions:",
        ]

        for symbol, pos in positions.items():
            exposure = pos["net_qty"] * pos["weighted_entry_price"]
            report.append(
                f"  {symbol}: {pos['side'].upper()} {pos['net_qty']:.8f} @ ${pos['weighted_entry_price']:.2f} "
                f"(exposure: ${exposure:,.2f}, {pos['buy_fills']} BUY / {pos['sell_fills']} SELL)"
            )

        report.append("=" * 80)
        return "\n".join(report)

    def run(self):
        """Main reconciliation workflow"""
        try:
            logger.info("🚀 Starting positions reconciliation...")

            self.connect()

            # Check existing positions
            existing = self.check_existing_positions()
            if existing:
                logger.warning(f"⚠️ Found {len(existing)} existing open positions:")
                for pos in existing:
                    logger.warning(f"  {pos['symbol']}: {pos['side'].upper()} {pos['size']:.8f}")
                logger.warning("⚠️ Reconciliation will skip existing positions (idempotent)")

            # Get filled orders
            orders = self.get_filled_orders()
            if not orders:
                logger.info("✅ No filled orders found - nothing to reconcile")
                return

            # Calculate net positions
            logger.info("📊 Calculating net positions from order history...")
            positions = self.calculate_net_positions(orders)

            if not positions:
                logger.info("✅ All positions are flat (net qty = 0) - nothing to write")
                return

            # Write positions
            logger.info(f"📝 Writing {len(positions)} positions to database...")
            written = self.write_positions(positions)

            # Generate report
            report = self.generate_report(positions)
            logger.info("\n" + report)

            logger.info(f"✅ Reconciliation complete: {written} positions written")

        except Exception as e:
            logger.error(f"❌ Reconciliation failed: {e}")
            raise
        finally:
            if self.conn:
                self.conn.close()
                logger.info("Database connection closed")


if __name__ == "__main__":
    try:
        reconciler = PositionReconciler()
        reconciler.run()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
