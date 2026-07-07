"""
Unit-Tests für Execution Service.

Governance: CDB_AGENT_POLICY.md, CDB_PSM_POLICY.md
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.execution import config, service

from tests.unit.execution._execution_boundary_contract_helpers import (
    ExecutionHarness,
    execution_harness,
    valid_order_payload,
)


@pytest.mark.unit
@pytest.mark.skipif(service.app is None, reason="Flask not installed")
def test_health_endpoint_reports_ok() -> None:
    client = service.app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["service"] == config.SERVICE_NAME
    assert payload["status"] == "ok"


@pytest.mark.unit
def test_service_stats_initialized_after_process_order(
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
    before = service.get_stats_copy()
    service.process_order(valid_order_payload(run_mode="paper"))
    after = service.get_stats_copy()
    assert after["orders_received"] == before["orders_received"] + 1


@pytest.mark.unit
def test_config_mock_trading_default_is_safe_for_ci() -> None:
    assert config.MOCK_TRADING is True or config.DRY_RUN is True


@pytest.mark.unit
def test_order_submission_calls_mock_executor_not_live(
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
    service.process_order(valid_order_payload(run_mode="paper"))
    execution_harness.executor.execute_order.assert_called_once()
