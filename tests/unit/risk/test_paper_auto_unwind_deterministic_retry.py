"""PAPER_AUTO_UNWIND deterministic order-id retry (Issue #4261).

Residual DETERMINISTIC_ORDER_ID_RETRY — Risk wiring for logical operation vs
attempt identity. Claim-before-dispatch remains mandatory.
"""

from __future__ import annotations

import copy
import threading
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from core.utils.uuid_gen import generate_uuid
from services.execution.reduce_only import (
    derive_reduce_only_attempt_order_id,
    derive_reduce_only_legacy_order_id,
)
from services.risk.service import RiskManager, risk_state, stats

pytestmark = [pytest.mark.unit]


@pytest.fixture
def _snapshot_risk_globals():
    positions_backup = copy.copy(risk_state.positions)
    last_prices_backup = copy.copy(risk_state.last_prices)
    pending_orders_backup = risk_state.pending_orders
    stats_backup = copy.copy(stats)
    yield
    risk_state.positions = positions_backup
    risk_state.last_prices = last_prices_backup
    risk_state.pending_orders = pending_orders_backup
    stats.clear()
    stats.update(stats_backup)


@pytest.fixture
def _paper_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("RUN_MODE", "paper")
    monkeypatch.delenv("TRADING_MODE", raising=False)


def _buy_fill(*, order_id: str = "parent-buy-1", qty: float = 0.01) -> MagicMock:
    result = MagicMock()
    result.status = "FILLED"
    result.side = "BUY"
    result.strategy_id = "paper"
    result.filled_quantity = qty
    result.symbol = "BTCUSDT"
    result.price = 50000.0
    result.reduce_only = False
    result.order_id = order_id
    result.bot_id = None
    return result


def _manager_with_attempt_claimer(claimer: MagicMock) -> RiskManager:
    rm = RiskManager.__new__(RiskManager)
    rm.config = MagicMock()
    rm.config.paper_auto_unwind = True
    rm.config.stop_loss_pct = 0.02
    rm.redis_client = MagicMock()
    rm._circuit_shutdown_emitted = False
    rm._reduce_only_claimer = claimer
    rm.send_order = MagicMock()
    return rm


@pytest.mark.usefixtures("_snapshot_risk_globals", "_paper_env")
def test_t1_first_attempt_dispatch_uses_attempt_order_id() -> None:
    key = "paper-auto-unwind:parent-t1"
    attempt1 = derive_reduce_only_attempt_order_id(key, 1)
    claimer = MagicMock()
    claimer.prepare_reduce_only_attempt.return_value = {
        "allowed": True,
        "duplicate": False,
        "order_id": attempt1,
        "attempt_number": 1,
        "retry_decision": "NEW_ATTEMPT",
        "status": "PREPARED",
    }
    rm = _manager_with_attempt_claimer(claimer)
    rm._maybe_auto_unwind(_buy_fill(order_id="parent-t1"))
    rm.send_order.assert_called_once()
    order = rm.send_order.call_args.args[0]
    assert order.order_id == attempt1
    assert order.decision_id == generate_uuid(name=f"{key}:decision:attempt:1")
    # Legacy bare key must not be used as the dispatch order_id anymore.
    assert order.order_id != derive_reduce_only_legacy_order_id(key)
    claimer.prepare_reduce_only_attempt.assert_called_once()
    assert (
        claimer.prepare_reduce_only_attempt.call_args.kwargs["logical_operation_key"]
        == key
    )


@pytest.mark.usefixtures("_snapshot_risk_globals", "_paper_env")
def test_t2_retry_after_rejected_dispatches_new_attempt() -> None:
    key = "paper-auto-unwind:parent-t2"
    attempt2 = derive_reduce_only_attempt_order_id(key, 2)
    claimer = MagicMock()
    claimer.prepare_reduce_only_attempt.return_value = {
        "allowed": True,
        "duplicate": False,
        "order_id": attempt2,
        "attempt_number": 2,
        "retry_decision": "NEW_ATTEMPT",
        "status": "PREPARED",
    }
    rm = _manager_with_attempt_claimer(claimer)
    rm._maybe_auto_unwind(_buy_fill(order_id="parent-t2"))
    order = rm.send_order.call_args.args[0]
    assert order.order_id == attempt2
    assert order.decision_id == generate_uuid(name=f"{key}:decision:attempt:2")


@pytest.mark.usefixtures("_snapshot_risk_globals", "_paper_env")
def test_t3_duplicate_rejected_event_single_retry_generation() -> None:
    key = "paper-auto-unwind:parent-t3"
    attempt2 = derive_reduce_only_attempt_order_id(key, 2)
    responses = iter(
        [
            {
                "allowed": True,
                "order_id": attempt2,
                "attempt_number": 2,
                "retry_decision": "NEW_ATTEMPT",
            },
            {
                "allowed": True,
                "duplicate": True,
                "resume_dispatch": True,
                "order_id": attempt2,
                "attempt_number": 2,
                "retry_decision": "RESUME_ACTIVE",
            },
        ]
    )
    claimer = MagicMock()
    claimer.prepare_reduce_only_attempt.side_effect = lambda **_k: next(responses)
    rm = _manager_with_attempt_claimer(claimer)
    fill = _buy_fill(order_id="parent-t3")
    # First retry wins; second delivery resumes same attempt — still one logical
    # generation. Dispatch count may be 2 only if resume is allowed; claim race
    # tests own "at most one" via claim outcome. Here both allowed → both may
    # dispatch same attempt id (execution bind is the adapter fence).
    rm._maybe_auto_unwind(fill)
    rm._maybe_auto_unwind(fill)
    order_ids = [c.args[0].order_id for c in rm.send_order.call_args_list]
    assert order_ids
    assert set(order_ids) == {attempt2}


