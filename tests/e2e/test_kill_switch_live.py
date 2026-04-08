"""
E2E Smoke Test — Kill-Switch shared state in Blue Stack
=======================================================

Issue #1198 Delta 2 — Evidence: POST /kill-switch/activate on Risk
blocks subsequent order flow in Execution via shared Docker Volume
(kill_switch_state:/app/kill_switch/.cdb_kill_switch.state).

Prerequisites:
- Blue Stack running (docker compose -f compose.blue.yml up -d)
- Risk accessible at localhost:8002 (port mapped)
- Execution subscribed to Redis 'orders' channel

Run:
    E2E_RUN=1 pytest tests/e2e/test_kill_switch_live.py -v

Teardown:
    Kill-switch is deactivated after each test — stack state is restored.
"""

import json
import os
import time

import pytest
import redis
import requests


pytestmark = pytest.mark.skipif(
    os.getenv("E2E_RUN") != "1", reason="E2E tests only run when E2E_RUN=1 is set"
)

RISK_BASE_URL = os.getenv("RISK_BASE_URL", "http://localhost:8002")


@pytest.fixture(scope="module")
def redis_client():
    """
    Redis client — same connection strategy as test_paper_trading_p0.
    Reads password from Docker secret mount; falls back to localhost.
    """
    try:
        with open("/run/secrets/redis_password", "r") as f:
            password = f.read().strip()
    except FileNotFoundError:
        pytest.fail(
            "Secret file /run/secrets/redis_password not found. "
            "Check Docker volume mount."
        )

    if not password:
        pytest.fail("Redis password file is empty.")

    for host in ("cdb_redis", "localhost"):
        try:
            client = redis.Redis(
                host=host,
                port=6379,
                password=password,
                decode_responses=True,
                socket_timeout=5,
            )
            client.ping()
            yield client
            return
        except (redis.ConnectionError, redis.TimeoutError):
            continue

    pytest.fail("Could not connect to Redis (tried cdb_redis:6379 and localhost:6379)")


@pytest.fixture(autouse=True)
def deactivate_kill_switch_after():
    """
    Always deactivate kill-switch after each test.
    Prevents state leakage into subsequent E2E tests.
    Ignores errors (deactivation of an already-inactive switch returns 400).
    """
    yield
    try:
        requests.post(
            f"{RISK_BASE_URL}/kill-switch/deactivate",
            json={
                "operator": "e2e-teardown",
                "justification": "post-test cleanup for #1198",
            },
            timeout=5,
        )
    except Exception:
        pass  # teardown must not mask real test failures


@pytest.fixture
def unique_order_id():
    return f"e2e-ks-{int(time.time() * 1000)}"


def _send_order_and_wait(redis_client, order_id, timeout_s=10):
    """
    Publish order to 'orders' channel, collect result from 'order_results'.
    Returns the parsed result payload dict, or None on timeout.
    """
    pubsub = redis_client.pubsub()
    pubsub.subscribe("order_results")

    # Drain stale messages before publishing
    for _ in range(5):
        pubsub.get_message(timeout=0.05)

    order_payload = {
        "order_id": order_id,
        "symbol": "BTC/USDT",
        "side": "BUY",
        "quantity": 0.001,
        "decision_id": f"e2e-decision-{order_id}",
    }

    subs = redis_client.publish("orders", json.dumps(order_payload))
    assert subs >= 1, (
        "No subscribers on 'orders' channel — Execution service not running?"
    )

    result = None
    for _ in range(timeout_s * 2):  # 0.5s per attempt
        msg = pubsub.get_message(timeout=0.5)
        if msg and msg["type"] == "message":
            result = json.loads(msg["data"])
            break
        time.sleep(0.5)

    pubsub.unsubscribe("order_results")
    pubsub.close()
    return result


@pytest.mark.e2e
def test_kill_switch_shared_volume_blocks_execution(redis_client, unique_order_id):
    """
    Delta 2 core test for #1198.

    Proves that the kill-switch state written by Risk via
    POST /kill-switch/activate reaches Execution through the
    shared Docker volume kill_switch_state:/app/kill_switch
    and that Execution rejects orders fail-closed.

    Assertion chain:
    1. Risk HTTP reachable + kill-switch inactive at test start
    2. Baseline order flows through without kill-switch rejection
    3. POST /kill-switch/activate returns active=True
    4. Subsequent order is REJECTED with kill-switch error message in Execution
    """
    # 1. Risk must be reachable and kill-switch must be inactive
    status_resp = requests.get(f"{RISK_BASE_URL}/kill-switch", timeout=5)
    assert status_resp.status_code == 200, (
        f"Risk /kill-switch endpoint unreachable: HTTP {status_resp.status_code}"
    )
    assert status_resp.json().get("active") is False, (
        "Kill-switch already active at test start — "
        "clean stack state required (run deactivate manually or restart stack)"
    )

    # 2. Baseline: order without active kill-switch must NOT be kill-switch-blocked
    baseline_result = _send_order_and_wait(redis_client, f"{unique_order_id}-baseline")
    assert baseline_result is not None, (
        "No result for baseline order (timeout 10s) — Execution not processing orders"
    )
    error_msg_baseline = (baseline_result.get("error_message") or "").lower()
    assert "kill-switch" not in error_msg_baseline, (
        f"Baseline order unexpectedly blocked by kill-switch: {baseline_result}"
    )

    # 3. Activate kill-switch via Risk HTTP endpoint
    activate_resp = requests.post(
        f"{RISK_BASE_URL}/kill-switch/activate",
        json={
            "reason": "manual",
            "message": "E2E smoke test Delta 2 — #1198",
            "operator": "e2e-test",
        },
        timeout=5,
    )
    assert activate_resp.status_code == 200, (
        f"Kill-switch activate failed: HTTP {activate_resp.status_code} — "
        f"{activate_resp.text}"
    )
    assert activate_resp.json().get("active") is True, (
        f"activate response did not confirm active=True: {activate_resp.json()}"
    )

    # Allow shared volume write to be visible in Execution container's FS layer
    time.sleep(0.5)

    # 4. Order under active kill-switch must be REJECTED by Execution
    blocked_result = _send_order_and_wait(redis_client, f"{unique_order_id}-blocked")
    assert blocked_result is not None, (
        "No result for blocked order (timeout 10s) — "
        "Execution not responding after kill-switch activation"
    )
    assert blocked_result.get("status") == "REJECTED", (
        f"Expected status=REJECTED (kill-switch active), "
        f"got: {blocked_result.get('status')!r}\n"
        f"Full payload: {blocked_result}"
    )
    error_msg = (blocked_result.get("error_message") or "").lower()
    assert "kill-switch" in error_msg, (
        f"Expected 'kill-switch' in error_message to confirm Execution read shared state, "
        f"got: {blocked_result.get('error_message')!r}"
    )
