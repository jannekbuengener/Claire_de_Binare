#!/usr/bin/env python3
"""
Paper Trading End-to-End Test
Tests: Order → EnhancedMockExecutor → Database

No Docker required - direct PostgreSQL connection.
"""

import sys
import os
from pathlib import Path

# CRITICAL: Set ENV variables BEFORE any imports!
os.environ['POSTGRES_HOST'] = 'localhost'
os.environ['POSTGRES_PORT'] = '5432'
os.environ['POSTGRES_USER'] = 'claire_user'
os.environ['POSTGRES_PASSWORD'] = 'claire_db_secret_2024'
os.environ['POSTGRES_DB'] = 'claire_de_binare'
os.environ['DATABASE_URL'] = 'postgresql://claire_user:claire_db_secret_2024@localhost:5432/claire_de_binare'

# Add services to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "services" / "execution"))
sys.path.insert(0, str(project_root / "core"))

from services.execution.models import Order, OrderStatus
from services.execution.mock_executor import MockExecutor
from services.execution.database import Database
import psycopg2

# Database connection (localhost, not docker)
DATABASE_URL = "postgresql://claire_user:claire_db_secret_2024@localhost:5432/claire_de_binare"

def test_paper_trading_e2e():
    """
    End-to-End test: Create order, execute with EnhancedMockExecutor, save to DB
    """
    print("=" * 70)
    print("Paper Trading E2E Test")
    print("=" * 70)

    # Step 1: Create test order
    print("\n[1/5] Creating test order...")
    test_order = Order(
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.01,  # 0.01 BTC
        client_id="test-e2e-001"
    )
    print(f"OK Order created: {test_order.symbol} {test_order.side} {test_order.quantity}")

    # Step 2: Execute with MockExecutor
    print("\n[2/5] Executing with MockExecutor...")
    executor = MockExecutor()
    result = executor.execute_order(test_order)

    print(f"[OK] Execution complete!")
    print(f"   Order ID: {result.order_id}")
    print(f"   Status: {result.status}")
    print(f"   Filled Quantity: {result.filled_quantity}")
    print(f"   Price: ${result.price:,.2f}")

    if hasattr(result, 'metadata') and result.metadata:
        print(f"   Slippage: {result.metadata.get('slippage_pct', 'N/A')}%")
        print(f"   Fee: ${result.metadata.get('fee_amount', 0):.2f}")
        print(f"   Fee Type: {result.metadata.get('fee_type', 'N/A')}")

    # Step 3: Test database connection
    print("\n[3/5] Testing PostgreSQL connection...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.close()
        print("[OK] Database connection successful")
    except Exception as e:
        print(f"[FAIL] Database connection failed: {e}")
        return False

    # Step 4: Save to database (paper_orders table)
    print("\n[4/5] Saving to database...")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Insert into paper_orders
        cur.execute("""
            INSERT INTO paper_orders (
                order_id, client_id, symbol, side, order_type,
                quantity, filled_quantity, filled_price,
                status, fees_usdt, fee_type, filled_at
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, NOW()
            )
        """, (
            result.order_id,
            result.client_id,
            result.symbol,
            result.side,
            "MARKET",
            result.quantity,
            result.filled_quantity,
            result.price,
            result.status,
            0.0,  # fees_usdt
            "TAKER",  # fee_type
        ))
        conn.commit()
        print("[OK] Saved to paper_orders table")

        # Insert into paper_fills if filled
        if result.status == OrderStatus.FILLED.value:
            fill_id = f"{result.order_id}-fill-1"
            cur.execute("""
                INSERT INTO paper_fills (
                    fill_id, order_id, symbol,
                    quantity, price, fees_usdt, filled_at
                ) VALUES (
                    %s, %s, %s,
                    %s, %s, %s, NOW()
                )
            """, (
                fill_id,
                result.order_id,
                result.symbol,
                result.filled_quantity,
                result.price,
                0.0
            ))
            conn.commit()
            print("[OK] Saved to paper_fills table")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"[FAIL] Failed to save: {e}")
        return False

    # Step 5: Verify in database
    print("\n[5/5] Verifying data in PostgreSQL...")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Check paper_orders table
        cur.execute(
            "SELECT order_id, symbol, side, quantity, filled_quantity, status FROM paper_orders WHERE order_id = %s",
            (result.order_id,)
        )
        row = cur.fetchone()

        if row:
            print(f"[OK] Found in paper_orders:")
            print(f"   Order ID: {row[0]}")
            print(f"   Symbol: {row[1]}")
            print(f"   Side: {row[2]}")
            print(f"   Quantity: {row[3]}")
            print(f"   Filled: {row[4]}")
            print(f"   Status: {row[5]}")
        else:
            print("[FAIL] Order not found in paper_orders!")
            return False

        # Check paper_fills table
        cur.execute(
            "SELECT fill_id, quantity, price FROM paper_fills WHERE order_id = %s",
            (result.order_id,)
        )
        fill_row = cur.fetchone()

        if fill_row:
            print(f"\n[OK] Found in paper_fills:")
            print(f"   Fill ID: {fill_row[0]}")
            print(f"   Quantity: {fill_row[1]}")
            print(f"   Price: ${fill_row[2]:,.2f}")
        else:
            print("\n[WARN]  No fill record (order might not be FILLED)")

        # Count total paper orders
        cur.execute("SELECT COUNT(*) FROM paper_orders")
        total_orders = cur.fetchone()[0]
        print(f"\n[STATS] Total paper orders in database: {total_orders}")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"[FAIL] Database verification failed: {e}")
        return False

    print("\n" + "=" * 70)
    print("[SUCCESS] E2E TEST PASSED - Paper Trading Working!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    # Override config for local execution (BEFORE imports!)
    os.environ['POSTGRES_HOST'] = 'localhost'
    os.environ['POSTGRES_PORT'] = '5432'
    os.environ['POSTGRES_USER'] = 'claire_user'
    os.environ['POSTGRES_PASSWORD'] = 'claire_db_secret_2024'
    os.environ['POSTGRES_DB'] = 'claire_de_binare'
    os.environ['DATABASE_URL'] = 'postgresql://claire_user:claire_db_secret_2024@localhost:5432/claire_de_binare'

    try:
        success = test_paper_trading_e2e()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[FAIL] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
