"""E2E Test: Redis & PostgreSQL Integration.

Diese Tests prüfen die echte Integration mit Redis und PostgreSQL
(keine Mocks).

Voraussetzung: docker compose up -d
Ausführung: pytest -v -m e2e tests/e2e/test_redis_postgres_integration.py
"""

from __future__ import annotations

import os
import time

import psycopg2
import pytest
import redis


@pytest.fixture(scope="module")
def redis_client():
    """Echte Redis-Verbindung (kein Mock)."""
    redis_password = os.getenv("REDIS_PASSWORD", "claire_redis_secret_2024")

    client = redis.Redis(
        host="localhost", port=6379, password=redis_password, decode_responses=True
    )

    # Verbindung testen
    try:
        client.ping()
    except redis.ConnectionError as e:
        pytest.skip(f"Redis nicht erreichbar: {e}. Starte: docker compose up -d")

    yield client
    client.close()


@pytest.fixture(scope="module")
def postgres_conn():
    """Echte PostgreSQL-Verbindung (kein Mock)."""
    pg_user = os.getenv("POSTGRES_USER", "claire_user")
    pg_password = os.getenv("POSTGRES_PASSWORD", "claire_db_secret_2024")
    pg_db = os.getenv("POSTGRES_DB", "claire_de_binare")

    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database=pg_db,
            user=pg_user,
            password=pg_password,
        )
    except psycopg2.OperationalError as e:
        pytest.skip(f"PostgreSQL nicht erreichbar: {e}. Starte: docker compose up -d")

    yield conn
    conn.close()


# =============================================================================
# Redis Integration Tests
# =============================================================================


@pytest.mark.e2e
@pytest.mark.local_only
def test_redis_connection(redis_client):
    """Test: Redis-Verbindung funktioniert."""
    assert redis_client.ping() is True


@pytest.mark.e2e
@pytest.mark.local_only
def test_redis_pub_sub_basic(redis_client):
    """Test: Redis Pub/Sub funktioniert."""
    channel = "test_channel"
    message = "test_message"

    # Subscribe
    pubsub = redis_client.pubsub()
    pubsub.subscribe(channel)

    # Warte auf Subscribe-Bestätigung
    time.sleep(0.1)

    # Publish
    redis_client.publish(channel, message)
    time.sleep(0.1)

    # Empfange Message
    messages = []
    for msg in pubsub.listen():
        if msg["type"] == "message":
            messages.append(msg["data"])
            break

    assert len(messages) > 0
    assert messages[0] == message

    pubsub.close()


@pytest.mark.e2e
@pytest.mark.local_only
def test_redis_set_get(redis_client):
    """Test: Redis SET/GET funktioniert."""
    key = "test:key"
    value = "test_value"

    redis_client.set(key, value, ex=10)  # 10s TTL
    result = redis_client.get(key)

    assert result == value

    # Cleanup
    redis_client.delete(key)


@pytest.mark.e2e
@pytest.mark.local_only
def test_redis_event_bus_simulation(redis_client):
    """Test: Simuliere Event-Bus Pattern (market_data → signals)."""
    market_data_channel = "market_data"
    test_event = '{"symbol":"BTCUSDT","price":50000.0,"timestamp":"2025-11-19T00:00:00Z"}'

    # Subscribe zu market_data
    pubsub = redis_client.pubsub()
    pubsub.subscribe(market_data_channel)
    time.sleep(0.1)

    # Publish market_data Event
    redis_client.publish(market_data_channel, test_event)
    time.sleep(0.1)

    # Empfange Event
    received = None
    for msg in pubsub.listen():
        if msg["type"] == "message":
            received = msg["data"]
            break

    assert received is not None
    assert "BTCUSDT" in received
    assert "50000" in received

    pubsub.close()


# =============================================================================
# PostgreSQL Integration Tests
# =============================================================================


@pytest.mark.e2e
@pytest.mark.local_only
def test_postgres_connection(postgres_conn):
    """Test: PostgreSQL-Verbindung funktioniert."""
    cursor = postgres_conn.cursor()
    cursor.execute("SELECT 1")
    result = cursor.fetchone()
    cursor.close()

    assert result == (1,)


@pytest.mark.e2e
@pytest.mark.local_only
def test_postgres_tables_exist(postgres_conn):
    """Test: Erwartete Tabellen existieren in PostgreSQL."""
    expected_tables = [
        "signals",
        "orders",
        "trades",
        "positions",
        "portfolio_snapshots",
    ]

    cursor = postgres_conn.cursor()
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
    """)

    existing_tables = [row[0] for row in cursor.fetchall()]
    cursor.close()

    for table in expected_tables:
        assert table in existing_tables, (
            f"Tabelle '{table}' fehlt in PostgreSQL. "
            f"Vorhandene Tabellen: {existing_tables}"
        )


@pytest.mark.e2e
@pytest.mark.local_only
def test_postgres_insert_select_signal(postgres_conn):
    """Test: Insert & Select in signals-Tabelle."""
    cursor = postgres_conn.cursor()

    # Insert Test-Signal
    cursor.execute("""
        INSERT INTO signals (
            symbol, signal_type, price, confidence, timestamp
        ) VALUES (
            %s, %s, %s, %s, NOW()
        ) RETURNING id
    """, ("BTCUSDT_TEST", "buy", 50000.0, 0.85))

    signal_id = cursor.fetchone()[0]
    postgres_conn.commit()

    # Select Test-Signal
    cursor.execute("SELECT symbol, signal_type, price FROM signals WHERE id = %s", (signal_id,))
    result = cursor.fetchone()

    assert result is not None
    assert result[0] == "BTCUSDT_TEST"
    assert result[1] == "buy"
    assert abs(float(result[2]) - 50000.0) < 0.01

    # Cleanup
    cursor.execute("DELETE FROM signals WHERE id = %s", (signal_id,))
    postgres_conn.commit()
    cursor.close()


# =============================================================================
# Cross-Service Integration
# =============================================================================


@pytest.mark.e2e
@pytest.mark.local_only
@pytest.mark.slow
def test_redis_to_postgres_flow(redis_client, postgres_conn):
    """Test: Simuliere Event-Flow von Redis zu PostgreSQL.

    Flow: Redis Event → (Service würde hier reagieren) → PostgreSQL Write
    Wir simulieren den Service-Teil manuell.
    """
    # 1. Publish Signal-Event in Redis
    signal_channel = "signals"
    signal_event = (
        '{"symbol":"ETHUSDT","signal_type":"sell","price":3000.0,"confidence":0.9}'
    )

    redis_client.publish(signal_channel, signal_event)
    time.sleep(0.2)

    # 2. Simuliere Service-Logic: Parse Event & Write to PostgreSQL
    cursor = postgres_conn.cursor()
    cursor.execute("""
        INSERT INTO signals (symbol, signal_type, price, confidence, timestamp)
        VALUES (%s, %s, %s, %s, NOW())
        RETURNING id
    """, ("ETHUSDT", "sell", 3000.0, 0.9))

    signal_id = cursor.fetchone()[0]
    postgres_conn.commit()

    # 3. Verify: Signal ist in DB
    cursor.execute("SELECT symbol, signal_type FROM signals WHERE id = %s", (signal_id,))
    result = cursor.fetchone()

    assert result is not None
    assert result[0] == "ETHUSDT"
    assert result[1] == "sell"

    # Cleanup
    cursor.execute("DELETE FROM signals WHERE id = %s", (signal_id,))
    postgres_conn.commit()
    cursor.close()
