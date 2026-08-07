"""Regression: cdb_risk must not crash-loop on Redis pubsub idle socket timeouts.

Live evidence (#4382): create_redis_client defaults socket_timeout=5.0; blocking
pubsub.listen() raises redis.TimeoutError after idle, only KeyboardInterrupt is
caught in RiskManager.run(), process exits 1, Docker restarts forever.
Execution survives via pubsub.get_message(timeout=1.0) in a try/except loop.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
import redis

from services.risk.service import RiskManager


def _idle_timeout_then_stop(manager: RiskManager, raise_count: int = 2):
    """Shared timeout injector for get_message() code paths."""
    raised = {"n": 0}

    def _raise_or_stop(*_args, **_kwargs):
        if not manager.running:
            return None
        if raised["n"] < raise_count:
            raised["n"] += 1
            raise redis.TimeoutError("Timeout reading from socket")
        manager.running = False
        return None

    return _raise_or_stop


@pytest.mark.unit
def test_run_must_survive_pubsub_socket_timeout_without_process_exit():
    """Desired contract: idle socket TimeoutError must not escape run().

    Pre-fix (main): TimeoutError propagates after finally/shutdown → Exit 1.
    Post-fix: run() returns cleanly after controlled stop.
    """
    manager = RiskManager()
    manager.redis_client = None  # skip regime/allocation/shutdown stream threads
    manager.pubsub_results = None  # skip order-result thread
    manager.pubsub = MagicMock()
    manager.pubsub.get_message.side_effect = _idle_timeout_then_stop(manager)

    # Contract under test: TimeoutError must not kill the process/run().
    manager.run()
    assert manager.running is False


@pytest.mark.unit
def test_listen_order_results_must_survive_pubsub_socket_timeout():
    """Order-result listener must not die on idle socket TimeoutError."""
    manager = RiskManager()
    manager.running = True
    manager.pubsub_results = MagicMock()
    manager.pubsub_results.get_message.side_effect = _idle_timeout_then_stop(
        manager, raise_count=2
    )

    # Desired: returns without raising.
    manager.listen_order_results()
    assert manager.running is False


@pytest.mark.unit
def test_run_still_processes_valid_signal_message(monkeypatch):
    """Positive path: a real pubsub message still reaches process_signal."""
    manager = RiskManager()
    manager.redis_client = None
    manager.pubsub_results = None
    manager.pubsub = MagicMock()

    processed = {"n": 0}

    def fake_process(signal, raw_payload=None):
        processed["n"] += 1
        manager.running = False
        return None

    monkeypatch.setattr(manager, "process_signal", fake_process)

    payload = {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "strategy_id": "test",
        "strength": 0.5,
    }

    manager.pubsub.get_message = MagicMock(
        side_effect=[
            {"type": "message", "data": json.dumps(payload)},
            None,
        ]
    )

    manager.run()
    assert processed["n"] >= 1


@pytest.mark.unit
def test_regime_stream_bootstraps_latest_instead_of_full_replay():
    """Restart must not xread from 0-0 across the full regime history."""
    manager = RiskManager()
    manager.running = True
    manager.redis_client = MagicMock()
    manager.config.regime_stream = "stream.regime_signals"
    manager.redis_client.xrevrange.return_value = [
        ("99-0", {"regime": "TREND_UP"}),
    ]

    def _xread(*_args, **_kwargs):
        manager.running = False
        return []

    manager.redis_client.xread.side_effect = _xread
    manager._listen_regime_stream()

    manager.redis_client.xrevrange.assert_called_once()
    stream_arg = manager.redis_client.xread.call_args[0][0]
    assert stream_arg == {"stream.regime_signals": "99-0"}
