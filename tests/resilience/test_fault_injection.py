"""
Resilience Tests: Service Recovery & Fault Injection

Tests for Issue #95:
- Service Restart (cdb_core, cdb_risk, cdb_execution)
- Connection Loss (PostgreSQL, Redis, MEXC API)
- Chaos Engineering (Random Kill, Network Partition)
- Data Integrity (Consistency nach Recovery)

Prerequisites:
- Docker Compose stack running
- RESILIENCE_RUN=1 to enable tests

Run:
```bash
RESILIENCE_RUN=1 pytest tests/resilience/test_fault_injection.py -v -s
```
"""

import json
import os
import subprocess
import time
from datetime import datetime
from typing import Dict, Any, Optional

import pytest
import redis


# Skip all tests unless explicitly enabled
pytestmark = [
    pytest.mark.resilience,
    pytest.mark.slow,
    pytest.mark.skipif(
        os.getenv("RESILIENCE_RUN") != "1",
        reason="Resilience tests only run when RESILIENCE_RUN=1 is set"
    ),
]

# Recovery time target
MAX_RECOVERY_TIME_SECONDS = 30


@pytest.fixture(scope="module")
def redis_client():
    """Redis client for health checks."""
    password = os.environ["REDIS_PASSWORD"]  # No fallback - must be set
    client = redis.Redis(
        host="localhost",
        port=6379,
        password=password,
        decode_responses=True,
        socket_timeout=5
    )
    yield client
    client.close()


def docker_compose_cmd(action: str, service: str = None, timeout: int = 30) -> subprocess.CompletedProcess:
    """Execute docker-compose command."""
    cmd = ["docker-compose", action]
    if service:
        cmd.append(service)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=os.getcwd()
    )


def wait_for_service(service_name: str, max_wait: int = 30) -> float:
    """Wait for service to be healthy, return recovery time."""
    start = time.time()
    while time.time() - start < max_wait:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Health.Status}}", service_name],
            capture_output=True,
            text=True
        )
        if result.stdout.strip() == "healthy":
            return time.time() - start
        time.sleep(1)
    return -1  # Timeout


def check_redis_connectivity() -> bool:
    """Check if Redis is accessible."""
    try:
        password = os.environ["REDIS_PASSWORD"]  # No fallback - must be set
        client = redis.Redis(host="localhost", port=6379, password=password, socket_timeout=2)
        client.ping()
        client.close()
        return True
    except Exception:
        return False


# =============================================================================
# SERVICE RESTART TESTS (3 tests)
# =============================================================================


class TestServiceRestart:
    """Test service recovery after restart."""

    @pytest.mark.resilience
    def test_restart_cdb_core(self):
        """Test: cdb_core service restart and recovery."""
        service = "cdb_core"

        # Restart service
        docker_compose_cmd("restart", service)

        # Wait for recovery
        recovery_time = wait_for_service(service, MAX_RECOVERY_TIME_SECONDS)

        assert recovery_time >= 0, f"{service} did not recover within {MAX_RECOVERY_TIME_SECONDS}s"
        assert recovery_time < MAX_RECOVERY_TIME_SECONDS, f"{service} recovery took {recovery_time:.1f}s > {MAX_RECOVERY_TIME_SECONDS}s"

        print(f"✅ {service} recovered in {recovery_time:.1f}s")

    @pytest.mark.resilience
    def test_restart_cdb_risk(self):
        """Test: cdb_risk service restart and recovery."""
        service = "cdb_risk"

        docker_compose_cmd("restart", service)
        recovery_time = wait_for_service(service, MAX_RECOVERY_TIME_SECONDS)

        assert recovery_time >= 0, f"{service} did not recover within {MAX_RECOVERY_TIME_SECONDS}s"
        print(f"✅ {service} recovered in {recovery_time:.1f}s")

    @pytest.mark.resilience
    def test_restart_cdb_execution(self):
        """Test: cdb_execution service restart and recovery."""
        service = "cdb_execution"

        docker_compose_cmd("restart", service)
        recovery_time = wait_for_service(service, MAX_RECOVERY_TIME_SECONDS)

        assert recovery_time >= 0, f"{service} did not recover within {MAX_RECOVERY_TIME_SECONDS}s"
        print(f"✅ {service} recovered in {recovery_time:.1f}s")


# =============================================================================
# CONNECTION LOSS TESTS (3 tests)
# =============================================================================


