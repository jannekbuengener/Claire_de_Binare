"""Unit + contract tests for kill-cancel open orders (#4185).

test_id: tc_kill_cancel_4185
test_type: schutz
cdb_area: execution
rule_ref: LR-050-kill-cancel / INV-kill-before-fill
issue_ref: #4185
security_relevant: true
live_relevant: false
profitability_relevant: false
surrealdb_export: true
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from core.contracts.external_adapter_contracts import (
    CancelOrderRequest,
    CancelOrderResponse,
    OpenOrderSnapshot,
)
from core.contracts.external_adapter_registry import (
    MexcExecutionAdapter,
    MockExecutionAdapter,
)
from services.execution.kill_cancel import (
    REQUIRED_REASON_CODES,
    EVIDENCE_SCHEMA_VERSION,
    KillCancelBatchVerdict,
    KillCancelCoordinator,
    KillCancelSupervisor,
    RC_CANCEL_ADAPTER_UNSUPPORTED,
    RC_CANCEL_ALREADY_CONFIRMED,
    RC_CANCEL_CONFIRMATION_MISSING,
    RC_CANCEL_EXECUTION_ERROR,
    RC_CANCEL_REQUEST_REJECTED,
    RC_FILL_AFTER_KILL_ACTIVATION,
    RC_KILL_CANCEL_HOLD,
    RC_KILL_CANCEL_PASS,
    RC_OPEN_ORDER_STATUS_UNKNOWN,
    RC_RESIDUAL_OPEN_ORDERS,
    RC_RESIDUAL_POSITION_UNKNOWN,
)
from services.execution.mock_executor import MockExecutor
from services.execution.models import Order, OrderStatus
from services.execution.open_order_registry import OpenOrderRegistry


def _authoritative_flat_snapshot():
    """Explicit test-only flat snapshot with clear provenance (not service default)."""
    return [
        {
            "symbol": "BTCUSDT",
            "status": "NONE",
            "quantity": 0.0,
            "reason_code": "RESIDUAL_POSITION_NONE",
            "provenance": "test_fixture_authoritative_flat",
        }
    ]


def _authoritative_open_snapshot():
    return [
        {
            "symbol": "BTCUSDT",
            "status": "OPEN",
            "quantity": 0.01,
            "reason_code": "RESIDUAL_POSITION_VISIBLE_NO_UNWIND",
            "provenance": "test_fixture_authoritative_open",
        }
    ]


def _coordinator(registry, adapter, *, position_resolver=None):
    """Default: no position truth → UNKNOWN/HOLD (production-honest)."""
    return KillCancelCoordinator(
        registry=registry,
        adapter=adapter,
        commit_sha="deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        position_resolver=position_resolver,
    )


def _assert_confirmed_cancels_hold_unknown(manifest) -> None:
    assert manifest.overall_verdict == KillCancelBatchVerdict.HOLD.value
    assert RC_RESIDUAL_POSITION_UNKNOWN in manifest.reason_codes
    assert RC_KILL_CANCEL_HOLD in manifest.reason_codes
    assert RC_KILL_CANCEL_PASS not in manifest.reason_codes
    assert any(p.get("status") == "UNKNOWN" for p in manifest.residual_positions)
    assert all(p.get("quantity") is None for p in manifest.residual_positions)


@pytest.fixture
def resting_adapter():
    executor = MockExecutor(
        resting_orders=True,
        success_rate=1.0,
        min_latency_ms=0,
        max_latency_ms=0,
        cancel_behavior="confirm",
    )
    return MockExecutionAdapter(executor=executor)


# --- Registry ---


@pytest.mark.unit
def test_registry_pending_submitted_partial_open(tmp_path: Path) -> None:
    reg = OpenOrderRegistry(ledger_path=tmp_path / "ledger.json")
    reg.register(internal_order_id="o1", symbol="BTCUSDT", status="PENDING", quantity=1)
    reg.register(
        internal_order_id="o2", symbol="ETHUSDT", status="SUBMITTED", quantity=2
    )
    reg.register(
        internal_order_id="o3",
        symbol="BTCUSDT",
        status="PARTIALLY_FILLED",
        quantity=3,
        filled_quantity=1,
    )
    opens = reg.list_open()
    assert [o.internal_order_id for o in opens] == ["o1", "o3", "o2"] or {
        o.internal_order_id for o in opens
    } == {"o1", "o2", "o3"}
    assert all(o.is_open() for o in opens)


@pytest.mark.unit
def test_registry_cancel_error_and_unknown_do_not_delete(tmp_path: Path) -> None:
    reg = OpenOrderRegistry(ledger_path=tmp_path / "ledger.json")
    reg.register(
        internal_order_id="o1", symbol="BTCUSDT", status="SUBMITTED", quantity=1
    )
    reg.mark_cancel_outcome(
        "o1",
        kill_cancel_state="CANCEL_ERROR",
        reason_code=RC_CANCEL_EXECUTION_ERROR,
        confirmed=False,
    )
    assert reg.get("o1") is not None
    assert reg.get("o1").residual_open is True
    reg.mark_cancel_outcome(
        "o1",
        kill_cancel_state="STATUS_UNKNOWN",
        reason_code=RC_OPEN_ORDER_STATUS_UNKNOWN,
        confirmed=False,
    )
    assert reg.count_open() == 1


@pytest.mark.unit
def test_registry_confirmed_cancelled_removes(tmp_path: Path) -> None:
    reg = OpenOrderRegistry(ledger_path=tmp_path / "ledger.json")
    reg.register(internal_order_id="o1", symbol="BTCUSDT", status="PENDING", quantity=1)
    reg.mark_cancel_outcome(
        "o1",
        kill_cancel_state="CANCEL_CONFIRMED",
        reason_code=RC_KILL_CANCEL_PASS,
        terminal_status="CANCELLED",
        confirmed=True,
    )
    assert reg.get("o1") is None
    assert reg.count_open() == 0


@pytest.mark.unit
def test_registry_thread_safety(tmp_path: Path) -> None:
    reg = OpenOrderRegistry(ledger_path=tmp_path / "ledger.json")

    def worker(start: int) -> None:
        for i in range(start, start + 50):
            reg.register(
                internal_order_id=f"o{i}",
                symbol="BTCUSDT",
                status="PENDING",
                quantity=1,
            )

    threads = [threading.Thread(target=worker, args=(i * 50,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert reg.count_open() == 200


@pytest.mark.unit
def test_registry_restart_reload(tmp_path: Path) -> None:
    path = tmp_path / "ledger.json"
    reg = OpenOrderRegistry(ledger_path=path)
    reg.register(
        internal_order_id="o1", symbol="BTCUSDT", status="SUBMITTED", quantity=1
    )
    reg2 = OpenOrderRegistry(ledger_path=path)
    assert reg2.count_open() == 1
    assert reg2.get("o1").status == "SUBMITTED"


@pytest.mark.unit
def test_registry_persist_oserror_keeps_in_memory(tmp_path: Path, monkeypatch) -> None:
    """Ledger IO failure must not drop in-memory open-order truth (#4185)."""
    path = tmp_path / "locked" / "ledger.json"
    reg = OpenOrderRegistry(ledger_path=path)

    def _boom(*_args, **_kwargs):
        raise PermissionError("ledger not writable")

    monkeypatch.setattr(Path, "write_text", _boom)
    reg.register(internal_order_id="o1", symbol="BTCUSDT", status="PENDING", quantity=1)
    assert reg.count_open() == 1
    assert reg.get("o1") is not None


# --- Cancellation outcomes ---


@pytest.mark.unit
def test_cancel_confirmed_hold_without_position_truth(
    resting_adapter, tmp_path: Path
) -> None:
    """Confirmed cancel is honest; missing position truth keeps batch HOLD (#4185 G1)."""
    reg = OpenOrderRegistry(ledger_path=tmp_path / "l.json")
    resting_adapter._executor.place_resting_order(
        order_id="o1", symbol="BTCUSDT", side="BUY", quantity=1.0, status="PENDING"
    )
    reg.register(internal_order_id="o1", symbol="BTCUSDT", status="PENDING", quantity=1)
    coord = _coordinator(reg, resting_adapter)
    manifest = coord.reconcile(kill_state="active", kill_reason="manual")
    _assert_confirmed_cancels_hold_unknown(manifest)
    assert manifest.orders_confirmed_cancelled == 1
    assert reg.count_open() == 0
    assert all(p["cancel_confirmed"] for p in manifest.per_order)
    assert manifest.commit_sha.endswith("deadbeef") or "deadbeef" in manifest.commit_sha


@pytest.mark.unit
def test_cancel_confirmed_pass_with_authoritative_flat(
    resting_adapter, tmp_path: Path
) -> None:
    """Isolated PASS only with an explicit authoritative flat fixture."""
    reg = OpenOrderRegistry(ledger_path=tmp_path / "l.json")
    resting_adapter._executor.place_resting_order(
        order_id="o1", symbol="BTCUSDT", side="BUY", quantity=1.0, status="PENDING"
    )
    reg.register(internal_order_id="o1", symbol="BTCUSDT", status="PENDING", quantity=1)
    coord = _coordinator(
        reg, resting_adapter, position_resolver=_authoritative_flat_snapshot
    )
    manifest = coord.reconcile(kill_state="active", kill_reason="manual")
    assert manifest.overall_verdict == KillCancelBatchVerdict.PASS.value
    assert RC_KILL_CANCEL_PASS in manifest.reason_codes
    assert RC_RESIDUAL_POSITION_UNKNOWN not in manifest.reason_codes
    assert reg.count_open() == 0


@pytest.mark.unit
def test_position_resolver_none_empty_and_raise_hold(
    resting_adapter, tmp_path: Path
) -> None:
    def _raise() -> list:
        raise RuntimeError("position resolver boom")

    cases = (
        ("none", None),
        ("empty", lambda: []),
        ("raise", _raise),
    )
    for name, resolver in cases:
        reg_i = OpenOrderRegistry(ledger_path=tmp_path / f"l-{name}.json")
        resting_adapter._executor.place_resting_order(
            order_id="o1", symbol="BTCUSDT", side="BUY", quantity=1.0, status="PENDING"
        )
        reg_i.register(
            internal_order_id="o1", symbol="BTCUSDT", status="PENDING", quantity=1
        )
        manifest = _coordinator(
            reg_i, resting_adapter, position_resolver=resolver
        ).reconcile(kill_state="active", kill_reason="manual")
        _assert_confirmed_cancels_hold_unknown(manifest)


@pytest.mark.unit
def test_service_position_resolver_empty_is_not_flat_zero(tmp_path: Path) -> None:
    from services.execution import service

    assert service._known_residual_positions == {}
    assert service._position_resolver() == []
    reg = OpenOrderRegistry(ledger_path=tmp_path / "svc.json")
    executor = MockExecutor(
        resting_orders=True, success_rate=1.0, min_latency_ms=0, max_latency_ms=0
    )
    adapter = MockExecutionAdapter(executor=executor)
    executor.place_resting_order(
        order_id="o1", symbol="BTCUSDT", side="BUY", quantity=1.0, status="PENDING"
    )
    reg.register(internal_order_id="o1", symbol="BTCUSDT", status="PENDING", quantity=1)
    manifest = KillCancelCoordinator(
        registry=reg,
        adapter=adapter,
        commit_sha="deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        position_resolver=service._position_resolver,
    ).reconcile(kill_state="active", kill_reason="manual")
    _assert_confirmed_cancels_hold_unknown(manifest)


@pytest.mark.unit
def test_authoritative_open_snapshot_visible(resting_adapter, tmp_path: Path) -> None:
    reg = OpenOrderRegistry(ledger_path=tmp_path / "l.json")
    coord = _coordinator(
        reg, resting_adapter, position_resolver=_authoritative_open_snapshot
    )
    manifest = coord.reconcile(kill_state="active", kill_reason="manual")
    assert manifest.residual_positions[0]["status"] == "OPEN"
    assert manifest.residual_positions[0]["quantity"] == 0.01
    assert (
        manifest.residual_positions[0]["reason_code"]
        == "RESIDUAL_POSITION_VISIBLE_NO_UNWIND"
    )


@pytest.mark.unit
def test_cancel_rejected_hold(resting_adapter, tmp_path: Path) -> None:
    resting_adapter._executor.cancel_behavior = "reject"
    reg = OpenOrderRegistry(ledger_path=tmp_path / "l.json")
    resting_adapter._executor.place_resting_order(
        order_id="o1", symbol="BTCUSDT", side="BUY", quantity=1.0
    )
    reg.register(internal_order_id="o1", symbol="BTCUSDT", status="PENDING", quantity=1)
    manifest = _coordinator(reg, resting_adapter).reconcile(
        kill_state="active", kill_reason="manual"
    )
    assert manifest.overall_verdict == KillCancelBatchVerdict.HOLD.value
    assert RC_RESIDUAL_OPEN_ORDERS in manifest.reason_codes
    assert RC_CANCEL_REQUEST_REJECTED in manifest.reason_codes
    assert reg.count_open() == 1


@pytest.mark.unit
def test_cancel_exception_hold(resting_adapter, tmp_path: Path) -> None:
    resting_adapter._executor.cancel_behavior = "error"
    reg = OpenOrderRegistry(ledger_path=tmp_path / "l.json")
    resting_adapter._executor.place_resting_order(
        order_id="o1", symbol="BTCUSDT", side="BUY", quantity=1.0
    )
    reg.register(internal_order_id="o1", symbol="BTCUSDT", status="PENDING", quantity=1)
    manifest = _coordinator(reg, resting_adapter).reconcile(
        kill_state="active", kill_reason="manual"
    )
    assert manifest.overall_verdict == KillCancelBatchVerdict.HOLD.value
    assert RC_CANCEL_EXECUTION_ERROR in manifest.reason_codes
    assert reg.get("o1") is not None


@pytest.mark.unit
def test_cancel_malformed_hold(resting_adapter, tmp_path: Path) -> None:
    resting_adapter._executor.cancel_behavior = "malformed"
    reg = OpenOrderRegistry(ledger_path=tmp_path / "l.json")
    resting_adapter._executor.place_resting_order(
        order_id="o1", symbol="BTCUSDT", side="BUY", quantity=1.0
    )
    reg.register(internal_order_id="o1", symbol="BTCUSDT", status="PENDING", quantity=1)
    manifest = _coordinator(reg, resting_adapter).reconcile(
        kill_state="active", kill_reason="manual"
    )
    assert manifest.overall_verdict == KillCancelBatchVerdict.HOLD.value
    assert reg.count_open() == 1


@pytest.mark.unit
def test_cancel_accepted_unconfirmed_hold(resting_adapter, tmp_path: Path) -> None:
    resting_adapter._executor.cancel_behavior = "accepted_unconfirmed"
    reg = OpenOrderRegistry(ledger_path=tmp_path / "l.json")
    resting_adapter._executor.place_resting_order(
        order_id="o1", symbol="BTCUSDT", side="BUY", quantity=1.0
    )
    reg.register(internal_order_id="o1", symbol="BTCUSDT", status="PENDING", quantity=1)
    manifest = _coordinator(reg, resting_adapter).reconcile(
        kill_state="active", kill_reason="manual"
    )
    assert manifest.overall_verdict == KillCancelBatchVerdict.HOLD.value
    assert RC_CANCEL_CONFIRMATION_MISSING in manifest.reason_codes


@pytest.mark.unit
def test_cancel_adapter_unsupported_hold(tmp_path: Path) -> None:
    reg = OpenOrderRegistry(ledger_path=tmp_path / "l.json")
    reg.register(internal_order_id="o1", symbol="BTCUSDT", status="PENDING", quantity=1)
    adapter = MexcExecutionAdapter(executor=object())  # type: ignore[arg-type]
    # Bypass LiveExecutor init
    adapter._executor = None
    manifest = _coordinator(reg, adapter).reconcile(
        kill_state="active", kill_reason="manual"
    )
    assert manifest.overall_verdict == KillCancelBatchVerdict.HOLD.value
    assert RC_CANCEL_ADAPTER_UNSUPPORTED in manifest.reason_codes


@pytest.mark.unit
def test_mixed_batch_hold(resting_adapter, tmp_path: Path) -> None:
    resting_adapter._executor.cancel_behavior_by_id["o2"] = "reject"
    reg = OpenOrderRegistry(ledger_path=tmp_path / "l.json")
    for oid in ("o1", "o2"):
        resting_adapter._executor.place_resting_order(
            order_id=oid, symbol="BTCUSDT", side="BUY", quantity=1.0
        )
        reg.register(
            internal_order_id=oid, symbol="BTCUSDT", status="PENDING", quantity=1
        )
    manifest = _coordinator(reg, resting_adapter).reconcile(
        kill_state="active", kill_reason="manual"
    )
    assert manifest.overall_verdict == KillCancelBatchVerdict.HOLD.value
    assert reg.get("o2") is not None


@pytest.mark.unit
def test_already_terminal_idempotent(resting_adapter, tmp_path: Path) -> None:
    reg = OpenOrderRegistry(ledger_path=tmp_path / "l.json")
    resting_adapter._executor.place_resting_order(
        order_id="o1", symbol="BTCUSDT", side="BUY", quantity=1.0
    )
    reg.register(internal_order_id="o1", symbol="BTCUSDT", status="PENDING", quantity=1)
    coord = _coordinator(reg, resting_adapter)
    first = coord.reconcile(
        kill_state="active", kill_reason="manual", kill_activated_at_utc="t0"
    )
    _assert_confirmed_cancels_hold_unknown(first)
    # Re-register as if residual appeared; confirmed set should skip duplicate cancel
    resting_adapter._executor.place_resting_order(
        order_id="o1", symbol="BTCUSDT", side="BUY", quantity=1.0
    )
    reg.register(internal_order_id="o1", symbol="BTCUSDT", status="PENDING", quantity=1)
    second = coord.reconcile(
        kill_state="active", kill_reason="manual", kill_activated_at_utc="t0"
    )
    assert (
        RC_CANCEL_ALREADY_CONFIRMED in second.reason_codes
        or second.orders_already_terminal >= 1
    )
    assert second.overall_verdict == KillCancelBatchVerdict.HOLD.value


# --- Kill transitions / supervisor ---


@pytest.mark.unit
def test_supervisor_inactive_to_active_once(resting_adapter, tmp_path: Path) -> None:
    reg = OpenOrderRegistry(ledger_path=tmp_path / "l.json")
    resting_adapter._executor.place_resting_order(
        order_id="o1", symbol="BTCUSDT", side="BUY", quantity=1.0
    )
    reg.register(internal_order_id="o1", symbol="BTCUSDT", status="PENDING", quantity=1)
    coord = _coordinator(reg, resting_adapter)
    state = {"active": False, "reason": None}

    def details(*, create_if_missing=False):
        return state["active"], state["reason"], "", None

    supervisor = KillCancelSupervisor(coordinator=coord, get_kill_details=details)
    assert supervisor.run_startup_gate() is None
    assert supervisor.orders_accepted is True
    state["active"] = True
    state["reason"] = "manual"
    m1 = supervisor.poll_once()
    assert m1 is not None
    assert m1.orders_confirmed_cancelled == 1
    m2 = supervisor.poll_once()
    assert m2 is None  # repeated active does not re-fire


@pytest.mark.unit
def test_supervisor_unevaluable_fail_closed(resting_adapter, tmp_path: Path) -> None:
    reg = OpenOrderRegistry(ledger_path=tmp_path / "l.json")
    coord = _coordinator(reg, resting_adapter)

    def details(*, create_if_missing=False):
        return True, "evaluation_error", "boom", None

    supervisor = KillCancelSupervisor(coordinator=coord, get_kill_details=details)
    manifest = supervisor.run_startup_gate()
    assert manifest is not None
    assert supervisor.hold_new_orders is True


@pytest.mark.unit
def test_supervisor_deactivation_resumes_order_acceptance(
    resting_adapter, tmp_path: Path
) -> None:
    """After unevaluable/active HOLD, kill inactive must accept new orders again."""
    reg = OpenOrderRegistry(ledger_path=tmp_path / "l.json")
    coord = _coordinator(reg, resting_adapter)
    state = {"active": True, "reason": "evaluation_error"}

    def details(*, create_if_missing=False):
        return state["active"], state["reason"], "boom", None

    supervisor = KillCancelSupervisor(coordinator=coord, get_kill_details=details)
    assert supervisor.run_startup_gate() is not None
    assert supervisor.hold_new_orders is True
    # Empty book still HOLD (unknown position); hold_new_orders blocks new orders.
    assert supervisor.status_snapshot()["ready_for_new_orders"] is False
    assert supervisor.last_verdict == KillCancelBatchVerdict.HOLD.value

    state["active"] = False
    state["reason"] = None
    assert supervisor.poll_once() is None
    assert supervisor.hold_new_orders is False
    assert supervisor.orders_accepted is True
    assert supervisor.status_snapshot()["ready_for_new_orders"] is True


@pytest.mark.unit
def test_fill_after_kill_fail(resting_adapter, tmp_path: Path) -> None:
    reg = OpenOrderRegistry(ledger_path=tmp_path / "l.json")
    resting_adapter._executor.place_resting_order(
        order_id="o1", symbol="BTCUSDT", side="BUY", quantity=1.0
    )
    reg.register(internal_order_id="o1", symbol="BTCUSDT", status="PENDING", quantity=1)
    coord = _coordinator(reg, resting_adapter)
    coord.reconcile(
        kill_state="active", kill_reason="manual", kill_activated_at_utc="t0"
    )
    # Simulate late fill tracked against active kill event
    coord.note_fill_after_kill(
        internal_order_id="o1",
        venue_order_id="o1",
        symbol="BTCUSDT",
        filled_quantity=1.0,
    )
    # Re-run with same event context: inject fill list via second reconcile after note
    # note_fill_after_kill already recorded; empty open set still FAIL due to fill events
    reg2 = OpenOrderRegistry(ledger_path=tmp_path / "l2.json")
    coord2 = _coordinator(reg2, resting_adapter)
    coord2._active_kill_event_id = "kill_x"
    coord2._fill_after_kill = list(coord._fill_after_kill)
    manifest = coord2.reconcile(kill_state="active", kill_reason="manual")
    assert manifest.overall_verdict == KillCancelBatchVerdict.FAIL.value
    assert RC_FILL_AFTER_KILL_ACTIVATION in manifest.reason_codes


# --- Evidence / contract ---


@pytest.mark.unit
@pytest.mark.contract
def test_evidence_schema_and_reason_codes(resting_adapter, tmp_path: Path) -> None:
    reg = OpenOrderRegistry(ledger_path=tmp_path / "l.json")
    coord = _coordinator(reg, resting_adapter)
    manifest = coord.reconcile(kill_state="active", kill_reason="manual")
    data = manifest.to_dict()
    required = {
        "schema_version",
        "run_id",
        "commit_sha",
        "kill_event_id",
        "kill_state",
        "kill_reason",
        "kill_activated_at_utc",
        "reconciliation_started_at_utc",
        "reconciliation_completed_at_utc",
        "open_order_source",
        "open_order_source_status",
        "orders_discovered",
        "cancel_attempts",
        "orders_confirmed_cancelled",
        "orders_already_terminal",
        "orders_rejected",
        "orders_unknown",
        "residual_open_orders",
        "residual_positions",
        "fill_after_kill_events",
        "overall_verdict",
        "reason_codes",
        "limitations",
        "safety_boundaries",
    }
    assert required.issubset(data.keys())
    assert data["schema_version"] == EVIDENCE_SCHEMA_VERSION
    assert "deadbeef" in data["commit_sha"]
    blob = json.dumps(data)
    assert "api_key" not in blob.lower()
    assert "password" not in blob.lower()
    assert REQUIRED_REASON_CODES  # exported set non-empty
    assert RC_KILL_CANCEL_PASS in REQUIRED_REASON_CODES


@pytest.mark.unit
@pytest.mark.contract
def test_cancel_order_request_response_contract(resting_adapter) -> None:
    req = CancelOrderRequest(
        internal_order_id="o1",
        venue_order_id="o1",
        symbol="BTCUSDT",
        reason_code="KILL_SWITCH_CANCEL",
        kill_event_id="kill_1",
        requested_at_utc="2026-07-30T00:00:00+00:00",
    )
    resting_adapter._executor.place_resting_order(
        order_id="o1", symbol="BTCUSDT", side="BUY", quantity=1.0
    )
    resp = resting_adapter.cancel_order(req)
    assert isinstance(resp, CancelOrderResponse)
    assert resp.accepted is True
    assert resp.confirmed_cancelled is True
    assert (
        resp.accepted and resp.confirmed_cancelled
    )  # accepted != sole proof; both set
    snap = resting_adapter.get_open_order(internal_order_id="o1", venue_order_id="o1")
    assert isinstance(snap, OpenOrderSnapshot)
    assert snap.status == "CANCELLED"


@pytest.mark.unit
@pytest.mark.contract
def test_no_automatic_position_close_in_evidence(
    resting_adapter, tmp_path: Path
) -> None:
    reg = OpenOrderRegistry(ledger_path=tmp_path / "l.json")
    manifest = _coordinator(reg, resting_adapter).reconcile(
        kill_state="active", kill_reason="manual"
    )
    assert all(p.get("position_effect", "none") == "none" for p in manifest.per_order)
    assert "No automatic position close" in manifest.safety_boundaries


@pytest.mark.unit
def test_mock_stack_multiple_pending_and_restart(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    executor = MockExecutor(
        resting_orders=True, success_rate=1.0, min_latency_ms=0, max_latency_ms=0
    )
    adapter = MockExecutionAdapter(executor=executor)
    reg = OpenOrderRegistry(ledger_path=ledger)
    for i in range(3):
        oid = f"o{i}"
        executor.place_resting_order(
            order_id=oid, symbol="BTCUSDT", side="BUY", quantity=1
        )
        reg.register(
            internal_order_id=oid, symbol="BTCUSDT", status="PENDING", quantity=1
        )
    m1 = _coordinator(reg, adapter).reconcile(kill_state="active", kill_reason="manual")
    _assert_confirmed_cancels_hold_unknown(m1)
    assert m1.orders_confirmed_cancelled == 3
    # Restart reconstruction
    reg2 = OpenOrderRegistry(ledger_path=ledger)
    assert reg2.count_open() == 0
    # Inject rejection residual then restart
    executor.place_resting_order(
        order_id="r1", symbol="ETHUSDT", side="SELL", quantity=2
    )
    executor.cancel_behavior_by_id["r1"] = "reject"
    reg2.register(
        internal_order_id="r1", symbol="ETHUSDT", status="SUBMITTED", quantity=2
    )
    m2 = _coordinator(reg2, adapter).reconcile(
        kill_state="active", kill_reason="manual"
    )
    assert m2.overall_verdict == KillCancelBatchVerdict.HOLD.value
    reg3 = OpenOrderRegistry(ledger_path=ledger)
    assert reg3.count_open() == 1


@pytest.mark.unit
def test_kill_before_submission_blocks_adapter(monkeypatch, tmp_path: Path) -> None:
    from services.execution import service

    monkeypatch.setattr(service, "open_order_registry", None)
    monkeypatch.setattr(service, "kill_cancel_coordinator", None)
    monkeypatch.setattr(service, "kill_cancel_supervisor", None)
    monkeypatch.setattr(service, "open_orders", set())
    monkeypatch.setattr(service, "bot_shutdown_active", False)
    monkeypatch.setattr(service, "blocked_strategy_ids", set())
    monkeypatch.setattr(service, "blocked_bot_ids", set())
    monkeypatch.setenv("TRACE_CONTRACT_V1_ENABLED", "0")
    monkeypatch.setenv("CDB_OPEN_ORDER_LEDGER_PATH", str(tmp_path / "l.json"))

    monkeypatch.setattr(
        "core.safety.kill_switch.get_kill_switch_details",
        lambda create_if_missing=False: (True, "manual", "x", None),
    )
    executor = MockExecutionAdapter(
        executor=MockExecutor(
            resting_orders=True, success_rate=1.0, min_latency_ms=0, max_latency_ms=0
        )
    )
    monkeypatch.setattr(service, "executor", executor)
    published = []
    monkeypatch.setattr(service, "_publish_result", lambda r: published.append(r))
    monkeypatch.setattr(service, "db", None)

    result = service.process_order(
        {
            "type": "order",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 0.01,
            "run_mode": "paper",
            "timestamp": 1,
        }
    )
    assert result.status == OrderStatus.REJECTED.value
    assert not executor._executor.orders
