import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import pytest

try:
    import redis  # type: ignore
except Exception as e:  # pragma: no cover
    redis = None


@dataclass(frozen=True)
class RedisCfg:
    host: str
    port: int
    password: str
    topic_orders: str
    topic_order_results: str
    stream_fills: str
    timeout_seconds: int
    require_stream: bool


def _cfg() -> RedisCfg:
    return RedisCfg(
        host=os.getenv("CDB_REDIS_HOST", "localhost"),
        port=int(os.getenv("CDB_REDIS_PORT", "6379")),
        password=os.getenv("CDB_REDIS_PASSWORD", ""),
        topic_orders=os.getenv("CDB_TOPIC_ORDERS", "orders"),
        topic_order_results=os.getenv("CDB_TOPIC_ORDER_RESULTS", "order_results"),
        stream_fills=os.getenv("CDB_STREAM_FILLS", "stream.fills"),
        timeout_seconds=int(os.getenv("CDB_E2E_TIMEOUT_SECONDS", "8")),
        require_stream=os.getenv("CDB_E2E_REQUIRE_STREAM", "0") == "1",
    )


def _redis_client(cfg: RedisCfg):
    if redis is None:
        pytest.skip("redis-py is not installed in this environment")
    return redis.Redis(
        host=cfg.host,
        port=cfg.port,
        password=cfg.password or None,
        decode_responses=True,
    )


def _pubsub_wait_json(pubsub, timeout_seconds: int) -> Optional[Dict[str, Any]]:
    """Wait for the first JSON message on a subscribed channel, ignoring subscribe acks."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        msg = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
        if not msg:
            continue
        if msg.get("type") != "message":
            continue
        data = msg.get("data")
        if not isinstance(data, str):
            continue
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            # Not JSON; keep waiting.
            continue
    return None


@pytest.mark.e2e
def test_order_to_execution_to_order_results_regression_shield():
    """
    Regression Shield for core messaging flow (#255):
      orders (Pub/Sub) -> execution -> order_results (Pub/Sub) [+ optional stream persistence].

    This test is intentionally NOT DB-dependent.
    """
    cfg = _cfg()
    r = _redis_client(cfg)

    # Diagnostics snapshot (helps when test fails)
    numsub_orders = r.execute_command("PUBSUB", "NUMSUB", cfg.topic_orders)
    numsub_results = r.execute_command("PUBSUB", "NUMSUB", cfg.topic_order_results)

    # Subscribe BEFORE publishing (avoid missing the message).
    pubsub = r.pubsub()
    pubsub.subscribe(cfg.topic_order_results)

    # Publish a minimal order payload.
    # Note: Execution service may require more fields; if so, the failure will show in execution logs.
    order_payload = {
        "order_id": "test-001",
        "symbol": "BTC/USDT",
        "side": "BUY",
        "quantity": 0.001,
    }
    published = r.publish(cfg.topic_orders, json.dumps(order_payload, ensure_ascii=False))

    # Wait for result
    result = _pubsub_wait_json(pubsub, cfg.timeout_seconds)
    pubsub.close()

    assert published >= 0, "Redis publish returned unexpected negative value"

    assert result is not None, (
        "Timed out waiting for order_results.\n"
        f"PUBSUB NUMSUB orders: {numsub_orders}\n"
        f"PUBSUB NUMSUB order_results: {numsub_results}\n"
        f"Tip: run `docker compose logs --tail 200 cdb_execution` to see if the order was processed."
    )

    # Contract assertions (MVP)
    assert result.get("type") == "order_result"
    assert isinstance(result.get("timestamp"), int), f"timestamp must be unix int, got: {type(result.get('timestamp'))}"
    assert "status" in result
    assert result.get("symbol") in (order_payload["symbol"], order_payload["symbol"].replace("/", "")) or isinstance(result.get("symbol"), str)
    assert isinstance(result.get("side"), str)

    # Optional: stream persistence proof (for replay)
    if cfg.require_stream:
        try:
            entries = r.xrevrange(cfg.stream_fills, max="+", min="-", count=1)
        except Exception as e:
            pytest.fail(f"Stream check failed for {cfg.stream_fills}: {e}")
        assert len(entries) >= 1, f"Expected at least 1 entry in stream {cfg.stream_fills}"
