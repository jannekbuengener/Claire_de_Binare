"""Execution paper/live boundary contract tests (#3835)."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from services.execution import service

from tests.unit.execution._execution_boundary_contract_helpers import (
    ExecutionHarness,
    execution_harness,
    valid_order_payload,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_shadow_mode_blocks_before_executor(
    execution_harness: ExecutionHarness,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING)
    result = service.process_order(valid_order_payload(run_mode="shadow"))
    assert result is not None
    assert result.status == "REJECTED"
    assert "shadow mode" in (result.error_message or "").lower()
    execution_harness.executor.execute_order.assert_not_called()
    assert service.stats["shadow_blocked"] >= 1


def test_invalid_payloads_are_deterministic_noops(
    execution_harness: ExecutionHarness,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING)
    before = service.get_stats_copy()
    result = service.process_order({"type": "order", "side": "BUY"})
    after = service.get_stats_copy()
    assert result is None
    assert after["invalid_payloads"] == before["invalid_payloads"] + 1
    execution_harness.executor.execute_order.assert_not_called()


def test_paper_run_mode_reaches_executor_when_gates_pass(
    execution_harness: ExecutionHarness,
) -> None:
    execution_harness.executor.execute_order.return_value = MagicMock(
        status="FILLED",
        filled_quantity=0.001,
        fill_id="f1",
        order_id="o1",
        symbol="BTCUSDT",
        side="BUY",
        price=50000.0,
        error_message=None,
    )
    result = service.process_order(valid_order_payload(run_mode="paper"))
    assert result is not None
    execution_harness.executor.execute_order.assert_called_once()