@pytest.mark.usefixtures("_snapshot_risk_globals", "_paper_env")
def test_t4_parallel_retry_handlers_one_winner_via_claim_outcome() -> None:
    lock = threading.Lock()
    winners = {"count": 0}
    key = "paper-auto-unwind:parent-t4"
    attempt2 = derive_reduce_only_attempt_order_id(key, 2)

    def attempt(**_kwargs) -> dict:
        with lock:
            if winners["count"] == 0:
                winners["count"] = 1
                return {
                    "allowed": True,
                    "order_id": attempt2,
                    "attempt_number": 2,
                    "retry_decision": "NEW_ATTEMPT",
                }
            return {
                "allowed": False,
                "duplicate": True,
                "order_id": attempt2,
                "attempt_number": 2,
                "retry_decision": "BLOCKED_SUCCESS",
                "reason_code": "REDUCE_ONLY_DUPLICATE_RESULT",
                "status": "PREPARED",
            }

    claimer = MagicMock()
    claimer.prepare_reduce_only_attempt.side_effect = attempt
    rm = _manager_with_attempt_claimer(claimer)
    fill = _buy_fill(order_id="parent-t4")
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            barrier.wait(timeout=2)
            rm._maybe_auto_unwind(fill)
        except BaseException as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)
    assert not errors
    assert rm.send_order.call_count == 1
    assert rm.send_order.call_args.args[0].order_id == attempt2


@pytest.mark.usefixtures("_snapshot_risk_globals", "_paper_env")
def test_t5_active_prepared_maps_to_dispatch_or_block_without_new_id() -> None:
    key = "paper-auto-unwind:parent-t5"
    attempt1 = derive_reduce_only_attempt_order_id(key, 1)
    claimer = MagicMock()
    claimer.prepare_reduce_only_attempt.return_value = {
        "allowed": True,
        "duplicate": True,
        "resume_dispatch": True,
        "order_id": attempt1,
        "attempt_number": 1,
        "retry_decision": "RESUME_ACTIVE",
    }
    rm = _manager_with_attempt_claimer(claimer)
    rm._maybe_auto_unwind(_buy_fill(order_id="parent-t5"))
    assert rm.send_order.call_count == 1
    assert rm.send_order.call_args.args[0].order_id == attempt1


@pytest.mark.usefixtures("_snapshot_risk_globals", "_paper_env")
def test_t6_success_blocks_retry() -> None:
    claimer = MagicMock()
    claimer.prepare_reduce_only_attempt.return_value = {
        "allowed": False,
        "duplicate": True,
        "status": "FILLED",
        "reason_code": "REDUCE_ONLY_DUPLICATE_RESULT",
        "retry_decision": "BLOCKED_SUCCESS",
        "attempt_number": 1,
        "order_id": "filled-1",
    }
    rm = _manager_with_attempt_claimer(claimer)
    rm._maybe_auto_unwind(_buy_fill(order_id="parent-t6"))
    rm.send_order.assert_not_called()


@pytest.mark.usefixtures("_snapshot_risk_globals", "_paper_env")
def test_t7_non_retryable_rejected_blocks() -> None:
    claimer = MagicMock()
    claimer.prepare_reduce_only_attempt.return_value = {
        "allowed": False,
        "duplicate": True,
        "status": "REJECTED",
        "reason_code": "REDUCE_ONLY_DUPLICATE_RESULT",
        "retry_decision": "BLOCKED_NON_RETRYABLE",
        "attempt_number": 1,
        "order_id": "bad-reject",
    }
    rm = _manager_with_attempt_claimer(claimer)
    rm._maybe_auto_unwind(_buy_fill(order_id="parent-t7"))
    rm.send_order.assert_not_called()


@pytest.mark.usefixtures("_snapshot_risk_globals", "_paper_env")
def test_t10_claim_before_dispatch_still_required() -> None:
    claimer = MagicMock()
    claimer.prepare_reduce_only_attempt.return_value = {
        "allowed": False,
        "duplicate": False,
        "reason_code": "REDUCE_ONLY_POSITION_UNKNOWN",
        "persisted": False,
    }
    rm = _manager_with_attempt_claimer(claimer)
    rm._maybe_auto_unwind(_buy_fill(order_id="parent-t10"))
    rm.send_order.assert_not_called()
    claimer.prepare_reduce_only_attempt.assert_called_once()
    assert (
        claimer.prepare_reduce_only_attempt.call_args.kwargs["bind_for_adapter"]
        is False
    )
    assert (
        claimer.prepare_reduce_only_attempt.call_args.kwargs["persist_blocked"] is False
    )


@pytest.mark.usefixtures("_snapshot_risk_globals", "_paper_env")
def test_t11_unknown_position_no_dispatch() -> None:
    claimer = MagicMock()
    claimer.prepare_reduce_only_attempt.return_value = {
        "allowed": False,
        "duplicate": False,
        "reason_code": "REDUCE_ONLY_POSITION_UNKNOWN",
    }
    rm = _manager_with_attempt_claimer(claimer)
    claim = rm._acquire_paper_unwind_claim(
        logical_operation_key="paper-auto-unwind:parent-t11",
        symbol="BTCUSDT",
        side="SELL",
        quantity=Decimal("0.01"),
    )
    assert claim["outcome"] == RiskManager.PAPER_UNWIND_POSITION_UNKNOWN
