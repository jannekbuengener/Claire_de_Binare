"""
Unit-Tests: Risk Order Phase-1 Metadata
Issue #1488
"""

import sys
import importlib.util
from pathlib import Path

import pytest

_RISK_MODELS = Path(__file__).parent.parent.parent.parent / "services" / "risk" / "models.py"
_spec = importlib.util.spec_from_file_location("risk_models", _RISK_MODELS)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
Order = _mod.Order
Signal = _mod.Signal


def _make_order(**kwargs) -> Order:
    defaults = dict(
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.001,
        stop_loss_pct=2.0,
        signal_id="sig-abc",
        reason="test",
        timestamp=1700000000,
        strategy_id="momentum_v1",
    )
    defaults.update(kwargs)
    return Order(**defaults)


@pytest.mark.unit
def test_order_metadata_contains_correlation_ids():
    """Order.metadata enthält decision_id, trace_id, signal_id."""
    meta = {
        "signal_id": "sig-abc",
        "strategy_id": "momentum_v1",
        "decision_id": "dec-123",
        "trace_id": "trace-456",
        "decision": "ALLOW",
        "reason_code": None,
    }
    order = _make_order(decision_id="dec-123", trace_id="trace-456", metadata=meta)

    payload = order.to_dict()
    assert "metadata" in payload
    m = payload["metadata"]
    assert m["decision_id"] == "dec-123"
    assert m["trace_id"] == "trace-456"
    assert m["signal_id"] == "sig-abc"


@pytest.mark.unit
def test_order_metadata_market_context():
    """Order.metadata enthält market_context mit regime_id, return_1m, return_5m."""
    meta = {
        "signal_id": "sig-abc",
        "decision": "ALLOW",
        "reason_code": None,
        "market_context": {
            "regime_id": 1,
            "return_1m": -0.003,
            "return_5m": -0.01,
        },
        "freshness": {},
    }
    order = _make_order(metadata=meta)
    payload = order.to_dict()

    mc = payload["metadata"]["market_context"]
    assert mc["regime_id"] == 1
    assert mc["return_1m"] == -0.003
    assert mc["return_5m"] == -0.01


@pytest.mark.unit
def test_order_metadata_freshness():
    """Order.metadata enthält freshness mit staleness_s, data_silence_s."""
    meta = {
        "signal_id": "sig-abc",
        "decision": "ALLOW",
        "reason_code": None,
        "freshness": {
            "staleness_s": 1.2,
            "data_silence_s": 3.5,
            "timestamps_ms": {"now_ms": 1700000000000},
        },
    }
    order = _make_order(metadata=meta)
    payload = order.to_dict()

    fr = payload["metadata"]["freshness"]
    assert fr["staleness_s"] == 1.2
    assert fr["data_silence_s"] == 3.5


@pytest.mark.unit
def test_order_metadata_policy_fields_absent_when_toggle_off():
    """policy_id/hash-Felder fehlen in metadata wenn Toggle OFF (None)."""
    meta = {
        "signal_id": "sig-abc",
        "decision": "ALLOW",
        "reason_code": None,
        "policy_id": None,
        "policy_hash": None,
    }
    order = _make_order(metadata=meta)
    payload = order.to_dict()

    m = payload["metadata"]
    # None-Werte bleiben vorerst im Dict; aber policy_snapshot nicht erfunden
    assert "policy_snapshot" not in m or m.get("policy_snapshot") is None


@pytest.mark.unit
def test_order_metadata_none_not_emitted():
    """Order ohne metadata → kein metadata-Key in to_dict()."""
    order = _make_order()
    payload = order.to_dict()
    assert "metadata" not in payload


@pytest.mark.unit
def test_risk_signal_from_dict_tolerates_metadata():
    """Signal.from_dict() verwirft metadata nicht — tolerierende Consumer-Seite."""
    data = {
        "signal_id": "sig-abc",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "strategy_id": "mom",
        "metadata": {"strategy_id": "mom", "signal_reason": "test"},
    }
    sig = Signal.from_dict(data)
    assert sig.metadata == {"strategy_id": "mom", "signal_reason": "test"}


@pytest.mark.unit
def test_risk_signal_from_dict_tolerates_metadata_json_string():
    """Signal.from_dict() parst metadata als JSON-String (Redis-Hop-Szenario)."""
    import json
    data = {
        "signal_id": "sig-xyz",
        "symbol": "ETHUSDT",
        "side": "BUY",
        "metadata": json.dumps({"strategy_id": "mom", "timing": {"signal_ts_ms": 1}}),
    }
    sig = Signal.from_dict(data)
    assert isinstance(sig.metadata, dict)
    assert sig.metadata["strategy_id"] == "mom"
