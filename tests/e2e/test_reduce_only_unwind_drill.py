"""Isolated PostgreSQL-backed reduce-only drill for Issue #4184."""

from __future__ import annotations

from decimal import Decimal
import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import psycopg2

from core.contracts.external_adapter_registry import MockExecutionAdapter
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
            cur.execute("""
                DELETE FROM trades
                WHERE metadata->'reduce_only'->>'position_update_owner'
                    = 'execution_reduce_only_v1'
                """)

    _configure_boundary(monkeypatch, database)
    return database


@pytest.fixture
def restart_boundary(monkeypatch: pytest.MonkeyPatch) -> Database:
    database = Database()
    _configure_boundary(monkeypatch, database)
    return database


def _configure_boundary(monkeypatch: pytest.MonkeyPatch, database: Database) -> None:
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
    underlying = ScriptedMockExecutor(
        status=adapter_status,
        filled_quantity=adapter_fill,
    )
    service.executor = MockExecutionAdapter(executor=underlying)
    result = service.process_order(
        _order_payload(scenario=scenario, side=side, quantity=requested)
    )
    assert result is not None
    position_after = _signed_position(database)
    contract = result.reduce_only_contract or {}
    published = json.loads(service.redis_client.publish.call_args.args[1])
    if adapter_status == OrderStatus.PARTIALLY_FILLED.value:
        assert published["status"] == OrderStatus.PARTIALLY_FILLED.value
        assert published.get("fill_id")
    submitted = (
        Decimal(str(underlying.calls[0].quantity)) if underlying.calls else Decimal("0")
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
        "adapter_result": adapter_status if underlying.calls else "NOT_CALLED",
        "reason_code": contract.get("reason_code"),
        "prepare_reason_code": contract.get("prepare_reason_code"),
        "serialized_status": published.get("status"),
        "serialized_fill_id": published.get("fill_id"),
    }
    return result, underlying


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
    duplicate = boundary.finalize_reduce_only(
        order_id="4184-R8_DUPLICATE_RESULT",
        status=OrderStatus.FILLED.value,
        filled_quantity=Decimal("0.4"),
        fill_price=Decimal("50000"),
    )
    assert duplicate["duplicate"] is True
    assert duplicate["reason_code"] == "REDUCE_ONLY_DUPLICATE_RESULT"
    assert len(executor.calls) == 1
    assert _signed_position(boundary) == first_after == Decimal("0.6")
    SCENARIOS["R8_DUPLICATE_RESULT"]["reason_code"] = duplicate["reason_code"]
    assert result.reduce_only is True


def test_r9_prepare_partial_before_restart(boundary: Database) -> None:
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
    assert len(executor.calls) == 1
    assert after_partial == Decimal("-0.75")
    SCENARIOS["R9_RESTART_AFTER_PARTIAL"]["status"] = "SETUP_PASS"


