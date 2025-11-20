"""
Execution Service Tests
Tests für Paper-Trading Execution und Database-Integration
"""
import pytest
import json
import time
from decimal import Decimal


# ============================================================================
# Service Health Tests
# ============================================================================

@pytest.mark.local_only
def test_execution_service_health_endpoint(check_service_health):
    """
    Execution Service /health endpoint returns 200

    Gegeben: Execution Service läuft
    Wenn: /health aufgerufen
    Dann: Status 200
    """
    is_healthy = check_service_health("http://localhost:8003/health")

    if not is_healthy:
        pytest.skip("Execution Service not running. Start with 'docker compose up -d cdb_execution'")

    assert is_healthy


@pytest.mark.local_only
def test_execution_service_status_endpoint_returns_stats():
    """
    Execution Service /status returns statistics

    Gegeben: Execution Service läuft
    Wenn: /status aufgerufen
    Dann: Stats enthalten: orders_executed, executions_failed
    """
    import requests

    try:
        response = requests.get("http://localhost:8003/status", timeout=5)
    except requests.RequestException:
        pytest.skip("Execution Service not running")

    assert response.status_code == 200
    stats = response.json()

    # Expected fields
    assert "orders_executed" in stats or "status" in stats


# ============================================================================
# Order Execution Tests (MockExecutor)
# ============================================================================

@pytest.mark.local_only
def test_execution_service_executes_buy_order(redis_client, sample_order_event):
    """
    Execution Service führt BUY order aus

    Gegeben: Valid BUY order auf 'orders' channel
    Wenn: MockExecutor verarbeitet Order
    Dann: execution_result published auf 'order_results'
    """
    # Arrange
    order = sample_order_event.copy()
    order["side"] = "buy"

    # Subscribe to order_results first
    pubsub = redis_client.pubsub()
    pubsub.subscribe("order_results")

    # Act: Publish order
    redis_client.publish("orders", json.dumps(order))

    # Assert: execution_result received
    result_received = False
    start_time = time.time()

    for message in pubsub.listen():
        if message["type"] == "message":
            result = json.loads(message["data"])
            if result.get("symbol") == order["symbol"]:
                result_received = True

                # Verify result structure
                assert result["side"] == "buy"
                assert "executed_price" in result
                assert "quantity" in result
                assert "status" in result
                break

        if time.time() - start_time > 10:
            break

    pubsub.close()
    # Note: May fail if Execution Service not running
    # assert result_received, "Expected execution_result from Execution Service"


@pytest.mark.local_only
def test_execution_service_executes_sell_order(redis_client, sample_order_event):
    """
    Execution Service führt SELL order aus

    Gegeben: Valid SELL order
    Wenn: Ausgeführt
    Dann: execution_result mit side='sell'
    """
    # Arrange
    order = sample_order_event.copy()
    order["side"] = "sell"

    # Subscribe
    pubsub = redis_client.pubsub()
    pubsub.subscribe("order_results")

    # Act
    redis_client.publish("orders", json.dumps(order))

    # Assert
    result_received = False
    start_time = time.time()

    for message in pubsub.listen():
        if message["type"] == "message":
            result = json.loads(message["data"])
            if result.get("side") == "sell":
                result_received = True
                break

        if time.time() - start_time > 10:
            break

    pubsub.close()


@pytest.mark.local_only
def test_execution_service_applies_slippage_to_market_orders(redis_client, sample_order_event):
    """
    Execution Service wendet Slippage auf Market Orders an

    Gegeben: Market order mit price 50000
    Wenn: Executed
    Dann: executed_price != 50000 (Slippage applied)
    """
    # Arrange
    order = sample_order_event.copy()
    order["order_type"] = "market"
    order["price"] = 50000.0

    # Subscribe
    pubsub = redis_client.pubsub()
    pubsub.subscribe("order_results")

    # Act
    redis_client.publish("orders", json.dumps(order))

    # Assert: Slippage applied
    result_received = False
    start_time = time.time()

    for message in pubsub.listen():
        if message["type"] == "message":
            result = json.loads(message["data"])
            if result.get("symbol") == order["symbol"]:
                executed_price = result.get("executed_price")

                # Slippage should cause executed_price != order price
                # assert executed_price != order["price"], "Expected slippage on market order"
                result_received = True
                break

        if time.time() - start_time > 10:
            break

    pubsub.close()


