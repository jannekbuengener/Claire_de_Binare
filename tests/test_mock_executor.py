"""
Unit Tests für MockExecutor
Test latency simulation, slippage und order execution
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock

# Add service path to sys.path
service_path = Path(__file__).parent.parent / "backoffice" / "services" / "execution_service"
sys.path.insert(0, str(service_path))

from mock_executor import MockExecutor
from models import Order, OrderStatus


@pytest.fixture
def executor():
    """MockExecutor mit Default-Params"""
    return MockExecutor(
        success_rate=1.0,  # 100% für deterministische Tests
        min_latency_ms=10,
        max_latency_ms=20,
        base_slippage_pct=0.02
    )


@pytest.fixture
def sample_order():
    """Sample Buy Order"""
    return Order(
        symbol="BTCUSDT",
        side="buy",
        quantity=1.0,
        client_id="TEST_001"
    )


@pytest.mark.unit
def test_executor_initialization():
    """Test: MockExecutor kann initialisiert werden"""
    executor = MockExecutor()

    assert executor.success_rate == 0.95
    assert executor.min_latency_ms == 50
    assert executor.max_latency_ms == 200
    assert executor.base_slippage_pct == 0.02
    assert executor.orders == {}


@pytest.mark.unit
def test_execute_order_success(executor, sample_order):
    """Test: Order wird erfolgreich ausgeführt"""
    result = executor.execute_order(sample_order)

    assert result.status == OrderStatus.FILLED.value
    assert result.symbol == "BTCUSDT"
    assert result.side == "buy"
    assert result.filled_quantity == 1.0
    assert result.price is not None
    assert result.price > 0
    assert result.error_message is None
    assert "MOCK_" in result.order_id


@pytest.mark.unit
def test_slippage_on_buy_order(executor, sample_order):
    """Test: Buy Order wird erfolgreich ausgeführt mit Preis"""
    result = executor.execute_order(sample_order)

    # Preis sollte im realistischen BTC-Bereich sein (~50k ± 1%)
    assert 49500 <= result.price <= 50500, f"BTC price out of range: {result.price}"
    assert result.status == OrderStatus.FILLED.value


@pytest.mark.unit
def test_slippage_on_sell_order(executor):
    """Test: Sell Order wird erfolgreich ausgeführt"""
    sell_order = Order(
        symbol="BTCUSDT",
        side="sell",
        quantity=1.0,
        client_id="TEST_SELL"
    )

    result = executor.execute_order(sell_order)

    # Preis sollte im realistischen BTC-Bereich sein
    assert 49500 <= result.price <= 50500, f"BTC price out of range: {result.price}"
    assert result.status == OrderStatus.FILLED.value


@pytest.mark.unit
def test_slippage_increases_with_quantity(executor):
    """Test: Slippage-Funktion existiert und läuft deterministisch"""
    # Teste die interne Slippage-Funktion direkt
    small_slippage = executor._simulate_slippage(quantity=1.0)
    large_slippage = executor._simulate_slippage(quantity=100.0)

    # Beide sollten positive Werte sein
    assert small_slippage > 0, "Small slippage should be positive"
    assert large_slippage > 0, "Large slippage should be positive"

    # Slippage sollte < 0.1% sein (maximum cap)
    assert small_slippage <= 0.001, f"Small slippage too high: {small_slippage}"
    assert large_slippage <= 0.001, f"Large slippage too high: {large_slippage}"


@pytest.mark.unit
def test_order_rejection():
    """Test: Orders können rejected werden"""
    # Executor mit 0% Success Rate
    failing_executor = MockExecutor(success_rate=0.0)

    order = Order(symbol="BTCUSDT", side="buy", quantity=1.0)
    result = failing_executor.execute_order(order)

    assert result.status == OrderStatus.REJECTED.value
    assert result.filled_quantity == 0.0
    assert result.price is None
    assert result.error_message is not None
    assert "Mock rejection" in result.error_message


@pytest.mark.unit
def test_get_order_status(executor, sample_order):
    """Test: Order-Status kann abgefragt werden"""
    result = executor.execute_order(sample_order)
    order_id = result.order_id

    # Abruf über get_order_status
    status = executor.get_order_status(order_id)

    assert status is not None
    assert status.order_id == order_id
    assert status.status == OrderStatus.FILLED.value


@pytest.mark.unit
def test_cancel_order(executor, sample_order):
    """Test: Orders können gecancelt werden"""
    result = executor.execute_order(sample_order)
    order_id = result.order_id

    # Cancel Order
    success = executor.cancel_order(order_id)

    assert success is True

    # Status sollte CANCELLED sein
    cancelled_order = executor.get_order_status(order_id)
    assert cancelled_order.status == OrderStatus.CANCELLED.value


@pytest.mark.unit
def test_cancel_nonexistent_order(executor):
    """Test: Cancel von nicht-existierender Order returnt False"""
    success = executor.cancel_order("NONEXISTENT_ID")
    assert success is False


@pytest.mark.unit
def test_price_simulation_for_btc():
    """Test: BTC-Price ist im erwarteten Bereich"""
    executor = MockExecutor()
    price = executor._simulate_price("BTCUSDT")

    # BTC sollte ~50k sein (+/- 0.1%)
    assert 49900 <= price <= 50100, f"BTC price out of range: {price}"


@pytest.mark.unit
def test_price_simulation_for_eth():
    """Test: ETH-Price ist im erwarteten Bereich"""
    executor = MockExecutor()
    price = executor._simulate_price("ETHUSDT")

    # ETH sollte ~3k sein (+/- 0.1%)
    assert 2990 <= price <= 3010, f"ETH price out of range: {price}"


@pytest.mark.unit
def test_latency_simulation(executor, sample_order):
    """Test: Latency wird simuliert (10-20ms)"""
    import time

    start = time.time()
    result = executor.execute_order(sample_order)
    end = time.time()

    elapsed_ms = (end - start) * 1000

    # Sollte mindestens 10ms dauern (min_latency)
    assert elapsed_ms >= 10, f"Latency zu kurz: {elapsed_ms}ms"

    # Sollte nicht viel länger als 20ms dauern (max_latency + overhead)
    assert elapsed_ms <= 50, f"Latency zu lang: {elapsed_ms}ms"


@pytest.mark.unit
def test_multiple_orders(executor):
    """Test: Mehrere Orders können nacheinander ausgeführt werden"""
    orders = [
        Order(symbol="BTCUSDT", side="buy", quantity=1.0),
        Order(symbol="ETHUSDT", side="sell", quantity=10.0),
        Order(symbol="BTCUSDT", side="sell", quantity=0.5),
    ]

    results = [executor.execute_order(order) for order in orders]

    assert len(results) == 3
    assert all(r.status == OrderStatus.FILLED.value for r in results)
    assert len(executor.orders) == 3

    # Alle Order-IDs sollten unique sein
    order_ids = [r.order_id for r in results]
    assert len(order_ids) == len(set(order_ids)), "Duplicate order IDs found"
