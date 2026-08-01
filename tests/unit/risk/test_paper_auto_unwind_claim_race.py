"""PAPER_AUTO_UNWIND claim-before-dispatch race guards (Issue #4261).

Test-first contract for residual PAPER_AUTO_UNWIND_CLAIM_RACE:
claim must be won before Redis dispatch; duplicates/parallel handlers
yield at most one dispatch; persistence failures are fail-closed.
"""

from __future__ import annotations

import copy
import logging
import threading
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

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


def _claim(
    outcome: str,
    *,
    order_id: str | None = "attempt-oid-1",
    attempt_number: int | None = 1,
    retry_decision: str | None = "NEW_ATTEMPT",
) -> dict:
    if outcome != RiskManager.PAPER_UNWIND_DISPATCH_ALLOWED:
        return {
            "outcome": outcome,
            "order_id": None,
            "attempt_number": None,
            "retry_decision": retry_decision,
        }
    return {
        "outcome": outcome,
        "order_id": order_id,
        "attempt_number": attempt_number,
        "retry_decision": retry_decision,
    }


def _make_manager(*, claim_side_effect=None, claim_return=None) -> RiskManager:
    rm = RiskManager.__new__(RiskManager)
    rm.config = MagicMock()
    rm.config.paper_auto_unwind = True
    rm.config.stop_loss_pct = 0.02
    rm.redis_client = MagicMock()
    rm._circuit_shutdown_emitted = False
    rm._reduce_only_claimer = MagicMock()
    if claim_side_effect is not None:
        rm._acquire_paper_unwind_claim = MagicMock(side_effect=claim_side_effect)
    elif claim_return is not None:
        rm._acquire_paper_unwind_claim = MagicMock(return_value=claim_return)
    rm.send_order = MagicMock()
    return rm


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


@pytest.mark.usefixtures("_snapshot_risk_globals", "_paper_env")
def test_t1_no_dispatch_when_persistence_missing() -> None:
    """T1: in-memory fill visible but durable claim/persistence missing → no dispatch."""
    rm = _make_manager(
        claim_return=_claim(RiskManager.PAPER_UNWIND_PERSISTENCE_UNAVAILABLE)
    )
    rm._maybe_auto_unwind(_buy_fill())
    rm.send_order.assert_not_called()


@pytest.mark.usefixtures("_snapshot_risk_globals", "_paper_env")
def test_t2_claim_failure_is_fail_closed(caplog: pytest.LogCaptureFixture) -> None:
    """T2: claim/read failure → fail-closed, no dispatch, observable block reason."""
    caplog.set_level(logging.WARNING)
    rm = _make_manager(claim_return=_claim(RiskManager.PAPER_UNWIND_CLAIM_NOT_ACQUIRED))
    rm._maybe_auto_unwind(_buy_fill())
    rm.send_order.assert_not_called()
    assert "PAPER_AUTO_UNWIND blocked before dispatch" in caplog.text
    assert RiskManager.PAPER_UNWIND_CLAIM_NOT_ACQUIRED in caplog.text


@pytest.mark.usefixtures("_snapshot_risk_globals", "_paper_env")
def test_t3_duplicate_fill_at_most_one_dispatch() -> None:
    """T3: same fill delivered twice → at most one successful claim/dispatch."""
    outcomes = iter(
        [
            _claim(RiskManager.PAPER_UNWIND_DISPATCH_ALLOWED),
            _claim(RiskManager.PAPER_UNWIND_CLAIM_ALREADY_EXISTS),
        ]
    )
    rm = _make_manager(claim_side_effect=lambda **_kwargs: next(outcomes))
    fill = _buy_fill(order_id="dup-fill-1")
    rm._maybe_auto_unwind(fill)
    rm._maybe_auto_unwind(fill)
    assert rm.send_order.call_count == 1


@pytest.mark.usefixtures("_snapshot_risk_globals", "_paper_env")
def test_t4_parallel_handlers_single_winner() -> None:
    """T4: two handlers race from a synchronized start → exactly one dispatch."""
    lock = threading.Lock()
    winners = {"count": 0}

    def claim(**_kwargs) -> dict:
        with lock:
            if winners["count"] == 0:
                winners["count"] = 1
                return _claim(RiskManager.PAPER_UNWIND_DISPATCH_ALLOWED)
            return _claim(RiskManager.PAPER_UNWIND_CLAIM_ALREADY_EXISTS)

    rm = _make_manager(claim_side_effect=claim)
    fill = _buy_fill(order_id="parallel-fill-1")
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            barrier.wait(timeout=2)
            rm._maybe_auto_unwind(fill)
        except BaseException as exc:  # pragma: no cover - surface in assert
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)
    assert not errors
    assert rm.send_order.call_count == 1


@pytest.mark.usefixtures("_snapshot_risk_globals", "_paper_env")
def test_t5_reentry_prepared_claim_no_second_independent_unwind() -> None:
    """T5: re-entry with existing claim continues or blocks — never two unwinds."""
    # First call wins claim+dispatch; re-entry with CLAIM_ALREADY_EXISTS blocks.
    outcomes = iter(
        [
            _claim(RiskManager.PAPER_UNWIND_DISPATCH_ALLOWED),
            _claim(RiskManager.PAPER_UNWIND_CLAIM_ALREADY_EXISTS),
        ]
    )
    rm = _make_manager(claim_side_effect=lambda **_kwargs: next(outcomes))
    fill = _buy_fill(order_id="reentry-1")
    rm._maybe_auto_unwind(fill)
    rm._maybe_auto_unwind(fill)
    assert rm.send_order.call_count == 1


