"""LR-030: Shadow-mode execution gate + kill-switch gate tests.

Tests verify that:
- Orders with run_mode="shadow" are hard-blocked before any executor
- Shadow blocks produce distinct telemetry (shadow_blocked counter)
- Shadow blocks publish auditable REJECTED results
- run_mode is read from top-level payload AND fallback from nested bundle
- Kill-switch active in execution service blocks orders (defense-in-depth)
- Kill-switch evaluation errors fail closed
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from services.execution import service


@dataclass
class _Harness:
    executor: MagicMock
    publish_result: MagicMock
    db: MagicMock


def _valid_order_payload(*, run_mode=None, decision_contract_v1=None, **overrides):
    """Build a minimal valid order payload."""
    payload = {
        "type": "order",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": 0.001,
        "strategy_id": "test",
        "timestamp": 1700000000,
    }
    if run_mode is not None:
        payload["run_mode"] = run_mode
    if decision_contract_v1 is not None:
        payload["decision_contract_v1"] = decision_contract_v1
    payload.update(overrides)
    return payload


@pytest.fixture
def execution_harness(monkeypatch: pytest.MonkeyPatch) -> _Harness:
    original_stats = service.stats.copy()
    service.stats.clear()
    service.stats.update(
        {
            "orders_received": 0,
            "orders_filled": 0,
            "orders_rejected": 0,
            "shadow_blocked": 0,
            "invalid_payloads": 0,
            "start_time": original_stats["start_time"],
            "last_result": None,
        }
    )

    executor = MagicMock()
    publish_result = MagicMock()
    db = MagicMock()

    monkeypatch.setattr(service, "executor", executor)
    monkeypatch.setattr(service, "_publish_result", publish_result)
    monkeypatch.setattr(service, "db", db)
    monkeypatch.setattr(service, "bot_shutdown_active", False)
    monkeypatch.setattr(service, "blocked_strategy_ids", set())
    monkeypatch.setattr(service, "blocked_bot_ids", set())
    monkeypatch.setenv("TRACE_CONTRACT_V1_ENABLED", "0")

    # LR-030: Kill-switch default inactive for deterministic tests.
    # Override only in dedicated kill-switch tests.
    monkeypatch.setattr(
        "core.safety.kill_switch.get_kill_switch_details",
        lambda create_if_missing=False: (False, None, None, None),
    )

    yield _Harness(executor=executor, publish_result=publish_result, db=db)

    service.stats.clear()
    service.stats.update(original_stats)


# --- Shadow-mode gate tests ---


@pytest.mark.unit
def test_shadow_mode_blocks_execution(
    execution_harness: _Harness,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Order with run_mode='shadow' must be REJECTED before executor."""
    caplog.set_level(logging.WARNING)

    result = service.process_order(_valid_order_payload(run_mode="shadow"))

    assert result is not None
    assert result.status == "REJECTED"
    assert "shadow mode" in result.error_message
    execution_harness.executor.execute_order.assert_not_called()
    assert service.stats["shadow_blocked"] == 1
    assert service.stats["orders_rejected"] == 1
    assert "SHADOW-BLOCKED" in caplog.text


@pytest.mark.unit
def test_shadow_block_publishes_auditable_result(
    execution_harness: _Harness,
) -> None:
    """Shadow block must publish a REJECTED result for audit trail."""
    result = service.process_order(_valid_order_payload(run_mode="shadow"))

    assert result is not None
    execution_harness.publish_result.assert_called_once()
    published = execution_harness.publish_result.call_args[0][0]
    assert published.status == "REJECTED"
    assert "shadow" in published.error_message.lower()
    assert published.symbol == "BTCUSDT"
    assert published.filled_quantity == 0.0


@pytest.mark.unit
def test_paper_mode_not_blocked(
    execution_harness: _Harness,
) -> None:
    """Order with run_mode='paper' must NOT be blocked by shadow gate."""
    execution_harness.executor.execute_order.return_value = MagicMock(
        status="FILLED",
        filled_quantity=0.001,
        fill_id="f1",
        order_id="o1",
        symbol="BTCUSDT",
        side="BUY",
        price=50000.0,
    )

    result = service.process_order(_valid_order_payload(run_mode="paper"))

    assert result is not None
    execution_harness.executor.execute_order.assert_called_once()
    assert service.stats["shadow_blocked"] == 0


@pytest.mark.unit
def test_none_mode_not_blocked(
    execution_harness: _Harness,
) -> None:
    """Order with run_mode=None (legacy) must NOT be blocked."""
    execution_harness.executor.execute_order.return_value = MagicMock(
        status="FILLED",
        filled_quantity=0.001,
        fill_id="f1",
        order_id="o1",
        symbol="BTCUSDT",
        side="BUY",
        price=50000.0,
    )

    result = service.process_order(_valid_order_payload())  # no run_mode

    assert result is not None
    execution_harness.executor.execute_order.assert_called_once()
    assert service.stats["shadow_blocked"] == 0


