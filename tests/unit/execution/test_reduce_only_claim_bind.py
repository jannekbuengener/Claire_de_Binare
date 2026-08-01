"""Unit tests for prepare_reduce_only bind/resume semantics (#4261)."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from services.execution.database import Database
from services.execution.reduce_only import (
    REDUCE_ONLY_ADAPTER_BOUND,
    REDUCE_ONLY_DUPLICATE_RESULT,
    REDUCE_ONLY_NO_POSITION,
    REDUCE_ONLY_READY,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def _db_without_connect() -> Database:
    with patch.object(Database, "_test_connection", lambda self: None):
        return Database(connection_string="postgresql://unused", test_on_init=False)


def test_bind_existing_prepared_allows_single_adapter_winner() -> None:
    db = _db_without_connect()
    existing = {
        "order_id": "bind-1",
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
    bound_row = dict(existing)
    bound_row["reason_code"] = REDUCE_ONLY_ADAPTER_BOUND

    cur = MagicMock()
    # 1) SELECT existing FOR UPDATE
    # 2) UPDATE bind RETURNING
    cur.fetchone.side_effect = [existing, bound_row]
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    conn.cursor.return_value.__exit__.return_value = False

    with patch.object(db, "get_connection") as get_conn:
        get_conn.return_value.__enter__.return_value = conn
        get_conn.return_value.__exit__.return_value = False
        result = db.prepare_reduce_only(
            order_id="bind-1",
            symbol="BTCUSDT",
            side="SELL",
            requested_quantity=Decimal("1"),
            bind_for_adapter=True,
        )

    assert result["allowed"] is True
    assert result["adapter_bound"] is True
    assert result["reason_code"] == REDUCE_ONLY_READY


def test_risk_claim_mode_allows_resume_dispatch_without_binding() -> None:
    db = _db_without_connect()
    existing = {
        "order_id": "resume-1",
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
    cur = MagicMock()
    cur.fetchone.side_effect = [existing]
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    conn.cursor.return_value.__exit__.return_value = False

    with patch.object(db, "get_connection") as get_conn:
        get_conn.return_value.__enter__.return_value = conn
        get_conn.return_value.__exit__.return_value = False
        result = db.prepare_reduce_only(
            order_id="resume-1",
            symbol="BTCUSDT",
            side="SELL",
            requested_quantity=Decimal("1"),
            persist_blocked=False,
            bind_for_adapter=False,
        )

    assert result["allowed"] is True
    assert result["resume_dispatch"] is True
    assert result["reason_code"] == REDUCE_ONLY_READY
    # No UPDATE bind when risk re-enters.
    assert cur.execute.call_count == 1


def test_adapter_bound_duplicate_blocks_second_submission() -> None:
    db = _db_without_connect()
    existing = {
        "order_id": "bound-1",
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
        "reason_code": REDUCE_ONLY_ADAPTER_BOUND,
    }
    cur = MagicMock()
    cur.fetchone.side_effect = [existing]
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    conn.cursor.return_value.__exit__.return_value = False

    with patch.object(db, "get_connection") as get_conn:
        get_conn.return_value.__enter__.return_value = conn
        get_conn.return_value.__exit__.return_value = False
        result = db.prepare_reduce_only(
            order_id="bound-1",
            symbol="BTCUSDT",
            side="SELL",
            requested_quantity=Decimal("1"),
            bind_for_adapter=True,
        )

    assert result["allowed"] is False
    assert result["duplicate"] is True
    assert result["reason_code"] == REDUCE_ONLY_DUPLICATE_RESULT


def test_persist_blocked_false_skips_insert_on_no_position() -> None:
    db = _db_without_connect()
    cur = MagicMock()
    # existing=None, position rows=[], reserved=0
    cur.fetchone.side_effect = [
        None,
        {"coalesce": Decimal("0")},
    ]
    cur.fetchall.return_value = []
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    conn.cursor.return_value.__exit__.return_value = False

    with patch.object(db, "get_connection") as get_conn:
        get_conn.return_value.__enter__.return_value = conn
        get_conn.return_value.__exit__.return_value = False
        result = db.prepare_reduce_only(
            order_id="nopersist-1",
            symbol="BTCUSDT",
            side="SELL",
            requested_quantity=Decimal("1"),
            persist_blocked=False,
            bind_for_adapter=False,
        )

    assert result["allowed"] is False
    assert result["persisted"] is False
    assert result["reason_code"] == REDUCE_ONLY_NO_POSITION
    # SELECT existing, SELECT positions, SELECT reserved — no INSERT.
    assert cur.execute.call_count == 3
