from __future__ import annotations

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


@pytest.fixture
def execution_harness(monkeypatch: pytest.MonkeyPatch) -> _Harness:
    original_stats = service.stats.copy()
    service.stats.clear()
    service.stats.update(
        {
            "orders_received": 0,
            "orders_filled": 0,
            "orders_rejected": 0,
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

    yield _Harness(executor=executor, publish_result=publish_result, db=db)

    service.stats.clear()
    service.stats.update(original_stats)


@pytest.mark.parametrize(
    "payload",
    [
        {"type": "order", "side": "BUY", "quantity": 1.0},  # missing symbol
        {"type": "order", "symbol": "BTCUSDT", "quantity": 1.0},  # missing side
        {"type": "order", "symbol": "BTCUSDT", "side": "BUY"},  # missing quantity
        {"type": "order", "symbol": "BTCUSDT", "side": "HOLD", "quantity": 1.0},
        {"type": "order", "symbol": "BTCUSDT", "side": "BUY", "quantity": "abc"},
        {"type": "order", "symbol": "BTCUSDT", "side": "BUY", "quantity": -1.0},
        {"type": "order", "symbol": "BTCUSDT", "side": "BUY", "quantity": float("nan")},
        {"type": "order", "symbol": "BTCUSDT", "side": "BUY", "quantity": float("inf")},
        {"type": "signal", "symbol": "BTCUSDT", "side": "BUY", "quantity": 1.0},
        {
            "type": "order",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 1.0,
            "policy_snapshot": "{not-json",
        },
        None,
        "not-a-dict",
        ["order", "BTCUSDT", "BUY", 1.0],
    ],
)
def test_invalid_payloads_are_deterministic_noops(
    payload: object,
    execution_harness: _Harness,
    caplog: pytest.LogCaptureFixture,
) -> None:
    before = service.get_stats_copy()
    caplog.set_level(logging.WARNING)

    result = service.process_order(payload)

    after = service.get_stats_copy()
    assert result is None
    assert after["invalid_payloads"] == before["invalid_payloads"] + 1
    assert after["orders_received"] == before["orders_received"]
    execution_harness.executor.execute_order.assert_not_called()
    execution_harness.publish_result.assert_not_called()
    assert execution_harness.db.mock_calls == []
    assert "Invalid order payload skipped" in caplog.text


def test_message_loop_invalid_json_is_skipped_without_processing(
    monkeypatch: pytest.MonkeyPatch,
    execution_harness: _Harness,
    caplog: pytest.LogCaptureFixture,
) -> None:
    class _OneBadMessagePubSub:
        def __init__(self) -> None:
            self.calls = 0

        def get_message(self, timeout: float = 1.0):  # noqa: ARG002
            self.calls += 1
            if self.calls == 1:
                return {"type": "message", "data": "{bad json"}
            monkeypatch.setattr(service, "running", False)
            return None

    before = service.get_stats_copy()
    process_order_mock = MagicMock()
    caplog.set_level(logging.WARNING)

    monkeypatch.setattr(service, "pubsub", _OneBadMessagePubSub())
    monkeypatch.setattr(service, "running", True)
    monkeypatch.setattr(service, "process_order", process_order_mock)

    service.message_loop()

    after = service.get_stats_copy()
    assert after["invalid_payloads"] == before["invalid_payloads"] + 1
    process_order_mock.assert_not_called()
    execution_harness.executor.execute_order.assert_not_called()
    execution_harness.publish_result.assert_not_called()
    assert "json_decode_failed" in caplog.text