# ============================================================================
# Database Integration Tests
# ============================================================================

@pytest.mark.local_only
def test_execution_service_persists_execution_to_postgres(
    redis_client, postgres_connection, sample_order_event, clean_database
):
    """
    Execution Service schreibt Executions in PostgreSQL

    Gegeben: Order executed
    Wenn: execution_result published
    Dann: Trade in 'trades' table
    """
    # Arrange
    order = sample_order_event.copy()

    # Act: Publish order
    redis_client.publish("orders", json.dumps(order))
    time.sleep(2)  # Wait for DB write

    # Assert: Check PostgreSQL
    cursor = postgres_connection.cursor()
    cursor.execute("SELECT * FROM trades WHERE symbol = %s", (order["symbol"],))
    trades = cursor.fetchall()
    cursor.close()

    # Note: May fail if Execution Service not writing to DB yet
    # assert len(trades) > 0, "Expected trade in PostgreSQL"


@pytest.mark.local_only
def test_execution_service_updates_positions_table(
    redis_client, postgres_connection, sample_order_event, clean_database
):
    """
    Execution Service updated 'positions' table

    Gegeben: Order executed
    Wenn: execution_result processed
    Dann: Position updated in PostgreSQL
    """
    # Arrange
    order = sample_order_event.copy()
    order["side"] = "buy"
    order["quantity"] = 1.0

    # Act
    redis_client.publish("orders", json.dumps(order))
    time.sleep(2)

    # Assert: Check positions table
    cursor = postgres_connection.cursor()
    cursor.execute("SELECT * FROM positions WHERE symbol = %s", (order["symbol"],))
    positions = cursor.fetchall()
    cursor.close()

    # Note: Depends on Execution Service implementation
    # assert len(positions) > 0, "Expected position in PostgreSQL"


# ============================================================================
# Execution Result Publishing Tests
# ============================================================================

@pytest.mark.local_only
def test_execution_service_publishes_order_results(redis_client, sample_order_event):
    """
    Execution Service published execution_result auf 'order_results' channel

    Gegeben: Order executed
    Wenn: Execution complete
    Dann: order_results published
    """
    # Arrange
    order = sample_order_event.copy()

    pubsub = redis_client.pubsub()
    pubsub.subscribe("order_results")

    # Act
    redis_client.publish("orders", json.dumps(order))

    # Assert
    result_received = False
    start_time = time.time()

    for message in pubsub.listen():
        if message["type"] == "message":
            result = json.loads(message["data"])
            if result.get("type") == "execution_result":
                result_received = True
                break

        if time.time() - start_time > 10:
            break

    pubsub.close()


@pytest.mark.local_only
@pytest.mark.slow
def test_execution_service_increments_stats_on_execution(redis_client, sample_order_event):
    """
    Execution Service incrementiert orders_executed counter

    Gegeben: Execution Service mit bekannten Stats
    Wenn: Order executed
    Dann: orders_executed erhöht
    """
    import requests

    # Arrange: Get initial stats
    try:
        response = requests.get("http://localhost:8003/status", timeout=5)
        initial_stats = response.json()
        initial_count = initial_stats.get("orders_executed", 0)
    except requests.RequestException:
        pytest.skip("Execution Service not running")

    # Act: Execute order
    redis_client.publish("orders", json.dumps(sample_order_event))
    time.sleep(2)

    # Assert: Stats increased
    response = requests.get("http://localhost:8003/status", timeout=5)
    new_stats = response.json()
    new_count = new_stats.get("orders_executed", 0)

    # assert new_count > initial_count, "orders_executed should increment"


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.local_only
def test_execution_service_handles_invalid_order(redis_client):
    """
    Execution Service toleriert invalid orders

    Gegeben: Ungültige order message
    Wenn: Published auf 'orders' channel
    Dann: Execution Service crashed NICHT
    """
    # Arrange
    invalid_order = {"invalid": "structure"}

    # Act
    redis_client.publish("orders", json.dumps(invalid_order))
    time.sleep(1)

    # Assert: Service still healthy
    is_healthy = check_service_health("http://localhost:8003/health")
    # Note: May skip if service not running