@pytest.mark.usefixtures("_snapshot_risk_globals", "_paper_env")
def test_t5b_resume_dispatch_allowed_for_unbound_prepared() -> None:
    """T5 variant: unbound PREPARED may resume a single dispatch (crash heal)."""
    rm = _make_manager(
        claim_return=_claim(
            RiskManager.PAPER_UNWIND_DISPATCH_ALLOWED,
            retry_decision="RESUME_ACTIVE",
        )
    )
    rm._maybe_auto_unwind(_buy_fill(order_id="resume-1"))
    assert rm.send_order.call_count == 1


@pytest.mark.usefixtures("_snapshot_risk_globals", "_paper_env")
def test_t6_position_unknown_blocks_optimistic_qty() -> None:
    """T6: unknown/inconsistent position → POSITION_UNKNOWN, no dispatch."""
    rm = _make_manager(claim_return=_claim(RiskManager.PAPER_UNWIND_POSITION_UNKNOWN))
    rm._maybe_auto_unwind(_buy_fill())
    rm.send_order.assert_not_called()
    rm._acquire_paper_unwind_claim.assert_called_once()


@pytest.mark.usefixtures("_snapshot_risk_globals", "_paper_env")
def test_t7_happy_path_single_dispatch() -> None:
    """T7: durable claim won → exactly one dispatch."""
    rm = _make_manager(
        claim_return=_claim(
            RiskManager.PAPER_UNWIND_DISPATCH_ALLOWED,
            order_id="happy-attempt-1",
            attempt_number=1,
        )
    )
    rm._maybe_auto_unwind(_buy_fill(order_id="happy-1", qty=0.02))
    rm.send_order.assert_called_once()
    order = rm.send_order.call_args.args[0]
    assert order.side == "SELL"
    assert order.reduce_only is True
    assert order.quantity == 0.02
    assert order.order_id == "happy-attempt-1"
    assert order.decision_id is not None


@pytest.mark.usefixtures("_snapshot_risk_globals", "_paper_env")
def test_t8_proactive_duplicate_completion_idempotent() -> None:
    """T8: repeated proactive trigger after claim exists does not re-dispatch."""
    outcomes = iter(
        [
            _claim(RiskManager.PAPER_UNWIND_DISPATCH_ALLOWED),
            _claim(RiskManager.PAPER_UNWIND_CLAIM_ALREADY_EXISTS),
        ]
    )
    rm = _make_manager(claim_side_effect=lambda **_kwargs: next(outcomes))
    risk_state.positions = {"BTCUSDT": 0.01}
    risk_state.last_prices = {"BTCUSDT": 50000.0}
    risk_state.pending_orders = 0
    rm._trigger_proactive_unwind()
    rm._trigger_proactive_unwind()
    assert rm.send_order.call_count == 1


@pytest.mark.usefixtures("_snapshot_risk_globals", "_paper_env")
def test_acquire_maps_duplicate_prepare_to_claim_already_exists() -> None:
    """Unit seam: attempt prepare duplicate → CLAIM_ALREADY_EXISTS (no dispatch)."""
    rm = RiskManager.__new__(RiskManager)
    rm.config = MagicMock()
    claimer = MagicMock()
    claimer.prepare_reduce_only_attempt.return_value = {
        "allowed": False,
        "duplicate": True,
        "reason_code": "REDUCE_ONLY_DUPLICATE_RESULT",
        "status": "FILLED",
        "retry_decision": "BLOCKED_SUCCESS",
        "order_id": "oid-1",
        "attempt_number": 1,
    }
    rm._reduce_only_claimer = claimer
    claim = rm._acquire_paper_unwind_claim(
        logical_operation_key="paper-auto-unwind:parent-1",
        symbol="BTCUSDT",
        side="SELL",
        quantity=Decimal("0.01"),
    )
    assert claim["outcome"] == RiskManager.PAPER_UNWIND_CLAIM_ALREADY_EXISTS
    claimer.prepare_reduce_only_attempt.assert_called_once_with(
        logical_operation_key="paper-auto-unwind:parent-1",
        symbol="BTCUSDT",
        side="SELL",
        requested_quantity=Decimal("0.01"),
        persist_blocked=False,
        bind_for_adapter=False,
    )


@pytest.mark.usefixtures("_snapshot_risk_globals", "_paper_env")
def test_acquire_maps_position_unknown() -> None:
    rm = RiskManager.__new__(RiskManager)
    rm.config = MagicMock()
    claimer = MagicMock()
    claimer.prepare_reduce_only_attempt.return_value = {
        "allowed": False,
        "duplicate": False,
        "reason_code": "REDUCE_ONLY_POSITION_UNKNOWN",
        "persisted": False,
    }
    rm._reduce_only_claimer = claimer
    claim = rm._acquire_paper_unwind_claim(
        logical_operation_key="paper-auto-unwind:parent-2",
        symbol="BTCUSDT",
        side="SELL",
        quantity=0.01,
    )
    assert claim["outcome"] == RiskManager.PAPER_UNWIND_POSITION_UNKNOWN


@pytest.mark.usefixtures("_snapshot_risk_globals", "_paper_env")
def test_acquire_exception_is_persistence_unavailable() -> None:
    rm = RiskManager.__new__(RiskManager)
    rm.config = MagicMock()
    claimer = MagicMock()
    claimer.prepare_reduce_only_attempt.side_effect = RuntimeError("db down")
    rm._reduce_only_claimer = claimer
    claim = rm._acquire_paper_unwind_claim(
        logical_operation_key="paper-auto-unwind:parent-3",
        symbol="BTCUSDT",
        side="SELL",
        quantity=0.01,
    )
    assert claim["outcome"] == RiskManager.PAPER_UNWIND_PERSISTENCE_UNAVAILABLE
