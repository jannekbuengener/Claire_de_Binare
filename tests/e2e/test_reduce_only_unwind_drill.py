"""Isolated PostgreSQL-backed reduce-only drill for Issue #4184."""

from __future__ import annotations

from decimal import Decimal
import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from services.execution import service
from services.execution.database import Database
from services.execution.models import ExecutionResult, OrderStatus

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        os.getenv("CDB_4184_DRILL") != "1",
        reason="Issue #4184 isolated drill only",
    ),
]

SCENARIO_PATH = Path(
    os.environ.get("CDB_4184_SCENARIO_JSON", "/app/evidence/scenarios.json")
)
SCENARIOS: dict[str, dict] = {}


class ScriptedMockExecutor:
    """Deterministic test adapter; no production path or network."""

    supports_reduce_only = True

    def __init__(self, *, status: str, filled_quantity: Decimal) -> None:
        self.status = status
        self.filled_quantity = filled_quantity
        self.calls: list = []

    def execute_order(self, order):
        self.calls.append(order)
        return ExecutionResult(
            order_id=f"mock-{order.order_id}",
            fill_id=f"fill-{order.order_id}" if self.filled_quantity > 0 else None,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            filled_quantity=float(self.filled_quantity),
            status=self.status,
            price=50000.0 if self.filled_quantity > 0 else None,
            client_id=order.client_id,
        )


@pytest.fixture(scope="module", autouse=True)
def write_scenario_evidence():
    yield
    SCENARIO_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCENARIO_PATH.write_text(
        json.dumps(SCENARIOS, indent=2, sort_keys=True),
        encoding="utf-8",
    )


@pytest.fixture
def boundary(monkeypatch: pytest.MonkeyPatch) -> Database:
    database = Database()
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM reduce_only_executions")
            cur.execute("DELETE FROM positions")

    monkeypatch.setattr(service, "db", database)
    monkeypatch.setattr(service, "redis_client", MagicMock())
    monkeypatch.setattr(service.config, "MOCK_TRADING", True)
    monkeypatch.setenv("TRACE_CONTRACT_V1_ENABLED", "0")
    monkeypatch.setattr(service, "bot_shutdown_active", False)
    monkeypatch.setattr(service, "blocked_strategy_ids", set())
    monkeypatch.setattr(service, "blocked_bot_ids", set())
    monkeypatch.setattr(
        "core.safety.kill_switch.get_kill_switch_details",
        lambda create_if_missing=False: (False, "inactive", None, None),
    )
    return database


def _seed_position(database: Database, *, side: str, quantity: Decimal) -> None:
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO positions (
                    symbol, side, size, entry_price, current_price,
                    opened_at, updated_at
                )
                VALUES (
                    'BTCUSDT', %s, %s, 50000, 50000,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """,
                (side, quantity),
            )


def _signed_position(database: Database) -> Decimal:
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT side, size
                FROM positions
                WHERE symbol = 'BTCUSDT' AND closed_at IS NULL
                """)
            row = cur.fetchone()
    if row is None:
        return Decimal("0")
    side, size = row
    return Decimal(str(size)) if side == "long" else -Decimal(str(size))


def _order_payload(*, scenario: str, side: str, quantity: Decimal) -> dict:
    return {
        "type": "order",
        "order_id": f"4184-{scenario}",
        "client_id": f"4184-client-{scenario}",
        "decision_id": f"4184-decision-{scenario}",
        "signal_id": f"4184-signal-{scenario}",
        "strategy_id": "issue-4184-drill",
        "symbol": "BTCUSDT",
        "side": side,
        "quantity": float(quantity),
        "reduce_only": True,
        "run_mode": "paper",
    }


