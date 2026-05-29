"""Emission wiring tests for services.risk.service."""

import sys
from unittest.mock import MagicMock

import pytest

from services.risk.service import RiskManager

# Reference to the actual module globals dict that RiskManager resolves from.
# Other tests (test_flask_import_guard) may purge the module from sys.modules,
# so monkeypatch.setattr("services.risk.service.X", ...) would patch a NEW
# module object while RiskManager still uses the OLD one.  Patching via
# _SVC_GLOBALS is immune to that because it targets the real dict directly.
_SVC_GLOBALS = RiskManager._setup_envelope_emitter.__globals__


@pytest.fixture(autouse=True)
def clear_toggle_env(monkeypatch):
    monkeypatch.delenv("CDB_ENVELOPE_EMISSION", raising=False)
    monkeypatch.delenv("LR021_ENVELOPE_EMIT_ENABLED", raising=False)
    monkeypatch.delenv("CDB_ENVELOPE_REDIS_MODE", raising=False)
    monkeypatch.delenv("CDB_ENVELOPE_REDIS_STREAM", raising=False)
    monkeypatch.delenv("CDB_ENVELOPE_REDIS_CHANNEL", raising=False)
    yield


def test_setup_envelope_emitter_off_does_not_create_client(monkeypatch):
    sys.modules.pop("core.replay.emitter", None)
    sys.modules.pop("core.replay.publisher", None)

    manager = RiskManager()
    manager.redis_client = MagicMock()
    called = False

    def fake_create(**kwargs):
        nonlocal called
        called = True
        return MagicMock()

    monkeypatch.setitem(_SVC_GLOBALS, "create_redis_client", fake_create)
    monkeypatch.setenv("CDB_ENVELOPE_EMISSION", "0")

    manager._setup_envelope_emitter()

    assert not called
    assert manager._envelope_publisher is None
    assert manager._envelope_redis_client is None
    assert "core.replay.emitter" not in sys.modules


def test_setup_envelope_emitter_on_pubsub(monkeypatch):
    manager = RiskManager()
    client = MagicMock()
    manager.redis_client = client
    monkeypatch.setenv("CDB_ENVELOPE_EMISSION", "1")
    monkeypatch.setenv("CDB_ENVELOPE_REDIS_MODE", "PuBSub")
    monkeypatch.setenv("CDB_ENVELOPE_REDIS_STREAM", "stream.envelopes")
    monkeypatch.setenv("CDB_ENVELOPE_REDIS_CHANNEL", "channel.envelopes")

    manager._setup_envelope_emitter()

    assert manager._envelope_publisher is not None
    assert manager._envelope_publisher._mode == "pubsub"

    from core.replay.emitter import emit_decision_envelope

    emit_decision_envelope(
        event_id="dec-emit",
        ts_ms=1000,
        decision="ALLOW",
        reason_code=None,
        symbol="BTCUSDT",
        evidence={"decision_id": "dec-emit"},
    )

    client.publish.assert_called_once()
    assert client.xadd.call_count == 0


def test_setup_envelope_emitter_invalid_mode_defaults_to_stream(monkeypatch):
    manager = RiskManager()
    client = MagicMock()
    manager.redis_client = client
    monkeypatch.setenv("CDB_ENVELOPE_EMISSION", "1")
    monkeypatch.setenv("CDB_ENVELOPE_REDIS_MODE", "INVALID")

    manager._setup_envelope_emitter()

    assert manager._envelope_publisher is not None
    assert manager._envelope_publisher._mode == "stream"