def test_r9_restart_after_partial_does_not_reapply_fill(
    restart_boundary: Database,
) -> None:
    underlying = ScriptedMockExecutor(
        status=OrderStatus.PARTIALLY_FILLED.value,
        filled_quantity=Decimal("0.25"),
    )
    service.executor = MockExecutionAdapter(executor=underlying)
    duplicate = service.process_order(
        _order_payload(
            scenario="R9_RESTART_AFTER_PARTIAL",
            side="BUY",
            quantity=Decimal("1"),
        )
    )
    assert duplicate is not None
    assert underlying.calls == []
    assert _signed_position(restart_boundary) == Decimal("-0.75")
    with restart_boundary.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT position_before, requested_quantity, submitted_quantity,
                       filled_quantity, position_after, status
                FROM reduce_only_executions
                WHERE order_id = '4184-R9_RESTART_AFTER_PARTIAL'
                """)
            persisted = cur.fetchone()
    SCENARIOS["R9_RESTART_AFTER_PARTIAL"] = {
        "status": "PASS",
        "before_position": str(persisted[0]),
        "requested_exit_quantity": str(persisted[1]),
        "submitted_exit_quantity": str(persisted[2]),
        "filled_quantity": str(persisted[3]),
        "after_position": str(persisted[4]),
        "position_increase_observed": False,
        "side_flip_observed": False,
        "adapter_result": persisted[5],
        "reason_code": duplicate.reduce_only_contract["reason_code"],
        "restart_adapter_result": "NOT_CALLED",
        "restart_filled_quantity": "0",
        "restart_reason_code": duplicate.reduce_only_contract["reason_code"],
    }


def test_r10_unknown_position_blocks_adapter(boundary: Database) -> None:
    _seed_position(boundary, side="long", quantity=Decimal("NaN"))
    underlying = ScriptedMockExecutor(
        status=OrderStatus.FILLED.value,
        filled_quantity=Decimal("1"),
    )
    service.executor = MockExecutionAdapter(executor=underlying)
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
    assert underlying.calls == []
    assert persisted[0] == "long"
    assert Decimal(str(persisted[1])).is_nan()
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


@pytest.mark.parametrize(
    ("position_side", "order_side", "fill_price", "expected_pnl"),
    [
        ("long", "SELL", Decimal("51000"), Decimal("400")),
        ("short", "BUY", Decimal("49000"), Decimal("400")),
    ],
)
def test_reduce_only_finalize_updates_price_and_realized_pnl_atomically(
    boundary: Database,
    position_side: str,
    order_side: str,
    fill_price: Decimal,
    expected_pnl: Decimal,
) -> None:
    _seed_position(boundary, side=position_side, quantity=Decimal("1"))
    order_id = f"4184-accounting-{position_side}"
    prepared = boundary.prepare_reduce_only(
        order_id=order_id,
        symbol="BTCUSDT",
        side=order_side,
        requested_quantity=Decimal("0.4"),
    )
    assert prepared["allowed"] is True
    finalized = boundary.finalize_reduce_only(
        order_id=order_id,
        status=OrderStatus.FILLED.value,
        filled_quantity=Decimal("0.4"),
        fill_price=fill_price,
    )
    with boundary.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT size, current_price, realized_pnl
                FROM positions
                WHERE symbol = 'BTCUSDT' AND closed_at IS NULL
                """)
            persisted = cur.fetchone()
    assert persisted == (Decimal("0.60000000"), fill_price, expected_pnl)
    assert finalized["fill_price"] == fill_price
    assert finalized["realized_pnl_delta"] == expected_pnl


def test_position_change_between_prepare_and_finalize_blocks_apply(
    boundary: Database,
) -> None:
    _seed_position(boundary, side="long", quantity=Decimal("1"))
    prepared = boundary.prepare_reduce_only(
        order_id="4184-interleaving",
        symbol="BTCUSDT",
        side="SELL",
        requested_quantity=Decimal("0.2"),
    )
    assert prepared["allowed"] is True
    with boundary.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE positions SET size = 0.8
                WHERE symbol = 'BTCUSDT' AND closed_at IS NULL
                """)
    finalized = boundary.finalize_reduce_only(
        order_id="4184-interleaving",
        status=OrderStatus.FILLED.value,
        filled_quantity=Decimal("0.2"),
        fill_price=Decimal("50000"),
    )
    assert finalized["applied"] is False
    assert finalized["filled_quantity"] == Decimal("0")
    assert finalized["adapter_reported_filled_quantity"] == Decimal("0.2")
    assert finalized["reason_code"] == "REDUCE_ONLY_POSITION_INCREASE_BLOCKED"
    assert _signed_position(boundary) == Decimal("0.8")


def test_concurrent_prepared_claim_is_blocked_before_adapter(
    boundary: Database,
) -> None:
    _seed_position(boundary, side="long", quantity=Decimal("1"))
    first = boundary.prepare_reduce_only(
        order_id="4184-concurrent-first",
        symbol="BTCUSDT",
        side="SELL",
        requested_quantity=Decimal("0.4"),
    )
    second = boundary.prepare_reduce_only(
        order_id="4184-concurrent-second",
        symbol="BTCUSDT",
        side="SELL",
        requested_quantity=Decimal("0.4"),
    )
    assert first["allowed"] is True
    assert second["allowed"] is False
    assert second["submitted_quantity"] == Decimal("0")
    assert second["reason_code"] == "REDUCE_ONLY_CONCURRENT_CLAIM_BLOCKED"
    boundary.finalize_reduce_only(
        order_id="4184-concurrent-first",
        status=OrderStatus.FILLED.value,
        filled_quantity=Decimal("0.4"),
        fill_price=Decimal("50000"),
    )
    assert _signed_position(boundary) == Decimal("0.6")


def test_adapter_overfill_is_failed_and_never_applied(boundary: Database) -> None:
    _seed_position(boundary, side="long", quantity=Decimal("1"))
    result, underlying = _run(
        boundary,
        scenario="OVERFILL_NEGATIVE_CONTROL",
        position_before=Decimal("1"),
        side="SELL",
        requested=Decimal("1"),
        adapter_status=OrderStatus.FILLED.value,
        adapter_fill=Decimal("2"),
    )
    SCENARIOS.pop("OVERFILL_NEGATIVE_CONTROL")
    assert len(underlying.calls) == 1
    assert result.status == OrderStatus.FAILED.value
    assert result.filled_quantity == 0
    assert result.fill_id is None
    assert _signed_position(boundary) == Decimal("1")
    with boundary.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT status, reason_code, filled_quantity
                FROM reduce_only_executions
                WHERE order_id = '4184-OVERFILL_NEGATIVE_CONTROL'
                """)
            persisted = cur.fetchone()
    assert persisted == (
        "BLOCKED",
        "REDUCE_ONLY_POSITION_INCREASE_BLOCKED",
        Decimal("0E-8"),
    )


