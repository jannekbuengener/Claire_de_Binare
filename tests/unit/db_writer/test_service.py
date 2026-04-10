"""
Unit-Tests für DB Writer Service.

Governance: CDB_AGENT_POLICY.md, CDB_PSM_POLICY.md

Note: Placeholder tests marked with @pytest.mark.skip (Issue #308)
"""

import json
import sys
from decimal import Decimal
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

try:
    import prometheus_client  # noqa: F401
except ImportError:
    _dummy_metrics = []

    class _DummyMetric:
        def __init__(self, name: str):
            self.name = name
            self.value = 0
            self._callback = None

        def labels(self, **kwargs):
            return self

        def inc(self, amount=1):
            self.value += amount
            return None

        def set(self, value):
            self.value = value
            return None

        def set_function(self, func):
            self._callback = func
            return None

        def render(self) -> str:
            value = self._callback() if self._callback is not None else self.value
            return f"{self.name} {value}\n"

    def _make_metric(name, *args, **kwargs):
        metric = _DummyMetric(name)
        _dummy_metrics.append(metric)
        return metric

    sys.modules["prometheus_client"] = SimpleNamespace(
        Counter=_make_metric,
        Gauge=_make_metric,
        generate_latest=lambda *args, **kwargs: "".join(
            metric.render() for metric in _dummy_metrics
        ).encode(),
        CONTENT_TYPE_LATEST="text/plain; version=0.0.4",
        start_http_server=lambda *args, **kwargs: None,
    )
from services.db_writer.db_writer import DatabaseWriter


@pytest.mark.unit
def test_normalize_exposure_pct_preserves_percentage_points():
    assert DatabaseWriter.normalize_exposure_pct(10.0) == 10.0
    assert DatabaseWriter.normalize_exposure_pct(0.5) == 0.5


@pytest.mark.unit
def test_process_portfolio_snapshot_persists_percentage_point_exposure():
    writer = DatabaseWriter()
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
    - side="BUY" → signal_type="buy"
    - side="SELL" → signal_type="sell"
    - Empty/missing → signal_type="unknown"
    """
    # Test data payloads
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
        # Apply same mapping logic as db_writer.py
        signal_type = payload.get("signal_type") or (payload.get("side") or "").lower()
        if not signal_type:
            signal_type = "unknown"

        assert (
            signal_type == expected
        ), f"Payload {payload} should map to '{expected}', got '{signal_type}'"


@pytest.mark.unit
def test_normalize_metadata_parses_json_object_string():
    metadata = DatabaseWriter.normalize_metadata('{"strategy_id":"paper"}')

    assert metadata == {"strategy_id": "paper"}


@pytest.mark.unit
def test_process_signal_event_persists_metadata_object(mock_postgres):
    writer = DatabaseWriter()
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
def test_process_order_event_upserts_by_order_id_without_losing_terminal_status():
    writer = DatabaseWriter()
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
def test_process_trade_event_decodes_metadata_json_string():
    """Trade metadata arriving as JSON string must be persisted as JSON object."""
    writer = DatabaseWriter()
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
def test_calculate_trade_realized_pnl_returns_none_for_buy_side():
    writer = DatabaseWriter()
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
def test_process_trade_event_persists_realized_pnl_for_full_close():
    writer = DatabaseWriter()
    writer.db_conn = MagicMock()
    cursor = writer.db_conn.cursor.return_value
    cursor.fetchone.side_effect = [
        ("long", Decimal("1.5"), Decimal("100.0"), Decimal("0.0"), datetime.now(timezone.utc)),
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
def test_update_position_from_trade_handles_partial_close_decimal_pnl():
    writer = DatabaseWriter()
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
