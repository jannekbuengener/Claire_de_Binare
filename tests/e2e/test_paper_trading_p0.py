"""
E2E Regression Tests - Paper Trading P0 Flow
============================================

Validates: Order → Execution → order_results publishing → Subscriber reception

**Purpose:** Regression shield for #225 (order_results publishing verified manually)

**Scope:** Redis Pub/Sub flow only (no DB persistence required)

**Tests:**
1. test_order_to_execution_flow - End-to-end message delivery
2. test_order_results_schema - Payload validation (timestamp format, required fields)
3. test_stream_persistence - Stream.fills event storage

**Prerequisites:**
- Stack must be running (docker-compose up)
- Redis accessible at cdb_redis:6379 (or localhost:6379 with port mapping)
- Execution service subscribed to 'orders' channel

**Run:**
```bash
E2E_RUN=1 pytest tests/e2e/test_paper_trading_p0.py -v
```
"""

import json
import os
import time
from datetime import datetime

import pytest
import redis


# Skip all tests if E2E_RUN is not set
pytestmark = pytest.mark.skipif(
    os.getenv("E2E_RUN") != "1",
    reason="E2E tests only run when E2E_RUN=1 is set"
)


@pytest.fixture(scope="module")
def redis_client():
    """
    Redis client connected to cdb_redis container.

    Tries multiple connection strategies:
    1. cdb_redis:6379 (internal Docker network)
    2. localhost:6379 (if port mapped)
    """
    # Get password from environment or use default
    password = os.getenv("REDIS_PASSWORD", "claire_redis_secret_2024")

    # Try internal docker network first
    try:
        client = redis.Redis(
            host="cdb_redis",
            port=6379,
            password=password,
            decode_responses=True,
            socket_timeout=5
        )
        client.ping()
        yield client
        return
    except (redis.ConnectionError, redis.TimeoutError):
        pass

    # Fallback to localhost
    try:
        client = redis.Redis(
            host="localhost",
            port=6379,
            password=password,
            decode_responses=True,
            socket_timeout=5
        )
        client.ping()
        yield client
        return
    except (redis.ConnectionError, redis.TimeoutError):
        pytest.fail("Could not connect to Redis (tried cdb_redis:6379 and localhost:6379)")


@pytest.fixture
def unique_order_id():
    """Generate unique order ID for each test to avoid collisions."""
    return f"e2e-test-{int(time.time() * 1000)}"


def test_order_to_execution_flow(redis_client, unique_order_id):
    """
    Test: Order → Execution → order_results publishing

    **Validates:**
    - Execution service receives order from 'orders' channel
    - Execution service publishes result to 'order_results' channel
    - Subscribers receive the order_result message

    **Flow:**
    1. Subscribe to order_results channel
    2. Publish test order to orders channel
    3. Wait for order_result message (timeout: 10s)
    4. Assert message received with correct type
    """
    # Setup: Subscribe to order_results before publishing
    pubsub = redis_client.pubsub()
    pubsub.subscribe("order_results")

    # Clear any pending messages
    for _ in range(3):
        pubsub.get_message(timeout=0.1)

    # Publish test order
    order_payload = {
        "order_id": unique_order_id,
        "symbol": "BTC/USDT",
        "side": "BUY",
        "quantity": 0.001
    }

    subscribers = redis_client.publish("orders", json.dumps(order_payload))
    assert subscribers >= 1, "No subscribers on 'orders' channel - execution service not running?"

    # Wait for order_result (max 10 seconds)
    result_message = None
    for attempt in range(20):  # 20 attempts * 0.5s = 10s timeout
        message = pubsub.get_message(timeout=0.5)
        if message and message["type"] == "message":
            result_message = message
            break
        time.sleep(0.5)

    # Cleanup
    pubsub.unsubscribe("order_results")
    pubsub.close()

    # Assertions
    assert result_message is not None, "No order_result received after 10 seconds"
    assert result_message["channel"] == "order_results"

    # Parse and validate payload
    payload = json.loads(result_message["data"])
    assert payload["type"] == "order_result", f"Expected type='order_result', got '{payload.get('type')}'"
    assert "order_id" in payload, "Missing order_id in payload"
    assert "status" in payload, "Missing status in payload"


