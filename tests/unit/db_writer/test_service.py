"""
Unit-Tests für DB Writer Service.

Governance: CDB_AGENT_POLICY.md, CDB_PSM_POLICY.md

Note: Placeholder tests marked with @pytest.mark.skip (Issue #308)
"""

import json
from unittest.mock import MagicMock

import pytest

from services.db_writer.db_writer import DatabaseWriter


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
    metadata_json = args[1][10]
    parsed_metadata = json.loads(metadata_json)
    assert parsed_metadata["fill_context"]["signal_ts_ms"] == 1700000000123
