"""Shared helpers for execution boundary contract tests (#3835)."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from services.execution import service


@dataclass
class ExecutionHarness:
    executor: MagicMock
    publish_result: MagicMock
    db: MagicMock


@pytest.fixture
def execution_harness(monkeypatch: pytest.MonkeyPatch) -> ExecutionHarness:
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
    executor.execute = None
    executor.supports_reduce_only = True
    publish_result = MagicMock()
    db = MagicMock()

    monkeypatch.setattr(service, "executor", executor)
    monkeypatch.setattr(service, "_publish_result", publish_result)
    monkeypatch.setattr(service, "db", db)
    monkeypatch.setattr(service, "bot_shutdown_active", False)
    monkeypatch.setattr(service, "blocked_strategy_ids", set())
    monkeypatch.setattr(service, "blocked_bot_ids", set())
    monkeypatch.setenv("TRACE_CONTRACT_V1_ENABLED", "0")
    monkeypatch.setattr(
        "core.safety.kill_switch.get_kill_switch_details",
        lambda create_if_missing=False: (False, "inactive", None, None),
    )

    yield ExecutionHarness(executor=executor, publish_result=publish_result, db=db)

    service.stats.clear()
    service.stats.update(original_stats)


def valid_order_payload(**overrides) -> dict:
    payload = {
        "type": "order",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": 0.001,
        "strategy_id": "test",
        "timestamp": 1700000000,
    }
    payload.update(overrides)
    return payload