def _run(
    database: Database,
    *,
    scenario: str,
    position_before: Decimal,
    side: str,
    requested: Decimal,
    adapter_status: str,
    adapter_fill: Decimal,
) -> tuple[ExecutionResult, ScriptedMockExecutor]:
    executor = ScriptedMockExecutor(
        status=adapter_status,
        filled_quantity=adapter_fill,
    )
    service.executor = executor
    result = service.process_order(
        _order_payload(scenario=scenario, side=side, quantity=requested)
    )
    assert result is not None
    position_after = _signed_position(database)
    contract = result.reduce_only_contract or {}
    submitted = (
        Decimal(str(executor.calls[0].quantity)) if executor.calls else Decimal("0")
    )
    SCENARIOS[scenario] = {
        "status": "PASS",
        "before_position": str(position_before),
        "requested_exit_quantity": str(requested),
        "submitted_exit_quantity": str(submitted),
        "filled_quantity": str(result.filled_quantity),
        "after_position": str(position_after),
        "position_increase_observed": abs(position_after) > abs(position_before),
        "side_flip_observed": position_before * position_after < 0,
        "adapter_result": adapter_status if executor.calls else "NOT_CALLED",
        "reason_code": contract.get("reason_code"),
    }
    return result, executor


def test_r1_long_full_exit(boundary: Database) -> None:
    before = Decimal("1")
    _seed_position(boundary, side="long", quantity=abs(before))
    result, _executor = _run(
        boundary,
        scenario="R1_LONG_FULL_EXIT",
        position_before=before,
        side="SELL",
        requested=Decimal("1"),
        adapter_status=OrderStatus.FILLED.value,
        adapter_fill=Decimal("1"),
    )
    assert _signed_position(boundary) == 0
    assert result.reduce_only_contract["side_flip_observed"] is False


def test_r2_short_full_exit(boundary: Database) -> None:
    before = Decimal("-1")
    _seed_position(boundary, side="short", quantity=abs(before))
    _run(
        boundary,
        scenario="R2_SHORT_FULL_EXIT",
        position_before=before,
        side="BUY",
        requested=Decimal("1"),
        adapter_status=OrderStatus.FILLED.value,
        adapter_fill=Decimal("1"),
    )
    assert _signed_position(boundary) == 0


def test_r3_long_partial_fill(boundary: Database) -> None:
    before = Decimal("1")
    _seed_position(boundary, side="long", quantity=before)
    _run(
        boundary,
        scenario="R3_LONG_PARTIAL_FILL",
        position_before=before,
        side="SELL",
        requested=Decimal("1"),
        adapter_status=OrderStatus.PARTIALLY_FILLED.value,
        adapter_fill=Decimal("0.4"),
    )
    assert _signed_position(boundary) == Decimal("0.6")


def test_r4_short_partial_fill(boundary: Database) -> None:
    before = Decimal("-1")
    _seed_position(boundary, side="short", quantity=abs(before))
    _run(
        boundary,
        scenario="R4_SHORT_PARTIAL_FILL",
        position_before=before,
        side="BUY",
        requested=Decimal("1"),
        adapter_status=OrderStatus.PARTIALLY_FILLED.value,
        adapter_fill=Decimal("0.4"),
    )
    assert _signed_position(boundary) == Decimal("-0.6")


@pytest.mark.parametrize(
    ("scenario", "position_before", "position_side", "order_side"),
    [
        ("R5_OVERSIZED_LONG_EXIT", Decimal("1"), "long", "SELL"),
        ("R6_OVERSIZED_SHORT_EXIT", Decimal("-1"), "short", "BUY"),
    ],
)
def test_oversized_exit_is_clamped_without_side_flip(
    boundary: Database,
    scenario: str,
    position_before: Decimal,
    position_side: str,
    order_side: str,
) -> None:
    _seed_position(boundary, side=position_side, quantity=abs(position_before))
    _result, executor = _run(
        boundary,
        scenario=scenario,
        position_before=position_before,
        side=order_side,
        requested=Decimal("2"),
        adapter_status=OrderStatus.FILLED.value,
        adapter_fill=Decimal("1"),
    )
    assert Decimal(str(executor.calls[0].quantity)) == Decimal("1")
    assert _signed_position(boundary) == 0


