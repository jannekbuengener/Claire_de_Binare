"""Regression: cdb_risk must not crash-loop on Redis pubsub idle socket timeouts.

Live evidence (#4382): create_redis_client defaults socket_timeout=5.0; blocking
pubsub.listen() raises redis.TimeoutError after idle, only KeyboardInterrupt is
caught in RiskManager.run(), process exits 1, Docker restarts forever.
Execution survives via pubsub.get_message(timeout=1.0) in a try/except loop.

Also covers fail-closed regime bootstrap and ConnectionError resubscribe.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
import redis

import services.risk.service as risk_service
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


@pytest.fixture(autouse=True)
def _reset_regime_globals():
    """Keep module regime posture isolated across tests."""
    previous = (risk_service.current_regime, risk_service.risk_off_active)
    risk_service.current_regime = "UNKNOWN"
    risk_service.risk_off_active = False
    yield
    risk_service.current_regime, risk_service.risk_off_active = previous


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
    assert risk_service.current_regime == "TREND_UP"
    assert risk_service.risk_off_active is False


@pytest.mark.unit
def test_regime_bootstrap_xrevrange_failure_is_fail_closed():
    """Bootstrap failure must assert risk_off, not continue as risk-on."""
    manager = RiskManager()
    manager.running = True
    manager.redis_client = MagicMock()
    manager.config.regime_stream = "stream.regime_signals"
    manager.redis_client.xrevrange.side_effect = redis.ConnectionError(
        "xrevrange unavailable"
    )

    def _xread(*_args, **_kwargs):
        manager.running = False
        return []

    manager.redis_client.xread.side_effect = _xread
    risk_service.risk_off_active = False
    risk_service.current_regime = "TREND_UP"

    manager._listen_regime_stream()

    assert risk_service.risk_off_active is True
    assert risk_service.current_regime == "UNKNOWN"
    stream_arg = manager.redis_client.xread.call_args[0][0]
    assert stream_arg == {"stream.regime_signals": "$"}


@pytest.mark.unit
def test_regime_bootstrap_empty_stream_is_fail_closed():
    """Empty regime stream at start is unknown state → risk_off."""
    manager = RiskManager()
    manager.running = True
    manager.redis_client = MagicMock()
    manager.config.regime_stream = "stream.regime_signals"
    manager.redis_client.xrevrange.return_value = []

    def _xread(*_args, **_kwargs):
        manager.running = False
        return []

    manager.redis_client.xread.side_effect = _xread
    risk_service.risk_off_active = False

    manager._listen_regime_stream()

    assert risk_service.risk_off_active is True
    assert risk_service.current_regime == "UNKNOWN"


@pytest.mark.unit
def test_regime_bootstrap_high_vol_chaotic_keeps_risk_off():
    """Proven HIGH_VOL_CHAOTIC at bootstrap must keep risk_off asserted."""
    manager = RiskManager()
    manager.running = True
    manager.redis_client = MagicMock()
    manager.config.regime_stream = "stream.regime_signals"
    manager.redis_client.xrevrange.return_value = [
        ("42-0", {"regime": "HIGH_VOL_CHAOTIC"}),
    ]

    def _xread(*_args, **_kwargs):
        manager.running = False
        return []

    manager.redis_client.xread.side_effect = _xread
    manager._listen_regime_stream()

    assert risk_service.current_regime == "HIGH_VOL_CHAOTIC"
    assert risk_service.risk_off_active is True


@pytest.mark.unit
def test_run_connection_error_resubscribes_without_process_exit():
    """ConnectionError on signal pubsub must resubscribe and not Exit 1."""
    manager = RiskManager()
    manager.redis_client = MagicMock()
    manager.pubsub_results = None
    manager.pubsub = MagicMock()
    manager.config.input_topic = "signals"

    replacement = MagicMock()
    manager.redis_client.pubsub.return_value = replacement

    calls = {"n": 0}

    def _get_message(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise redis.ConnectionError("connection dropped")
        manager.running = False
        return None

    manager.pubsub.get_message.side_effect = _get_message
    replacement.get_message.side_effect = _get_message

    # Avoid background stream threads racing the test.
    manager._regime_thread = MagicMock(is_alive=MagicMock(return_value=True))
    manager._allocation_thread = MagicMock(is_alive=MagicMock(return_value=True))
    manager._shutdown_thread = MagicMock(is_alive=MagicMock(return_value=True))

    manager.run()

    assert manager.running is False
    manager.redis_client.pubsub.assert_called()
    replacement.subscribe.assert_called_with("signals")
    assert manager.pubsub is replacement


@pytest.mark.unit
def test_order_results_connection_error_resubscribes_without_exit():
    """ConnectionError on order-results pubsub must resubscribe and continue."""
    manager = RiskManager()
    manager.running = True
    manager.redis_client = MagicMock()
    manager.pubsub_results = MagicMock()
    manager.config.input_topic_order_results = "order_results"

    replacement = MagicMock()
    manager.redis_client.pubsub.return_value = replacement

    calls = {"n": 0}

    def _get_message(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise redis.ConnectionError("order-results connection dropped")
        manager.running = False
        return None

    manager.pubsub_results.get_message.side_effect = _get_message
    replacement.get_message.side_effect = _get_message

    manager.listen_order_results()

    manager.redis_client.pubsub.assert_called()
    replacement.subscribe.assert_called_with("order_results")
    assert manager.pubsub_results is replacement


@pytest.mark.unit
def test_signal_resubscribe_failure_stays_alive_without_raising(monkeypatch):
    """Failed resubscribe must not crash run(); loop retries while running."""
    monkeypatch.setattr(risk_service.time, "sleep", lambda *_args, **_kwargs: None)

    manager = RiskManager()
    manager.redis_client = MagicMock()
    manager.pubsub_results = None
    manager.pubsub = MagicMock()
    manager.redis_client.pubsub.side_effect = redis.ConnectionError("still down")

    calls = {"n": 0}

    def _get_message(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] <= 2:
            raise redis.ConnectionError("connection dropped")
        manager.running = False
        return None

    manager.pubsub.get_message.side_effect = _get_message
    manager._regime_thread = MagicMock(is_alive=MagicMock(return_value=True))
    manager._allocation_thread = MagicMock(is_alive=MagicMock(return_value=True))
    manager._shutdown_thread = MagicMock(is_alive=MagicMock(return_value=True))

    manager.run()
    assert manager.running is False
    assert calls["n"] >= 2
