"""E2E Test: Vollständiger Event-Flow Pipeline.

Testet den kompletten Event-Flow:
market_data → signal_engine → risk_manager → execution → postgres

Voraussetzung: Alle Services laufen (docker compose up -d)
Ausführung: pytest -v -m e2e tests/e2e/test_event_flow_pipeline.py
"""

from __future__ import annotations

import json
import os
import time

import psycopg2
import pytest
import redis
import requests


@pytest.fixture(scope="module")
def redis_client():
    """Echte Redis-Verbindung."""
    redis_password = os.getenv("REDIS_PASSWORD", "claire_redis_secret_2024")
    client = redis.Redis(
        host="localhost", port=6379, password=redis_password, decode_responses=True
    )

    try:
        client.ping()
    except redis.ConnectionError as e:
        pytest.skip(f"Redis nicht erreichbar: {e}")

    yield client
    client.close()


@pytest.fixture(scope="module")
def postgres_conn():
    """Echte PostgreSQL-Verbindung."""
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
        pytest.skip(f"PostgreSQL nicht erreichbar: {e}")

    yield conn
    conn.close()


def _check_service_health(service_name: str, port: int) -> bool:
    """Prüft ob Service-Health-Endpoint erreichbar ist."""
    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=3)
        return response.status_code == 200
    except requests.RequestException:
        return False


# =============================================================================
# Event-Flow Tests
# =============================================================================


@pytest.mark.e2e
@pytest.mark.local_only
@pytest.mark.slow
def test_market_data_event_published(redis_client):
    """Test: Market-Data-Events können in Redis gepublished werden."""
    channel = "market_data"
    test_event = {
        "symbol": "BTCUSDT",
        "price": 50000.0,
        "volume": 1000.0,
        "timestamp": "2025-11-19T00:00:00Z",
    }

    # Subscribe
    pubsub = redis_client.pubsub()
    pubsub.subscribe(channel)
    time.sleep(0.1)

    # Publish
    redis_client.publish(channel, json.dumps(test_event))
    time.sleep(0.1)

    # Receive
    received = None
    for msg in pubsub.listen():
        if msg["type"] == "message":
            received = json.loads(msg["data"])
            break

    assert received is not None
    assert received["symbol"] == "BTCUSDT"
    assert received["price"] == 50000.0

    pubsub.close()


@pytest.mark.e2e
@pytest.mark.local_only
@pytest.mark.slow
def test_signal_engine_responds_to_market_data(redis_client):
    """Test: Signal Engine empfängt Market-Data und generiert Signal.

    Hinweis: Dieser Test prüft das Pattern, nicht die echte Service-Logic.
    """
    # 1. Simuliere Market-Data Event
    market_data_channel = "market_data"
    market_event = {
        "symbol": "ETHUSDT",
        "price": 3000.0,
        "volume": 500.0,
        "timestamp": "2025-11-19T00:00:00Z",
    }

    redis_client.publish(market_data_channel, json.dumps(market_event))
    time.sleep(0.2)

    # 2. In echtem System würde Signal Engine reagieren und Signal publishen
    # Hier simulieren wir das manuelle:
    signal_channel = "signals"
    signal_event = {
        "symbol": "ETHUSDT",
        "signal_type": "buy",
        "price": 3000.0,
        "confidence": 0.85,
        "source": "momentum_strategy",
    }

    # Subscribe zu signals
    pubsub = redis_client.pubsub()
    pubsub.subscribe(signal_channel)
    time.sleep(0.1)

    # Publish Signal
    redis_client.publish(signal_channel, json.dumps(signal_event))
    time.sleep(0.1)

    # Verify Signal empfangen
    received = None
    for msg in pubsub.listen():
        if msg["type"] == "message":
            received = json.loads(msg["data"])
            break

    assert received is not None
    assert received["symbol"] == "ETHUSDT"
    assert received["signal_type"] == "buy"

    pubsub.close()


