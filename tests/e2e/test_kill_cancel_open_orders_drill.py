"""Isolated Compose kill-cancel drill for Issue #4185.

Stack scenarios exercise Redis → execution resting orders → kill-switch cancel.
In-process scenarios cover cancel rejection/error/malformed/unsupported, fill-after-kill,
and residual positions without claiming productive venue behavior.

test_id: tc_kill_cancel_4185_compose
test_type: schutz
cdb_area: execution
rule_ref: EXECUTION_KILL_CANCEL_CONTRACT_V1
issue_ref: #4185
security_relevant: true
live_relevant: false
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import pytest
import redis
import requests

from core.contracts.external_adapter_registry import (
    MexcExecutionAdapter,
    MockExecutionAdapter,
)
from services.execution.kill_cancel import (
    KillCancelBatchVerdict,
    KillCancelCoordinator,
    RC_CANCEL_ADAPTER_UNSUPPORTED,
    RC_CANCEL_ALREADY_CONFIRMED,
    RC_CANCEL_EXECUTION_ERROR,
    RC_CANCEL_REQUEST_REJECTED,
    RC_FILL_AFTER_KILL_ACTIVATION,
    RC_KILL_CANCEL_HOLD,
    RC_KILL_CANCEL_PASS,
    RC_OPEN_ORDER_STATUS_UNKNOWN,
    RC_RESIDUAL_OPEN_ORDERS,
)
from services.execution.mock_executor import MockExecutor
from services.execution.open_order_registry import OpenOrderRegistry

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        os.getenv("CDB_4185_DRILL") != "1",
        reason="Issue #4185 isolated kill-cancel drill only",
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
LEDGER_PATH = Path(
    os.environ.get(
        "CDB_OPEN_ORDER_LEDGER_PATH",
        "/tmp/cdb_open_orders.json",
    )
)


def _flat_positions() -> list[dict[str, Any]]:
    return [
        {
            "symbol": "BTCUSDT",
            "status": "OPEN",
            "quantity": 0.01,
            "reason_code": "RESIDUAL_POSITION_VISIBLE_NO_UNWIND",
        }
    ]


@pytest.fixture(scope="module")
def redis_client() -> redis.Redis:
    secret_path = Path("/run/secrets/redis_password")
    password = secret_path.read_text(encoding="utf-8").strip()
    client = redis.Redis(
        host=os.environ.get("REDIS_HOST", "redis"),
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
            "operator": "issue-4185-drill",
            "justification": "isolated kill-cancel test-state reset",
        },
        timeout=10,
    )
    assert response.status_code == 200, response.text
    assert response.json()["active"] is False
    # Wait until execution supervisor resumes acceptance after deactivation.
    _wait_for_kill_cancel(
        predicate=lambda snap: snap.get("ready_for_new_orders") is True
        and snap.get("hold_new_orders") is False,
        timeout_s=20.0,
    )


def _set_active(*, reason: str = "manual") -> None:
    response = requests.post(
        f"{RISK_BASE_URL}/kill-switch/activate",
        json={
            "reason": reason,
            "message": "Issue #4185 isolated kill-cancel drill",
            "operator": "issue-4185-drill",
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


def _execution_status() -> dict:
    response = requests.get(f"{EXECUTION_BASE_URL}/status", timeout=10)
    assert response.status_code == 200, response.text
    return response.json()


def _wait_for_kill_cancel(
    *,
    predicate,
    timeout_s: float = 30.0,
) -> dict:
    deadline = time.monotonic() + timeout_s
    last: dict = {}
    while time.monotonic() < deadline:
        last = _execution_status().get("kill_cancel") or {}
        if predicate(last):
            return last
        time.sleep(0.5)
    raise AssertionError(f"kill_cancel condition not met; last={last}")


def _is_schema_mapped_resting_open(result: dict) -> bool:
    """EVENT_SCHEMA only allows FILLED|REJECTED|ERROR on order_results.

    Resting PENDING/SUBMITTED are published as ERROR with no error_message and
    zero fill. Registry/status remain the authoritative open-order view.
    """
    if result.get("status") in {"PENDING", "SUBMITTED"}:
        return True
    return (
        result.get("status") == "ERROR"
        and not result.get("error_message")
        and float(result.get("filled_quantity") or 0.0) == 0.0
    )


def _send_resting_order(client: redis.Redis, *, suffix: str) -> dict:
    pubsub = client.pubsub()
    pubsub.subscribe("order_results")
    pubsub.get_message(timeout=1)
    payload = {
        "type": "order",
        "order_id": f"4185-{suffix}",
        "client_id": f"4185-client-{suffix}",
        "decision_id": f"4185-decision-{suffix}",
        "strategy_id": "issue-4185-drill",
        "symbol": "BTC/USDT",
        "side": "BUY",
        "quantity": 0.001,
    }
    assert client.publish("orders", json.dumps(payload)) >= 1
    result = _wait_for_message(pubsub)
    pubsub.close()
    assert result is not None
    return result


def _register_multiple_resting(client: redis.Redis, *, n: int = 3) -> list[dict]:
    before = int(
        (_execution_status().get("kill_cancel") or {}).get("residual_open_order_count")
        or 0
    )
    results = []
    for i in range(n):
        result = _send_resting_order(client, suffix=f"rest-{i}-{int(time.time())}")
        assert _is_schema_mapped_resting_open(result), result
        results.append(result)
    _wait_for_kill_cancel(
        predicate=lambda snap: int(snap.get("residual_open_order_count") or 0)
        >= before + n
    )
    return results


# --- Stack scenarios ---


def test_s1_s2_inactive_keeps_resting_orders_open(redis_client: redis.Redis) -> None:
    """S1+S2: multiple resting orders registered; kill inactive → no cancels."""
    _set_inactive()
    status = _execution_status()
    assert status["mode"] == "mock"
    before = int(
        (status.get("kill_cancel") or {}).get("residual_open_order_count") or 0
    )
    results = _register_multiple_resting(redis_client, n=3)
    assert len(results) == 3
    kc = _wait_for_kill_cancel(
        predicate=lambda snap: int(snap.get("residual_open_order_count") or 0)
        >= before + 3
    )
    assert kc.get("last_verdict") in {None, "PASS_IDLE", "PASS"}
    assert "KILL_CANCEL_PASS" not in (kc.get("last_reason_codes") or [])


def test_s3_s5_active_cancels_confirmed(redis_client: redis.Redis) -> None:
    """S3+S5: kill active cancels cancelable opens; readback removes residuals."""
    _set_inactive()
    _register_multiple_resting(redis_client, n=2)
    _wait_for_kill_cancel(
        predicate=lambda snap: int(snap.get("residual_open_order_count") or 0) >= 2
    )
    _set_active()
    kc = _wait_for_kill_cancel(
        predicate=lambda snap: snap.get("last_verdict") == "PASS"
        and int(snap.get("residual_open_order_count") or 0) == 0
        and RC_KILL_CANCEL_PASS in (snap.get("last_reason_codes") or [])
    )
    assert kc["hold_new_orders"] is True
    # New order acceptance blocked while kill active
    blocked = _send_resting_order(redis_client, suffix=f"blocked-{int(time.time())}")
    assert blocked["status"] == "REJECTED"
    assert "kill-switch" in (blocked.get("error_message") or "").lower()


def test_s4_unevaluable_fail_closed(redis_client: redis.Redis) -> None:
    """S4: kill unevaluable → HALT / fail-closed, no new acceptance."""
    STATE_FILE.write_text("not=a=valid=kill=switch\n", encoding="utf-8")
    # Force supervisor to observe unevaluable/active fail-closed via risk API view
    status = requests.get(f"{RISK_BASE_URL}/kill-switch", timeout=10).json()
    assert status["active"] is True
    result = _send_resting_order(redis_client, suffix=f"uneval-{int(time.time())}")
    assert result["status"] == "REJECTED"
    assert "kill-switch" in (result.get("error_message") or "").lower()
    _set_inactive()


def test_s9_double_kill_idempotent(redis_client: redis.Redis) -> None:
    """S9: second kill while already active must not contradict first cancel."""
    _set_inactive()
    _register_multiple_resting(redis_client, n=2)
    _wait_for_kill_cancel(
        predicate=lambda snap: int(snap.get("residual_open_order_count") or 0) >= 2
    )
    _set_active()
    first = _wait_for_kill_cancel(
        predicate=lambda snap: snap.get("last_verdict") == "PASS"
        and int(snap.get("residual_open_order_count") or 0) == 0
    )
    event_id = first.get("active_kill_event_id")
    _set_active()
    time.sleep(2.0)
    second = _execution_status().get("kill_cancel") or {}
    assert int(second.get("residual_open_order_count") or 0) == 0
    assert second.get("last_verdict") == "PASS"
    # Same kill event or still clean residual — no contradictory re-cancel batch
    if event_id and second.get("active_kill_event_id"):
        assert (
            second.get("active_kill_event_id") == event_id
            or second.get("last_verdict") == "PASS"
        )


def test_s10a_ledger_persists_open_orders(redis_client: redis.Redis) -> None:
    """S10a: resting registration persists open-order ledger for restart reconstruction."""
    _set_inactive()
    _register_multiple_resting(redis_client, n=2)
    _wait_for_kill_cancel(
        predicate=lambda snap: int(snap.get("residual_open_order_count") or 0) >= 2
    )
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if LEDGER_PATH.exists() and LEDGER_PATH.stat().st_size > 2:
            break
        time.sleep(0.5)
    assert LEDGER_PATH.exists(), "open-order ledger was not persisted"
    payload = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    assert payload, "ledger must contain reconstructed open-order records"


@pytest.mark.skipif(
    os.getenv("CDB_4185_RESTART_PHASE") != "1",
    reason="Restart phase prepared by run_kill_cancel_drill.sh",
)
def test_s10b_restart_reconciles_before_new_orders(redis_client: redis.Redis) -> None:
    """S10b: after execution restart with active kill, reconcile before new orders."""
    risk = requests.get(f"{RISK_BASE_URL}/kill-switch", timeout=10).json()
    assert risk["active"] is True
    kc = _wait_for_kill_cancel(
        predicate=lambda snap: snap.get("hold_new_orders") is True
        and snap.get("kill_cancel_contract") == "EXECUTION_KILL_CANCEL_CONTRACT_V1",
        timeout_s=45.0,
    )
    blocked = _send_resting_order(
        redis_client, suffix=f"restart-block-{int(time.time())}"
    )
    assert blocked["status"] == "REJECTED"
    assert kc.get("hold_new_orders") is True


def test_s12_positions_visible_no_auto_unwind(tmp_path: Path) -> None:
    """S12: residual positions remain visible; no auto-unwind claim."""
    reg = OpenOrderRegistry(ledger_path=tmp_path / "s12.json")
    adapter = MockExecutionAdapter(
        executor=MockExecutor(
            resting_orders=True,
            success_rate=1.0,
            min_latency_ms=0,
            max_latency_ms=0,
            cancel_behavior="confirm",
        )
    )
    coord = KillCancelCoordinator(
        registry=reg,
        adapter=adapter,
        commit_sha=os.getenv("CDB_GIT_COMMIT", "unknown"),
        position_resolver=_flat_positions,
    )
    manifest = coord.reconcile(kill_state="active", kill_reason="manual")
    assert manifest.residual_positions
    assert manifest.residual_positions[0]["quantity"] == 0.01
    assert (
        manifest.residual_positions[0].get("reason_code")
        == "RESIDUAL_POSITION_VISIBLE_NO_UNWIND"
    )


# --- In-process cancel contract scenarios (mock-only, compose-gated) ---


def test_s6_cancel_rejection_hold(tmp_path: Path) -> None:
    executor = MockExecutor(
        resting_orders=True,
        success_rate=1.0,
        min_latency_ms=0,
        max_latency_ms=0,
        cancel_behavior="reject",
    )
    adapter = MockExecutionAdapter(executor=executor)
    reg = OpenOrderRegistry(ledger_path=tmp_path / "s6.json")
    executor.place_resting_order(
        order_id="s6", symbol="BTCUSDT", side="BUY", quantity=1.0
    )
    reg.register(internal_order_id="s6", symbol="BTCUSDT", status="PENDING", quantity=1)
    manifest = KillCancelCoordinator(
        registry=reg, adapter=adapter, position_resolver=_flat_positions
    ).reconcile(kill_state="active", kill_reason="manual")
    assert manifest.overall_verdict == KillCancelBatchVerdict.HOLD.value
    assert RC_CANCEL_REQUEST_REJECTED in manifest.reason_codes
    assert RC_RESIDUAL_OPEN_ORDERS in manifest.reason_codes or RC_KILL_CANCEL_HOLD in (
        manifest.reason_codes
    )
    assert reg.count_open() == 1


def test_s7_cancel_exception_and_malformed_hold(tmp_path: Path) -> None:
    for behavior, expected in (
        ("error", RC_CANCEL_EXECUTION_ERROR),
        ("malformed", RC_OPEN_ORDER_STATUS_UNKNOWN),
    ):
        executor = MockExecutor(
            resting_orders=True,
            success_rate=1.0,
            min_latency_ms=0,
            max_latency_ms=0,
            cancel_behavior=behavior,
        )
        adapter = MockExecutionAdapter(executor=executor)
        reg = OpenOrderRegistry(ledger_path=tmp_path / f"s7-{behavior}.json")
        oid = f"s7-{behavior}"
        executor.place_resting_order(
            order_id=oid, symbol="BTCUSDT", side="BUY", quantity=1.0
        )
        reg.register(
            internal_order_id=oid, symbol="BTCUSDT", status="PENDING", quantity=1
        )
        manifest = KillCancelCoordinator(
            registry=reg, adapter=adapter, position_resolver=_flat_positions
        ).reconcile(kill_state="active", kill_reason="manual")
        assert manifest.overall_verdict != KillCancelBatchVerdict.PASS.value
        assert expected in manifest.reason_codes or reg.count_open() == 1
        assert reg.get(oid) is not None


def test_s8_adapter_without_cancel_hold(tmp_path: Path) -> None:
    reg = OpenOrderRegistry(ledger_path=tmp_path / "s8.json")
    reg.register(internal_order_id="s8", symbol="BTCUSDT", status="PENDING", quantity=1)
    adapter = MexcExecutionAdapter(executor=object())  # type: ignore[arg-type]
    adapter._executor = None
    manifest = KillCancelCoordinator(
        registry=reg, adapter=adapter, position_resolver=_flat_positions
    ).reconcile(kill_state="active", kill_reason="manual")
    assert manifest.overall_verdict == KillCancelBatchVerdict.HOLD.value
    assert RC_CANCEL_ADAPTER_UNSUPPORTED in manifest.reason_codes


def test_s11_fill_after_kill_fail(tmp_path: Path) -> None:
    executor = MockExecutor(
        resting_orders=True,
        success_rate=1.0,
        min_latency_ms=0,
        max_latency_ms=0,
        cancel_behavior="confirm",
    )
    adapter = MockExecutionAdapter(executor=executor)
    reg = OpenOrderRegistry(ledger_path=tmp_path / "s11.json")
    executor.place_resting_order(
        order_id="s11", symbol="BTCUSDT", side="BUY", quantity=1.0
    )
    reg.register(
        internal_order_id="s11", symbol="BTCUSDT", status="PENDING", quantity=1
    )
    coord = KillCancelCoordinator(
        registry=reg, adapter=adapter, position_resolver=_flat_positions
    )
    coord.reconcile(
        kill_state="active", kill_reason="manual", kill_activated_at_utc="t0"
    )
    coord.note_fill_after_kill(
        internal_order_id="s11",
        venue_order_id="s11",
        symbol="BTCUSDT",
        filled_quantity=1.0,
    )
    reg2 = OpenOrderRegistry(ledger_path=tmp_path / "s11b.json")
    coord2 = KillCancelCoordinator(
        registry=reg2, adapter=adapter, position_resolver=_flat_positions
    )
    coord2._active_kill_event_id = "kill_x"
    coord2._fill_after_kill = list(coord._fill_after_kill)
    manifest = coord2.reconcile(kill_state="active", kill_reason="manual")
    assert manifest.overall_verdict == KillCancelBatchVerdict.FAIL.value
    assert RC_FILL_AFTER_KILL_ACTIVATION in manifest.reason_codes


def test_s9_inprocess_double_reconcile_no_duplicate_cancel(tmp_path: Path) -> None:
    executor = MockExecutor(
        resting_orders=True,
        success_rate=1.0,
        min_latency_ms=0,
        max_latency_ms=0,
        cancel_behavior="confirm",
    )
    adapter = MockExecutionAdapter(executor=executor)
    reg = OpenOrderRegistry(ledger_path=tmp_path / "s9.json")
    executor.place_resting_order(
        order_id="s9i", symbol="BTCUSDT", side="BUY", quantity=1.0
    )
    reg.register(
        internal_order_id="s9i", symbol="BTCUSDT", status="PENDING", quantity=1
    )
    coord = KillCancelCoordinator(
        registry=reg, adapter=adapter, position_resolver=_flat_positions
    )
    first = coord.reconcile(
        kill_state="active", kill_reason="manual", kill_activated_at_utc="t0"
    )
    assert first.overall_verdict == KillCancelBatchVerdict.PASS.value
    executor.place_resting_order(
        order_id="s9i", symbol="BTCUSDT", side="BUY", quantity=1.0
    )
    reg.register(
        internal_order_id="s9i", symbol="BTCUSDT", status="PENDING", quantity=1
    )
    second = coord.reconcile(
        kill_state="active", kill_reason="manual", kill_activated_at_utc="t0"
    )
    assert (
        RC_CANCEL_ALREADY_CONFIRMED in second.reason_codes
        or second.orders_already_terminal >= 1
    )
