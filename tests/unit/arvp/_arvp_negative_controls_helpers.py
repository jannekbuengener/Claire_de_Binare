"""Shared helpers for ARVP runtime negative-controls contract tests (#3829)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

from core.utils.trace_toggle import allow_evidence_debt
from services.execution import service as execution_service

from tests.unit.execution._execution_boundary_contract_helpers import (
    ExecutionHarness,
    valid_order_payload,
)


@dataclass(frozen=True)
class NegativeControlOutcome:
    name: str
    executor_called: bool
    db_write_attempted: bool
    blocked: bool


def run_invalid_execution_payload(execution_harness: ExecutionHarness) -> NegativeControlOutcome:
    result = execution_service.process_order({"type": "order", "side": "BUY"})
    insert_calls = [
        call
        for call in execution_harness.db.cursor.return_value.__enter__.return_value.execute.call_args_list
        if call.args and "INSERT" in str(call.args[0]).upper()
    ]
    return NegativeControlOutcome(
        name="invalid_execution_payload",
        executor_called=execution_harness.executor.execute_order.called,
        db_write_attempted=bool(insert_calls),
        blocked=result is None,
    )


def run_kill_switch_active_block(execution_harness: ExecutionHarness, monkeypatch) -> NegativeControlOutcome:
    monkeypatch.setattr(
        "core.safety.kill_switch.get_kill_switch_details",
        lambda create_if_missing=False: (True, "active", None, None),
    )
    result = execution_service.process_order(valid_order_payload(run_mode="paper"))
    return NegativeControlOutcome(
        name="kill_switch_active",
        executor_called=execution_harness.executor.execute_order.called,
        db_write_attempted=False,
        blocked=result is not None and result.status == "REJECTED",
    )


def run_missing_decision_id_block(
    execution_harness: ExecutionHarness, monkeypatch
) -> NegativeControlOutcome:
    monkeypatch.setenv("TRACE_CONTRACT_V1_ENABLED", "1")
    result = execution_service.process_order(valid_order_payload(run_mode="paper"))
    return NegativeControlOutcome(
        name="missing_decision_id",
        executor_called=execution_harness.executor.execute_order.called,
        db_write_attempted=False,
        blocked=result is not None and result.status == "REJECTED",
    )


def run_evidence_debt_invalid_ledger_event(
    mock_connect, mock_db_config, monkeypatch
) -> tuple[bool, bool]:
    from services.execution.database import Database

    monkeypatch.delenv("ALLOW_EVIDENCE_DEBT", raising=False)
    db, mock_cur = _ledger_db(mock_connect, mock_db_config)
    raised = False
    try:
        db.persist_correlation_event(
            signal_id="sig-1",
            decision_id="dec-1",
            event_type="BLOCK",
            symbol="BTCUSDT",
            timestamp_ms=1_700_000_000_000,
        )
    except ValueError:
        raised = True
    insert_calls = [
        call
        for call in mock_cur.execute.call_args_list
        if call.args and "INSERT INTO correlation_ledger" in str(call.args[0])
    ]
    return raised, bool(insert_calls)


def run_evidence_debt_on_skips_write(
    mock_connect, mock_db_config, monkeypatch
) -> tuple[bool, bool]:
    from services.execution.database import Database

    monkeypatch.setenv("ALLOW_EVIDENCE_DEBT", "1")
    db, mock_cur = _ledger_db(mock_connect, mock_db_config)
    assert allow_evidence_debt() is True
    ok = db.persist_correlation_event(
        signal_id="sig-1",
        decision_id="dec-1",
        event_type="BLOCK",
        symbol="BTCUSDT",
        timestamp_ms=1_700_000_000_000,
    )
    insert_calls = [
        call
        for call in mock_cur.execute.call_args_list
        if call.args and "INSERT INTO correlation_ledger" in str(call.args[0])
    ]
    return ok is False, bool(insert_calls)


def _ledger_db(mock_connect, mock_db_config):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn
    mock_cur = mock_conn.cursor.return_value.__enter__.return_value
    from services.execution.database import Database

    return Database(), mock_cur


def invalid_signal_payload() -> dict[str, Any]:
    return {"symbol": "BTCUSDT"}
