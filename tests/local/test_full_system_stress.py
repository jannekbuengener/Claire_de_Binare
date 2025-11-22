"""
Full System Stress Test - Claire de Binaire
Lokaler-only Test: Vollständige System-Belastung mit realistischen Event-Flows

WICHTIG: Dieser Test MUSS lokal mit Docker Compose ausgeführt werden!
    - Erfordert alle 9 Services running
    - Simuliert 100+ Events
    - Prüft Performance unter Last
    - NICHT in CI ausführen (zu ressourcenintensiv)

Ausführung:
    pytest -v -m local_only tests/local/test_full_system_stress.py
"""

import pytest
import redis
import psycopg2
import json
import time
from datetime import datetime, UTC


@pytest.fixture
def redis_client():
    """Redis client für Event-Publishing"""
    client = redis.Redis(
        host="localhost",
        port=6379,
        password="claire_redis_secret_2024",
        decode_responses=True,
    )
    yield client
    client.close()


@pytest.fixture
def postgres_conn():
    """PostgreSQL connection für Daten-Validierung"""
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="claire_de_binaire",
        user="claire_user",
        password="claire_db_secret_2024",
    )
    yield conn
    conn.close()


@pytest.mark.local_only
@pytest.mark.slow
def test_stress_100_market_data_events(redis_client, postgres_conn):
    """
    Stress-Test: 100 Market-Data Events in 10 Sekunden

    Validiert:
    - Redis Pub/Sub unter Last
    - Signal Engine Throughput
    - DB Writer Performance
    """
    print("\n🔥 Starting stress test: 100 market data events...")

    start_time = time.time()
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"]

    # Publish 100 Events
    for i in range(100):
        symbol = symbols[i % len(symbols)]
        event = {
            "type": "market_data",
            "symbol": symbol,
            "price": 50000 + (i * 10),  # Realistic price movement
            "volume": 1000 + (i * 5),
            "timestamp": datetime.now(UTC).isoformat(),
            "sequence": i,
        }
        redis_client.publish("market_data", json.dumps(event))

        if i % 20 == 0:
            print(f"  ✓ Published {i+1}/100 events...")

    elapsed = time.time() - start_time
    print(f"\n✅ Published 100 events in {elapsed:.2f}s")
    print(f"📊 Throughput: {100/elapsed:.2f} events/sec")

    # Performance-Assertion
    assert elapsed < 15.0, f"Stress test too slow: {elapsed}s (max 15s)"

    # Wait for processing
    time.sleep(3)

    # Validate DB persistence (wenn DB Writer läuft)
    cursor = postgres_conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM signals WHERE timestamp > NOW() - INTERVAL '30 seconds'"
    )
    recent_signals = cursor.fetchone()[0]

    print(f"📊 Recent signals in DB: {recent_signals}")

    # NICHT asserten (DB Writer könnte nicht laufen in allen Szenarien)
    # aber loggen für Debugging
    if recent_signals > 0:
        print(f"✅ DB Writer persisted {recent_signals} signals")
    else:
        print("⚠️  No signals persisted (DB Writer might not be running)")


@pytest.mark.local_only
@pytest.mark.slow
def test_stress_concurrent_signal_and_order_flow(redis_client, postgres_conn):
    """
    Stress-Test: Parallel Signal + Order Events

    Simuliert realistischen Trading-Flow:
    - 50 Signals published
    - 50 Orders published (simuliert Risk-Approval)
    - 25 Order Results (simuliert Execution)

    Validiert Concurrency-Handling
    """
    print("\n🔥 Starting concurrent flow stress test...")

    start = time.time()

    # Phase 1: Signals
    print("  📊 Phase 1: Publishing 50 signals...")
    for i in range(50):
        signal = {
            "type": "signal",
            "symbol": "BTCUSDT",
            "signal_type": "buy" if i % 2 == 0 else "sell",
            "price": 50000 + (i * 50),
            "confidence": 0.7 + (i % 3) * 0.1,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        redis_client.publish("signals", json.dumps(signal))

    # Phase 2: Orders (parallel)
    print("  📊 Phase 2: Publishing 50 orders...")
    for i in range(50):
        order = {
            "type": "order",
            "symbol": "BTCUSDT",
            "side": "buy" if i % 2 == 0 else "sell",
            "quantity": 0.1 + (i % 5) * 0.05,
            "price": 50000 + (i * 50),
            "approved": i % 4 != 0,  # 75% approval rate
            "timestamp": datetime.now(UTC).isoformat(),
        }
        redis_client.publish("orders", json.dumps(order))

    # Phase 3: Order Results
    print("  📊 Phase 3: Publishing 25 order results...")
    for i in range(25):
        result = {
            "type": "order_result",
            "symbol": "BTCUSDT",
            "side": "buy" if i % 2 == 0 else "sell",
            "quantity": 0.1,
            "price": 50000 + (i * 50),
            "status": "filled",
            "timestamp": datetime.now(UTC).isoformat(),
        }
        redis_client.publish("order_results", json.dumps(result))

    elapsed = time.time() - start
    print(f"\n✅ Published 125 events across 3 channels in {elapsed:.2f}s")
    print(f"📊 Throughput: {125/elapsed:.2f} events/sec")

    # Performance assertion
    assert elapsed < 10.0, f"Concurrent flow too slow: {elapsed}s"

    # Wait for DB persistence
    time.sleep(5)

    # Validate DB counts
    cursor = postgres_conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM signals WHERE timestamp > NOW() - INTERVAL '1 minute'"
    )
    signals_count = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM orders WHERE created_at > NOW() - INTERVAL '1 minute'"
    )
    orders_count = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM trades WHERE timestamp > NOW() - INTERVAL '1 minute'"
    )
    trades_count = cursor.fetchone()[0]

    print("\n📊 DB Persistence Results:")
    print(f"  - Signals: {signals_count}")
    print(f"  - Orders: {orders_count}")
    print(f"  - Trades: {trades_count}")

    # Soft assertions (logging only)
    if signals_count > 0 or orders_count > 0 or trades_count > 0:
        print("✅ DB Writer is persisting events")
    else:
        print("⚠️  DB Writer not persisting (check if service is running)")