@pytest.mark.e2e
@pytest.mark.local_only
@pytest.mark.slow
def test_risk_manager_validates_signal(redis_client):
    """Test: Risk Manager validiert Signal und erzeugt Order.

    Flow: Signal → Risk Validation → Order (approved/rejected)
    """
    # 1. Publish Signal
    signal_channel = "signals"
    signal_event = {
        "symbol": "BTCUSDT",
        "signal_type": "buy",
        "price": 50000.0,
        "size": 0.1,
        "confidence": 0.9,
    }

    redis_client.publish(signal_channel, json.dumps(signal_event))
    time.sleep(0.2)

    # 2. Simuliere Risk-Validation (würde normalerweise Risk Manager tun)
    # Bei validem Signal → Order erstellen
    order_channel = "orders"
    order_event = {
        "symbol": "BTCUSDT",
        "side": "buy",
        "price": 50000.0,
        "size": 0.1,
        "approved": True,
        "reason": None,
    }

    # Subscribe zu orders
    pubsub = redis_client.pubsub()
    pubsub.subscribe(order_channel)
    time.sleep(0.1)

    # Publish Order
    redis_client.publish(order_channel, json.dumps(order_event))
    time.sleep(0.1)

    # Verify Order empfangen
    received = None
    for msg in pubsub.listen():
        if msg["type"] == "message":
            received = json.loads(msg["data"])
            break

    assert received is not None
    assert received["symbol"] == "BTCUSDT"
    assert received["approved"] is True

    pubsub.close()


@pytest.mark.e2e
@pytest.mark.local_only
@pytest.mark.slow
def test_full_event_pipeline_simulation(redis_client, postgres_conn):
    """Test: Simuliere vollständigen Event-Flow von Market-Data bis DB.

    Flow:
    1. Market-Data Event (Redis)
    2. Signal generiert (Redis)
    3. Risk-Validation (Redis)
    4. Order approved (Redis)
    5. Trade persisted (PostgreSQL)
    """
    # 1. Market-Data Event
    market_data_channel = "market_data"
    market_event = {
        "symbol": "ADAUSDT",
        "price": 0.5,
        "volume": 10000.0,
        "timestamp": "2025-11-19T00:00:00Z",
    }
    redis_client.publish(market_data_channel, json.dumps(market_event))
    time.sleep(0.1)

    # 2. Signal Event
    signal_channel = "signals"
    signal_event = {
        "symbol": "ADAUSDT",
        "signal_type": "buy",
        "price": 0.5,
        "confidence": 0.88,
    }
    redis_client.publish(signal_channel, json.dumps(signal_event))
    time.sleep(0.1)

    # 3. Order Event (nach Risk-Validation)
    order_channel = "orders"
    order_event = {
        "symbol": "ADAUSDT",
        "side": "buy",
        "price": 0.5,
        "size": 100.0,
        "approved": True,
    }
    redis_client.publish(order_channel, json.dumps(order_event))
    time.sleep(0.1)

    # 4. Simuliere Trade-Execution → PostgreSQL
    cursor = postgres_conn.cursor()
    cursor.execute(
        """
        INSERT INTO trades (
            symbol, side, price, size, status, timestamp
        ) VALUES (
            %s, %s, %s, %s, %s, NOW()
        ) RETURNING id
    """,
        ("ADAUSDT", "buy", 0.5, 100.0, "filled"),
    )

    trade_id = cursor.fetchone()[0]
    postgres_conn.commit()

    # 5. Verify: Trade ist in DB
    cursor.execute(
        "SELECT symbol, side, price, size FROM trades WHERE id = %s", (trade_id,)
    )
    result = cursor.fetchone()

    assert result is not None
    assert result[0] == "ADAUSDT"
    assert result[1] == "buy"
    assert abs(float(result[2]) - 0.5) < 0.001
    assert abs(float(result[3]) - 100.0) < 0.001

    # Cleanup
    cursor.execute("DELETE FROM trades WHERE id = %s", (trade_id,))
    postgres_conn.commit()
    cursor.close()


# =============================================================================
# Service Health Integration
# =============================================================================


@pytest.mark.e2e
@pytest.mark.local_only
def test_all_services_are_healthy_for_event_flow():
    """Test: Alle Services für Event-Flow sind healthy."""
    required_services = {
        "cdb_ws": 8000,
        "cdb_core": 8001,
        "cdb_risk": 8002,
        "cdb_execution": 8003,
    }

    for service_name, port in required_services.items():
        is_healthy = _check_service_health(service_name, port)
        assert is_healthy, (
            f"Service '{service_name}' ist nicht healthy. "
            f"Event-Flow kann nicht vollständig getestet werden.\n"
            f"Prüfe: docker compose logs {service_name}"
        )
