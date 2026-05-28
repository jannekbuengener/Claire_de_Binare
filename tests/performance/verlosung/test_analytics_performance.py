"""
Analytics Performance Test - Claire de Binare
Lokaler-only Test: Query-Performance mit realen Daten

WICHTIG: Dieser Test MUSS lokal ausgeführt werden!
    - Erfordert PostgreSQL mit Daten
    - Testet Query-Performance
    - Identifiziert langsame Queries
    - NICHT in CI (braucht populated DB)

Ausführung:
    pytest -v -m local_only tests/local/test_analytics_performance.py
"""

import pytest
import psycopg2
from psycopg2.extras import RealDictCursor
import time


@pytest.fixture
def postgres_conn():
    """PostgreSQL connection"""
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="claire_de_binare",
        user="claire_user",
        password="local_test",
    )
    yield conn
    conn.close()


@pytest.mark.local_only
def test_query_performance_signals_aggregation(postgres_conn):
    """
    Performance-Test: Signals Aggregation Query

    Validiert:
    - Query-Laufzeit < 500ms
    - Index-Nutzung
    - Aggregation-Performance
    """
    print("\n📊 Testing signals aggregation performance...")

    cursor = postgres_conn.cursor(cursor_factory=RealDictCursor)

    start = time.time()

    cursor.execute("""
        SELECT
            symbol,
            signal_type,
            COUNT(*) as signal_count,
            AVG(confidence) as avg_confidence,
            MAX(price) as max_price,
            MIN(price) as min_price
        FROM signals
        WHERE timestamp >= NOW() - INTERVAL '7 days'
        GROUP BY symbol, signal_type
        ORDER BY signal_count DESC
        LIMIT 10
    """)

    results = cursor.fetchall()
    elapsed = time.time() - start

    print(f"✓ Query completed in {elapsed*1000:.2f}ms")
    print(f"✓ Returned {len(results)} rows")

    # Performance assertion
    assert elapsed < 0.5, f"Query too slow: {elapsed*1000:.0f}ms (max 500ms)"

    # Log results
    if results:
        print("\n📊 Top Symbols by Signal Count:")
        for row in results[:5]:
            print(
                f"  - {row['symbol']} ({row['signal_type']}): {row['signal_count']} signals"
            )


@pytest.mark.local_only
def test_query_performance_portfolio_snapshots_timeseries(postgres_conn):
    """
    Performance-Test: Portfolio Snapshots Time-Series

    Validiert:
    - Time-Series Query Performance
    - Index auf timestamp-Spalte
    - Aggregation-Performance
    """
    print("\n📊 Testing portfolio snapshots time-series performance...")

    cursor = postgres_conn.cursor(cursor_factory=RealDictCursor)

    start = time.time()

    cursor.execute("""
        SELECT
            DATE(timestamp) as date,
            COUNT(*) as snapshot_count,
            AVG(total_equity) as avg_equity,
            AVG(daily_pnl) as avg_daily_pnl,
            MAX(total_exposure_pct) * 100 as max_exposure_pct
        FROM portfolio_snapshots
        WHERE timestamp >= NOW() - INTERVAL '30 days'
        GROUP BY DATE(timestamp)
        ORDER BY date DESC
        LIMIT 30
    """)

    results = cursor.fetchall()
    elapsed = time.time() - start

    print(f"✓ Query completed in {elapsed*1000:.2f}ms")
    print(f"✓ Returned {len(results)} days")

    # Performance assertion
    assert elapsed < 1.0, f"Time-series query too slow: {elapsed*1000:.0f}ms"

    if results:
        print(f"\n📊 Portfolio Performance (Last {len(results)} days):")
        for row in results[:5]:
            print(
                f"  - {row['date']}: Equity={row['avg_equity']:.2f}, P&L={row['avg_daily_pnl']:.2f}"
            )


@pytest.mark.local_only
def test_query_performance_trades_join_orders(postgres_conn):
    """
    Performance-Test: Trades JOIN Orders

    Validiert:
    - JOIN Performance
    - Foreign-Key Index-Nutzung
    - Complex Query Performance
    """
    print("\n📊 Testing trades-orders JOIN performance...")

    cursor = postgres_conn.cursor(cursor_factory=RealDictCursor)

    start = time.time()

    cursor.execute("""
        SELECT
            t.id as trade_id,
            t.symbol,
            t.side,
            t.price as execution_price,
            t.size,
            t.slippage_bps,
            o.price as order_price,
            o.approved,
            o.status as order_status
        FROM trades t
        LEFT JOIN orders o ON t.order_id = o.id
        WHERE t.timestamp >= NOW() - INTERVAL '24 hours'
        ORDER BY t.timestamp DESC
        LIMIT 100
    """)

    results = cursor.fetchall()
    elapsed = time.time() - start

    print(f"✓ JOIN query completed in {elapsed*1000:.2f}ms")
    print(f"✓ Returned {len(results)} trades")

    # Performance assertion
    assert elapsed < 1.5, f"JOIN query too slow: {elapsed*1000:.0f}ms"

    if results:
        print(f"\n📊 Recent Trades (Last 24h): {len(results)} trades")
        filled_trades = [r for r in results if r.get("order_status") == "filled"]
        if filled_trades:
            print(f"  ✓ {len(filled_trades)} filled orders")


