#!/usr/bin/env python3
"""
PostgreSQL Persistence Validator - Claire de Binare
Validates that test events were correctly persisted to PostgreSQL
"""

import os
import sys
from datetime import datetime

import psycopg2


ALLOWED_SIGNAL_TYPES = {"buy", "sell"}
ALLOWED_ORDER_SIDES = {"buy", "sell", "long", "short"}
ALLOWED_TRADE_SIDES = {"buy", "sell"}


def connect_postgres():
    """Connect to PostgreSQL"""
    pg_host = os.getenv("POSTGRES_HOST", "localhost")
    pg_port = int(os.getenv("POSTGRES_PORT", "5432"))
    pg_db = os.getenv("POSTGRES_DB", "claire_de_binare")
    pg_user = os.getenv("POSTGRES_USER", "claire_user")
    pg_password = os.getenv("POSTGRES_PASSWORD", "")

    try:
        conn = psycopg2.connect(
            host=pg_host,
            port=pg_port,
            database=pg_db,
            user=pg_user,
            password=pg_password,
        )
        print(f"✅ Connected to PostgreSQL at {pg_host}:{pg_port}/{pg_db}")
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to PostgreSQL: {e}")
        sys.exit(1)


def validate_signals(conn):
    """Validate signals table"""
    print("\n" + "=" * 60)
    print("📊 VALIDATING: signals")
    print("=" * 60)

    cursor = conn.cursor()

    # Count
    cursor.execute("SELECT COUNT(*) FROM signals")
    count = cursor.fetchone()[0]
    print(f"✅ Total signals: {count}")

    issues = []

    if count == 0:
        issue = "No signals found! Did you publish the events?"
        print(f"⚠️  {issue}")
        issues.append(issue)
        return issues

    # Check signal_type (should be lowercase)
    cursor.execute("""
        SELECT id, symbol, signal_type, confidence,
               TO_CHAR(timestamp, 'YYYY-MM-DD HH24:MI:SS') AS ts
        FROM signals
        ORDER BY id DESC
        LIMIT 5
    """)

    print("\n📋 Latest 5 signals:")
    print(f"{'ID':<5} {'Symbol':<10} {'Type':<6} {'Confidence':<12} {'Timestamp':<20}")
    print("-" * 60)

    for row in cursor.fetchall():
        id_, symbol, signal_type, confidence, ts = row

        # Validate signal_type is lowercase
        if signal_type not in ALLOWED_SIGNAL_TYPES:
            issues.append(f"Signal {id_} has invalid signal_type '{signal_type}'")
            print(f"❌ {id_:<5} {symbol:<10} {signal_type:<6} INVALID (not lowercase!)")
        else:
            print(f"✅ {id_:<5} {symbol:<10} {signal_type:<6} {float(confidence):<12.2f} {ts:<20}")

    # Check for uppercase signal_type (should NOT exist after fix)
    cursor.execute("SELECT COUNT(*) FROM signals WHERE signal_type IN ('BUY', 'SELL')")
    uppercase_count = cursor.fetchone()[0]

    if uppercase_count > 0:
        issues.append(f"Found {uppercase_count} signals with UPPERCASE signal_type")
        print(f"\n❌ WARNING: Found {uppercase_count} signals with UPPERCASE signal_type!")
    else:
        print("\n✅ All signals have lowercase signal_type")

    return issues


def validate_orders(conn):
    """Validate orders table"""
    print("\n" + "=" * 60)
    print("📊 VALIDATING: orders")
    print("=" * 60)

    cursor = conn.cursor()

    # Count
    cursor.execute("SELECT COUNT(*) FROM orders")
    count = cursor.fetchone()[0]
    print(f"✅ Total orders: {count}")

    issues = []

    if count == 0:
        issues.append("No orders found!")
        print("⚠️  No orders found!")
        return issues

    # Check side (should be lowercase)
    cursor.execute("""
        SELECT id, symbol, side, approved, status,
               TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') AS ts
        FROM orders
        ORDER BY id DESC
        LIMIT 5
    """)

    print("\n📋 Latest 5 orders:")
    print(f"{'ID':<5} {'Symbol':<10} {'Side':<6} {'Approved':<10} {'Status':<10} {'Created At':<20}")
    print("-" * 80)

    for row in cursor.fetchall():
        id_, symbol, side, approved, status, ts = row

        # Validate side is lowercase
        if side not in ALLOWED_ORDER_SIDES:
            issues.append(f"Order {id_} has invalid side '{side}'")
            print(f"❌ {id_:<5} {symbol:<10} {side:<6} INVALID!")
        else:
            approved_str = "✅ Yes" if approved else "❌ No"
            print(f"✅ {id_:<5} {symbol:<10} {side:<6} {approved_str:<10} {status:<10} {ts:<20}")

    # Check for UPPERCASE side (should NOT exist after fix)
    cursor.execute("SELECT COUNT(*) FROM orders WHERE side IN ('BUY', 'SELL', 'LONG', 'SHORT')")
    uppercase_count = cursor.fetchone()[0]

    if uppercase_count > 0:
        issues.append(f"Found {uppercase_count} orders with UPPERCASE side")
        print(f"\n❌ CRITICAL: Found {uppercase_count} orders with UPPERCASE side!")
        print("   This means the fix didn't work - check db_writer.py line 200")
    else:
        print("\n✅ All orders have lowercase side ← FIX WORKING!")

    return issues