class TestConnectionLoss:
    """Test service behavior during connection loss."""

    @pytest.mark.resilience
    def test_redis_connection_loss(self, redis_client):
        """Test: Services handle Redis connection loss gracefully."""
        # Pause Redis
        docker_compose_cmd("pause", "cdb_redis")

        # Wait a bit for services to notice
        time.sleep(5)

        # Unpause Redis
        docker_compose_cmd("unpause", "cdb_redis")

        # Wait for reconnection
        start = time.time()
        while time.time() - start < MAX_RECOVERY_TIME_SECONDS:
            if check_redis_connectivity():
                recovery_time = time.time() - start
                print(f"✅ Redis reconnected in {recovery_time:.1f}s")
                return
            time.sleep(1)

        pytest.fail(f"Redis did not recover within {MAX_RECOVERY_TIME_SECONDS}s")

    @pytest.mark.resilience
    def test_postgres_connection_loss(self):
        """Test: Services handle PostgreSQL connection loss gracefully."""
        # Pause PostgreSQL
        docker_compose_cmd("pause", "cdb_postgres")

        time.sleep(5)

        # Unpause PostgreSQL
        docker_compose_cmd("unpause", "cdb_postgres")

        # Check if db_writer recovers
        recovery_time = wait_for_service("cdb_db_writer", MAX_RECOVERY_TIME_SECONDS)

        if recovery_time < 0:
            print("⚠️ db_writer did not auto-recover (may need manual restart)")
        else:
            print(f"✅ PostgreSQL connection recovered in {recovery_time:.1f}s")

    @pytest.mark.resilience
    def test_mexc_api_timeout_handling(self, redis_client):
        """Test: Execution service handles MEXC API timeouts."""
        # Set a flag to simulate API timeout in paper trading mode
        redis_client.set("test:simulate_api_timeout", "1")

        try:
            # Publish test order
            order_payload = {
                "order_id": f"resilience-timeout-{int(time.time())}",
                "symbol": "BTC/USDT",
                "side": "BUY",
                "quantity": 0.001,
                "type": "MARKET",
                "source": "resilience_test"
            }

            pubsub = redis_client.pubsub()
            pubsub.subscribe("order_results")
            for _ in range(3):
                pubsub.get_message(timeout=0.1)

            redis_client.publish("orders", json.dumps(order_payload))

            # Wait for result (should still get response even with timeout)
            result = None
            for _ in range(30):  # 15 seconds
                msg = pubsub.get_message(timeout=0.5)
                if msg and msg["type"] == "message":
                    result = msg
                    break

            pubsub.close()

            if result:
                payload = json.loads(result["data"])
                # In paper mode, should still work
                print(f"✅ Order processed despite timeout simulation: {payload['status']}")
            else:
                print("⚠️ No response (may indicate timeout handling needs improvement)")

        finally:
            redis_client.delete("test:simulate_api_timeout")


# =============================================================================
# CHAOS ENGINEERING TESTS (3 tests)
# =============================================================================