def test_missing_accounting_state_blocks_before_adapter(boundary: Database) -> None:
    with boundary.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO positions (
                    symbol, side, size, entry_price, current_price,
                    opened_at, updated_at
                )
                VALUES (
                    'BTCUSDT', 'long', 1, NULL, 50000,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """)
    underlying = ScriptedMockExecutor(
        status=OrderStatus.FILLED.value,
        filled_quantity=Decimal("1"),
    )
    service.executor = MockExecutionAdapter(executor=underlying)
    result = service.process_order(
        _order_payload(
            scenario="UNKNOWN_ACCOUNTING",
            side="SELL",
            quantity=Decimal("1"),
        )
    )
    assert result is not None
    assert result.status == OrderStatus.REJECTED.value
    assert result.reduce_only_contract["reason_code"] == "REDUCE_ONLY_POSITION_UNKNOWN"
    assert underlying.calls == []


def test_db_writer_verifies_ledger_pnl_and_deduplicates_trade(
    boundary: Database,
) -> None:
    from services.db_writer.db_writer import DatabaseWriter

    _seed_position(boundary, side="long", quantity=Decimal("1"))
    result, _underlying = _run(
        boundary,
        scenario="DB_WRITER_NEGATIVE_CONTROL",
        position_before=Decimal("1"),
        side="SELL",
        requested=Decimal("0.4"),
        adapter_status=OrderStatus.FILLED.value,
        adapter_fill=Decimal("0.4"),
    )
    SCENARIOS.pop("DB_WRITER_NEGATIVE_CONTROL")
    writer = DatabaseWriter()
    writer.db_conn = psycopg2.connect(boundary.connection_string)
    writer.db_conn.autocommit = True
    try:
        payload = result.to_dict()
        writer.process_trade_event(payload)
        writer.process_trade_event(payload)
        with boundary.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*), MIN(realized_pnl)
                    FROM trades
                    WHERE metadata->>'order_id'
                        = '4184-DB_WRITER_NEGATIVE_CONTROL'
                    """)
                persisted = cur.fetchone()
        assert persisted == (1, Decimal("0E-8"))
        assert _signed_position(boundary) == Decimal("0.6")
    finally:
        writer.db_conn.close()


def test_ambiguous_open_position_rows_fail_closed(boundary: Database) -> None:
    constraint_name = None
    try:
        with boundary.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT conname
                    FROM pg_constraint
                    WHERE conrelid = 'positions'::regclass
                      AND contype = 'u'
                    """)
                row = cur.fetchone()
                constraint_name = row[0] if row else None
                if constraint_name:
                    cur.execute(
                        f'ALTER TABLE positions DROP CONSTRAINT "{constraint_name}"'
                    )
                cur.execute("""
                    INSERT INTO positions (
                        symbol, side, size, entry_price, current_price,
                        opened_at, updated_at
                    )
                    VALUES
                        ('BTCUSDT', 'long', 1, 50000, 50000,
                         CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                        ('BTCUSDT', 'long', 1, 50000, 50000,
                         CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """)
        prepared = boundary.prepare_reduce_only(
            order_id="4184-ambiguous-position",
            symbol="BTCUSDT",
            side="SELL",
            requested_quantity=Decimal("1"),
        )
        assert prepared["allowed"] is False
        assert prepared["reason_code"] == "REDUCE_ONLY_POSITION_UNKNOWN"
    finally:
        with boundary.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM positions WHERE symbol = 'BTCUSDT'")
                if constraint_name:
                    cur.execute(
                        f'ALTER TABLE positions ADD CONSTRAINT "{constraint_name}" '
                        "UNIQUE (symbol)"
                    )
