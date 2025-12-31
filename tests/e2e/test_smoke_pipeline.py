"""
E2E Smoke Test - Market Data → Signal Generation
Issue #354: Deterministic E2E Test Path

Tests the core pipeline:
1. Fixture market_data → Redis Pub/Sub
2. cdb_signal consumes → generates signals
3. Validate: signals_generated_total > 0
"""

import json
import os
import time
from pathlib import Path

import pytest
import redis
import requests

# Mark all tests in this module as E2E for selective runs.
pytestmark = pytest.mark.e2e


# Fixtures path
FIXTURES_DIR = Path(__file__).parent / "fixtures"
MARKET_DATA_FIXTURE = FIXTURES_DIR / "market_data.json"


@pytest.fixture(scope="module")
def redis_client():
    """Redis client for publishing market_data"""
    password = os.getenv("REDIS_PASSWORD")
    if not password:
        pytest.fail("REDIS_PASSWORD environment variable not set. Load secrets first.")

    env_host = os.getenv("REDIS_HOST")
    targets = [env_host] if env_host else ["localhost", "cdb_redis"]
    last_error = None

    for host in targets:
        try:
            client = redis.Redis(
                host=host,
                port=6379,
                password=password,
                db=0,
                decode_responses=True,
                socket_timeout=5,
            )
            client.ping()
            return client
        except (redis.ConnectionError, redis.TimeoutError, redis.AuthenticationError) as e:
            last_error = e
            continue

    pytest.fail(f"Could not connect to Redis (tried {', '.join(targets)}): {last_error}")


@pytest.fixture(scope="module")
def prometheus_url():
    """Prometheus base URL"""
    return os.getenv("PROMETHEUS_URL", "http://localhost:19090")


def load_market_data_fixture():
    """Load deterministisches market_data fixture"""
    with open(MARKET_DATA_FIXTURE, "r") as f:
        return json.load(f)


def publish_market_data(redis_client, messages, delay_ms=100):
    """
    Publish market_data Messages to Redis Pub/Sub

    Args:
        redis_client: Redis client
        messages: List of market_data dicts
        delay_ms: Delay between publishes (ms) for realistic spacing
    """
    for msg in messages:
        payload = json.dumps(msg)
        redis_client.publish("market_data", payload)
        time.sleep(delay_ms / 1000.0)


def get_prometheus_metric(prometheus_url, metric_name):
    """
    Query Prometheus for a metric value

    Args:
        prometheus_url: Prometheus base URL
        metric_name: Metric name (e.g., "signals_generated_total")

    Returns:
        Metric value (float) or None if metric not found
    """
    try:
        response = requests.get(
            f"{prometheus_url}/api/v1/query",
            params={"query": metric_name},
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()

        if data["status"] == "success" and data["data"]["result"]:
            value = float(data["data"]["result"][0]["value"][1])
            return value
        return None
    except requests.RequestException as e:
        pytest.fail(f"Prometheus not available: {e}")
        return None


def test_smoke_market_data_to_signal(redis_client, prometheus_url):
    """
    E2E Smoke Test: market_data → signal generation

    Pipeline:
    1. Load fixture: market_data.json (10 deterministic messages)
    2. Publish to Redis market_data topic
    3. cdb_signal consumes + generates signals
    4. Validate: signals_generated_total metric increased

    Success Criteria:
    - At least 1 signal generated
    - Deterministic results across runs

    Evidence:
    - Prometheus signals_generated_total > 0
    """
    # Step 1: Load fixture
    market_data_messages = load_market_data_fixture()
    assert len(market_data_messages) == 10, "Fixture muss 10 Messages haben"

    # Step 2: Get baseline metric (before publishing)
    baseline = get_prometheus_metric(prometheus_url, "signals_generated_total")
    if baseline is None:
        baseline = 0.0  # Assume 0 if metric doesn't exist yet

    # Step 3: Publish market_data to Redis
    print(f"📤 Publishing {len(market_data_messages)} market_data messages...")
    publish_market_data(redis_client, market_data_messages, delay_ms=100)

    # Step 4: Wait for Signal Engine to process
    # (Allow 5 seconds for cdb_signal to consume + generate signals)
    print("⏳ Waiting 5s for signal generation...")
    time.sleep(5)

    # Step 5: Query Prometheus for signals_generated_total
    final = get_prometheus_metric(prometheus_url, "signals_generated_total")
    assert final is not None, "signals_generated_total metric not found in Prometheus"

    # Step 6: Validate signals were generated
    signals_generated = final - baseline
    print(f"✅ Signals generated: {signals_generated} (baseline={baseline}, final={final})")

    assert signals_generated > 0, (
        f"Expected at least 1 signal, got {signals_generated}. "
        "Check cdb_signal logs: docker logs cdb_signal"
    )

    # Step 7: Determinism check (optional: run 3x local to verify)
    # For CI: This test should pass consistently (<5% flake rate)


def test_fixture_contract_compliance():
    """Validate market_data fixture is Contract v1.0 compliant"""
    messages = load_market_data_fixture()

    required_fields = ["schema_version", "source", "symbol", "ts_ms", "price", "trade_qty", "side"]

    for i, msg in enumerate(messages):
        for field in required_fields:
            assert field in msg, f"Message {i}: Missing required field '{field}'"

        # Schema version
        assert msg["schema_version"] == "v1.0", f"Message {i}: Invalid schema_version"

        # Type checks
        assert isinstance(msg["ts_ms"], int), f"Message {i}: ts_ms must be int"
        assert isinstance(msg["price"], str), f"Message {i}: price must be str (precision)"
        assert isinstance(msg["trade_qty"], str), f"Message {i}: trade_qty must be str (precision)"


def test_redis_health(redis_client):
    """Health check: Redis connection"""
    try:
        assert redis_client.ping()
    except redis.ConnectionError as e:
        pytest.fail(f"Redis not healthy: {e}")


def test_prometheus_health(prometheus_url):
    """Health check: Prometheus API"""
    try:
        response = requests.get(f"{prometheus_url}/api/v1/status/config", timeout=5)
        response.raise_for_status()
        assert response.json()["status"] == "success"
    except requests.RequestException as e:
        pytest.fail(f"Prometheus not healthy: {e}")