def test_r7_adapter_rejection_keeps_position(boundary: Database) -> None:
    before = Decimal("1")
    _seed_position(boundary, side="long", quantity=before)
    result, _executor = _run(
        boundary,
        scenario="R7_ADAPTER_REJECTION",
        position_before=before,
        side="SELL",
        requested=Decimal("1"),
        adapter_status=OrderStatus.REJECTED.value,
        adapter_fill=Decimal("0"),
    )
    assert _signed_position(boundary) == before
    assert result.reduce_only_contract["reason_code"] == "REDUCE_ONLY_REJECTED"


def test_r8_duplicate_result_is_not_applied_twice(boundary: Database) -> None:
    before = Decimal("1")
    _seed_position(boundary, side="long", quantity=before)
    result, executor = _run(
        boundary,
        scenario="R8_DUPLICATE_RESULT",
        position_before=before,
        side="SELL",
        requested=Decimal("0.4"),
        adapter_status=OrderStatus.FILLED.value,
        adapter_fill=Decimal("0.4"),
    )
    first_after = _signed_position(boundary)
    service.db = Database()
    duplicate = service.process_order(
        _order_payload(
            scenario="R8_DUPLICATE_RESULT",
            side="SELL",
            quantity=Decimal("0.4"),
        )
    )
    assert duplicate is not None
    assert duplicate.status == OrderStatus.REJECTED.value
    assert len(executor.calls) == 1
    assert _signed_position(service.db) == first_after == Decimal("0.6")
    SCENARIOS["R8_DUPLICATE_RESULT"]["reason_code"] = duplicate.reduce_only_contract[
        "reason_code"
    ]
    assert result.reduce_only is True


def test_r9_restart_after_partial_does_not_reapply_fill(boundary: Database) -> None:
    before = Decimal("-1")
    _seed_position(boundary, side="short", quantity=abs(before))
    _result, executor = _run(
        boundary,
        scenario="R9_RESTART_AFTER_PARTIAL",
        position_before=before,
        side="BUY",
        requested=Decimal("1"),
        adapter_status=OrderStatus.PARTIALLY_FILLED.value,
        adapter_fill=Decimal("0.25"),
    )
    after_partial = _signed_position(boundary)
    service.db = Database()
    duplicate = service.process_order(
        _order_payload(
            scenario="R9_RESTART_AFTER_PARTIAL",
            side="BUY",
            quantity=Decimal("1"),
        )
    )
    assert duplicate is not None
    assert len(executor.calls) == 1
    assert _signed_position(service.db) == after_partial == Decimal("-0.75")
    SCENARIOS["R9_RESTART_AFTER_PARTIAL"]["reason_code"] = (
        duplicate.reduce_only_contract["reason_code"]
    )


def test_r10_unknown_position_blocks_adapter(boundary: Database) -> None:
    _seed_position(boundary, side="corrupt", quantity=Decimal("1"))
    executor = ScriptedMockExecutor(
        status=OrderStatus.FILLED.value,
        filled_quantity=Decimal("1"),
    )
    service.executor = executor
    result = service.process_order(
        _order_payload(
            scenario="R10_UNKNOWN_POSITION",
            side="SELL",
            quantity=Decimal("1"),
        )
    )

    with boundary.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT side, size
                FROM positions
                WHERE symbol = 'BTCUSDT' AND closed_at IS NULL
                """)
            persisted = cur.fetchone()

    assert result is not None
    assert result.status == OrderStatus.REJECTED.value
    assert executor.calls == []
    assert persisted == ("corrupt", Decimal("1.00000000"))
    assert result.reduce_only_contract["reason_code"] == "REDUCE_ONLY_POSITION_UNKNOWN"
    SCENARIOS["R10_UNKNOWN_POSITION"] = {
        "status": "PASS",
        "before_position": "UNKNOWN",
        "requested_exit_quantity": "1",
        "submitted_exit_quantity": "0",
        "filled_quantity": "0.0",
        "after_position": "UNKNOWN",
        "position_increase_observed": False,
        "side_flip_observed": False,
        "adapter_result": "NOT_CALLED",
        "reason_code": result.reduce_only_contract["reason_code"],
    }