def test_order_results_schema(redis_client, unique_order_id):
    """
    Test: order_results payload schema validation

    **Validates:**
    - Timestamp is Unix integer (not ISO string) - critical for #225
    - Required fields present (type, order_id, status, symbol, side, quantity)
    - Timestamp value is reasonable (within last 60 seconds)

    **Context:** #225 originally identified timestamp schema mismatch
    (ISO string vs Unix int). This test prevents regression.
    """
    # Subscribe to order_results
    pubsub = redis_client.pubsub()
    pubsub.subscribe("order_results")

    # Clear pending messages
    for _ in range(3):
        pubsub.get_message(timeout=0.1)

    # Publish test order
    order_payload = {
        "order_id": unique_order_id,
        "symbol": "ETH/USDT",
        "side": "SELL",
        "quantity": 0.05
    }

    redis_client.publish("orders", json.dumps(order_payload))

    # Wait for result
    result_message = None
    for _ in range(20):
        message = pubsub.get_message(timeout=0.5)
        if message and message["type"] == "message":
            result_message = message
            break
        time.sleep(0.5)

    # Cleanup
    pubsub.unsubscribe("order_results")
    pubsub.close()

    assert result_message is not None, "No order_result received"

    # Parse payload
    payload = json.loads(result_message["data"])

    # Schema validation
    required_fields = ["type", "order_id", "status", "symbol", "side", "quantity", "timestamp"]
    for field in required_fields:
        assert field in payload, f"Missing required field: {field}"

    # Timestamp format validation (CRITICAL for #225)
    timestamp = payload["timestamp"]
    assert isinstance(timestamp, int), f"Timestamp must be Unix int, got {type(timestamp).__name__}: {timestamp}"

    # Timestamp reasonableness check (should be recent)
    now = int(time.time())
    assert abs(now - timestamp) < 60, f"Timestamp {timestamp} is not recent (now={now}, diff={abs(now - timestamp)}s)"

    # Type field validation
    assert payload["type"] == "order_result", f"Expected type='order_result', got '{payload['type']}'"

    # Status validation (should be valid order status)
    valid_statuses = ["FILLED", "PENDING", "CANCELLED", "REJECTED", "PARTIAL", "filled", "pending", "cancelled", "rejected", "partial"]
    assert payload["status"] in valid_statuses, f"Invalid status: {payload['status']}"


def test_stream_persistence(redis_client, unique_order_id):
    """
    Test: order_results persisted to stream.fills

    **Validates:**
    - Events are added to stream.fills (XADD)
    - Stream can be queried with XRANGE
    - Event payload matches published order_result

    **Purpose:** Ensures deterministic replay (#227) has historical data
    """
    # Get current stream length
    stream_name = "stream.fills"

    try:
        initial_entries = redis_client.xlen(stream_name)
    except redis.ResponseError:
        # Stream doesn't exist yet
        initial_entries = 0

    # Publish test order
    order_payload = {
        "order_id": unique_order_id,
        "symbol": "BTC/USDT",
        "side": "BUY",
        "quantity": 0.002
    }

    redis_client.publish("orders", json.dumps(order_payload))

    # Wait for execution (give it time to process and add to stream)
    time.sleep(3)

    # Check stream length increased
    try:
        final_entries = redis_client.xlen(stream_name)
    except redis.ResponseError:
        pytest.fail(f"Stream '{stream_name}' does not exist after order execution")

    assert final_entries > initial_entries, f"Stream length did not increase (was {initial_entries}, now {final_entries})"

    # Read latest entry from stream
    entries = redis_client.xrevrange(stream_name, count=1)
    assert len(entries) > 0, "Could not read latest entry from stream"

    entry_id, entry_data = entries[0]

    # Validate entry contains expected fields
    assert "type" in entry_data, "Stream entry missing 'type' field"
    assert entry_data["type"] == "order_result", f"Expected type='order_result', got '{entry_data['type']}'"

    # Timestamp validation (should be Unix int as string in stream)
    assert "timestamp" in entry_data, "Stream entry missing 'timestamp' field"
    timestamp_str = entry_data["timestamp"]

    try:
        timestamp_int = int(timestamp_str)
        now = int(time.time())
        assert abs(now - timestamp_int) < 60, f"Stream timestamp {timestamp_int} is not recent"
    except ValueError:
        pytest.fail(f"Stream timestamp is not a valid integer: {timestamp_str}")