def validate_trades(conn):
    """Validate trades table"""
    print("\n" + "=" * 60)
    print("📊 VALIDATING: trades")
    print("=" * 60)

    cursor = conn.cursor()

    # Count
    cursor.execute("SELECT COUNT(*) FROM trades")
    count = cursor.fetchone()[0]
    print(f"✅ Total trades: {count}")

    issues = []

    if count == 0:
        issues.append("No trades found!")
        print("⚠️  No trades found!")
        return issues

    # Check side and slippage
    cursor.execute("""
        SELECT id, symbol, side, price, slippage_bps,
               TO_CHAR(timestamp, 'YYYY-MM-DD HH24:MI:SS') AS ts
        FROM trades
        ORDER BY id DESC
        LIMIT 5
    """)

    print("\n📋 Latest 5 trades:")
    print(f"{'ID':<5} {'Symbol':<10} {'Side':<6} {'Price':<12} {'Slippage (bps)':<15} {'Timestamp':<20}")
    print("-" * 80)

    for row in cursor.fetchall():
        id_, symbol, side, price, slippage_bps, ts = row

        # Validate side is lowercase
        if side not in ALLOWED_TRADE_SIDES:
            issues.append(f"Trade {id_} has invalid side '{side}'")
            print(f"❌ {id_:<5} {symbol:<10} {side:<6} INVALID!")
        else:
            if slippage_bps is None:
                slippage_str = "N/A"
            else:
                slippage_str = f"{float(slippage_bps):.2f}"
            print(f"✅ {id_:<5} {symbol:<10} {side:<6} {float(price):<12.2f} {slippage_str:<15} {ts:<20}")

    # Check for UPPERCASE side
    cursor.execute("SELECT COUNT(*) FROM trades WHERE side IN ('BUY', 'SELL')")
    uppercase_count = cursor.fetchone()[0]

    if uppercase_count > 0:
        issues.append(f"Found {uppercase_count} trades with UPPERCASE side")
        print(f"\n❌ CRITICAL: Found {uppercase_count} trades with UPPERCASE side!")
        print("   Check db_writer.py line 248")
    else:
        print("\n✅ All trades have lowercase side ← FIX WORKING!")

    return issues


def validate_portfolio_snapshots(conn):
    """Validate portfolio_snapshots table"""
    print("\n" + "=" * 60)
    print("📊 VALIDATING: portfolio_snapshots")
    print("=" * 60)

    cursor = conn.cursor()

    # Count
    cursor.execute("SELECT COUNT(*) FROM portfolio_snapshots")
    count = cursor.fetchone()[0]
    print(f"✅ Total snapshots: {count}")

    issues = []

    if count == 0:
        issues.append("No portfolio snapshots found!")
        print("⚠️  No portfolio snapshots found!")
        return issues

    # Check total_exposure_pct (should be 0.0-1.0, NOT 0.0-0.01)
    cursor.execute("""
        SELECT id, total_equity, total_exposure_pct, daily_pnl,
               TO_CHAR(timestamp, 'YYYY-MM-DD HH24:MI:SS') AS ts
        FROM portfolio_snapshots
        ORDER BY id DESC
        LIMIT 5
    """)

    print("\n📋 Latest 5 snapshots:")
    print(f"{'ID':<5} {'Equity':<12} {'Exposure %':<12} {'Daily PnL':<12} {'Timestamp':<20}")
    print("-" * 70)

    exposure_issues = []

    for row in cursor.fetchall():
        id_, equity, exposure_pct, daily_pnl, ts = row

        exposure_val = float(exposure_pct)

        # Check if exposure looks wrong (e.g., 0.0005 instead of 0.05)
        if 0 < exposure_val < 0.01:
            exposure_issues.append((id_, exposure_val))
            print(f"⚠️  {id_:<5} {float(equity):<12.2f} {exposure_val:<12.6f} ← SUSPICIOUS! {float(daily_pnl):<12.2f} {ts:<20}")
        else:
            print(f"✅ {id_:<5} {float(equity):<12.2f} {exposure_val:<12.4f} {float(daily_pnl):<12.2f} {ts:<20}")

    if exposure_issues:
        issues.append(f"Found {len(exposure_issues)} snapshots with suspicious exposure values")
        print(f"\n❌ WARNING: Found {len(exposure_issues)} snapshots with suspicious exposure values!")
        print("   Expected: 0.05 (5%), 0.30 (30%)")
        print("   Found:    0.0005, 0.003, etc. (too small!)")
        print("   This indicates the double-division bug might still exist!")
        print("   Check db_writer.py line 297")
    else:
        print("\n✅ All exposure values look correct ← FIX WORKING!")

    return issues


def summary(conn):
    """Print summary"""
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            'signals' AS table_name, COUNT(*) AS row_count FROM signals
        UNION ALL
        SELECT 'orders', COUNT(*) FROM orders
        UNION ALL
        SELECT 'trades', COUNT(*) FROM trades
        UNION ALL
        SELECT 'portfolio_snapshots', COUNT(*) FROM portfolio_snapshots
        UNION ALL
        SELECT 'positions', COUNT(*) FROM positions
    """)

    print(f"\n{'Table':<25} {'Rows':<10}")
    print("-" * 35)

    for row in cursor.fetchall():
        table, count = row
        status = "✅" if count > 0 else "⚠️ "
        print(f"{status} {table:<23} {count:<10}")

    print("\n" + "=" * 60)


def run_validations(conn):
    """Run all validations and collect any issues."""
    issues = []
    issues.extend(validate_signals(conn))
    issues.extend(validate_orders(conn))
    issues.extend(validate_trades(conn))
    issues.extend(validate_portfolio_snapshots(conn))
    return issues


def main():
    """Main execution"""
    print("=" * 60)
    print("🧪 Claire de Binare - Persistence Validator")
    print("=" * 60)

    # Connect
    conn = connect_postgres()

    try:
        issues = run_validations(conn)

        # Summary
        summary(conn)

        if issues:
            print("\n❌ Validation found issues:")
            for issue in issues:
                print(f" - {issue}")
            sys.exit(1)

        print("\n✅ Validation complete!")

    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
