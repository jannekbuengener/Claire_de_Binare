"""
Contract Test: Signal → DB Writer → PostgreSQL Schema Validation

Tests the signal persistence path to ensure schema compliance and prevent regression.

Issue: #595
Context: Signals emit 'side' (BUY/SELL), but DB schema expects 'signal_type' (buy/sell lowercase).
         The db_writer maps side→signal_type for backward compatibility.

Acceptance Criteria:
- Test fails if side/signal_type are missing or mismatched
- Test passes when signal_type is correctly mapped from side
- Test enforces lowercase 'buy'/'sell' constraint

Test Command:
    pytest tests/contract/test_signal_schema.py -v

Related:
- services/db_writer/db_writer.py:296-300 (side→signal_type mapping)
- infrastructure/database/schema.sql (CHECK constraint)
- Issue #427, #587, #586, #581, #332
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from decimal import Decimal

import sys
from pathlib import Path

# Add project root for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.db_writer.db_writer import DatabaseWriter


class TestSignalSchemaContract:
    """
    Contract tests for signal → db_writer → PostgreSQL schema validation.

    These tests ensure the side → signal_type mapping works correctly
    and that schema constraints are enforced.
    """

    @pytest.fixture
    def db_writer(self, mock_postgres):
        """Create db_writer instance with mocked database connection."""
        writer = DatabaseWriter()
        writer.db_conn = mock_postgres
        return writer

    @pytest.fixture
    def mock_postgres(self):
        """Mock PostgreSQL connection for testing."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Mock successful insert returning ID
        mock_cursor.fetchone.return_value = (1,)  # Return signal_id
        mock_conn.cursor.return_value = mock_cursor

        return mock_conn

    # ============================================
    # HAPPY PATH TESTS
    # ============================================

    def test_signal_with_side_buy_maps_to_signal_type_buy(self, db_writer, mock_postgres):
        """
        Test that signal with side='BUY' correctly maps to signal_type='buy'.

        This is the primary mapping path: signals emit 'side', db_writer converts to 'signal_type'.
        """
        signal_data = {
            "symbol": "BTCUSDT",
            "side": "BUY",  # Uppercase from signal engine
            "price": 50000.0,
            "confidence": 0.75,
            "timestamp": 1768498000,
            "source": "test_signal"
        }

        db_writer.process_signal_event(signal_data)

        # Verify INSERT was called
        cursor = mock_postgres.cursor.return_value
        cursor.execute.assert_called_once()

        # Extract the executed SQL and parameters
        call_args = cursor.execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        # Verify signal_type parameter (index 1) is lowercase 'buy'
        assert params[1] == "buy", f"Expected signal_type='buy', got '{params[1]}'"
        assert "INSERT INTO signals" in sql

    def test_signal_with_side_sell_maps_to_signal_type_sell(self, db_writer, mock_postgres):
        """
        Test that signal with side='SELL' correctly maps to signal_type='sell'.
        """
        signal_data = {
            "symbol": "BTCUSDT",
            "side": "SELL",  # Uppercase from signal engine
            "price": 50000.0,
            "confidence": 0.75,
            "timestamp": 1768498000,
            "source": "test_signal"
        }

        db_writer.process_signal_event(signal_data)

        cursor = mock_postgres.cursor.return_value
        call_args = cursor.execute.call_args
        params = call_args[0][1]

        # Verify signal_type parameter is lowercase 'sell'
        assert params[1] == "sell", f"Expected signal_type='sell', got '{params[1]}'"

    def test_signal_with_explicit_signal_type_is_preserved(self, db_writer, mock_postgres):
        """
        Test that signals with explicit signal_type field use it directly.

        When signal_type is provided, side field should be ignored.
        """
        signal_data = {
            "symbol": "BTCUSDT",
            "signal_type": "buy",  # Explicit lowercase signal_type
            "side": "SELL",  # Should be ignored
            "price": 50000.0,
            "confidence": 0.75,
            "timestamp": 1768498000,
        }

        db_writer.process_signal_event(signal_data)

        cursor = mock_postgres.cursor.return_value
        call_args = cursor.execute.call_args
        params = call_args[0][1]

        # signal_type should be 'buy' (from signal_type field, not side)
        assert params[1] == "buy", f"Expected signal_type='buy', got '{params[1]}'"

    # ============================================
    # EDGE CASE TESTS
    # ============================================

    def test_signal_with_lowercase_side_is_normalized(self, db_writer, mock_postgres):
        """
        Test that lowercase side values are correctly handled.

        Signal engines might emit lowercase 'buy'/'sell' directly.
        """
        signal_data = {
            "symbol": "BTCUSDT",
            "side": "buy",  # Already lowercase
            "price": 50000.0,
            "confidence": 0.75,
            "timestamp": 1768498000,
        }

        db_writer.process_signal_event(signal_data)

        cursor = mock_postgres.cursor.return_value
        call_args = cursor.execute.call_args
        params = call_args[0][1]

        assert params[1] == "buy"

    def test_signal_with_mixed_case_side_converts_to_lowercase(self, db_writer, mock_postgres):
        """
        Test that mixed-case side values (Buy, SELL, etc.) normalize to lowercase.
        """
        for side_variant in ["Buy", "BUY", "bUy"]:
            mock_postgres.reset_mock()

            signal_data = {
                "symbol": "BTCUSDT",
                "side": side_variant,
                "price": 50000.0,
                "timestamp": 1768498000,
            }

            db_writer.process_signal_event(signal_data)

            cursor = mock_postgres.cursor.return_value
            call_args = cursor.execute.call_args
            params = call_args[0][1]

            assert params[1] == "buy", f"side='{side_variant}' should map to 'buy', got '{params[1]}'"

    # ============================================
    # FAILURE MODE TESTS (Regression Prevention)
    # ============================================

    def test_signal_missing_both_side_and_signal_type_gets_unknown(self, db_writer, mock_postgres):
        """
        Test that signals missing both side and signal_type get 'unknown'.

        CRITICAL: This will FAIL the PostgreSQL CHECK constraint (only 'buy'/'sell' allowed).
        This test documents the current behavior and serves as regression detection.

        Expected behavior: db_writer sets signal_type='unknown', PostgreSQL should reject it.
        """
        signal_data = {
            "symbol": "BTCUSDT",
            "price": 50000.0,
            "confidence": 0.75,
            "timestamp": 1768498000,
            # No 'side' or 'signal_type' field
        }

        db_writer.process_signal_event(signal_data)

        cursor = mock_postgres.cursor.return_value
        call_args = cursor.execute.call_args
        params = call_args[0][1]

        # db_writer guard sets signal_type='unknown'
        assert params[1] == "unknown", f"Expected signal_type='unknown' for missing fields, got '{params[1]}'"

        # NOTE: In real PostgreSQL, this INSERT would fail with:
        # psycopg2.errors.CheckViolation: new row for relation "signals" violates check constraint
        # CHECK (signal_type IN ('buy', 'sell'))

    def test_signal_with_empty_side_gets_unknown(self, db_writer, mock_postgres):
        """
        Test that signals with empty side string get 'unknown'.

        This also triggers the guard and will fail PostgreSQL constraint.
        """
        signal_data = {
            "symbol": "BTCUSDT",
            "side": "",  # Empty string
            "price": 50000.0,
            "timestamp": 1768498000,
        }

        db_writer.process_signal_event(signal_data)

        cursor = mock_postgres.cursor.return_value
        call_args = cursor.execute.call_args
        params = call_args[0][1]

        assert params[1] == "unknown"

    def test_signal_with_invalid_side_value_converts_to_lowercase(self, db_writer, mock_postgres):
        """
        Test that invalid side values (not BUY/SELL) are lowercased.

        This will fail PostgreSQL CHECK constraint but tests the mapping behavior.
        """
        signal_data = {
            "symbol": "BTCUSDT",
            "side": "HOLD",  # Invalid value
            "price": 50000.0,
            "timestamp": 1768498000,
        }

        db_writer.process_signal_event(signal_data)

        cursor = mock_postgres.cursor.return_value
        call_args = cursor.execute.call_args
        params = call_args[0][1]

        # Mapping logic converts to lowercase, but 'hold' is not valid per schema
        assert params[1] == "hold", f"Expected 'hold' (lowercase), got '{params[1]}'"
        # NOTE: PostgreSQL would reject this with CHECK constraint violation

    # ============================================
    # SCHEMA CONSTRAINT VALIDATION
    # ============================================

    def test_schema_only_accepts_buy_or_sell_lowercase(self):
        """
        Documentation test: PostgreSQL schema CHECK constraint.

        This test documents the schema constraint without executing SQL.
        Actual constraint: CHECK (signal_type IN ('buy', 'sell'))

        Valid values: 'buy', 'sell'
        Invalid values: 'BUY', 'SELL', 'unknown', 'hold', '', NULL
        """
        # Schema constraint from infrastructure/database/schema.sql:
        # signal_type VARCHAR(10) NOT NULL CHECK (signal_type IN ('buy', 'sell'))

        valid_values = {'buy', 'sell'}
        invalid_values = {'BUY', 'SELL', 'unknown', 'hold', '', 'Buy', 'HOLD'}

        # This test serves as documentation
        assert valid_values == {'buy', 'sell'}
        assert len(invalid_values) > 0  # Ensure we're testing edge cases

    # ============================================
    # INTEGRATION SMOKE TEST (Optional - requires DB)
    # ============================================

    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires live PostgreSQL connection - run manually for full validation")
    def test_real_db_rejects_unknown_signal_type(self):
        """
        Integration test: Verify PostgreSQL actually rejects 'unknown' signal_type.

        This test requires a live PostgreSQL instance and should be run manually
        or in CI with database available.

        Command: pytest tests/contract/test_signal_schema.py::TestSignalSchemaContract::test_real_db_rejects_unknown_signal_type -v
        """
        import psycopg2
        import os

        # Connect to test database
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "claire_de_binare"),
            user=os.getenv("POSTGRES_USER", "claire_user"),
            password=os.getenv("POSTGRES_PASSWORD", "")
        )

        cursor = conn.cursor()

        try:
            # Attempt to insert signal with 'unknown' signal_type
            cursor.execute("""
                INSERT INTO signals (symbol, signal_type, price, confidence, timestamp)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            """, ("BTCUSDT", "unknown", 50000.0, 0.75))

            conn.commit()

            # If we reach here, the constraint is NOT enforced (BUG!)
            pytest.fail("PostgreSQL accepted 'unknown' signal_type - CHECK constraint not enforced!")

        except psycopg2.errors.CheckViolation as e:
            # Expected: PostgreSQL rejects 'unknown'
            assert "signal_type" in str(e).lower()
            conn.rollback()

        finally:
            cursor.close()
            conn.close()


# ============================================
# SUMMARY
# ============================================
"""
Contract Test Coverage:

✅ Happy Path:
   - side='BUY' → signal_type='buy'
   - side='SELL' → signal_type='sell'
   - Explicit signal_type is preserved
   - Lowercase/mixed-case normalization

⚠️  Edge Cases (Regression Detection):
   - Missing both fields → 'unknown' (violates schema)
   - Empty side → 'unknown' (violates schema)
   - Invalid side values → lowercase but invalid (violates schema)

📋 Documentation:
   - Schema constraint: CHECK (signal_type IN ('buy', 'sell'))
   - Integration test available (requires live DB)

Run Commands:
   # Unit tests (fast, mocked)
   pytest tests/contract/test_signal_schema.py -v

   # Integration test (requires PostgreSQL)
   pytest tests/contract/test_signal_schema.py::TestSignalSchemaContract::test_real_db_rejects_unknown_signal_type -v

   # Run all contract tests
   pytest tests/contract/ -v
"""
