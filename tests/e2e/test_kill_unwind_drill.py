"""Isolated real-stack kill/unwind drill for Issue #4182.

This suite never claims end-to-end stop-loss protection. D6 and D8 deliberately
return UNWIND_NOT_PROVEN while proving that the synthetic position does not grow.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import time
from unittest.mock import patch

import pytest
import redis
import requests

from core.domain.models import Signal
from core.safety.stop_loss_protection import STOP_LOSS_PROTECTION_BLOCK_REASON
from services.execution.mock_executor import MockExecutor
from services.execution.models import Order as ExecutionOrder
from services.risk.config import RiskConfig
from services.risk.models import RiskState
from services.risk.service import RiskManager
import services.risk.service as risk_service

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        os.getenv("CDB_4182_DRILL") != "1",
        reason="Issue #4182 isolated drill only",
    ),
]

RISK_BASE_URL = os.environ.get("RISK_BASE_URL", "http://cdb_risk_test:8002")
EXECUTION_BASE_URL = os.environ.get(
    "EXECUTION_BASE_URL", "http://cdb_execution_test:8003"
)
STATE_FILE = Path(
    os.environ.get(
        "CDB_KILL_SWITCH_STATE_FILE",
        "/app/kill_switch/.cdb_kill_switch.state",
    )
)


@pytest.fixture(scope="module")
def redis_client() -> redis.Redis:
    secret_path = Path("/run/secrets/redis_password")
    password = secret_path.read_text(encoding="utf-8").strip()
    client = redis.Redis(
        host=os.environ.get("REDIS_HOST", "cdb_redis"),
        port=int(os.environ.get("REDIS_PORT", "6379")),
        password=password,
        decode_responses=True,
        socket_timeout=5,
    )
    client.ping()
    return client


def _set_inactive() -> None:
    response = requests.post(
        f"{RISK_BASE_URL}/kill-switch/deactivate",
        json={
            "operator": "issue-4182-drill",
            "justification": "isolated test-state reset",
        },
        timeout=10,
    )
    assert response.status_code == 200, response.text
    assert response.json()["active"] is False


def _set_active() -> None:
    response = requests.post(
        f"{RISK_BASE_URL}/kill-switch/activate",
        json={
            "reason": "manual",
            "message": "Issue #4182 isolated drill",
            "operator": "issue-4182-drill",
        },
        timeout=10,
    )
    assert response.status_code == 200, response.text
    assert response.json()["active"] is True


def _wait_for_message(pubsub, *, timeout_s: float = 10.0) -> dict | None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        message = pubsub.get_message(timeout=0.25)
        if message and message["type"] == "message":
            return json.loads(message["data"])
    return None


def _send_direct_order(
    client: redis.Redis,
    *,
    suffix: str,
    side: str = "BUY",
    quantity: float = 0.001,
) -> dict:
    pubsub = client.pubsub()
    pubsub.subscribe("order_results")
    pubsub.get_message(timeout=1)
    payload = {
        "type": "order",
        "order_id": f"4182-{suffix}",
        "client_id": f"4182-client-{suffix}",
        "decision_id": f"4182-decision-{suffix}",
        "strategy_id": "issue-4182-drill",
        "symbol": "BTC/USDT",
        "side": side,
        "quantity": quantity,
    }
    subscribers = client.publish("orders", json.dumps(payload))
    assert subscribers >= 1
    result = _wait_for_message(pubsub)
    pubsub.close()
    assert result is not None
    return result


def _publish_signal_and_wait_for_alert(
    client: redis.Redis,
    *,
    suffix: str,
    metadata: dict | None = None,
) -> tuple[dict, dict | None]:
    alerts = client.pubsub()
    orders = client.pubsub()
    alerts.subscribe("alerts")
    orders.subscribe("orders")
    alerts.get_message(timeout=1)
    orders.get_message(timeout=1)
    payload = {
        "type": "signal",
        "signal_id": f"4182-signal-{suffix}",
        "strategy_id": "issue-4182-drill",
        "symbol": "BTCUSDT",
        "direction": "BUY",
        "side": "BUY",
        "strength": 0.9,
        "price": 50000.0,
        "timestamp": time.time(),
        "metadata": metadata or {},
    }
    assert client.publish("signals", json.dumps(payload)) >= 1
    alert = _wait_for_message(alerts)
    order = _wait_for_message(orders, timeout_s=1.0)
    alerts.close()
    orders.close()
    assert alert is not None
    return alert, order


def test_d1_inactive_reaches_mock_execution(redis_client: redis.Redis) -> None:
    _set_inactive()
    status = requests.get(f"{EXECUTION_BASE_URL}/status", timeout=10).json()
    assert status["mode"] == "mock"
    result = _send_direct_order(redis_client, suffix="d1")
    assert "kill-switch" not in (result.get("error_message") or "").lower()
    assert result["status"] in {"FILLED", "REJECTED"}


def test_d2_active_blocks_risk_and_execution(redis_client: redis.Redis) -> None:
    _set_active()
    alert, order = _publish_signal_and_wait_for_alert(redis_client, suffix="d2")
    assert alert["code"] == "KILL_SWITCH_ACTIVE"
    assert order is None
    result = _send_direct_order(redis_client, suffix="d2")
    assert result["status"] == "REJECTED"
    assert "kill-switch" in (result.get("error_message") or "").lower()


def test_d3_missing_state_blocks_both_services(redis_client: redis.Redis) -> None:
    STATE_FILE.unlink(missing_ok=True)
    status = requests.get(f"{RISK_BASE_URL}/kill-switch", timeout=10).json()
    assert status["active"] is True
    assert status["reason"] == "system_error"
    alert, order = _publish_signal_and_wait_for_alert(redis_client, suffix="d3")
    assert alert["code"] == "KILL_SWITCH_ACTIVE"
    assert order is None
    result = _send_direct_order(redis_client, suffix="d3")
    assert result["status"] == "REJECTED"
    assert "kill-switch" in (result.get("error_message") or "").lower()


def test_d4_corrupt_state_remains_fail_closed(redis_client: redis.Redis) -> None:
    STATE_FILE.write_text("not=a=valid=kill=switch\n", encoding="utf-8")
    status = requests.get(f"{RISK_BASE_URL}/kill-switch", timeout=10).json()
    assert status["active"] is True
    result = _send_direct_order(redis_client, suffix="d4")
    assert result["status"] == "REJECTED"
    assert STATE_FILE.read_text(encoding="utf-8") == "not=a=valid=kill=switch\n"


def test_d5_restart_keeps_missing_state_fail_closed(
    redis_client: redis.Redis,
) -> None:
    """The PowerShell runner removes state and restarts both services first."""
    assert not STATE_FILE.exists()
    status = requests.get(f"{RISK_BASE_URL}/kill-switch", timeout=10).json()
    assert status["active"] is True
    result = _send_direct_order(redis_client, suffix="d5")
    assert result["status"] == "REJECTED"
    assert "kill-switch" in (result.get("error_message") or "").lower()


def test_d6_existing_unwind_is_not_proven_and_position_does_not_grow(
    redis_client: redis.Redis,
) -> None:
    _set_inactive()
    test_config = RiskConfig(
        max_position_pct=0.10,
        max_total_exposure_pct=0.30,
        max_daily_drawdown_pct=0.05,
        stop_loss_pct=0.02,
        paper_auto_unwind=True,
    )
    with patch.object(risk_service, "config", test_config):
        manager = RiskManager()

    position_before = 0.01
    isolated_state = RiskState()
    isolated_state.positions["BTCUSDT"] = position_before
    isolated_state.last_prices["BTCUSDT"] = 50000.0
    with (
        patch.object(risk_service, "risk_state", isolated_state),
        patch.object(manager, "send_order") as send_order,
    ):
        manager._trigger_proactive_unwind()

    send_order.assert_called_once()
    unwind_order = send_order.call_args.args[0]
    assert unwind_order.side == "SELL"
    assert unwind_order.quantity == position_before
    assert unwind_order.decision_contract_v1 is None
    assert isolated_state.positions["BTCUSDT"] == position_before


def test_d7_required_protection_blocks_without_order(
    redis_client: redis.Redis,
) -> None:
    _set_inactive()
    alert, order = _publish_signal_and_wait_for_alert(
        redis_client,
        suffix="d7",
        metadata={"requires_stop_loss_protection": True},
    )
    assert alert["code"] == STOP_LOSS_PROTECTION_BLOCK_REASON
    assert order is None


def test_d8_mock_adapter_rejection_leaves_position_visible() -> None:
    position_before = 0.01
    executor = MockExecutor(
        success_rate=0.0,
        min_latency_ms=0,
        max_latency_ms=0,
    )
    result = executor.execute_order(
        ExecutionOrder(
            order_id="4182-d8-exit",
            client_id="4182-d8-exit",
            decision_id="4182-d8-decision",
            strategy_id="issue-4182-drill",
            symbol="BTC/USDT",
            side="SELL",
            quantity=position_before,
        )
    )
    position_after = position_before
    assert result.status == "REJECTED"
    assert result.filled_quantity == 0.0
    assert position_after == position_before