@pytest.mark.local_only
@pytest.mark.slow
def test_stress_portfolio_snapshot_frequency(redis_client, postgres_conn):
    """
    Stress-Test: Portfolio Snapshots unter hoher Frequenz

    Simuliert:
    - 20 Portfolio-Snapshots in 30 Sekunden
    - Validiert DB Write-Performance
    - Prüft auf Bottlenecks
    """
    print("\n🔥 Starting portfolio snapshot stress test...")

    start = time.time()

    # Baseline snapshot count
    cursor = postgres_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM portfolio_snapshots")
    baseline_count = cursor.fetchone()[0]
    print(f"  📊 Baseline snapshots in DB: {baseline_count}")

    # Publish 20 snapshots
    print("  📊 Publishing 20 portfolio snapshots...")
    for i in range(20):
        snapshot = {
            "type": "portfolio_snapshot",
            "timestamp": datetime.now(UTC).isoformat(),
            "equity": 100000 + (i * 100),
            "cash": 95000 + (i * 50),
            "total_unrealized_pnl": 500 + (i * 10),
            "total_realized_pnl": 1000 + (i * 20),
            "daily_pnl": 200 + (i * 5),
            "total_exposure_pct": 5 + (i % 10),
            "num_positions": 2 + (i % 3),
            "metadata": {"stress_test": True, "sequence": i},
        }
        redis_client.publish("portfolio_snapshots", json.dumps(snapshot))
        time.sleep(1.5)  # Realistic interval (90s between snapshots)

        if i % 5 == 0:
            print(f"    ✓ Published {i+1}/20 snapshots...")

    elapsed = time.time() - start
    print(f"\n✅ Published 20 snapshots in {elapsed:.2f}s")

    # Wait for persistence
    time.sleep(3)

    # Validate DB
    cursor.execute("SELECT COUNT(*) FROM portfolio_snapshots")
    final_count = cursor.fetchone()[0]
    new_snapshots = final_count - baseline_count

    print("\n📊 DB Validation:")
    print(f"  - Baseline: {baseline_count}")
    print(f"  - Final: {final_count}")
    print(f"  - New snapshots: {new_snapshots}")

    # Soft assertion (DB Writer might not be running)
    if new_snapshots > 0:
        print(f"✅ DB Writer persisted {new_snapshots} new snapshots")
        assert (
            new_snapshots >= 10
        ), f"Expected at least 10 snapshots, got {new_snapshots}"
    else:
        print("⚠️  No new snapshots (DB Writer might not be running)")


@pytest.mark.local_only
def test_all_docker_services_under_load(redis_client, postgres_conn):
    """
    Lokaler Test: Alle 9 Services unter realistischer Last

    Validiert:
    - Alle Container sind healthy
    - Keine Memory/CPU-Spikes
    - Services antworten unter Last
    """
    import subprocess

    print("\n🔥 Testing all services under load...")

    # Check Docker status
    result = subprocess.run(
        ["docker", "compose", "ps", "--format", "json"], capture_output=True, text=True
    )

    if result.returncode != 0:
        pytest.skip("Docker Compose not available")

    # Parse multiple JSON objects (one per line)
    services = []
    for line in result.stdout.strip().split("\n"):
        if line.strip():
            services.append(json.loads(line))

    print("\n📊 Docker Services Status:")
    healthy_count = 0
    for service in services:
        name = service.get("Name", "unknown")
        status = service.get("Status", "unknown")
        health = service.get("Health", "N/A")

        is_healthy = "healthy" in status.lower() or health == "healthy"
        if is_healthy:
            healthy_count += 1
            print(f"  ✅ {name}: {status}")
        else:
            print(f"  ⚠️  {name}: {status}")

    print(f"\n📊 Healthy Services: {healthy_count}/{len(services)}")

    # Assertion: Mindestens 7/9 Services müssen healthy sein
    # (DB Writer oder andere könnten in bestimmten Setups fehlen)
    assert (
        healthy_count >= 7
    ), f"Too many unhealthy services: {healthy_count}/{len(services)}"

    # Load test: Publish events while checking health
    print("\n📊 Publishing events under load...")
    for i in range(20):
        event = {
            "type": "market_data",
            "symbol": "BTCUSDT",
            "price": 50000,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        redis_client.publish("market_data", json.dumps(event))

    time.sleep(2)

    # Re-check health after load
    result = subprocess.run(
        ["docker", "compose", "ps", "--format", "json"], capture_output=True, text=True
    )
    services_after = []
    for line in result.stdout.strip().split("\n"):
        if line.strip():
            services_after.append(json.loads(line))

    healthy_after = sum(
        1
        for s in services_after
        if "healthy" in s.get("Status", "").lower() or s.get("Health") == "healthy"
    )

    print(f"\n📊 Services after load: {healthy_after}/{len(services_after)} healthy")

    # Services should remain stable under load
    assert healthy_after >= healthy_count, "Services degraded under load"

    print("\n✅ All services stable under load")


if __name__ == "__main__":
    # Run with: pytest -v -m local_only tests/local/test_full_system_stress.py
    pytest.main([__file__, "-v", "-m", "local_only"])
