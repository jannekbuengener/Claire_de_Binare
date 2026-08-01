"""Deterministic reduce-only attempt retry identity (Issue #4261).

Residual DETERMINISTIC_ORDER_ID_RETRY: a terminal retryable REJECTED attempt
must not permanently block the next durable attempt, while duplicates and
active/success states remain fail-closed.
"""

from __future__ import annotations

import threading
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from services.execution.database import Database
from services.execution.reduce_only import (
    REDUCE_ONLY_ADAPTER_BOUND,
    REDUCE_ONLY_DUPLICATE_RESULT,
    REDUCE_ONLY_POSITION_INCREASE_BLOCKED,
    REDUCE_ONLY_READY,
    REDUCE_ONLY_REJECTED,
    derive_reduce_only_attempt_order_id,
    derive_reduce_only_legacy_order_id,
    is_retryable_reduce_only_terminal,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def _db_without_connect() -> Database:
    with patch.object(Database, "_test_connection", lambda self: None):
        return Database(connection_string="postgresql://unused", test_on_init=False)


def _rejected_row(*, order_id: str, filled: str = "0") -> dict:
    return {
        "order_id": order_id,
        "symbol": "BTCUSDT",
        "side": "SELL",
        "position_before": Decimal("1"),
        "requested_quantity": Decimal("1"),
        "submitted_quantity": Decimal("1"),
        "filled_quantity": Decimal(filled),
        "fill_price": None,
        "realized_pnl_delta": None,
        "position_after": Decimal("1"),
        "status": "REJECTED",
        "reason_code": REDUCE_ONLY_REJECTED,
    }


def test_retryable_terminal_policy_is_explicit() -> None:
    assert is_retryable_reduce_only_terminal(
        status="REJECTED",
        reason_code=REDUCE_ONLY_REJECTED,
        filled_quantity=0,
    )
    assert not is_retryable_reduce_only_terminal(
        status="REJECTED",
        reason_code=REDUCE_ONLY_REJECTED,
        filled_quantity=Decimal("0.01"),
    )
    assert not is_retryable_reduce_only_terminal(
        status="PREPARED",
        reason_code=REDUCE_ONLY_READY,
        filled_quantity=0,
    )
    assert not is_retryable_reduce_only_terminal(
        status="FILLED",
        reason_code="REDUCE_ONLY_FILLED",
        filled_quantity=Decimal("1"),
    )
    assert not is_retryable_reduce_only_terminal(
        status="REJECTED",
        reason_code=REDUCE_ONLY_POSITION_INCREASE_BLOCKED,
        filled_quantity=0,
    )


def test_attempt_order_ids_are_deterministic_and_distinct() -> None:
    key = "paper-auto-unwind:parent-buy-1"
    a1 = derive_reduce_only_attempt_order_id(key, 1)
    a2 = derive_reduce_only_attempt_order_id(key, 2)
    legacy = derive_reduce_only_legacy_order_id(key)
    assert a1 == derive_reduce_only_attempt_order_id(key, 1)
    assert a1 != a2
    assert a1 != legacy


def test_legacy_same_order_id_after_rejected_is_duplicate_blocked() -> None:
    """Root-cause regression: identical order_id after REJECTED cannot re-prepare."""
    db = _db_without_connect()
    order_id = derive_reduce_only_legacy_order_id("paper-auto-unwind:block-1")
    existing = _rejected_row(order_id=order_id)
    cur = MagicMock()
    cur.fetchone.side_effect = [existing]
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    conn.cursor.return_value.__exit__.return_value = False
    with patch.object(db, "get_connection") as get_conn:
        get_conn.return_value.__enter__.return_value = conn
        get_conn.return_value.__exit__.return_value = False
        result = db.prepare_reduce_only(
            order_id=order_id,
            symbol="BTCUSDT",
            side="SELL",
            requested_quantity=Decimal("1"),
            persist_blocked=False,
            bind_for_adapter=False,
        )
    assert result["allowed"] is False
    assert result["duplicate"] is True
    assert result["reason_code"] == REDUCE_ONLY_DUPLICATE_RESULT


def test_t2_retryable_rejected_creates_next_attempt() -> None:
    """T2: terminal retryable REJECTED → new attempt identity may prepare once."""
    db = _db_without_connect()
    key = "paper-auto-unwind:retry-parent"
    attempt1 = derive_reduce_only_attempt_order_id(key, 1)
    attempt2 = derive_reduce_only_attempt_order_id(key, 2)
    rejected = _rejected_row(order_id=attempt1)
    prepared = {
        "order_id": attempt2,
        "symbol": "BTCUSDT",
        "side": "SELL",
        "position_before": Decimal("1"),
        "requested_quantity": Decimal("1"),
        "submitted_quantity": Decimal("1"),
        "filled_quantity": Decimal("0"),
        "fill_price": None,
        "realized_pnl_delta": None,
        "position_after": Decimal("1"),
        "status": "PREPARED",
        "reason_code": REDUCE_ONLY_READY,
    }

    scan_cur = MagicMock()
    # attempt1 row, attempt2 missing
    scan_cur.fetchone.side_effect = [rejected, None]
    scan_conn = MagicMock()
    scan_conn.cursor.return_value.__enter__.return_value = scan_cur
    scan_conn.cursor.return_value.__exit__.return_value = False

    with (
        patch.object(db, "get_connection") as get_conn,
        patch.object(
            db,
            "prepare_reduce_only",
            return_value=dict(prepared, allowed=True, duplicate=False),
        ) as prepare,
    ):
        get_conn.return_value.__enter__.return_value = scan_conn
        get_conn.return_value.__exit__.return_value = False
        result = db.prepare_reduce_only_attempt(
            logical_operation_key=key,
            symbol="BTCUSDT",
            side="SELL",
            requested_quantity=Decimal("1"),
            persist_blocked=False,
            bind_for_adapter=False,
        )

    prepare.assert_called_once()
    assert prepare.call_args.kwargs["order_id"] == attempt2
    assert result["allowed"] is True
    assert result["attempt_number"] == 2
    assert result["retry_decision"] == "NEW_ATTEMPT"
    assert result["order_id"] == attempt2


def test_t5_prepared_blocks_new_generation() -> None:
    """T5: PREPARED/active attempt resumes — no independent next generation."""
    db = _db_without_connect()
    key = "paper-auto-unwind:active-parent"
    attempt1 = derive_reduce_only_attempt_order_id(key, 1)
    active = {
        "order_id": attempt1,
        "symbol": "BTCUSDT",
        "side": "SELL",
        "position_before": Decimal("1"),
        "requested_quantity": Decimal("1"),
        "submitted_quantity": Decimal("1"),
        "filled_quantity": Decimal("0"),
        "status": "PREPARED",
        "reason_code": REDUCE_ONLY_ADAPTER_BOUND,
    }
    scan_cur = MagicMock()
    scan_cur.fetchone.side_effect = [active]
    scan_conn = MagicMock()
    scan_conn.cursor.return_value.__enter__.return_value = scan_cur
    scan_conn.cursor.return_value.__exit__.return_value = False
    resume_payload = {
        "allowed": True,
        "duplicate": True,
        "resume_dispatch": True,
        "order_id": attempt1,
        "status": "PREPARED",
        "reason_code": REDUCE_ONLY_ADAPTER_BOUND,
    }
    with (
        patch.object(db, "get_connection") as get_conn,
        patch.object(db, "prepare_reduce_only", return_value=resume_payload) as prepare,
    ):
        get_conn.return_value.__enter__.return_value = scan_conn
        get_conn.return_value.__exit__.return_value = False
        result = db.prepare_reduce_only_attempt(
            logical_operation_key=key,
            symbol="BTCUSDT",
            side="SELL",
            requested_quantity=Decimal("1"),
            persist_blocked=False,
            bind_for_adapter=False,
        )
    prepare.assert_called_once_with(
        order_id=attempt1,
        symbol="BTCUSDT",
        side="SELL",
        requested_quantity=Decimal("1"),
        persist_blocked=False,
        bind_for_adapter=False,
    )
    assert result["retry_decision"] == "RESUME_ACTIVE"
    assert result["attempt_number"] == 1


def test_t6_filled_never_retries() -> None:
    db = _db_without_connect()
    key = "paper-auto-unwind:filled-parent"
    attempt1 = derive_reduce_only_attempt_order_id(key, 1)
    filled = {
        "order_id": attempt1,
        "symbol": "BTCUSDT",
        "side": "SELL",
        "position_before": Decimal("1"),
        "requested_quantity": Decimal("1"),
        "submitted_quantity": Decimal("1"),
        "filled_quantity": Decimal("1"),
        "status": "FILLED",
        "reason_code": "REDUCE_ONLY_FILLED",
    }
    scan_cur = MagicMock()
    scan_cur.fetchone.side_effect = [filled]
    scan_conn = MagicMock()
    scan_conn.cursor.return_value.__enter__.return_value = scan_cur
    scan_conn.cursor.return_value.__exit__.return_value = False
    with (
        patch.object(db, "get_connection") as get_conn,
        patch.object(db, "prepare_reduce_only") as prepare,
    ):
        get_conn.return_value.__enter__.return_value = scan_conn
        get_conn.return_value.__exit__.return_value = False
        result = db.prepare_reduce_only_attempt(
            logical_operation_key=key,
            symbol="BTCUSDT",
            side="SELL",
            requested_quantity=Decimal("1"),
            persist_blocked=False,
            bind_for_adapter=False,
        )
    prepare.assert_not_called()
    assert result["allowed"] is False
    assert result["retry_decision"] == "BLOCKED_SUCCESS"


def test_t7_rejected_with_unclear_effect_is_blocked() -> None:
    """T7: REJECTED with non-zero filled quantity → not retryable."""
    db = _db_without_connect()
    key = "paper-auto-unwind:unclear-parent"
    attempt1 = derive_reduce_only_attempt_order_id(key, 1)
    unclear = _rejected_row(order_id=attempt1, filled="0.25")
    scan_cur = MagicMock()
    scan_cur.fetchone.side_effect = [unclear]
    scan_conn = MagicMock()
    scan_conn.cursor.return_value.__enter__.return_value = scan_cur
    scan_conn.cursor.return_value.__exit__.return_value = False
    with (
        patch.object(db, "get_connection") as get_conn,
        patch.object(db, "prepare_reduce_only") as prepare,
    ):
        get_conn.return_value.__enter__.return_value = scan_conn
        get_conn.return_value.__exit__.return_value = False
        result = db.prepare_reduce_only_attempt(
            logical_operation_key=key,
            symbol="BTCUSDT",
            side="SELL",
            requested_quantity=Decimal("1"),
            persist_blocked=False,
            bind_for_adapter=False,
        )
    prepare.assert_not_called()
    assert result["allowed"] is False
    assert result["retry_decision"] == "BLOCKED_NON_RETRYABLE"


def test_t4_parallel_retry_create_collapses_to_one_attempt() -> None:
    """T4: concurrent retry creators target the same next attempt order_id."""
    db = _db_without_connect()
    key = "paper-auto-unwind:race-parent"
    attempt1 = derive_reduce_only_attempt_order_id(key, 1)
    attempt2 = derive_reduce_only_attempt_order_id(key, 2)
    rejected = _rejected_row(order_id=attempt1)
    barrier = threading.Barrier(2)
    seen_order_ids: list[str] = []
    lock = threading.Lock()

    def fake_prepare_reduce_only(**kwargs):
        barrier.wait(timeout=2)
        with lock:
            seen_order_ids.append(kwargs["order_id"])
        return {
            "allowed": True,
            "duplicate": len(seen_order_ids) > 1,
            "order_id": kwargs["order_id"],
            "status": "PREPARED",
            "reason_code": REDUCE_ONLY_READY,
        }

    def fake_get_connection():
        scan_cur = MagicMock()
        scan_cur.fetchone.side_effect = [rejected, None]
        scan_conn = MagicMock()
        scan_conn.cursor.return_value.__enter__.return_value = scan_cur
        scan_conn.cursor.return_value.__exit__.return_value = False
        ctx = MagicMock()
        ctx.__enter__.return_value = scan_conn
        ctx.__exit__.return_value = False
        return ctx

    results: list[dict] = []
    errors: list[BaseException] = []

    with (
        patch.object(db, "get_connection", side_effect=fake_get_connection),
        patch.object(db, "prepare_reduce_only", side_effect=fake_prepare_reduce_only),
    ):

        def worker() -> None:
            try:
                results.append(
                    db.prepare_reduce_only_attempt(
                        logical_operation_key=key,
                        symbol="BTCUSDT",
                        side="SELL",
                        requested_quantity=Decimal("1"),
                        persist_blocked=False,
                        bind_for_adapter=False,
                    )
                )
            except BaseException as exc:  # pragma: no cover
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

    assert not errors
    assert len(results) == 2
    assert seen_order_ids == [attempt2, attempt2]
    assert {r["attempt_number"] for r in results} == {2}
