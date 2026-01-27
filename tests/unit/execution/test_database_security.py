
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
        timestamp="2026-01-01T00:00:00Z"
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
    assert "injected" not in parsed_metadata or parsed_metadata["injected"] != "true"