def test_subscriber_count(redis_client):
    """
    Test: Verify order_results channel has active subscribers

    **Validates:**
    - At least 2 subscribers on order_results channel
    - Expected subscribers: risk, db_writer (and possibly paper_runner)

    **Purpose:** Detect if services are not properly subscribed
    """
    # Check subscribers on order_results channel
    pubsub_channels = redis_client.execute_command("PUBSUB", "NUMSUB", "order_results")

    # Response format: ['order_results', <count>]
    assert len(pubsub_channels) == 2, f"Unexpected PUBSUB NUMSUB response: {pubsub_channels}"

    channel_name, subscriber_count = pubsub_channels
    assert channel_name == "order_results"
    assert subscriber_count >= 2, f"Expected at least 2 subscribers on order_results, got {subscriber_count}"


def test_replay_determinism(redis_client, unique_order_id, tmp_path):
    """
    Test: Deterministic replay produces identical output

    **Validates:**
    - Same stream entries → same replay output (hash match)
    - Replay processes events in deterministic order
    - Output is stable across multiple runs

    **Purpose:** Ensures replay is truly deterministic (#258)

    **Method:**
    1. Inject test order to ensure stream has data
    2. Capture stream state (XLEN)
    3. Run replay twice with same parameters
    4. Compare SHA256 hashes of output files
    5. Assert hashes are identical
    """
    import hashlib
    import subprocess
    import sys

    # Inject test order to ensure stream has data
    order_payload = {
        "order_id": unique_order_id,
        "symbol": "BTC/USDT",
        "side": "BUY",
        "quantity": 0.001
    }
    redis_client.publish("orders", json.dumps(order_payload))

    # Wait for execution and stream persistence
    time.sleep(3)

    # Verify stream has data
    stream_name = "stream.fills"
    try:
        stream_length = redis_client.xlen(stream_name)
    except redis.ResponseError:
        pytest.fail(f"Stream '{stream_name}' does not exist")

    assert stream_length > 0, f"Stream is empty (length={stream_length})"

    # Get stream ID range to replay
    entries = redis_client.xrevrange(stream_name, count=min(10, stream_length))
    assert len(entries) > 0, "Could not read stream entries"

    # Use first and last entry IDs as range
    from_id = entries[-1][0]  # Oldest in our sample
    to_id = entries[0][0]     # Newest in our sample
    count = len(entries)

    # Prepare output files
    replay_run1 = tmp_path / "replay_run1.jsonl"
    replay_run2 = tmp_path / "replay_run2.jsonl"

    # Run replay twice with identical parameters
    replay_cmd = [
        sys.executable, "-m", "tools.replay.replay",
        "--from-id", from_id,
        "--to-id", to_id,
        "--count", str(count),
        "--out", str(replay_run1)
    ]

    # First run
    result1 = subprocess.run(
        replay_cmd,
        capture_output=True,
        text=True,
        env={**os.environ, "CDB_REPLAY": "1"}
    )
    assert result1.returncode == 0, f"Replay run 1 failed: {result1.stderr}"

    # Second run (change output file only)
    replay_cmd[-1] = str(replay_run2)
    result2 = subprocess.run(
        replay_cmd,
        capture_output=True,
        text=True,
        env={**os.environ, "CDB_REPLAY": "1"}
    )
    assert result2.returncode == 0, f"Replay run 2 failed: {result2.stderr}"

    # Verify both output files exist
    assert replay_run1.exists(), "Replay run 1 output file not created"
    assert replay_run2.exists(), "Replay run 2 output file not created"

    # Calculate SHA256 hashes
    def calculate_hash(file_path):
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    hash1 = calculate_hash(replay_run1)
    hash2 = calculate_hash(replay_run2)

    # Determinism assertion: hashes must match
    assert hash1 == hash2, (
        f"Replay output is NOT deterministic!\n"
        f"Run 1 hash: {hash1}\n"
        f"Run 2 hash: {hash2}\n"
        f"Files: {replay_run1}, {replay_run2}\n"
        f"Range: {from_id} → {to_id} (count={count})"
    )

    # Additional validation: verify output is not empty
    with open(replay_run1, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) > 0, "Replay output is empty"
        assert len(lines) == count, f"Expected {count} lines, got {len(lines)}"

        # Verify each line is valid JSON
        for i, line in enumerate(lines):
            try:
                event = json.loads(line)
                assert "stream_id" in event, f"Line {i+1} missing stream_id"
                assert "timestamp" in event, f"Line {i+1} missing timestamp"
                assert "order_id" in event, f"Line {i+1} missing order_id"
            except json.JSONDecodeError as e:
                pytest.fail(f"Line {i+1} is not valid JSON: {e}")


if __name__ == "__main__":
    # Allow running tests directly with: python -m pytest tests/e2e/test_paper_trading_p0.py -v
    pytest.main([__file__, "-v", "-s"])
