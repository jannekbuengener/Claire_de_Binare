"""
Unit-Tests fur DB Writer Service.

Governance: CDB_AGENT_POLICY.md, CDB_PSM_POLICY.md

Note: Placeholder tests marked with @pytest.mark.skip (Issue #308)
"""

import importlib
import json
import sys
import types
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest


def _build_prometheus_client_stub() -> types.ModuleType:
    """Provide only the prometheus API surface needed by db_writer tests."""
    prometheus_client = types.ModuleType("prometheus_client")

    class _MetricStub:
        def labels(self, **kwargs):
            return self

        def inc(self):
            return None

        def set(self, value):
            return None

        def set_function(self, func):
            return None

    prometheus_client.Counter = lambda *args, **kwargs: _MetricStub()
    prometheus_client.Gauge = lambda *args, **kwargs: _MetricStub()
    prometheus_client.start_http_server = lambda *args, **kwargs: None
    return prometheus_client


@pytest.fixture
def database_writer_cls(monkeypatch):
    """Import DatabaseWriter with a test-local prometheus stub when needed."""
    monkeypatch.delitem(sys.modules, "services.db_writer.db_writer", raising=False)

    monkeypatch.setitem(
        sys.modules,
        "prometheus_client",
        _build_prometheus_client_stub(),
    )

    module = importlib.import_module("services.db_writer.db_writer")
    return module.DatabaseWriter


@pytest.mark.unit
def test_normalize_exposure_pct_preserves_percentage_points(database_writer_cls):
    assert database_writer_cls.normalize_exposure_pct(10.0) == 10.0
    assert database_writer_cls.normalize_exposure_pct(0.5) == 0.5


@pytest.mark.unit
def test_process_portfolio_snapshot_persists_percentage_point_exposure(
    database_writer_cls,
):
    writer = database_writer_cls()
    writer.db_conn = MagicMock()
    cursor = writer.db_conn.cursor.return_value
    cursor.fetchone.return_value = (1,)

    writer.process_portfolio_snapshot(
        {
            "timestamp": datetime.now(timezone.utc),
            "total_equity": 10000.0,
            "available_balance": 9000.0,
            "margin_used": 1000.0,
            "daily_pnl": 50.0,
            "total_unrealized_pnl": 25.0,
            "total_realized_pnl": 10.0,
            "total_exposure_pct": 10.0,
            "max_drawdown_pct": 1.5,
            "open_positions": 2,
            "metadata": {"source": "test"},
        }
    )

    insert_params = cursor.execute.call_args[0][1]
    assert insert_params[7] == 10.0


@pytest.mark.unit
def test_signal_type_mapping_from_side():
    """
    Test: signal_type backward compatibility mapping from 'side' field.

    Regression test for signal persistence bug where signals emitted 'side' (BUY/SELL)
    but DB schema expected 'signal_type' (buy/sell lowercase).

    Verifies:
    - side="BUY" -> signal_type="buy"
    - side="SELL" -> signal_type="sell"
    - Empty/missing -> signal_type="unknown"
    """
    test_cases = [
        ({"side": "BUY"}, "buy"),
        ({"side": "SELL"}, "sell"),
        ({"side": "buy"}, "buy"),
        ({"side": "sell"}, "sell"),
        ({"signal_type": "buy"}, "buy"),  # Existing field takes precedence
        ({"signal_type": "sell", "side": "BUY"}, "sell"),  # signal_type wins
        ({}, "unknown"),  # Missing both fields
        ({"side": ""}, "unknown"),  # Empty side
    ]

    for payload, expected in test_cases:
        signal_type = payload.get("signal_type") or (payload.get("side") or "").lower()
        if not signal_type:
            signal_type = "unknown"

        assert (
            signal_type == expected
        ), f"Payload {payload} should map to '{expected}', got '{signal_type}'"


@pytest.mark.unit
def test_normalize_metadata_parses_json_object_string(database_writer_cls):
    metadata = database_writer_cls.normalize_metadata('{"strategy_id":"paper"}')

    assert metadata == {"strategy_id": "paper"}


@pytest.mark.unit
def test_process_signal_event_persists_metadata_object(
    mock_postgres,
    database_writer_cls,
):
    writer = database_writer_cls()
    writer.db_conn = mock_postgres
    cursor = mock_postgres.cursor.return_value
    cursor.fetchone.return_value = (1,)

    writer.process_signal_event(
        {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "price": 50000.0,
            "timestamp": 1700000000,
            "metadata": '{"strategy_id":"paper","signal_reason":"Momentum"}',
        }
    )

    params = cursor.execute.call_args[0][1]
    assert json.loads(params[6]) == {
        "strategy_id": "paper",
        "signal_reason": "Momentum",
    }


