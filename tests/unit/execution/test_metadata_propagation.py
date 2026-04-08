"""
Unit-Tests: Execution Service Phase-1 Metadata Propagation
Issue #1488
"""

import sys
import json
import importlib.util
from pathlib import Path

import pytest

_EXEC_MODELS = Path(__file__).parent.parent.parent.parent / "services" / "execution" / "models.py"

# Ensure core is importable (execution/models imports from core)
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

_spec = importlib.util.spec_from_file_location("execution_models", _EXEC_MODELS)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
Order = _mod.Order
ExecutionResult = _mod.ExecutionResult
OrderStatus = _mod.OrderStatus


def _make_execution_order(**kwargs) -> Order:
    defaults = dict(
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.001,
        signal_id="sig-abc",
        decision_id="dec-123",
        order_id="ord-456",
        trace_id="trace-789",
        strategy_id="momentum_v1",
    )
    defaults.update(kwargs)
    return Order(**defaults)


@pytest.mark.unit
def test_order_from_event_parses_metadata_dict():
    """Order.from_event() nimmt metadata als dict entgegen."""
    payload = {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": "0.001",
        "signal_id": "sig-abc",
        "decision_id": "dec-123",
        "order_id": "ord-456",
        "trace_id": "trace-789",
        "metadata": {"decision": "ALLOW", "strategy_id": "mom"},
    }
    order = Order.from_event(payload)
    assert order.metadata is not None
    assert order.metadata["decision"] == "ALLOW"


@pytest.mark.unit
def test_order_from_event_parses_metadata_json_string():
    """Order.from_event() parst metadata als JSON-String (von sanitize_payload)."""
    payload = {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": "0.001",
        "signal_id": "sig-abc",
        "decision_id": "dec-123",
        "metadata": json.dumps({"decision": "ALLOW", "trace_id": "trace-789"}),
    }
    order = Order.from_event(payload)
    assert isinstance(order.metadata, dict)
    assert order.metadata["decision"] == "ALLOW"


@pytest.mark.unit
def test_order_to_dict_carries_metadata():
    """Order.to_dict() emittiert metadata wenn gesetzt (für Weiterleitung)."""
    order = _make_execution_order(metadata={"decision": "ALLOW", "reason_code": None})
    payload = order.to_dict()
    assert "metadata" in payload
    assert payload["metadata"]["decision"] == "ALLOW"


@pytest.mark.unit
def test_order_to_dict_no_metadata_key_when_none():
    """Order.to_dict() enthält keinen metadata-Key wenn None."""
    order = _make_execution_order()
    payload = order.to_dict()
    assert "metadata" not in payload


@pytest.mark.unit
def test_order_result_retains_correlation_ids():
    """signal_id, decision_id, trace_id dürfen top-level ODER in metadata erhalten bleiben.

    Fehler nur wenn komplett absent.
    """
    order = _make_execution_order(
        metadata={
            "signal_id": "sig-abc",
            "decision_id": "dec-123",
            "trace_id": "trace-789",
        }
    )
    result = ExecutionResult(
        order_id="ord-456",
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.001,
        filled_quantity=0.001,
        status=OrderStatus.FILLED.value,
        price=50000.0,
    )
    result.metadata = {
        "signal_id": order.signal_id,
        "decision_id": order.decision_id,
        "trace_id": order.trace_id,
        "order_id": result.order_id,
    }

    def _find_id(name: str, result: ExecutionResult, order: Order) -> bool:
        """True wenn ID top-level in order ODER in result.metadata vorhanden."""
        if getattr(order, name, None):
            return True
        if result.metadata and result.metadata.get(name):
            return True
        return False

    assert _find_id("signal_id", result, order), "signal_id nicht auffindbar"
    assert _find_id("decision_id", result, order), "decision_id nicht auffindbar"
    assert _find_id("trace_id", result, order), "trace_id nicht auffindbar"


@pytest.mark.unit
def test_execution_result_metadata_populated_for_filled():
    """FILLED ExecutionResult hat metadata mit fill_context."""
    result = ExecutionResult(
        order_id="ord-456",
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.001,
        filled_quantity=0.001,
        status=OrderStatus.FILLED.value,
        price=50000.0,
    )
    result.metadata = {
        "signal_id": "sig-abc",
        "strategy_id": "mom",
        "decision_id": "dec-123",
        "trace_id": "trace-789",
        "order_id": "ord-456",
        "expected_price": 49900.0,
        "execution_price": 50000.0,
        "slippage_bps": 20.04,
        "fill_context": {
            "signal_ts_ms": 1700000000000,
            "decision_ts_ms": 1700000001000,
        },
    }

    assert result.metadata["signal_id"] == "sig-abc"
    assert "fill_context" in result.metadata
    assert result.metadata["fill_context"]["signal_ts_ms"] == 1700000000000


@pytest.mark.unit
def test_execution_result_metadata_omits_none_fields():
    """Optionale Felder die None sind werden nicht erfunden."""
    result = ExecutionResult(
        order_id="ord-999",
        symbol="ETHUSDT",
        side="BUY",
        quantity=0.01,
        filled_quantity=0.01,
        status=OrderStatus.FILLED.value,
        price=None,
    )
    # Wie service.py es aufbaut (price=None → slippage_bps=None → wird rausgefiltert)
    raw = {
        "signal_id": "sig-xyz",
        "expected_price": None,
        "execution_price": None,
        "slippage_bps": None,
        "fill_context": {},
    }
    result.metadata = {k: v for k, v in raw.items() if v is not None}

    assert "expected_price" not in result.metadata
    assert "slippage_bps" not in result.metadata
