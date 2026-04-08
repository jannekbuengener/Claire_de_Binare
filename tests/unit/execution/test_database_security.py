import json
import pytest
from unittest.mock import MagicMock, patch
from services.execution.database import Database
from services.execution.models import ExecutionResult, OrderStatus


@pytest.fixture
def mock_db_config():
    with patch("services.execution.database.config") as mock_config:
        mock_config.DATABASE_URL = "postgresql://user:pass@host:5432/db"
        mock_config.SERVICE_NAME = "execution_service"
        yield mock_config


@patch("psycopg2.connect")
def test_save_trade_metadata_json_serialization(mock_connect, mock_db_config):
    # Setup mock connection and cursor
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn
    mock_cur = mock_conn.cursor.return_value.__enter__.return_value

    db = Database()

    # Create an ExecutionResult with a potentially problematic order_id
    result = ExecutionResult(
        order_id='test-uuid-123", "injected": "true',
        client_id="client-123",
        symbol="BTCUSDT",
        side="BUY",
        quantity=1.0,
        filled_quantity=1.0,
        price=50000.0,
        status=OrderStatus.FILLED.value,
        timestamp="2026-01-01T00:00:00Z",
        metadata={"signal_id": "sig-123"},
    )

    # Call save_trade
    success = db.save_trade(result)

    assert success is True

    # Verify that cur.execute was called with valid JSON
    # The 8th argument in the VALUES tuple is metadata
    args, kwargs = mock_cur.execute.call_args
    query_params = args[1]
    metadata_json = query_params[7]

    # Verify it's valid JSON and contains the full order_id
    parsed_metadata = json.loads(metadata_json)
    assert parsed_metadata["order_id"] == 'test-uuid-123", "injected": "true'
    assert parsed_metadata["signal_id"] == "sig-123"
    assert "injected" not in parsed_metadata or parsed_metadata["injected"] != "true"


@patch("psycopg2.connect")
def test_save_trade_preserves_fill_context_metadata(mock_connect, mock_db_config):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn
    mock_cur = mock_conn.cursor.return_value.__enter__.return_value

    db = Database()
    result = ExecutionResult(
        order_id="test-order-ctx",
        client_id="client-ctx",
        symbol="BTCUSDT",
        side="BUY",
        quantity=1.0,
        filled_quantity=1.0,
        price=50000.0,
        status=OrderStatus.FILLED.value,
        timestamp="2026-01-01T00:00:00Z",
        metadata={
            "fill_context": {
                "signal_ts_ms": 1700000000123,
                "decision_ts_ms": 1700000001123,
            }
        },
    )

    success = db.save_trade(result)

    assert success is True
    args, kwargs = mock_cur.execute.call_args
    query_params = args[1]
    metadata_json = query_params[7]
    parsed_metadata = json.loads(metadata_json)
    assert parsed_metadata["order_id"] == "test-order-ctx"
    assert parsed_metadata["fill_context"]["signal_ts_ms"] == 1700000000123


@patch("psycopg2.connect")
def test_save_order_updates_existing_order_row_and_merges_metadata(
    mock_connect, mock_db_config
):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn
    mock_cur = mock_conn.cursor.return_value.__enter__.return_value
    mock_cur.fetchone.side_effect = [(1,), (123,)]

    db = Database()
    result = ExecutionResult(
        order_id="exchange-1498-update",
        client_id="client-1498",
        symbol="BTCUSDT",
        side="BUY",
        quantity=1.0,
        filled_quantity=1.0,
        price=50000.0,
        status=OrderStatus.FILLED.value,
        timestamp="2026-01-01T00:00:00Z",
        metadata={
            "order_id": "ord-1498-update",
            "fill_context": {"signal_ts_ms": 1700000000123},
        },
    )

    success = db.save_order(result)

    assert success is True
    assert mock_cur.execute.call_count == 3
    update_query, update_params = mock_cur.execute.call_args_list[2][0]
    assert "UPDATE orders" in update_query
    assert "metadata = COALESCE(metadata, '{}'::jsonb) || %s::jsonb" in update_query
    assert update_params[8] == "ord-1498-update"
    parsed_metadata = json.loads(update_params[7])
    assert parsed_metadata["order_id"] == "ord-1498-update"
    assert parsed_metadata["exchange_order_id"] == "exchange-1498-update"
    assert parsed_metadata["fill_context"]["signal_ts_ms"] == 1700000000123


@patch("psycopg2.connect")
def test_save_order_skips_when_no_canonical_order_row_exists(
    mock_connect, mock_db_config, caplog
):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn
    mock_cur = mock_conn.cursor.return_value.__enter__.return_value
    mock_cur.fetchone.side_effect = [(1,), None]

    db = Database()
    result = ExecutionResult(
        order_id="exchange-miss-1",
        client_id="client-miss-1",
        symbol="BTCUSDT",
        side="BUY",
        quantity=1.0,
        filled_quantity=0.0,
        price=None,
        status=OrderStatus.REJECTED.value,
        timestamp="2026-01-01T00:00:00Z",
        metadata={"order_id": "ord-miss-1"},
    )

    with caplog.at_level("WARNING"):
        success = db.save_order(result)

    assert success is False
    assert mock_cur.execute.call_count == 3
    update_query, update_params = mock_cur.execute.call_args_list[2][0]
    assert "UPDATE orders" in update_query
    assert update_params[8] == "ord-miss-1"
    assert "no existing order row found" in caplog.text


@patch("psycopg2.connect")
def test_save_order_skips_when_canonical_order_id_missing_even_if_exchange_id_exists(
    mock_connect, mock_db_config, caplog
):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn
    mock_cur = mock_conn.cursor.return_value.__enter__.return_value
    mock_cur.fetchone.side_effect = [(1,)]

    db = Database()
    result = ExecutionResult(
        order_id="exchange-only-1",
        client_id="client-exchange-only-1",
        symbol="BTCUSDT",
        side="BUY",
        quantity=1.0,
        filled_quantity=0.0,
        price=None,
        status=OrderStatus.REJECTED.value,
        timestamp="2026-01-01T00:00:00Z",
        metadata={"exchange": "mock"},
    )

    with caplog.at_level("WARNING"):
        success = db.save_order(result)

    assert success is False
    assert mock_cur.execute.call_count == 2
    assert "missing canonical order_id" in caplog.text