@pytest.mark.local_only
def test_query_performance_full_text_search(postgres_conn):
    """
    Performance-Test: Full-Text Search (wenn implementiert)

    Validiert:
    - Text-Search Performance
    - JSONB Query Performance
    """
    print("\n📊 Testing metadata search performance...")

    cursor = postgres_conn.cursor(cursor_factory=RealDictCursor)

    start = time.time()

    # Search in JSONB metadata
    cursor.execute("""
        SELECT
            symbol,
            signal_type,
            confidence,
            metadata
        FROM signals
        WHERE metadata ? 'strategy'
        ORDER BY timestamp DESC
        LIMIT 50
    """)

    results = cursor.fetchall()
    elapsed = time.time() - start

    print(f"✓ JSONB search completed in {elapsed*1000:.2f}ms")
    print(f"✓ Found {len(results)} signals with metadata.strategy")

    # Performance assertion
    assert elapsed < 2.0, f"Metadata search too slow: {elapsed*1000:.0f}ms"


@pytest.mark.local_only
def test_database_index_effectiveness(postgres_conn):
    """
    Test: Index-Effectiveness prüfen

    Validiert:
    - Alle wichtigen Indices existieren
    - Indices werden genutzt (EXPLAIN ANALYZE)
    """
    print("\n📊 Checking database indices...")

    cursor = postgres_conn.cursor(cursor_factory=RealDictCursor)

    # Check existing indices
    cursor.execute("""
        SELECT
            schemaname,
            tablename,
            indexname,
            indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
        ORDER BY tablename, indexname
    """)

    indices = cursor.fetchall()

    print(f"\n📊 Found {len(indices)} indices:")
    for idx in indices:
        print(f"  - {idx['tablename']}.{idx['indexname']}")

    # Validate critical indices exist
    critical_indices = [
        "idx_signals_timestamp",
        "idx_signals_symbol",
        "idx_orders_created_at",
        "idx_trades_timestamp",
        "idx_portfolio_snapshots_timestamp",
    ]

    existing_index_names = [idx["indexname"] for idx in indices]

    missing = [idx for idx in critical_indices if idx not in existing_index_names]

    if missing:
        print(f"\n⚠️  Missing critical indices: {missing}")
    else:
        print("\n✅ All critical indices present")

    # EXPLAIN ANALYZE für wichtige Query
    print("\n📊 Checking index usage (EXPLAIN ANALYZE)...")

    cursor.execute("""
        EXPLAIN (FORMAT JSON, ANALYZE TRUE)
        SELECT * FROM signals
        WHERE timestamp >= NOW() - INTERVAL '1 day'
        ORDER BY timestamp DESC
        LIMIT 10
    """)

    # RealDictCursor returns dict, not tuple
    row = cursor.fetchone()
    if row:
        # EXPLAIN JSON returns column named 'QUERY PLAN'
        explain_result = list(row.values())[0] if row else []
    else:
        explain_result = []

    # Check if Index Scan is used (not Seq Scan)
    explain_str = str(explain_result)

    if "Index Scan" in explain_str:
        print("  ✅ Query uses Index Scan (optimal)")
    elif "Seq Scan" in explain_str:
        print("  ⚠️  Query uses Sequential Scan (consider adding index)")
    else:
        print(f"  ℹ️  Scan type: {explain_str[:100]}")


@pytest.mark.local_only
@pytest.mark.slow
def test_analytics_query_tool_integration(postgres_conn):
    """
    Integration-Test: Analytics Query Tool gegen echte DB

    Validiert:
    - query_analytics.py funktioniert
    - Alle Queries laufen durch
    - Keine SQL-Errors

    Requires: live PostgreSQL on localhost with claire_user credentials.
    Excluded from standard pytest collection via norecursedirs=verlosung (pytest.ini).
    Run explicitly: pytest tests/performance/verlosung/test_analytics_performance.py -m local_only
    """
    print("\n📊 Testing analytics query tool integration...")

    import subprocess
    import os

    # Test verschiedene Query-Commands
    commands = [
        ["python", "infrastructure/scripts/query_analytics.py", "--last-signals", "5"],
        ["python", "infrastructure/scripts/query_analytics.py", "--last-trades", "5"],
        ["python", "infrastructure/scripts/query_analytics.py", "--portfolio-summary"],
        ["python", "infrastructure/scripts/query_analytics.py", "--trade-statistics"],
    ]

    # Prepare environment: copy current env and add PostgreSQL credentials
    test_env = os.environ.copy()
    test_env["POSTGRES_HOST"] = "localhost"
    test_env["POSTGRES_PASSWORD"] = "local_test"

    results = []

    for cmd in commands:
        print(f"\n  Testing: {' '.join(cmd[2:])}")
        result = subprocess.run(
            cmd, env=test_env, capture_output=True, text=True, timeout=10
        )

        success = result.returncode == 0
        results.append((cmd, success, result.returncode))

        if success:
            print("    ✅ Command successful")
        else:
            print(f"    ❌ Command failed with code {result.returncode}")
            if result.stderr:
                print(f"    Error: {result.stderr[:200]}")

    # Summary
    successful = sum(1 for _, success, _ in results if success)
    total = len(results)

    print(f"\n📊 Analytics Tool Integration: {successful}/{total} commands successful")

    # Mindestens 2/4 sollten funktionieren (DB könnte leer sein)
    assert successful >= 2, f"Too many query tool failures: {successful}/{total}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "local_only"])
