"""
Contract Validation Tests - Issue #356
Tests für Canonical Message Contracts (market_data, signal)
"""

import json
import pytest
from pathlib import Path
from jsonschema import validate, ValidationError, Draft7Validator

# Contract paths
CONTRACTS_DIR = Path(__file__).parent.parent.parent.parent / "docs" / "contracts"
EXAMPLES_DIR = CONTRACTS_DIR / "examples"

MARKET_DATA_SCHEMA = CONTRACTS_DIR / "market_data.schema.json"
SIGNAL_SCHEMA = CONTRACTS_DIR / "signal.schema.json"

MARKET_DATA_VALID = EXAMPLES_DIR / "market_data_valid.json"
MARKET_DATA_INVALID = EXAMPLES_DIR / "market_data_invalid.json"
SIGNAL_VALID = EXAMPLES_DIR / "signal_valid.json"
SIGNAL_INVALID = EXAMPLES_DIR / "signal_invalid.json"


def load_json(path: Path) -> dict | list:
    """Load JSON file"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class TestMarketDataContract:
    """Tests für market_data.schema.json"""

    @pytest.fixture
    def schema(self):
        """Load market_data schema"""
        return load_json(MARKET_DATA_SCHEMA)

    def test_schema_exists(self, schema):
        """Schema file muss existieren und valides JSON sein"""
        assert schema is not None
        assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
        assert schema["title"] == "Market Data Message Contract"

    def test_schema_required_fields(self, schema):
        """Required fields müssen definiert sein"""
        required = schema["required"]
        assert "schema_version" in required
        assert "source" in required
        assert "symbol" in required
        assert "ts_ms" in required
        assert "price" in required
        assert "trade_qty" in required
        assert "side" in required

    def test_schema_no_additional_properties(self, schema):
        """additionalProperties muss false sein (strict contract)"""
        assert schema["additionalProperties"] is False

    def test_valid_examples(self, schema):
        """Alle valid examples müssen gegen Schema validieren"""
        examples = load_json(MARKET_DATA_VALID)
        validator = Draft7Validator(schema)

        for example in examples:
            payload = example["payload"]
            errors = list(validator.iter_errors(payload))
            assert len(errors) == 0, (
                f"Valid example '{example['description']}' failed validation: "
                f"{errors[0].message if errors else 'unknown error'}"
            )

    def test_invalid_examples(self, schema):
        """Alle invalid examples müssen fehlschlagen"""
        examples = load_json(MARKET_DATA_INVALID)
        validator = Draft7Validator(schema)

        for example in examples:
            payload = example["payload"]
            errors = list(validator.iter_errors(payload))
            assert len(errors) > 0, (
                f"Invalid example '{example['description']}' should have failed but passed"
            )

    def test_qty_field_rejected(self, schema):
        """Legacy 'qty' field muss rejected werden (migration zu trade_qty)"""
        payload = {
            "schema_version": "v1.0",
            "source": "mexc",
            "symbol": "BTCUSDT",
            "ts_ms": 1735574400000,
            "price": "50000.50",
            "qty": "1.5",  # LEGACY, sollte fehlschlagen
            "side": "buy"
        }

        validator = Draft7Validator(schema)
        errors = list(validator.iter_errors(payload))
        # Muss fehlschlagen wegen: missing 'trade_qty' + additionalProperty 'qty'
        assert len(errors) >= 1

    def test_price_must_be_string(self, schema):
        """Price muss String sein (Precision-Erhaltung)"""
        payload = {
            "schema_version": "v1.0",
            "source": "mexc",
            "symbol": "BTCUSDT",
            "ts_ms": 1735574400000,
            "price": 50000.50,  # NUMBER statt STRING
            "trade_qty": "1.5",
            "side": "buy"
        }

        validator = Draft7Validator(schema)
        errors = list(validator.iter_errors(payload))
        assert len(errors) > 0


class TestSignalContract:
    """Tests für signal.schema.json"""

    @pytest.fixture
    def schema(self):
        """Load signal schema"""
        return load_json(SIGNAL_SCHEMA)

    def test_schema_exists(self, schema):
        """Schema file muss existieren und valides JSON sein"""
        assert schema is not None
        assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
        assert schema["title"] == "Trading Signal Message Contract"

    def test_schema_required_fields(self, schema):
        """Required fields müssen definiert sein"""
        required = schema["required"]
        assert "schema_version" in required
        assert "signal_id" in required
        assert "strategy_id" in required
        assert "symbol" in required
        assert "side" in required
        assert "timestamp" in required

    def test_schema_no_additional_properties(self, schema):
        """additionalProperties muss false sein (strict contract)"""
        assert schema["additionalProperties"] is False

    def test_valid_examples(self, schema):
        """Alle valid examples müssen gegen Schema validieren"""
        examples = load_json(SIGNAL_VALID)
        validator = Draft7Validator(schema)

        for example in examples:
            payload = example["payload"]
            errors = list(validator.iter_errors(payload))
            assert len(errors) == 0, (
                f"Valid example '{example['description']}' failed validation: "
                f"{errors[0].message if errors else 'unknown error'}"
            )

    def test_invalid_examples(self, schema):
        """Alle invalid examples müssen fehlschlagen"""
        examples = load_json(SIGNAL_INVALID)
        validator = Draft7Validator(schema)

        for example in examples:
            payload = example["payload"]
            errors = list(validator.iter_errors(payload))
            assert len(errors) > 0, (
                f"Invalid example '{example['description']}' should have failed but passed"
            )

    def test_direction_field_rejected(self, schema):
        """Legacy 'direction' field muss rejected werden (migration zu 'side')"""
        payload = {
            "schema_version": "v1.0",
            "signal_id": "sig-001",
            "strategy_id": "momentum-v2",
            "symbol": "BTCUSDT",
            "direction": "BUY",  # LEGACY, sollte fehlschlagen
            "timestamp": 1735574400
        }

        validator = Draft7Validator(schema)
        errors = list(validator.iter_errors(payload))
        # Muss fehlschlagen wegen: missing 'side' + additionalProperty 'direction'
        assert len(errors) >= 1

    def test_side_must_be_uppercase(self, schema):
        """Signal side muss uppercase sein (BUY/SELL, nicht buy/sell)"""
        payload = {
            "schema_version": "v1.0",
            "signal_id": "sig-001",
            "strategy_id": "momentum-v2",
            "symbol": "BTCUSDT",
            "side": "buy",  # LOWERCASE (falsch)
            "timestamp": 1735574400
        }

        validator = Draft7Validator(schema)
        errors = list(validator.iter_errors(payload))
        assert len(errors) > 0

    def test_timestamp_must_be_integer(self, schema):
        """Timestamp muss integer sein (seconds), nicht float"""
        payload = {
            "schema_version": "v1.0",
            "signal_id": "sig-001",
            "strategy_id": "momentum-v2",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "timestamp": 1735574400.123  # FLOAT statt INTEGER
        }

        validator = Draft7Validator(schema)
        errors = list(validator.iter_errors(payload))
        assert len(errors) > 0

    def test_strength_range_validation(self, schema):
        """Strength muss zwischen 0.0 und 1.0 liegen"""
        # Test > 1.0
        payload_too_high = {
            "schema_version": "v1.0",
            "signal_id": "sig-001",
            "strategy_id": "momentum-v2",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "timestamp": 1735574400,
            "strength": 1.5  # > 1.0
        }

        validator = Draft7Validator(schema)
        errors = list(validator.iter_errors(payload_too_high))
        assert len(errors) > 0

        # Test < 0.0
        payload_too_low = {
            "schema_version": "v1.0",
            "signal_id": "sig-001",
            "strategy_id": "momentum-v2",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "timestamp": 1735574400,
            "strength": -0.1  # < 0.0
        }

        errors = list(validator.iter_errors(payload_too_low))
        assert len(errors) > 0


class TestContractEvolution:
    """Tests für Schema-Versionierung und Migration"""

    def test_market_data_schema_version(self):
        """market_data Schema version muss v1.0 sein"""
        schema = load_json(MARKET_DATA_SCHEMA)
        assert schema["properties"]["schema_version"]["const"] == "v1.0"

    def test_signal_schema_version(self):
        """signal Schema version muss v1.0 sein"""
        schema = load_json(SIGNAL_SCHEMA)
        assert schema["properties"]["schema_version"]["const"] == "v1.0"

    def test_migration_comment_exists(self):
        """Migration notes müssen in $comment dokumentiert sein"""
        market_data_schema = load_json(MARKET_DATA_SCHEMA)
        signal_schema = load_json(SIGNAL_SCHEMA)

        assert "$comment" in market_data_schema
        assert "qty" in market_data_schema["$comment"]  # qty→trade_qty migration

        assert "$comment" in signal_schema
        assert "direction" in signal_schema["$comment"]  # direction→side migration


class TestRuntimeMapping:
    """Runtime checks for contract-aligned payloads."""

    def test_market_data_from_dict_trade_qty(self):
        """MarketData.from_dict accepts trade_qty and maps to volume."""
        from services.signal.models import MarketData

        payload = {
            "schema_version": "v1.0",
            "source": "mexc",
            "symbol": "BTCUSDT",
            "ts_ms": 1735574400000,
            "price": "50000.50",
            "trade_qty": "1.5",
            "side": "buy",
        }

        market_data = MarketData.from_dict(payload)
        assert market_data.trade_qty == 1.5
        assert market_data.volume == 1.5

    def test_signal_to_dict_matches_schema(self):
        """Signal.to_dict output matches signal schema."""
        from services.signal.models import Signal

        schema = load_json(SIGNAL_SCHEMA)
        validator = Draft7Validator(schema)
        signal = Signal(
            signal_id="sig-20251230-btcusdt-001",
            strategy_id="momentum-v2",
            symbol="BTCUSDT",
            side="BUY",
            timestamp=1735574400,
            strength=0.85,
            confidence=0.92,
            price=50100.50,
            reason="Test signal",
        )

        payload = signal.to_dict()
        errors = list(validator.iter_errors(payload))
        assert len(errors) == 0, (
            f"Signal payload failed validation: {errors[0].message if errors else 'unknown error'}"
        )