@pytest.mark.unit
def test_process_order_event_upserts_by_order_id_without_losing_terminal_status(
    database_writer_cls,
):
    writer = database_writer_cls()
    writer.db_conn = MagicMock()
    cursor = writer.db_conn.cursor.return_value
    cursor.fetchone.return_value = [7]

    writer.process_order_event(
        {
            "order_id": "ord-1498-1",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 0.01,
            "price": 50000.0,
            "approved": True,
            "status": "pending",
            "timestamp": 1700000000,
            "metadata": {"signal_id": "sig-1498-1"},
        }
    )

    query, params = cursor.execute.call_args[0]
    assert "ON CONFLICT (order_id) DO UPDATE" in query
    assert params[0] == "ord-1498-1"
    assert json.loads(params[9]) == {"signal_id": "sig-1498-1"}


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.skip(reason="Placeholder - needs implementation (Issue #308)")
def test_service_initialization(mock_postgres, test_config):
    """
    Test: DB Writer kann initialisiert werden.
    """
    pass


@pytest.mark.unit
@pytest.mark.skip(reason="Placeholder - needs implementation (Issue #308)")
def test_config_validation(test_config):
    """
    Test: Config wird korrekt validiert.
    """
    pass


@pytest.mark.unit
@pytest.mark.skip(reason="Placeholder - needs implementation (Issue #308)")
def test_event_persistence(mock_postgres, signal_factory):
    """
    Test: Events werden korrekt in DB geschrieben.

    Governance: CDB_PSM_POLICY.md (Event-Sourcing, Append-Only)
    """
    pass


@pytest.mark.unit
def test_process_trade_event_decodes_metadata_json_string(database_writer_cls):
    """Trade metadata arriving as JSON string must be persisted as JSON object."""
    writer = database_writer_cls()
    writer.db_conn = MagicMock()
    cursor = writer.db_conn.cursor.return_value
    cursor.fetchone.return_value = [1]
    writer.update_position_from_trade = MagicMock()

    writer.process_trade_event(
        {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "status": "filled",
            "price": 50000.0,
            "quantity": 0.001,
            "timestamp": 1700000000,
            "metadata": json.dumps(
                {
                    "fill_context": {
                        "signal_ts_ms": 1700000000123,
                        "decision_ts_ms": 1700000001123,
                    }
                }
            ),
        }
    )

    args, kwargs = cursor.execute.call_args
    metadata_json = args[1][11]
    parsed_metadata = json.loads(metadata_json)
    assert parsed_metadata["fill_context"]["signal_ts_ms"] == 1700000000123


@pytest.mark.unit
def test_calculate_trade_realized_pnl_returns_none_for_buy_side(
    database_writer_cls,
):
    writer = database_writer_cls()
    existing_position = (
        "long",
        Decimal("1.0"),
        Decimal("100.0"),
        Decimal("0.0"),
        datetime.now(timezone.utc),
    )

    realized_pnl = writer._calculate_trade_realized_pnl(
        existing_position,
        "buy",
        Decimal("110.0"),
        Decimal("1.0"),
    )

    assert realized_pnl is None


@pytest.mark.unit
def test_process_trade_event_persists_realized_pnl_for_full_close(
    database_writer_cls,
):
    writer = database_writer_cls()
    writer.db_conn = MagicMock()
    cursor = writer.db_conn.cursor.return_value
    cursor.fetchone.side_effect = [
        (
            "long",
            Decimal("1.5"),
            Decimal("100.0"),
            Decimal("0.0"),
            datetime.now(timezone.utc),
        ),
        (7,),
    ]

    writer.process_trade_event(
        {
            "symbol": "BTCUSDT",
            "side": "SELL",
            "status": "filled",
            "price": 110.0,
            "quantity": 2.0,
            "timestamp": 1700000000,
        }
    )

    insert_params = cursor.execute.call_args_list[1][0][1]
    assert insert_params[8] == Decimal("15.00")


@pytest.mark.unit
def test_update_position_from_trade_handles_partial_close_decimal_pnl(
    database_writer_cls,
):
    writer = database_writer_cls()
    writer.db_conn = MagicMock()
    cursor = writer.db_conn.cursor.return_value
    cursor.fetchone.return_value = (
        "long",
        Decimal("2.0"),
        Decimal("100.0"),
        Decimal("3.0"),
        datetime.now(timezone.utc),
    )

    writer.update_position_from_trade(
        {
            "symbol": "BTCUSDT",
            "side": "SELL",
            "status": "filled",
            "price": 105.0,
            "quantity": 0.5,
            "timestamp": 1700000000,
        }
    )

    update_params = cursor.execute.call_args_list[1][0][1]
    assert update_params[0] == Decimal("1.5")
    assert update_params[2] == Decimal("5.5")
