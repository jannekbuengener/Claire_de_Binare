"""Execution-boundary enforcement tests for Issue #4184."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from services.execution import service
from services.execution.models import Order
from services.execution.reduce_only import (
    REDUCE_ONLY_DUPLICATE_RESULT,
    REDUCE_ONLY_POSITION_INCREASE_BLOCKED,
    REDUCE_ONLY_POSITION_UNKNOWN,
    REDUCE_ONLY_QUANTITY_CLAMPED,
)
from tests.unit.execution._execution_boundary_contract_helpers import (
    ExecutionHarness,
    execution_harness,
    valid_order_payload,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def _filled_result(quantity: float) -> MagicMock:
    return MagicMock(
        status="FILLED",
        filled_quantity=quantity,
        fill_id="fill-4184",
        order_id="mock-4184",
        symbol="BTCUSDT",
        side="SELL",
        price=50000.0,
        error_message=None,
    )


def test_reduce_only_clamps_before_executor_and_finalizes_position(
    execution_harness: ExecutionHarness,
) -> None:
    execution_harness.db.prepare_reduce_only.return_value = {
        "allowed": True,
        "duplicate": False,
        "position_before": Decimal("1"),
        "requested_quantity": Decimal("2"),
        "submitted_quantity": Decimal("1"),
        "reason_code": REDUCE_ONLY_QUANTITY_CLAMPED,
    }
    execution_harness.db.finalize_reduce_only.return_value = {
        "applied": True,
        "duplicate": False,
        "position_after": Decimal("0"),
        "remaining_position_quantity": Decimal("0"),
        "reason_code": "REDUCE_ONLY_FILLED",
    }
    execution_harness.executor.execute_order.return_value = _filled_result(1.0)

    result = service.process_order(
        valid_order_payload(
            order_id="reduce-4184",
            decision_id="decision-4184",
            side="SELL",
            quantity=2.0,
            reduce_only=True,
            run_mode="paper",
        )
    )

    submitted = execution_harness.executor.execute_order.call_args.args[0]
    assert submitted.quantity == 1.0
    assert submitted.reduce_only is True
    execution_harness.db.finalize_reduce_only.assert_called_once()
    assert result is not None
    assert result.metadata["reduce_only"]["position_before"] == "1"
    assert result.metadata["reduce_only"]["position_after"] == "0"
    assert (
        result.metadata["reduce_only"]["prepare_reason_code"]
        == REDUCE_ONLY_QUANTITY_CLAMPED
    )
    assert execution_harness.db.finalize_reduce_only.call_args.kwargs[
        "fill_price"
    ] == Decimal("50000.0")


def test_blocked_adapter_overfill_is_not_published_as_fill(
    execution_harness: ExecutionHarness,
) -> None:
    execution_harness.db.prepare_reduce_only.return_value = {
        "allowed": True,
        "duplicate": False,
        "position_before": Decimal("1"),
        "requested_quantity": Decimal("1"),
        "submitted_quantity": Decimal("1"),
        "reason_code": "REDUCE_ONLY_READY",
    }
    execution_harness.db.finalize_reduce_only.return_value = {
        "applied": False,
        "duplicate": False,
        "filled_quantity": Decimal("0"),
        "adapter_reported_filled_quantity": Decimal("2"),
        "position_after": Decimal("1"),
        "remaining_position_quantity": Decimal("1"),
        "reason_code": REDUCE_ONLY_POSITION_INCREASE_BLOCKED,
    }
    execution_harness.executor.execute_order.return_value = _filled_result(2.0)

    result = service.process_order(
        valid_order_payload(
            order_id="reduce-overfill-4184",
            decision_id="decision-overfill-4184",
            side="SELL",
            quantity=1.0,
            reduce_only=True,
            run_mode="paper",
        )
    )

    assert result is not None
    assert result.status == "FAILED"
    assert result.filled_quantity == 0
    assert result.fill_id is None
    assert result.metadata["reduce_only"]["adapter_reported_filled_quantity"] == "2"
    assert (
        result.metadata["reduce_only"]["reason_code"]
        == REDUCE_ONLY_POSITION_INCREASE_BLOCKED
    )


def test_unknown_position_blocks_before_executor(
    execution_harness: ExecutionHarness,
) -> None:
    execution_harness.db.prepare_reduce_only.return_value = {
        "allowed": False,
        "duplicate": False,
        "position_before": None,
        "requested_quantity": Decimal("1"),
        "submitted_quantity": Decimal("0"),
        "reason_code": REDUCE_ONLY_POSITION_UNKNOWN,
    }

    result = service.process_order(
        valid_order_payload(
            order_id="reduce-unknown-4184",
            decision_id="decision-unknown-4184",
            side="SELL",
            quantity=1.0,
            reduce_only=True,
            run_mode="paper",
        )
    )

    assert result is not None
    assert result.status == "REJECTED"
    assert result.metadata["reduce_only"]["reason_code"] == REDUCE_ONLY_POSITION_UNKNOWN
    execution_harness.executor.execute_order.assert_not_called()


def test_reduce_only_is_blocked_outside_mock_trading(
    execution_harness: ExecutionHarness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service.config, "MOCK_TRADING", False)

    result = service.process_order(
        valid_order_payload(
            order_id="reduce-live-blocked-4184",
            decision_id="decision-live-blocked-4184",
            side="SELL",
            quantity=1.0,
            reduce_only=True,
            run_mode="paper",
        )
    )

    assert result is not None
    assert result.status == "REJECTED"
    assert result.metadata["reduce_only"]["reason_code"] == "REDUCE_ONLY_REJECTED"
    execution_harness.db.prepare_reduce_only.assert_not_called()
    execution_harness.executor.execute_order.assert_not_called()


def test_adapter_without_explicit_reduce_only_capability_is_blocked(
    execution_harness: ExecutionHarness,
) -> None:
    execution_harness.executor.supports_reduce_only = False

    result = service.process_order(
        valid_order_payload(
            order_id="reduce-adapter-blocked-4184",
            decision_id="decision-adapter-blocked-4184",
            side="SELL",
            quantity=1.0,
            reduce_only=True,
            run_mode="paper",
        )
    )

    assert result is not None
    assert result.status == "REJECTED"
    assert result.metadata["reduce_only"]["reason_code"] == "REDUCE_ONLY_REJECTED"
    execution_harness.db.prepare_reduce_only.assert_not_called()
    execution_harness.executor.execute_order.assert_not_called()


def test_persisted_duplicate_blocks_before_executor_after_restart(
    execution_harness: ExecutionHarness,
) -> None:
    execution_harness.db.prepare_reduce_only.return_value = {
        "allowed": False,
        "duplicate": True,
        "position_before": Decimal("1"),
        "position_after": Decimal("0.6"),
        "requested_quantity": Decimal("0.4"),
        "submitted_quantity": Decimal("0.4"),
        "reason_code": REDUCE_ONLY_DUPLICATE_RESULT,
    }

    result = service.process_order(
        valid_order_payload(
            order_id="reduce-duplicate-4184",
            decision_id="decision-duplicate-4184",
            side="SELL",
            quantity=0.4,
            reduce_only=True,
            run_mode="paper",
        )
    )

    assert result is not None
    assert result.status == "REJECTED"
    assert result.metadata["reduce_only"]["reason_code"] == REDUCE_ONLY_DUPLICATE_RESULT
    execution_harness.executor.execute_order.assert_not_called()


def test_normal_entry_order_remains_unchanged(
    execution_harness: ExecutionHarness,
) -> None:
    execution_harness.executor.execute_order.return_value = _filled_result(0.1)

    service.process_order(
        valid_order_payload(
            order_id="entry-4184",
            decision_id="decision-entry-4184",
            quantity=0.1,
            reduce_only=False,
            run_mode="paper",
        )
    )

    execution_harness.db.prepare_reduce_only.assert_not_called()
    execution_harness.db.finalize_reduce_only.assert_not_called()
    execution_harness.executor.execute_order.assert_called_once()


def test_reduce_only_parser_rejects_non_boolean_contract_value() -> None:
    with pytest.raises(ValueError, match="reduce_only must be a boolean"):
        Order.from_event(
            valid_order_payload(
                reduce_only="true",
            )
        )