@pytest.mark.unit
def test_live_mode_not_blocked(
    execution_harness: _Harness,
) -> None:
    """Order with run_mode='live' must NOT be blocked by shadow gate."""
    execution_harness.executor.execute_order.return_value = MagicMock(
        status="FILLED",
        filled_quantity=0.001,
        fill_id="f1",
        order_id="o1",
        symbol="BTCUSDT",
        side="BUY",
        price=50000.0,
    )

    result = service.process_order(_valid_order_payload(run_mode="live"))

    assert result is not None
    execution_harness.executor.execute_order.assert_called_once()
    assert service.stats["shadow_blocked"] == 0


@pytest.mark.unit
def test_shadow_gate_independent_of_mock_trading(
    execution_harness: _Harness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Shadow gate must block even when MOCK_TRADING=false (config-level)."""
    # Patch the imported config module, not the env var (resolved at import time)
    monkeypatch.setattr(service.config, "MOCK_TRADING", False)

    result = service.process_order(_valid_order_payload(run_mode="shadow"))

    assert result is not None
    assert result.status == "REJECTED"
    execution_harness.executor.execute_order.assert_not_called()
    assert service.stats["shadow_blocked"] == 1


# --- run_mode fallback from nested bundle ---


@pytest.mark.unit
def test_run_mode_fallback_from_bundle(
    execution_harness: _Harness,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """run_mode must be read from decision_contract_v1.input.run_mode when top-level is missing."""
    caplog.set_level(logging.WARNING)
    bundle = {"input": {"run_mode": "shadow", "order": {}}, "output": {}}

    # No top-level run_mode, but bundle contains it
    result = service.process_order(_valid_order_payload(decision_contract_v1=bundle))

    assert result is not None
    assert result.status == "REJECTED"
    assert service.stats["shadow_blocked"] == 1
    assert "SHADOW-BLOCKED" in caplog.text


@pytest.mark.unit
def test_run_mode_fallback_from_bundle_as_json_string(
    execution_harness: _Harness,
) -> None:
    """run_mode fallback must work when bundle arrives as JSON string from Redis."""
    bundle = {"input": {"run_mode": "shadow", "order": {}}, "output": {}}

    result = service.process_order(
        _valid_order_payload(decision_contract_v1=json.dumps(bundle))
    )

    assert result is not None
    assert result.status == "REJECTED"
    assert service.stats["shadow_blocked"] == 1


# --- Kill-switch gate tests ---


@pytest.mark.unit
def test_kill_switch_active_blocks_execution(
    execution_harness: _Harness,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Kill-switch active in execution service must block order."""
    caplog.set_level(logging.WARNING)
    monkeypatch.setattr(
        "core.safety.kill_switch.get_kill_switch_details",
        lambda create_if_missing=False: (
            True,
            "manual",
            "test kill",
            "2026-01-01T00:00:00",
        ),
    )

    result = service.process_order(_valid_order_payload(run_mode="paper"))

    assert result is not None
    assert result.status == "REJECTED"
    assert "kill-switch" in result.error_message.lower()
    execution_harness.executor.execute_order.assert_not_called()
    assert "KILL-SWITCH-BLOCKED" in caplog.text


@pytest.mark.unit
def test_kill_switch_eval_error_fails_closed(
    execution_harness: _Harness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Kill-switch evaluation error must fail closed (block order)."""

    def _raise(*args, **kwargs):
        raise RuntimeError("state file corrupt")

    monkeypatch.setattr(
        "core.safety.kill_switch.get_kill_switch_details",
        _raise,
    )

    result = service.process_order(_valid_order_payload(run_mode="paper"))

    assert result is not None
    assert result.status == "REJECTED"
    assert "kill-switch" in result.error_message.lower()
    execution_harness.executor.execute_order.assert_not_called()


@pytest.mark.unit
def test_kill_switch_inactive_passes(
    execution_harness: _Harness,
) -> None:
    """Kill-switch inactive must not block order (fixture default)."""
    execution_harness.executor.execute_order.return_value = MagicMock(
        status="FILLED",
        filled_quantity=0.001,
        fill_id="f1",
        order_id="o1",
        symbol="BTCUSDT",
        side="BUY",
        price=50000.0,
    )

    result = service.process_order(_valid_order_payload(run_mode="paper"))

    assert result is not None
    execution_harness.executor.execute_order.assert_called_once()