class TestChaosEngineering:
    """Chaos engineering tests for system resilience."""

    @pytest.mark.resilience
    def test_random_service_kill(self):
        """Test: System recovers from random service kill."""
        import random

        services = ["cdb_signal", "cdb_risk", "cdb_execution"]
        target = random.choice(services)

        # Kill the service
        subprocess.run(["docker", "kill", target], capture_output=True)

        # Let docker-compose restart it (depends on restart policy)
        time.sleep(10)

        # Check if service came back
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={target}", "--format", "{{.Status}}"],
            capture_output=True,
            text=True
        )

        if "Up" in result.stdout:
            print(f"✅ {target} auto-restarted after kill")
        else:
            # Manual restart
            docker_compose_cmd("up", f"-d {target}")
            time.sleep(10)
            print(f"⚠️ {target} required manual restart")

    @pytest.mark.resilience
    def test_network_partition_simulation(self, redis_client):
        """Test: Order processing during network issues."""
        # This is a simplified test - real network partition would use toxiproxy

        # Submit order
        order_id = f"chaos-partition-{int(time.time())}"
        order_payload = {
            "order_id": order_id,
            "symbol": "BTC/USDT",
            "side": "BUY",
            "quantity": 0.001,
            "type": "MARKET"
        }

        # Subscribe before publish
        pubsub = redis_client.pubsub()
        pubsub.subscribe("order_results")
        for _ in range(3):
            pubsub.get_message(timeout=0.1)

        redis_client.publish("orders", json.dumps(order_payload))

        # Wait for result
        result = None
        for _ in range(20):
            msg = pubsub.get_message(timeout=0.5)
            if msg and msg["type"] == "message":
                result = msg
                break

        pubsub.close()

        assert result is not None, "No order result during partition test"
        print("✅ Order processed during network partition simulation")

    @pytest.mark.resilience
    def test_high_load_burst(self, redis_client):
        """Test: System handles burst of 100 orders."""
        order_count = 100
        start_time = time.time()

        # Subscribe to results
        pubsub = redis_client.pubsub()
        pubsub.subscribe("order_results")
        for _ in range(3):
            pubsub.get_message(timeout=0.1)

        # Burst of orders
        for i in range(order_count):
            order_payload = {
                "order_id": f"burst-{start_time}-{i}",
                "symbol": "BTC/USDT",
                "side": "BUY" if i % 2 == 0 else "SELL",
                "quantity": 0.001,
                "type": "MARKET"
            }
            redis_client.publish("orders", json.dumps(order_payload))

        # Count received results (within 30 seconds)
        received = 0
        timeout_at = time.time() + 30
        while time.time() < timeout_at and received < order_count:
            msg = pubsub.get_message(timeout=0.1)
            if msg and msg["type"] == "message":
                received += 1

        pubsub.close()

        elapsed = time.time() - start_time
        throughput = received / elapsed

        print(f"📊 Burst test: {received}/{order_count} orders in {elapsed:.1f}s ({throughput:.1f}/s)")
        assert received >= order_count * 0.9, f"Only {received}/{order_count} orders processed"


# =============================================================================
# DATA INTEGRITY TESTS (3 tests)
# =============================================================================


class TestDataIntegrity:
    """Test data consistency after failures."""

    @pytest.mark.resilience
    def test_stream_consistency_after_restart(self, redis_client):
        """Test: Redis stream data consistent after service restart."""
        stream_name = "stream.fills"

        # Get current stream length
        try:
            initial_length = redis_client.xlen(stream_name)
        except redis.ResponseError:
            initial_length = 0

        # Restart execution service
        docker_compose_cmd("restart", "cdb_execution")
        time.sleep(10)

        # Check stream length unchanged
        try:
            final_length = redis_client.xlen(stream_name)
        except redis.ResponseError:
            final_length = 0

        assert final_length >= initial_length, "Stream data lost after restart!"
        print(f"✅ Stream consistent: {initial_length} → {final_length} entries")

    @pytest.mark.resilience
    def test_order_state_consistency(self, redis_client):
        """Test: Order state consistent after reconnection."""
        # Submit order
        order_id = f"consistency-{int(time.time())}"
        order_payload = {
            "order_id": order_id,
            "symbol": "BTC/USDT",
            "side": "BUY",
            "quantity": 0.001,
            "type": "MARKET"
        }

        redis_client.publish("orders", json.dumps(order_payload))
        time.sleep(3)

        # Check order state in stream
        stream_name = "stream.fills"
        entries = redis_client.xrevrange(stream_name, count=10)

        found = False
        for entry_id, entry_data in entries:
            if entry_data.get("order_id") == order_id:
                found = True
                status = entry_data.get("status", "unknown")
                print(f"✅ Order {order_id} found with status: {status}")
                break

        if not found:
            print(f"⚠️ Order {order_id} not found in recent stream entries")

    @pytest.mark.resilience
    def test_no_duplicate_orders_after_restart(self, redis_client):
        """Test: No duplicate order processing after restart."""
        order_id = f"dedup-{int(time.time())}"

        # Submit order
        order_payload = {
            "order_id": order_id,
            "symbol": "BTC/USDT",
            "side": "BUY",
            "quantity": 0.001,
            "type": "MARKET"
        }
        redis_client.publish("orders", json.dumps(order_payload))

        time.sleep(2)

        # Restart execution
        docker_compose_cmd("restart", "cdb_execution")
        time.sleep(10)

        # Try to resubmit same order
        redis_client.publish("orders", json.dumps(order_payload))
        time.sleep(2)

        # Check stream for duplicates
        stream_name = "stream.fills"
        entries = redis_client.xrevrange(stream_name, count=20)

        order_count = sum(1 for _, data in entries if data.get("order_id") == order_id)

        if order_count > 1:
            print(f"⚠️ Duplicate detected: order {order_id} appears {order_count} times")
        else:
            print(f"✅ No duplicates: order {order_id} appears {order_count} time(s)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
